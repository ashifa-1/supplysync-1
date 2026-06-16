from rest_framework import serializers
from apps.products.models import Product
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer

class ProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    category_id = serializers.IntegerField(required=True, write_only=True)
    category = CategorySerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, allow_null=False)
    unit_of_measure = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    reorder_level = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'description', 'category', 'category_id',
            'unit_price', 'unit_of_measure', 'reorder_level', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sku', 'category', 'created_at', 'updated_at']

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price must be non-negative.")
        return value

    def validate_reorder_level(self, value):
        if value < 0:
            raise serializers.ValidationError("Reorder level must be non-negative.")
        return value

    def validate_category_id(self, value):
        if not Category.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError("Category does not exist or is deleted.")
        return value
