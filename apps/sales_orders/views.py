from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.sales_orders.models import SalesOrder
from apps.sales_orders.serializers import (
    SalesOrderSerializer,
    SalesOrderCreateSerializer,
    SalesOrderCancelSerializer
)
from apps.sales_orders.services import (
    create_sales_order,
    dispatch_sales_order,
    deliver_sales_order,
    cancel_sales_order
)
from core.permissions import IsWarehouseManagerOrAdminOrStaff
from core.pagination import StandardResultsPagination

class SalesOrderListCreateView(APIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsWarehouseManagerOrAdminOrStaff()]
        return [permissions.IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = SalesOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        so = create_sales_order(serializer.validated_data, request.user.id)
        out_serializer = SalesOrderSerializer(so)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = SalesOrder.objects.filter(is_deleted=False).order_by('id')
        
        # Simple optional filters
        warehouse_id = request.query_params.get('warehouse_id')
        status_val = request.query_params.get('status')
        
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if status_val:
            queryset = queryset.filter(status=status_val)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SalesOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class SalesOrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            so = SalesOrder.objects.prefetch_related('items__product').get(id=pk, is_deleted=False)
        except SalesOrder.DoesNotExist:
            return Response({"message": "Sales order not found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = SalesOrderSerializer(so)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalesOrderDispatchView(APIView):
    def get_permissions(self):
        return [IsWarehouseManagerOrAdminOrStaff()]

    def post(self, request, pk, *args, **kwargs):
        so = dispatch_sales_order(so_id=pk)
        serializer = SalesOrderSerializer(so)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalesOrderDeliverView(APIView):
    def get_permissions(self):
        return [IsWarehouseManagerOrAdminOrStaff()]

    def post(self, request, pk, *args, **kwargs):
        so = deliver_sales_order(so_id=pk)
        serializer = SalesOrderSerializer(so)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalesOrderCancelView(APIView):
    def get_permissions(self):
        return [IsWarehouseManagerOrAdminOrStaff()]

    def post(self, request, pk, *args, **kwargs):
        serializer = SalesOrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        so = cancel_sales_order(so_id=pk, reason=serializer.validated_data['reason'])
        out_serializer = SalesOrderSerializer(so)
        return Response(out_serializer.data, status=status.HTTP_200_OK)
