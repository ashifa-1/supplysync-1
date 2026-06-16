import pytest
from apps.inventory.services import (
    adjust_inventory,
    transfer_inventory,
    get_low_stock_alerts
)
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from core.exceptions import InsufficientInventoryException

def test_adjust_inventory_creates_transaction_record_when_inbound(db, sample_inventory, staff_user):
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.INBOUND,
        "quantity": 50,
        "notes": "Test inbound adjustment"
    }
    tx = adjust_inventory(data, staff_user.id)
    
    assert tx is not None
    assert tx.transaction_type == TransactionType.INBOUND
    assert tx.quantity == 50
    assert tx.performed_by == staff_user
    
    # Verify inventory was updated
    sample_inventory.refresh_from_db()
    assert sample_inventory.quantity_available == 150


def test_adjust_inventory_raises_exception_when_outbound_exceeds_available(db, sample_inventory, staff_user):
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.OUTBOUND,
        "quantity": 150,  # exceeds 100 available
        "notes": "Test outbound too high"
    }
    
    with pytest.raises(InsufficientInventoryException):
        adjust_inventory(data, staff_user.id)


def test_adjust_inventory_dispatches_celery_task_on_success(db, sample_inventory, staff_user, mocker):
    mock_task = mocker.patch('apps.inventory.tasks.process_inventory_updated_event.delay')
    
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": TransactionType.INBOUND,
        "quantity": 50,
        "notes": "Test inbound celery dispatch"
    }
    adjust_inventory(data, staff_user.id)
    
    mock_task.assert_called_once_with(
        product_id=sample_inventory.product.id,
        warehouse_id=sample_inventory.warehouse.id,
        transaction_type=TransactionType.INBOUND,
        quantity=50
    )


def test_transfer_inventory_deducts_from_source_and_adds_to_destination(db, sample_inventory, sample_warehouse, staff_user):
    # Create destination warehouse and destination inventory
    from apps.warehouses.models import Warehouse
    dest_warehouse = Warehouse.objects.create(
        warehouse_code="WH-TEST02",
        name="Dest Warehouse",
        location="456 Dest Street",
        city="Dest City",
        state="Dest State",
        pincode="654321",
        capacity=1000
    )
    
    data = {
        "product_id": sample_inventory.product.id,
        "source_warehouse_id": sample_inventory.warehouse.id,
        "destination_warehouse_id": dest_warehouse.id,
        "quantity": 40,
        "notes": "Transfer 40 units"
    }
    
    result = transfer_inventory(data, staff_user.id)
    assert "reference_id" in result
    
    # Verify source inventory
    sample_inventory.refresh_from_db()
    assert sample_inventory.quantity_available == 60
    
    # Verify destination inventory
    dest_inv = Inventory.objects.get(product=sample_inventory.product, warehouse=dest_warehouse)
    assert dest_inv.quantity_available == 40


def test_transfer_inventory_raises_exception_when_source_has_insufficient_stock(db, sample_inventory, staff_user):
    from apps.warehouses.models import Warehouse
    dest_warehouse = Warehouse.objects.create(
        warehouse_code="WH-TEST02",
        name="Dest Warehouse",
        location="456 Dest Street",
        city="Dest City",
        state="Dest State",
        pincode="654321",
        capacity=1000
    )
    
    data = {
        "product_id": sample_inventory.product.id,
        "source_warehouse_id": sample_inventory.warehouse.id,
        "destination_warehouse_id": dest_warehouse.id,
        "quantity": 120,  # exceeds 100 available
        "notes": "Transfer too much"
    }
    
    with pytest.raises(InsufficientInventoryException):
        transfer_inventory(data, staff_user.id)


def test_get_low_stock_alerts_returns_products_below_reorder_level(db, sample_inventory):
    # Reorder level of sample product is 10. Available is 100, which is above reorder level.
    # Set available stock to 5, which is <= 10.
    sample_inventory.quantity_available = 5
    sample_inventory.save()
    
    alerts = get_low_stock_alerts()
    assert len(alerts) == 1
    assert alerts[0]['product_id'] == sample_inventory.product.id
    assert alerts[0]['deficit'] == 5  # 10 - 5
