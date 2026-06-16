import datetime
import logging
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from apps.sales_orders.models import SalesOrder, SalesOrderItem, SalesOrderStatus
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from apps.accounts.models import User
from core.exceptions import (
    InsufficientStockForOrderException,
    ResourceNotFoundException,
    InvalidOperationException,
    DuplicateResourceException
)

logger = logging.getLogger(__name__)

def create_sales_order(data: dict, created_by_user_id: int) -> SalesOrder:
    warehouse_id = data['warehouse_id']
    customer_name = data['customer_name']
    customer_email = data['customer_email']
    customer_phone = data['customer_phone']
    shipping_address = data['shipping_address']
    notes = data.get('notes')
    items_data = data.get('items', [])

    try:
        creator = User.objects.get(id=created_by_user_id)
        warehouse = Warehouse.objects.get(id=warehouse_id, is_deleted=False)
    except (User.DoesNotExist, Warehouse.DoesNotExist):
        raise ResourceNotFoundException("Warehouse or User not found.")

    # Generate daily sequence order number: SO-<YYYYMMDD>-<4 digit sequence>
    today_str = datetime.date.today().strftime('%Y%m%d')
    redis_key = f"so-sequence:{today_str}"
    try:
        seq = cache.incr(redis_key)
    except ValueError:
        cache.set(redis_key, 1, timeout=86400)
        seq = 1

    order_number = f"SO-{today_str}-{seq:04d}"

    # Verify uniqueness in DB just in case
    if SalesOrder.objects.filter(order_number=order_number).exists():
        raise DuplicateResourceException(f"Sales order with number {order_number} already exists.")

    with transaction.atomic():
        # Lock Inventory records in warehouse in a sorted product_id order to prevent deadlocks
        product_ids = sorted([item['product_id'] for item in items_data])
        
        inventories = {}
        for p_id in product_ids:
            inv, created = Inventory.objects.select_for_update().get_or_create(
                product_id=p_id,
                warehouse_id=warehouse_id,
                defaults={'quantity_available': 0, 'quantity_reserved': 0, 'quantity_damaged': 0}
            )
            inventories[p_id] = inv

        # Check stock sufficiency
        short_items = []
        for item_data in items_data:
            p_id = item_data['product_id']
            qty = item_data['quantity']
            inv = inventories[p_id]
            
            if inv.quantity_available < qty:
                short_items.append({
                    "sku": inv.product.sku,
                    "requested_quantity": qty,
                    "available_quantity": inv.quantity_available
                })

        if short_items:
            raise InsufficientStockForOrderException(short_items=short_items)

        # Create SalesOrder in CONFIRMED status
        so = SalesOrder.objects.create(
            order_number=order_number,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            shipping_address=shipping_address,
            warehouse=warehouse,
            status=SalesOrderStatus.CONFIRMED,
            created_by=creator,
            notes=notes
        )

        total_amount = 0
        for item_data in items_data:
            p_id = item_data['product_id']
            qty = item_data['quantity']
            unit_price = item_data['unit_price']
            inv = inventories[p_id]

            # Reserve stock: increase reserved, decrease available
            inv.quantity_available -= qty
            inv.quantity_reserved += qty
            inv.save()

            total_price = qty * unit_price
            SalesOrderItem.objects.create(
                sales_order=so,
                product_id=p_id,
                quantity=qty,
                unit_price=unit_price,
                total_price=total_price
            )
            total_amount += total_price

        so.total_amount = total_amount
        so.save()

    # Invalidate cache
    cache.delete('inventory:low-stock')
    cache.delete('reports:dashboard')

    # Dispatch Celery event
    from apps.sales_orders.tasks import process_sales_order_created_event
    process_sales_order_created_event.delay(
        order_id=so.id,
        created_by_user_id=created_by_user_id
    )

    return so


def dispatch_sales_order(so_id: int) -> SalesOrder:
    try:
        so = SalesOrder.objects.get(id=so_id)
    except SalesOrder.DoesNotExist:
        raise ResourceNotFoundException("Sales order not found.")

    if so.status not in [SalesOrderStatus.CONFIRMED, SalesOrderStatus.PROCESSING]:
        raise InvalidOperationException("Only CONFIRMED or PROCESSING orders can be dispatched.")

    with transaction.atomic():
        so.status = SalesOrderStatus.DISPATCHED
        so.dispatched_at = timezone.now()
        so.save()

        # Update inventory and write outbound transaction records
        # Lock records first
        items = list(so.items.all())
        product_ids = sorted([item.product_id for item in items])
        
        inventories = {}
        for p_id in product_ids:
            inv = Inventory.objects.select_for_update().get(
                product_id=p_id,
                warehouse_id=so.warehouse_id
            )
            inventories[p_id] = inv

        for item in items:
            inv = inventories[item.product_id]
            
            # Decrease quantity_reserved (fulfilled reservation)
            inv.quantity_reserved -= item.quantity
            inv.save()

            # Create OUTBOUND transaction
            InventoryTransaction.objects.create(
                product=item.product,
                warehouse=so.warehouse,
                transaction_type=TransactionType.OUTBOUND,
                quantity=item.quantity,
                reference_id=so.order_number,
                performed_by=so.created_by,
                notes=f"Dispatch for Sales Order {so.order_number}"
            )

    cache.delete('reports:dashboard')
    return so


def deliver_sales_order(so_id: int) -> SalesOrder:
    try:
        so = SalesOrder.objects.get(id=so_id)
    except SalesOrder.DoesNotExist:
        raise ResourceNotFoundException("Sales order not found.")

    if so.status != SalesOrderStatus.DISPATCHED:
        raise InvalidOperationException("Only DISPATCHED orders can be marked as DELIVERED.")

    so.status = SalesOrderStatus.DELIVERED
    so.delivered_at = timezone.now()
    so.save()

    cache.delete('reports:dashboard')
    return so


def cancel_sales_order(so_id: int, reason: str) -> SalesOrder:
    try:
        so = SalesOrder.objects.get(id=so_id)
    except SalesOrder.DoesNotExist:
        raise ResourceNotFoundException("Sales order not found.")

    # Only PENDING and CONFIRMED orders can be cancelled.
    if so.status not in [SalesOrderStatus.PENDING, SalesOrderStatus.CONFIRMED]:
        raise InvalidOperationException("Only PENDING or CONFIRMED orders can be cancelled.")

    with transaction.atomic():
        # Release reserved inventory
        items = list(so.items.all())
        product_ids = sorted([item.product_id for item in items])

        inventories = {}
        for p_id in product_ids:
            inv = Inventory.objects.select_for_update().get(
                product_id=p_id,
                warehouse_id=so.warehouse_id
            )
            inventories[p_id] = inv

        for item in items:
            inv = inventories[item.product_id]
            # Release reservation: reverse quantity_available and quantity_reserved
            inv.quantity_available += item.quantity
            inv.quantity_reserved -= item.quantity
            inv.save()

        so.status = SalesOrderStatus.CANCELLED
        if so.notes:
            so.notes += f"\nCancellation Reason: {reason}"
        else:
            so.notes = f"Cancellation Reason: {reason}"
        so.save()

    # Dispatch Celery event
    from apps.sales_orders.tasks import process_sales_order_cancelled_event
    process_sales_order_cancelled_event.delay(order_id=so.id)

    # Invalidate cache
    cache.delete('inventory:low-stock')
    cache.delete('reports:dashboard')
    return so
