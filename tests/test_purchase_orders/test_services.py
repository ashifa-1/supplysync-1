import pytest
from apps.purchase_orders.services import (
    create_purchase_order,
    submit_purchase_order,
    approve_purchase_order,
    receive_purchase_order,
    cancel_purchase_order
)
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderStatus
from core.exceptions import InvalidOperationException

def test_po_lifecycle(db, sample_supplier, sample_warehouse, procurement_manager_user, warehouse_manager_user, sample_product, sample_inventory):
    # 1. Create DRAFT PO
    data = {
        "supplier_id": sample_supplier.id,
        "warehouse_id": sample_warehouse.id,
        "expected_delivery_date": "2025-08-01",
        "notes": "Test purchase order",
        "items": [
            {
                "product_id": sample_product.id,
                "quantity_ordered": 50,
                "unit_price": 8.00
            }
        ]
    }
    po = create_purchase_order(data, procurement_manager_user.id)
    assert po is not None
    assert po.status == PurchaseOrderStatus.DRAFT
    assert po.total_amount == 400.00
    assert po.items.count() == 1

    # 2. Submit PO (moves to PENDING_APPROVAL)
    po = submit_purchase_order(po.id)
    assert po.status == PurchaseOrderStatus.PENDING_APPROVAL

    # 3. Approve PO (moves to APPROVED)
    # Approved by warehouse_manager_user (different from creator)
    po = approve_purchase_order(po.id, warehouse_manager_user.id)
    assert po.status == PurchaseOrderStatus.APPROVED
    assert po.approved_by == warehouse_manager_user

    # 4. Receive PO (partial receipt)
    item = po.items.first()
    receive_data = {
        "items": [
            {
                "po_item_id": item.id,
                "quantity_received": 30
            }
        ],
        "actual_delivery_date": "2025-08-01"
    }
    po = receive_purchase_order(po.id, receive_data, warehouse_manager_user.id)
    assert po.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
    assert po.items.first().quantity_received == 30
    
    # Check inventory updated
    sample_inventory.refresh_from_db()
    assert sample_inventory.quantity_available == 130  # 100 + 30
