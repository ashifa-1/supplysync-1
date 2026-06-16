import uuid
import logging
from django.db import transaction, models
from django.core.cache import cache
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.products.models import Product
from apps.warehouses.models import Warehouse
from apps.accounts.models import User
from core.exceptions import InsufficientInventoryException, ResourceNotFoundException, InvalidOperationException
from core.constants import LOW_STOCK_CACHE_TTL

logger = logging.getLogger(__name__)

def adjust_inventory(data: dict, performed_by_user_id: int) -> InventoryTransaction:
    product_id = data['product_id']
    warehouse_id = data['warehouse_id']
    transaction_type = data['transaction_type']
    quantity = data['quantity']
    notes = data.get('notes')

    try:
        user = User.objects.get(id=performed_by_user_id)
        product = Product.objects.get(id=product_id, is_deleted=False)
        warehouse = Warehouse.objects.get(id=warehouse_id, is_deleted=False)
    except (User.DoesNotExist, Product.DoesNotExist, Warehouse.DoesNotExist):
        raise ResourceNotFoundException("Product, warehouse, or user not found.")

    with transaction.atomic():
        # Get or create inventory record with row-level lock
        inventory, created = Inventory.objects.select_for_update().get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={'quantity_available': 0, 'quantity_reserved': 0, 'quantity_damaged': 0}
        )

        orig_available = inventory.quantity_available
        orig_damaged = inventory.quantity_damaged

        if transaction_type == TransactionType.INBOUND:
            inventory.quantity_available += quantity
        elif transaction_type == TransactionType.OUTBOUND:
            if inventory.quantity_available < quantity:
                raise InsufficientInventoryException(
                    f"Insufficient inventory. Available: {inventory.quantity_available}, Requested: {quantity}"
                )
            inventory.quantity_available -= quantity
        elif transaction_type == TransactionType.DAMAGE_REPORT:
            if inventory.quantity_available < quantity:
                raise InsufficientInventoryException(
                    f"Insufficient inventory to report damage. Available: {inventory.quantity_available}, Requested: {quantity}"
                )
            inventory.quantity_available -= quantity
            inventory.quantity_damaged += quantity
        elif transaction_type == TransactionType.ADJUSTMENT:
            # quantity can be positive (increase) or negative (decrease)
            if inventory.quantity_available + quantity < 0:
                raise InsufficientInventoryException(
                    f"Adjustment would result in negative inventory. Available: {inventory.quantity_available}, Change: {quantity}"
                )
            inventory.quantity_available += quantity
        else:
            raise InvalidOperationException(f"Unsupported transaction type: {transaction_type}")

        inventory.save()

        # Create transaction record
        tx = InventoryTransaction.objects.create(
            product=product,
            warehouse=warehouse,
            transaction_type=transaction_type,
            quantity=quantity,
            performed_by=user,
            notes=notes
        )

    # Invalidate cache for low stock alert
    cache.delete('inventory:low-stock')
    cache.delete('reports:dashboard')

    # Dispatch Celery task asynchronously
    from apps.inventory.tasks import process_inventory_updated_event
    process_inventory_updated_event.delay(
        product_id=product.id,
        warehouse_id=warehouse.id,
        transaction_type=transaction_type,
        quantity=quantity
    )

    return tx


