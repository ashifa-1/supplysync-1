from rest_framework import serializers
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from apps.suppliers.serializers import SupplierSerializer
from apps.warehouses.serializers import WarehouseSerializer
from apps.products.serializers import ProductSerializer

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product', 'quantity_ordered', 'quantity_received', 'unit_price', 'total_price']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'warehouse', 'status', 'total_amount',
            'expected_delivery_date', 'actual_delivery_date', 'created_by',
            'created_by_name', 'approved_by', 'approved_by_name', 'notes',
            'items', 'created_at', 'updated_at'
        ]


class PurchaseOrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity_ordered = serializers.IntegerField(required=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    def validate_quantity_ordered(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity ordered must be greater than zero.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price must be non-negative.")
        return value


class PurchaseOrderCreateSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True)
    warehouse_id = serializers.IntegerField(required=True)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    items = PurchaseOrderCreateItemSerializer(many=True, required=True)

    def validate_items(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("At least one purchase order item is required.")
        return value


class PurchaseOrderReceiveItemSerializer(serializers.Serializer):
    po_item_id = serializers.IntegerField(required=True)
    quantity_received = serializers.IntegerField(required=True)

    def validate_quantity_received(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity received must be greater than zero.")
        return value


class PurchaseOrderReceiveSerializer(serializers.Serializer):
    items = PurchaseOrderReceiveItemSerializer(many=True, required=True)
    actual_delivery_date = serializers.DateField(required=False, allow_null=True)


class PurchaseOrderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_null=False, allow_blank=False)
