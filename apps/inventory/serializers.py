from rest_framework import serializers
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.products.serializers import ProductSerializer
from apps.warehouses.serializers import WarehouseSerializer

class InventorySerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)
    quantity_available = serializers.IntegerField(required=True)
    quantity_reserved = serializers.IntegerField(required=True)
    quantity_damaged = serializers.IntegerField(required=True)

    class Meta:
        model = Inventory
        fields = [
            'id', 'product', 'warehouse', 'quantity_available',
            'quantity_reserved', 'quantity_damaged', 'last_updated_at'
        ]


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.full_name', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'product', 'warehouse', 'transaction_type', 'quantity',
            'reference_id', 'performed_by', 'performed_by_name', 'notes', 'created_at'
        ]


class InventoryAdjustSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True, allow_null=False)
    warehouse_id = serializers.IntegerField(required=True, allow_null=False)
    transaction_type = serializers.ChoiceField(choices=TransactionType.choices, required=True)
    quantity = serializers.IntegerField(required=True, allow_null=False)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        tx_type = attrs.get('transaction_type')
        quantity = attrs.get('quantity')
        
        if tx_type == TransactionType.ADJUSTMENT:
            if quantity == 0:
                raise serializers.ValidationError({"quantity": "Adjustment quantity cannot be zero."})
        else:
            if quantity <= 0:
                raise serializers.ValidationError({"quantity": "Quantity must be greater than zero."})
        return attrs


class InventoryTransferSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True, allow_null=False)
    source_warehouse_id = serializers.IntegerField(required=True, allow_null=False)
    destination_warehouse_id = serializers.IntegerField(required=True, allow_null=False)
    quantity = serializers.IntegerField(required=True, allow_null=False)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate(self, attrs):
        src = attrs.get('source_warehouse_id')
        dest = attrs.get('destination_warehouse_id')
        if src == dest:
            raise serializers.ValidationError("Source and destination warehouses must be different.")
        return attrs
