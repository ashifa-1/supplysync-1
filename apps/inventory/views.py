from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.inventory.models import Inventory, InventoryTransaction
from apps.inventory.serializers import (
    InventorySerializer,
    InventoryTransactionSerializer,
    InventoryAdjustSerializer,
    InventoryTransferSerializer
)
from apps.inventory.services import (
    adjust_inventory,
    transfer_inventory,
    get_low_stock_alerts
)
from core.permissions import IsWarehouseManagerOrAdminOrStaff
from core.pagination import StandardResultsPagination

class InventoryAdjustView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, *args, **kwargs):
        serializer = InventoryAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx = adjust_inventory(serializer.validated_data, request.user.id)
        out_serializer = InventoryTransactionSerializer(tx)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class InventoryTransferView(APIView):
    permission_classes = [IsWarehouseManagerOrAdminOrStaff]

    def post(self, request, *args, **kwargs):
        serializer = InventoryTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = transfer_inventory(serializer.validated_data, request.user.id)
        return Response(result, status=status.HTTP_200_OK)


class LowStockAlertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        alerts = get_low_stock_alerts()
        return Response(alerts, status=status.HTTP_200_OK)


class WarehouseInventoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get(self, request, warehouse_id, *args, **kwargs):
        queryset = Inventory.objects.filter(
            warehouse_id=warehouse_id,
            is_deleted=False
        ).select_related('product', 'warehouse').order_by('id')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = InventorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
