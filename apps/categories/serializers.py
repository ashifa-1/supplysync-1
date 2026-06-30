from rest_framework import serializers
from apps.categories.models import Category

class CategorySerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    parent_category_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Category
        fields = ['id', 'category_code', 'name', 'description', 'parent_category', 'parent_category_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'parent_category', 'created_at', 'updated_at']

    def validate_parent_category_id(self, value):
        if value is not None:
            if not Category.objects.filter(id=value).exists():
                raise serializers.ValidationError("Parent category does not exist.")
        return value


class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'category_code', 'name', 'description', 'children']

    def get_children(self, obj):
        children = obj.children.filter(is_deleted=False)
        return CategoryTreeSerializer(children, many=True).data
