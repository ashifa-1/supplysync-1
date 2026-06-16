from django.urls import path
from apps.purchase_orders.views import (
    PurchaseOrderListCreateView,
    PurchaseOrderDetailView,
    PurchaseOrderSubmitView,
    PurchaseOrderApproveView,
    PurchaseOrderReceiveView,
    PurchaseOrderCancelView
)

urlpatterns = [
    path('', PurchaseOrderListCreateView.as_view(), name='purchase_order_list_create'),
    path('<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('<int:pk>/submit/', PurchaseOrderSubmitView.as_view(), name='purchase_order_submit'),
    path('<int:pk>/approve/', PurchaseOrderApproveView.as_view(), name='purchase_order_approve'),
    path('<int:pk>/receive/', PurchaseOrderReceiveView.as_view(), name='purchase_order_receive'),
    path('<int:pk>/cancel/', PurchaseOrderCancelView.as_view(), name='purchase_order_cancel'),
]
