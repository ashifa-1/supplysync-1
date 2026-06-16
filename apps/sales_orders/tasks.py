import logging
import datetime
from celery import shared_task
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_sales_order_created_event(self, order_id: int, created_by_user_id: int):
    logger.info(f"EVENT [sales-order-created]: order_id={order_id}, created_by={created_by_user_id}")
    
    try:
        # Downstream tasks can trigger check of low stock alert for all ordered products
        from apps.sales_orders.models import SalesOrder
        from apps.inventory.services import check_and_publish_low_stock_alert
        so = SalesOrder.objects.get(id=order_id)
        for item in so.items.all():
            check_and_publish_low_stock_alert(item.product_id, so.warehouse_id)
    except Exception as exc:
        countdown = 2 ** self.request.retries
        logger.error(f"Error processing sales order created event, retrying in {countdown} seconds: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def process_sales_order_cancelled_event(self, order_id: int):
    logger.info(f"EVENT [sales-order-cancelled]: order_id={order_id}")
    
    try:
        # Downstream tasks can trigger alerts check
        pass
    except Exception as exc:
        countdown = 2 ** self.request.retries
        logger.error(f"Error processing sales order cancelled event, retrying in {countdown} seconds: {exc}")
        raise self.retry(exc=exc, countdown=countdown)


@shared_task
def generate_daily_operations_summary():
    from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderStatus
    from apps.sales_orders.models import SalesOrder, SalesOrderStatus
    
    today = timezone.localdate()
    
    new_pos = PurchaseOrder.objects.filter(created_at__date=today).count()
    pos_received = PurchaseOrder.objects.filter(status=PurchaseOrderStatus.RECEIVED, updated_at__date=today).count()
    
    new_sos = SalesOrder.objects.filter(created_at__date=today).count()
    sos_dispatched = SalesOrder.objects.filter(dispatched_at__date=today).count()
    sos_delivered = SalesOrder.objects.filter(delivered_at__date=today).count()
    
    logger.info(
        f"DAILY SUMMARY: Date={today}, New POs={new_pos}, POs Received={pos_received}, "
        f"New Sales Orders={new_sos}, Orders Dispatched={sos_dispatched}, Orders Delivered={sos_delivered}"
    )
