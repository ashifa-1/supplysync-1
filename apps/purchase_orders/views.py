from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.purchase_orders.models import PurchaseOrder
from apps.purchase_orders.serializers import (
    PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderReceiveSerializer,
    PurchaseOrderCancelSerializer
)
from apps.purchase_orders.services import (
    create_purchase_order,
    submit_purchase_order,
    approve_purchase_order,
    receive_purchase_order,
    cancel_purchase_order
)
from core.permissions import (
    IsProcurementManagerOrAdmin,
    IsWarehouseManagerOrAdmin,
    IsWarehouseManagerOrAdminOrStaff
)
from core.pagination import StandardResultsPagination

class PurchaseOrderListCreateView(APIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsProcurementManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        po = create_purchase_order(serializer.validated_data, request.user.id)
        out_serializer = PurchaseOrderSerializer(po)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = PurchaseOrder.objects.filter(is_deleted=False).order_by('id')
        
        
        supplier_id = request.query_params.get('supplier_id')
        warehouse_id = request.query_params.get('warehouse_id')
        status_val = request.query_params.get('status')
        
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if status_val:
            queryset = queryset.filter(status=status_val)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = PurchaseOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PurchaseOrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            po = PurchaseOrder.objects.prefetch_related('items__product').get(id=pk, is_deleted=False)
        except PurchaseOrder.DoesNotExist:
            return Response({"message": "Purchase order not found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = PurchaseOrderSerializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderSubmitView(APIView):
    def get_permissions(self):
        
        return [IsProcurementManagerOrAdmin()]

    def post(self, request, pk, *args, **kwargs):
        po = submit_purchase_order(po_id=pk)
        serializer = PurchaseOrderSerializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderApproveView(APIView):
    def get_permissions(self):
        
        return [IsWarehouseManagerOrAdmin()]

    def post(self, request, pk, *args, **kwargs):
        po = approve_purchase_order(po_id=pk, approved_by_user_id=request.user.id)
        serializer = PurchaseOrderSerializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderReceiveView(APIView):
    def get_permissions(self):
        
        return [IsWarehouseManagerOrAdminOrStaff()]

    def post(self, request, pk, *args, **kwargs):
        serializer = PurchaseOrderReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        po = receive_purchase_order(po_id=pk, data=serializer.validated_data, performed_by_user_id=request.user.id)
        out_serializer = PurchaseOrderSerializer(po)
        return Response(out_serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderCancelView(APIView):
    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role not in ['ADMIN', 'PROCUREMENT_MANAGER', 'WAREHOUSE_MANAGER']:
            return Response({
                "message": "Only admins, procurement managers, or warehouse managers can cancel purchase orders."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = PurchaseOrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        po = cancel_purchase_order(po_id=pk, reason=serializer.validated_data['reason'])
        out_serializer = PurchaseOrderSerializer(po)
        return Response(out_serializer.data, status=status.HTTP_200_OK)
