from django.core.cache import cache
from django.db.models import QuerySet
from apps.suppliers.models import Supplier
from core.utils import generate_random_code
from core.exceptions import DuplicateResourceException, ResourceNotFoundException
from core.constants import SUPPLIER_DETAIL_CACHE_TTL

def create_supplier(data: dict) -> Supplier:
    supplier_code = data.get('supplier_code')
    if not supplier_code:
        while True:
            supplier_code = generate_random_code('SUP', 6)
            if not Supplier.objects.filter(supplier_code=supplier_code).exists():
                break
    else:
        if Supplier.objects.filter(supplier_code=supplier_code).exists():
            raise DuplicateResourceException("Supplier with this code already exists.")

    supplier = Supplier.objects.create(
        supplier_code=supplier_code,
        name=data['name'],
        contact_person=data['contact_person'],
        email=data['email'],
        phone=data['phone'],
        address=data['address'],
        city=data['city'],
        state=data['state'],
        pincode=data['pincode'],
        gstin=data.get('gstin'),
        is_active=data.get('is_active', True)
    )
    
    cache.delete('reports:dashboard')
    return supplier


def update_supplier(supplier_id: int, data: dict) -> Supplier:
    try:
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        raise ResourceNotFoundException("Supplier not found.")

    supplier_code = data.get('supplier_code')
    if supplier_code and supplier_code != supplier.supplier_code:
        if Supplier.objects.filter(supplier_code=supplier_code).exclude(id=supplier_id).exists():
            raise DuplicateResourceException("Supplier with this code already exists.")
        supplier.supplier_code = supplier_code

    for field in ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'gstin', 'is_active']:
        if field in data:
            setattr(supplier, field, data[field])

    supplier.save()

    # Invalidate cache
    cache.delete(f'suppliers:detail:{supplier_id}')
    cache.delete('reports:dashboard')
    return supplier


def get_supplier_by_id(supplier_id: int) -> Supplier:
    cache_key = f'suppliers:detail:{supplier_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        raise ResourceNotFoundException("Supplier not found.")

    cache.set(cache_key, supplier, timeout=SUPPLIER_DETAIL_CACHE_TTL)
    return supplier


def list_suppliers(filters: dict, page: int, page_size: int) -> QuerySet:
    # We ignore pagination here as we return QuerySet as required by signature,
    # then views can apply DRF pagination on the QuerySet
    queryset = Supplier.objects.filter(is_deleted=False).order_by('id')
    
    if 'name' in filters:
        queryset = queryset.filter(name__icontains=filters['name'])
    if 'city' in filters:
        queryset = queryset.filter(city__iexact=filters['city'])
    if 'state' in filters:
        queryset = queryset.filter(state__iexact=filters['state'])
    if 'is_active' in filters:
        queryset = queryset.filter(is_active=filters['is_active'])

    return queryset


def delete_supplier(supplier_id: int) -> None:
    try:
        supplier = Supplier.objects.get(id=supplier_id)
    except Supplier.DoesNotExist:
        raise ResourceNotFoundException("Supplier not found.")

    supplier.delete() # soft delete

    # Invalidate caches
    cache.delete(f'suppliers:detail:{supplier_id}')
    cache.delete('reports:dashboard')
