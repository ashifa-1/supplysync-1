from django.core.cache import cache
from django.db.models import Sum
from django.db import models
from apps.warehouses.models import Warehouse
from core.utils import generate_random_code
from core.exceptions import InvalidOperationException, DuplicateResourceException, ResourceNotFoundException
from core.constants import WAREHOUSE_DETAIL_CACHE_TTL, WAREHOUSES_LIST_CACHE_TTL
from django.db import transaction

def create_warehouse(data: dict) -> Warehouse:
    warehouse_code = data.get('warehouse_code')
    if not warehouse_code:
        # Auto generate WH-<6 character alphanumeric>
        while True:
            warehouse_code = generate_random_code('WH', 6)
            if not Warehouse.objects.filter(warehouse_code=warehouse_code).exists():
                break
    else:
        if Warehouse.objects.filter(warehouse_code=warehouse_code).exists():
            raise DuplicateResourceException("Warehouse with this code already exists.")
            
    warehouse = Warehouse.objects.create(
        warehouse_code=warehouse_code,
        name=data['name'],
        location=data['location'],
        city=data['city'],
        state=data['state'],
        pincode=data['pincode'],
        capacity=data['capacity'],
        is_active=data.get('is_active', True)
    )
    
    # Invalidate cache
    cache.delete('warehouses:list')
    return warehouse


def get_warehouse_with_summary(warehouse_id: int) -> dict:
    cache_key = f'warehouses:detail:{warehouse_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise ResourceNotFoundException("Warehouse not found.")

    # Calculate summary
    from apps.inventory.models import Inventory
    inv_qs = Inventory.objects.filter(warehouse=warehouse, is_deleted=False)
    
    # Total distinct products (which have quantity_available > 0 or reserved > 0)
    distinct_products = inv_qs.filter(
        models.Q(quantity_available__gt=0) | models.Q(quantity_reserved__gt=0)
    ).values('product_id').distinct().count()
    
    total_quantity = inv_qs.aggregate(total=Sum('quantity_available'))['total'] or 0

    result = {
        "id": warehouse.id,
        "warehouse_code": warehouse.warehouse_code,
        "name": warehouse.name,
        "location": warehouse.location,
        "city": warehouse.city,
        "state": warehouse.state,
        "pincode": warehouse.pincode,
        "capacity": warehouse.capacity,
        "is_active": warehouse.is_active,
        "total_distinct_products": distinct_products,
        "total_quantity_available": total_quantity
    }
    
    cache.set(cache_key, result, timeout=WAREHOUSE_DETAIL_CACHE_TTL)
    return result


def update_warehouse(warehouse_id: int, data: dict) -> Warehouse:
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise ResourceNotFoundException("Warehouse not found.")

    # If code is changing, raise InvalidOperationException
    new_code = data.get('warehouse_code')
    if new_code and new_code != warehouse.warehouse_code:
        raise InvalidOperationException("WAREHOUSE_CODE_IMMUTABLE")

    for field in ['name', 'location', 'city', 'state', 'pincode', 'capacity', 'is_active']:
        if field in data:
            setattr(warehouse, field, data[field])
            
    warehouse.save()
    
    # Invalidate caches
    cache.delete('warehouses:list')
    cache.delete(f'warehouses:detail:{warehouse_id}')
    return warehouse


def delete_warehouse(warehouse_id: int) -> None:
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id)
    except Warehouse.DoesNotExist:
        raise ResourceNotFoundException("Warehouse not found.")

    # A warehouse cannot be deleted if it has active inventory
    from apps.inventory.models import Inventory
    active_inv = Inventory.objects.filter(
        warehouse=warehouse,
        is_deleted=False
    ).filter(
        models.Q(quantity_available__gt=0) | models.Q(quantity_reserved__gt=0)
    ).exists()
    
    if active_inv:
        # Throw validation/conflict error with specific text/code
        from rest_framework.exceptions import APIException
        class WarehouseHasActiveInventoryException(APIException):
            status_code = 409
            default_code = 'WAREHOUSE_HAS_ACTIVE_INVENTORY'
            default_detail = 'Warehouse cannot be deleted because it has active inventory.'
        raise WarehouseHasActiveInventoryException()

    warehouse.delete() # Soft delete is called on BaseModel
    
    # Invalidate caches
    cache.delete('warehouses:list')
    cache.delete(f'warehouses:detail:{warehouse_id}')
