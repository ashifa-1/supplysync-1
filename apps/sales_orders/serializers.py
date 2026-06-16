from rest_framework import serializers
from apps.sales_orders.models import SalesOrder, SalesOrderItem, SalesOrderStatus
from apps.warehouses.serializers import WarehouseSerializer
from apps.products.serializers import ProductSerializer

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ['id', 'product', 'quantity', 'unit_price', 'total_price']


class SalesOrderSerializer(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    items = SalesOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            'id', 'order_number', 'customer_name', 'customer_email', 'customer_phone',
            'shipping_address', 'warehouse', 'status', 'total_amount', 'dispatched_at',
            'delivered_at', 'created_by', 'created_by_name', 'notes', 'items',
            'created_at', 'updated_at'
        ]


class SalesOrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price must be non-negative.")
        return value


class SalesOrderCreateSerializer(serializers.Serializer):
    warehouse_id = serializers.IntegerField(required=True)
    customer_name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    customer_email = serializers.EmailField(required=True, allow_null=False, allow_blank=False)
    customer_phone = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    shipping_address = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    items = SalesOrderCreateItemSerializer(many=True, required=True)

    def validate_items(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("At least one sales order item is required.")
        return value


class SalesOrderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_null=False, allow_blank=False)
