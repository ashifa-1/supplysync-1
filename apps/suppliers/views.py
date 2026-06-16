from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.suppliers.serializers import SupplierSerializer
from apps.suppliers.services import (
    create_supplier,
    update_supplier,
    get_supplier_by_id,
    list_suppliers,
    delete_supplier
)
from core.pagination import StandardResultsPagination

class SupplierListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination

    def post(self, request, *args, **kwargs):
        serializer = SupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = create_supplier(serializer.validated_data)
        out_serializer = SupplierSerializer(supplier)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        filters = {}
        for param in ['name', 'city', 'state', 'is_active']:
            val = request.query_params.get(param)
            if val is not None:
                if param == 'is_active':
                    filters[param] = val.lower() in ['true', '1', 'yes']
                else:
                    filters[param] = val

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        queryset = list_suppliers(filters, page, page_size)
        paginator = self.pagination_class()
        page_obj = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SupplierSerializer(page_obj, many=True)
        return paginator.get_paginated_response(serializer.data)


class SupplierDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        supplier = get_supplier_by_id(pk)
        serializer = SupplierSerializer(supplier)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        serializer = SupplierSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        supplier = update_supplier(pk, serializer.validated_data)
        out_serializer = SupplierSerializer(supplier)
        return Response(out_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        delete_supplier(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
