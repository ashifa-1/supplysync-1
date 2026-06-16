import datetime
import logging
from django.db import transaction
from django.core.cache import cache
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from apps.suppliers.models import Supplier
from apps.warehouses.models import Warehouse
from apps.accounts.models import User
from apps.products.models import Product
from apps.inventory.services import adjust_inventory
from core.exceptions import InvalidOperationException, ResourceNotFoundException, DuplicateResourceException
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class SelfApprovalNotAllowedException(PermissionDenied):
    status_code = 403
    default_code = 'SELF_APPROVAL_NOT_ALLOWED'
    default_detail = 'A purchase order cannot be approved by its creator.'

def create_purchase_order(data: dict, created_by_user_id: int) -> PurchaseOrder:
    supplier_id = data['supplier_id']
    warehouse_id = data['warehouse_id']
    expected_delivery_date = data.get('expected_delivery_date')
    notes = data.get('notes')
    items_data = data.get('items', [])

    try:
        creator = User.objects.get(id=created_by_user_id)
        supplier = Supplier.objects.get(id=supplier_id, is_deleted=False)
        warehouse = Warehouse.objects.get(id=warehouse_id, is_deleted=False)
    except (User.DoesNotExist, Supplier.DoesNotExist, Warehouse.DoesNotExist):
        raise ResourceNotFoundException("Supplier, Warehouse, or User not found.")

    # Generate daily sequence PO number: PO-<YYYYMMDD>-<4 digit sequence>
    today_str = datetime.date.today().strftime('%Y%m%d')
    redis_key = f"po-sequence:{today_str}"
    try:
        seq = cache.incr(redis_key)
    except ValueError:
        # Key does not exist, set initial value to 1 and TTL to 24 hours
        cache.set(redis_key, 1, timeout=86400)
        seq = 1

    po_number = f"PO-{today_str}-{seq:04d}"

    # Verify uniqueness in DB just in case
    if PurchaseOrder.objects.filter(po_number=po_number).exists():
        raise DuplicateResourceException(f"Purchase order with number {po_number} already exists.")

    with transaction.atomic():
        po = PurchaseOrder.objects.create(
            po_number=po_number,
            supplier=supplier,
            warehouse=warehouse,
            status=PurchaseOrderStatus.DRAFT,
            expected_delivery_date=expected_delivery_date,
            created_by=creator,
            notes=notes
        )

        total_amount = 0
        for item_data in items_data:
            product_id = item_data['product_id']
            qty = item_data['quantity_ordered']
            unit_price = item_data['unit_price']
            
            try:
                product = Product.objects.get(id=product_id, is_deleted=False)
            except Product.DoesNotExist:
                raise ResourceNotFoundException(f"Product ID {product_id} not found.")

            total_price = qty * unit_price
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=product,
                quantity_ordered=qty,
                quantity_received=0,
                unit_price=unit_price,
                total_price=total_price
            )
            total_amount += total_price

        po.total_amount = total_amount
        po.save()

    cache.delete('reports:dashboard')
    return po


def submit_purchase_order(po_id: int) -> PurchaseOrder:
    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase order not found.")

    if po.status != PurchaseOrderStatus.DRAFT:
        raise InvalidOperationException("Only DRAFT purchase orders can be submitted.")

    # Check if PO has at least one item
    if not po.items.exists():
        raise InvalidOperationException(
            detail="Purchase order must have at least one item before submission.",
            code="PO_HAS_NO_ITEMS"
        )

    po.status = PurchaseOrderStatus.PENDING_APPROVAL
    po.save()
    return po


def approve_purchase_order(po_id: int, approved_by_user_id: int) -> PurchaseOrder:
    try:
        po = PurchaseOrder.objects.get(id=po_id)
        approver = User.objects.get(id=approved_by_user_id)
    except (PurchaseOrder.DoesNotExist, User.DoesNotExist):
        raise ResourceNotFoundException("Purchase order or User not found.")

    if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise InvalidOperationException("Only PENDING_APPROVAL purchase orders can be approved.")

    if po.created_by == approver:
        raise SelfApprovalNotAllowedException()

    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by = approver
    po.save()
    return po


def receive_purchase_order(po_id: int, data: dict, performed_by_user_id: int) -> PurchaseOrder:
    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase order not found.")

    # Receipt can happen if order is APPROVED or partially received/ordered.
    # Wait, what are the allowed states? Approved or Ordered or Partially Received.
    if po.status not in [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.PARTIALLY_RECEIVED]:
        raise InvalidOperationException("Purchase order cannot be received in the current state.")

    items_receipt = data.get('items', [])
    actual_delivery_date = data.get('actual_delivery_date')

    with transaction.atomic():
        po_items = {item.id: item for item in po.items.all()}
        
        for receipt in items_receipt:
            po_item_id = receipt['po_item_id']
            qty_rec = receipt['quantity_received']

            if po_item_id not in po_items:
                raise ResourceNotFoundException(f"Purchase order item ID {po_item_id} does not belong to this PO.")

            po_item = po_items[po_item_id]
            max_allowed = po_item.quantity_ordered - po_item.quantity_received
            
            if qty_rec > max_allowed:
                raise InvalidOperationException(
                    f"Received quantity {qty_rec} exceeds the remaining allowed quantity {max_allowed} for item {po_item.product.sku}."
                )

            # Update item received quantity
            po_item.quantity_received += qty_rec
            po_item.save()

            # Call adjust_inventory with INBOUND transaction type
            adjust_inventory(
                data={
                    "product_id": po_item.product.id,
                    "warehouse_id": po.warehouse.id,
                    "transaction_type": "INBOUND",
                    "quantity": qty_rec,
                    "notes": f"Goods receipt for PO {po.po_number}"
                },
                performed_by_user_id=performed_by_user_id
            )

        # Re-fetch items from DB to check status
        items = list(po.items.all())
        all_fully_received = all(item.quantity_received == item.quantity_ordered for item in items)
        any_received = any(item.quantity_received > 0 for item in items)

        if all_fully_received:
            po.status = PurchaseOrderStatus.RECEIVED
        elif any_received:
            po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
        else:
            po.status = PurchaseOrderStatus.ORDERED

        if actual_delivery_date:
            po.actual_delivery_date = actual_delivery_date
            
        po.save()

    # Dispatch Celery task
    from apps.purchase_orders.tasks import process_purchase_order_received_event
    process_purchase_order_received_event.delay(
        po_id=po.id,
        received_by_user_id=performed_by_user_id
    )

    cache.delete('reports:dashboard')
    return po


def cancel_purchase_order(po_id: int, reason: str) -> PurchaseOrder:
    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        raise ResourceNotFoundException("Purchase order not found.")

    if po.status not in [PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING_APPROVAL, PurchaseOrderStatus.APPROVED]:
        raise InvalidOperationException(
            detail="Only DRAFT, PENDING_APPROVAL, or APPROVED purchase orders can be cancelled.",
            code="PO_CANCELLATION_NOT_ALLOWED"
        )

    po.status = PurchaseOrderStatus.CANCELLED
    if po.notes:
        po.notes += f"\nCancellation Reason: {reason}"
    else:
        po.notes = f"Cancellation Reason: {reason}"
    po.save()
    
    cache.delete('reports:dashboard')
    return po
