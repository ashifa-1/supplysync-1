from rest_framework import serializers
from apps.suppliers.models import Supplier

class SupplierSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    contact_person = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    email = serializers.EmailField(required=True, allow_null=False, allow_blank=False)
    phone = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    address = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    city = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    state = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    pincode = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    gstin = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'supplier_code', 'name', 'contact_person', 'email', 'phone',
            'address', 'city', 'state', 'pincode', 'gstin', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