def transfer_inventory(data: dict, performed_by_user_id: int) -> dict:
    product_id = data['product_id']
    source_warehouse_id = data['source_warehouse_id']
    destination_warehouse_id = data['destination_warehouse_id']
    quantity = data['quantity']
    notes = data.get('notes')

    if source_warehouse_id == destination_warehouse_id:
        raise InvalidOperationException("Source and destination warehouses must be different.")

    try:
        user = User.objects.get(id=performed_by_user_id)
        product = Product.objects.get(id=product_id, is_deleted=False)
        source_wh = Warehouse.objects.get(id=source_warehouse_id, is_deleted=False)
        dest_wh = Warehouse.objects.get(id=destination_warehouse_id, is_deleted=False)
    except (User.DoesNotExist, Product.DoesNotExist, Warehouse.DoesNotExist):
        raise ResourceNotFoundException("Product, warehouse, or user not found.")

    reference_id = f"TRANSFER-{uuid.uuid4().hex[:12].upper()}"

    with transaction.atomic():
        # Lock in consistent order to prevent deadlocks (lower ID first)
        wh_ids = sorted([source_warehouse_id, destination_warehouse_id])
        
        # We query the inventory objects locking them in order
        inventories = {}
        for wh_id in wh_ids:
            wh_obj = source_wh if wh_id == source_warehouse_id else dest_wh
            inv, created = Inventory.objects.select_for_update().get_or_create(
                product=product,
                warehouse=wh_obj,
                defaults={'quantity_available': 0, 'quantity_reserved': 0, 'quantity_damaged': 0}
            )
            inventories[wh_id] = inv

        source_inv = inventories[source_warehouse_id]
        dest_inv = inventories[destination_warehouse_id]

        if source_inv.quantity_available < quantity:
            raise InsufficientInventoryException(
                f"Source warehouse has insufficient inventory. Available: {source_inv.quantity_available}, Requested: {quantity}"
            )

        # Deduct from source
        source_inv.quantity_available -= quantity
        source_inv.save()

        # Add to destination
        dest_inv.quantity_available += quantity
        dest_inv.save()

        # Create two InventoryTransaction records
        tx_out = InventoryTransaction.objects.create(
            product=product,
            warehouse=source_wh,
            transaction_type=TransactionType.OUTBOUND,
            quantity=quantity,
            reference_id=reference_id,
            performed_by=user,
            notes=f"Transfer to {dest_wh.warehouse_code}. Notes: {notes or ''}"
        )

        tx_in = InventoryTransaction.objects.create(
            product=product,
            warehouse=dest_wh,
            transaction_type=TransactionType.INBOUND,
            quantity=quantity,
            reference_id=reference_id,
            performed_by=user,
            notes=f"Transfer from {source_wh.warehouse_code}. Notes: {notes or ''}"
        )

    # Invalidate cache
    cache.delete('inventory:low-stock')
    cache.delete('reports:dashboard')

    # Dispatch Celery task
    from apps.inventory.tasks import process_inventory_transfer_event
    process_inventory_transfer_event.delay(
        product_id=product.id,
        source_warehouse_id=source_wh.id,
        destination_warehouse_id=dest_wh.id,
        quantity=quantity
    )

    return {
        "reference_id": reference_id,
        "source_transaction_id": tx_out.id,
        "destination_transaction_id": tx_in.id
    }


def get_low_stock_alerts() -> list:
    cache_key = 'inventory:low-stock'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Query all inventory records below reorder level (active records)
    # We join with product and warehouse
    low_stock_records = Inventory.objects.filter(
        is_deleted=False,
        product__is_deleted=False,
        warehouse__is_deleted=False
    ).select_related('product', 'warehouse').annotate(
        deficit=models.F('product__reorder_level') - models.F('quantity_available')
    ).filter(
        quantity_available__lte=models.F('product__reorder_level')
    )

    results = []
    for inv in low_stock_records:
        results.append({
            "product_id": inv.product.id,
            "sku": inv.product.sku,
            "product_name": inv.product.name,
            "warehouse_id": inv.warehouse.id,
            "warehouse_name": inv.warehouse.name,
            "quantity_available": inv.quantity_available,
            "reorder_level": inv.product.reorder_level,
            "deficit": inv.product.reorder_level - inv.quantity_available
        })

    cache.set(cache_key, results, timeout=LOW_STOCK_CACHE_TTL)
    return results


def check_and_publish_low_stock_alert(product_id: int, warehouse_id: int) -> None:
    try:
        inventory = Inventory.objects.select_related('product', 'warehouse').get(
            product_id=product_id,
            warehouse_id=warehouse_id,
            is_deleted=False
        )
    except Inventory.DoesNotExist:
        return

    if inventory.quantity_available <= inventory.product.reorder_level:
        # Log warning with exact format:
        # LOW STOCK ALERT: Product {sku} in Warehouse {warehouse_code} has {quantity_available} units remaining (reorder level: {reorder_level})
        logger.warning(
            f"LOW STOCK ALERT: Product {inventory.product.sku} in Warehouse {inventory.warehouse.warehouse_code} "
            f"has {inventory.quantity_available} units remaining (reorder level: {inventory.product.reorder_level})"
        )
        
        # Invalidate the low-stock cache key
        cache.delete('inventory:low-stock')
