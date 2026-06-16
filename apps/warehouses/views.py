from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.cache import cache
from apps.warehouses.models import Warehouse
from apps.warehouses.serializers import WarehouseSerializer
from apps.warehouses.services import (
    create_warehouse,
    get_warehouse_with_summary,
    update_warehouse,
    delete_warehouse
)
from core.permissions import IsAdminUser
from core.constants import WAREHOUSES_LIST_CACHE_TTL
from core.pagination import StandardResultsPagination

class WarehouseListCreateView(APIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = WarehouseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = create_warehouse(serializer.validated_data)
        out_serializer = WarehouseSerializer(warehouse)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        city = request.query_params.get('city')
        state = request.query_params.get('state')
        page = request.query_params.get('page', '1')

        # Caching logic: only cache unfiltered default page 1 queries to avoid cache keys explosion
        use_cache = not city and not state and page == '1'
        cache_key = 'warehouses:list'

        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data)

        # Query and filter
        queryset = Warehouse.objects.filter(is_active=True).order_by('id')
        if city:
            queryset = queryset.filter(city__iexact=city)
        if state:
            queryset = queryset.filter(state__iexact=state)

        paginator = self.pagination_class()
        page_obj = paginator.paginate_queryset(queryset, request, view=self)
        serializer = WarehouseSerializer(page_obj, many=True)
        
        response_data = paginator.get_paginated_response(serializer.data).data

        if use_cache:
            cache.set(cache_key, response_data, timeout=WAREHOUSES_LIST_CACHE_TTL)

        return Response(response_data)


class WarehouseDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [IsAdminUser()]

    def get(self, request, pk, *args, **kwargs):
        summary = get_warehouse_with_summary(pk)
        return Response(summary, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        serializer = WarehouseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        warehouse = update_warehouse(pk, serializer.validated_data)
        out_serializer = WarehouseSerializer(warehouse)
        return Response(out_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        delete_warehouse(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
