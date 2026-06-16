from django.urls import path
from apps.sales_orders.views import (
    SalesOrderListCreateView,
    SalesOrderDetailView,
    SalesOrderDispatchView,
    SalesOrderDeliverView,
    SalesOrderCancelView
)

urlpatterns = [
    path('', SalesOrderListCreateView.as_view(), name='sales_order_list_create'),
    path('<int:pk>/', SalesOrderDetailView.as_view(), name='sales_order_detail'),
    path('<int:pk>/dispatch/', SalesOrderDispatchView.as_view(), name='sales_order_dispatch'),
    path('<int:pk>/deliver/', SalesOrderDeliverView.as_view(), name='sales_order_deliver'),
    path('<int:pk>/cancel/', SalesOrderCancelView.as_view(), name='sales_order_cancel'),
]
