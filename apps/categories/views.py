from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from apps.categories.services import create_category, get_category_tree
from core.permissions import IsWarehouseManagerOrAdmin
from core.pagination import StandardResultsPagination

class CategoryListCreateView(APIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsWarehouseManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = create_category(serializer.validated_data)
        out_serializer = CategorySerializer(category)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        queryset = Category.objects.filter(is_deleted=False).order_by('id')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CategorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CategoryTreeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tree = get_category_tree()
        return Response(tree, status=status.HTTP_200_OK)
