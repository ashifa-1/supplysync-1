import pytest
from apps.sales_orders.services import create_sales_order
from apps.sales_orders.models import SalesOrder, SalesOrderStatus
from core.exceptions import InsufficientStockForOrderException

def test_create_sales_order_reserves_inventory_on_creation(db, sample_inventory, staff_user):
    data = {
        "warehouse_id": sample_inventory.warehouse.id,
        "customer_name": "Test Customer",
        "customer_email": "customer@test.com",
        "customer_phone": "1234567890",
        "shipping_address": "123 Customer Street",
        "items": [
            {
                "product_id": sample_inventory.product.id,
                "quantity": 30,
                "unit_price": 12.00
            }
        ]
    }
    
    so = create_sales_order(data, staff_user.id)
    
    assert so is not None
    assert so.status == SalesOrderStatus.CONFIRMED
    assert so.total_amount == 360.00
    
    # Check inventory reservation
    sample_inventory.refresh_from_db()
    assert sample_inventory.quantity_available == 70  # 100 - 30
    assert sample_inventory.quantity_reserved == 30   # +30


def test_create_sales_order_raises_exception_when_insufficient_stock(db, sample_inventory, staff_user):
    data = {
        "warehouse_id": sample_inventory.warehouse.id,
        "customer_name": "Test Customer",
        "customer_email": "customer@test.com",
        "customer_phone": "1234567890",
        "shipping_address": "123 Customer Street",
        "items": [
            {
                "product_id": sample_inventory.product.id,
                "quantity": 130,  # exceeds 100 available
                "unit_price": 12.00
            }
        ]
    }
    
    with pytest.raises(InsufficientStockForOrderException):
        create_sales_order(data, staff_user.id)
