from django.core.cache import cache
from apps.categories.models import Category
from core.utils import generate_random_code
from core.exceptions import DuplicateResourceException, ResourceNotFoundException
from core.constants import CATEGORIES_TREE_CACHE_TTL
from apps.categories.serializers import CategoryTreeSerializer

def create_category(data: dict) -> Category:
    category_code = data.get('category_code')
    if not category_code:
        while True:
            category_code = generate_random_code('CAT', 6)
            if not Category.objects.filter(category_code=category_code).exists():
                break
    else:
        if Category.objects.filter(category_code=category_code).exists():
            raise DuplicateResourceException("Category with this code already exists.")

    parent_id = data.get('parent_category_id')
    parent = None
    if parent_id:
        try:
            parent = Category.objects.get(id=parent_id)
        except Category.DoesNotExist:
            raise ResourceNotFoundException("Parent category does not exist.")

    category = Category.objects.create(
        category_code=category_code,
        name=data['name'],
        description=data.get('description'),
        parent_category=parent
    )
    
    # Invalidate category tree cache
    cache.delete('categories:tree')
    return category


def get_category_tree() -> list:
    cache_key = 'categories:tree'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Query root categories
    roots = Category.objects.filter(parent_category__isnull=True, is_deleted=False).order_by('id')
    serializer = CategoryTreeSerializer(roots, many=True)
    tree_data = serializer.data
    
    cache.set(cache_key, tree_data, timeout=CATEGORIES_TREE_CACHE_TTL)
    return tree_data
