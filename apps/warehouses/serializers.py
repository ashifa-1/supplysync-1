from rest_framework import serializers
from apps.warehouses.models import Warehouse

class WarehouseSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    location = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    city = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    state = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    pincode = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    capacity = serializers.IntegerField(required=True, allow_null=False)
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Warehouse
        fields = ['id', 'warehouse_code', 'name', 'location', 'city', 'state', 'pincode', 'capacity', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than zero.")
        return value
