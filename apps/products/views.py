from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.cache import cache
from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from apps.products.filters import ProductFilter
from apps.products.services import (
    create_product,
    get_product_with_inventory,
    update_product,
    delete_product
)
from core.permissions import IsWarehouseManagerOrAdmin
from core.constants import PRODUCTS_LIST_CACHE_TTL
from core.pagination import StandardResultsPagination

class ProductListCreateView(APIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsWarehouseManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = create_product(serializer.validated_data)
        out_serializer = ProductSerializer(product)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        # Determine if filters are applied
        filter_params = ['category_id', 'is_active', 'min_price', 'max_price', 'search']
        has_filters = any(request.query_params.get(param) is not None for param in filter_params)
        page = request.query_params.get('page', '1')

        # Caching logic
        use_cache = not has_filters and page == '1'
        cache_key = 'products:list'

        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)

        # Apply filtering
        queryset = Product.objects.filter(is_deleted=False).order_by('id')
        filter_set = ProductFilter(request.query_params, queryset=queryset)
        if filter_set.is_valid():
            queryset = filter_set.qs

        paginator = self.pagination_class()
        page_obj = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductSerializer(page_obj, many=True)
        
        response_data = paginator.get_paginated_response(serializer.data).data

        if use_cache:
            cache.set(cache_key, response_data, timeout=PRODUCTS_LIST_CACHE_TTL)

        return Response(response_data)


class ProductDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsWarehouseManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get(self, request, pk, *args, **kwargs):
        summary = get_product_with_inventory(pk)
        return Response(summary, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        serializer = ProductSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = update_product(pk, serializer.validated_data)
        out_serializer = ProductSerializer(product)
        return Response(out_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        delete_product(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
