from django.core.cache import cache
from apps.products.models import Product
from apps.categories.models import Category
from core.utils import generate_random_code
from core.exceptions import DuplicateResourceException, ResourceNotFoundException
from core.constants import PRODUCT_DETAIL_CACHE_TTL, PRODUCTS_LIST_CACHE_TTL
from django.db import models

def create_product(data: dict) -> Product:
    category_id = data.get('category_id')
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        raise ResourceNotFoundException("Category not found.")

    sku = data.get('sku')
    if not sku:
        while True:
            import random
            import string
            rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            sku = f"SKU-{category.category_code}-{rand_part}"
            if not Product.objects.filter(sku=sku).exists():
                break
    else:
        if Product.objects.filter(sku=sku).exists():
            raise DuplicateResourceException("Product with this SKU already exists.")

    product = Product.objects.create(
        sku=sku,
        name=data['name'],
        description=data.get('description'),
        category=category,
        unit_price=data['unit_price'],
        unit_of_measure=data['unit_of_measure'],
        reorder_level=data.get('reorder_level', 0),
        is_active=data.get('is_active', True)
    )

    cache.delete('products:list')
    return product


def get_product_with_inventory(product_id: int) -> dict:
    cache_key = f'products:detail:{product_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        product = Product.objects.select_related('category').get(id=product_id)
    except Product.DoesNotExist:
        raise ResourceNotFoundException("Product not found.")

    from apps.inventory.models import Inventory
    inv_records = Inventory.objects.filter(product=product, is_deleted=False).select_related('warehouse')

    inventory_by_warehouse = []
    for inv in inv_records:
        inventory_by_warehouse.append({
            "warehouse_id": inv.warehouse.id,
            "warehouse_name": inv.warehouse.name,
            "quantity_available": inv.quantity_available,
            "quantity_reserved": inv.quantity_reserved
        })

    result = {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category": {
            "id": product.category.id,
            "name": product.category.name,
            "category_code": product.category.category_code
        },
        "unit_price": str(product.unit_price),
        "unit_of_measure": product.unit_of_measure,
        "reorder_level": product.reorder_level,
        "is_active": product.is_active,
        "inventory_by_warehouse": inventory_by_warehouse
    }

    cache.set(cache_key, result, timeout=PRODUCT_DETAIL_CACHE_TTL)
    return result


def update_product(product_id: int, data: dict) -> Product:
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ResourceNotFoundException("Product not found.")

    sku = data.get('sku')
    if sku and sku != product.sku:
        if Product.objects.filter(sku=sku).exclude(id=product_id).exists():
            raise DuplicateResourceException("Product with this SKU already exists.")
        product.sku = sku

    category_id = data.get('category_id')
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            product.category = category
        except Category.DoesNotExist:
            raise ResourceNotFoundException("Category not found.")

    for field in ['name', 'description', 'unit_price', 'unit_of_measure', 'reorder_level', 'is_active']:
        if field in data:
            setattr(product, field, data[field])

    product.save()

    cache.delete('products:list')
    cache.delete(f'products:detail:{product_id}')
    return product


def delete_product(product_id: int) -> None:
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ResourceNotFoundException("Product not found.")

    product.delete() # soft delete

    cache.delete('products:list')
    cache.delete(f'products:detail:{product_id}')
