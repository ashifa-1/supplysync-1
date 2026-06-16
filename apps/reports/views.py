from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import datetime
from django.core.exceptions import ValidationError
from apps.reports.services import (
    get_dashboard_summary,
    get_inventory_valuation,
    get_purchase_order_summary,
    get_sales_order_summary
)
from core.permissions import IsReportViewer

class DashboardReportView(APIView):
    permission_classes = [IsReportViewer]

    def get(self, request, *args, **kwargs):
        summary = get_dashboard_summary()
        return Response(summary, status=status.HTTP_200_OK)


class InventoryValuationReportView(APIView):
    permission_classes = [IsReportViewer]

    def get(self, request, *args, **kwargs):
        wh_id = request.query_params.get('warehouse_id')
        if wh_id:
            try:
                wh_id = int(wh_id)
            except ValueError:
                return Response({"message": "Invalid warehouse_id format."}, status=status.HTTP_400_BAD_REQUEST)
                
        valuation = get_inventory_valuation(wh_id)
        return Response(valuation, status=status.HTTP_200_OK)


class PurchaseOrderSummaryReportView(APIView):
    permission_classes = [IsReportViewer]

    def get(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        supplier_id = request.query_params.get('supplier_id')
        status_val = request.query_params.get('status')

        if not start_date or not end_date:
            return Response({
                "timestamp": timezone.now().isoformat() if 'timezone' in globals() else datetime.datetime.now().isoformat(),
                "status": 400,
                "error_code": "VALIDATION_FAILED",
                "message": "Both start_date and end_date are required.",
                "path": request.path,
                "errors": [
                    {"field": "start_date", "message": "This parameter is required."} if not start_date else None,
                    {"field": "end_date", "message": "This parameter is required."} if not end_date else None
                ]
            }, status=status.HTTP_400_BAD_REQUEST)

        if supplier_id:
            try:
                supplier_id = int(supplier_id)
            except ValueError:
                return Response({"message": "Invalid supplier_id."}, status=status.HTTP_400_BAD_REQUEST)

        summary = get_purchase_order_summary(start_date, end_date, supplier_id, status_val)
        return Response(summary, status=status.HTTP_200_OK)


class SalesOrderSummaryReportView(APIView):
    permission_classes = [IsReportViewer]

    def get(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        warehouse_id = request.query_params.get('warehouse_id')
        status_val = request.query_params.get('status')

        if not start_date or not end_date:
            return Response({
                "timestamp": timezone.now().isoformat() if 'timezone' in globals() else datetime.datetime.now().isoformat(),
                "status": 400,
                "error_code": "VALIDATION_FAILED",
                "message": "Both start_date and end_date are required.",
                "path": request.path,
                "errors": [
                    {"field": "start_date", "message": "This parameter is required."} if not start_date else None,
                    {"field": "end_date", "message": "This parameter is required."} if not end_date else None
                ]
            }, status=status.HTTP_400_BAD_REQUEST)

        if warehouse_id:
            try:
                warehouse_id = int(warehouse_id)
            except ValueError:
                return Response({"message": "Invalid warehouse_id."}, status=status.HTTP_400_BAD_REQUEST)

        summary = get_sales_order_summary(start_date, end_date, warehouse_id, status_val)
        return Response(summary, status=status.HTTP_200_OK)
