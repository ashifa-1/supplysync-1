import datetime
from django.core.cache import cache
from django.db.models import F, DecimalField, ExpressionWrapper, Sum, Count
from django.utils import timezone
from apps.warehouses.models import Warehouse
from apps.products.models import Product
from apps.suppliers.models import Supplier
from apps.inventory.models import Inventory, InventoryTransaction, TransactionType
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderStatus
from apps.sales_orders.models import SalesOrder, SalesOrderStatus
from apps.inventory.serializers import InventoryTransactionSerializer
from core.constants import DASHBOARD_CACHE_TTL

def get_dashboard_summary() -> dict:
    cache_key = 'reports:dashboard'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Basic Counts
    total_warehouses = Warehouse.objects.filter(is_active=True, is_deleted=False).count()
    total_products = Product.objects.filter(is_active=True, is_deleted=False).count()
    total_suppliers = Supplier.objects.filter(is_active=True, is_deleted=False).count()

    # Total inventory value
    total_val = Inventory.objects.filter(
        is_deleted=False,
        product__is_deleted=False,
        warehouse__is_deleted=False
    ).annotate(
        item_value=ExpressionWrapper(
            F('quantity_available') * F('product__unit_price'),
            output_field=DecimalField(max_digits=20, decimal_places=2)
        )
    ).aggregate(
        grand_total=Sum('item_value')
    )['grand_total'] or 0

    # Open purchase orders
    open_pos = PurchaseOrder.objects.filter(
        is_deleted=False,
        status__in=[
            PurchaseOrderStatus.DRAFT,
            PurchaseOrderStatus.PENDING_APPROVAL,
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.ORDERED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED
        ]
    ).count()

    # Pending sales orders
    pending_sos = SalesOrder.objects.filter(
        is_deleted=False,
        status__in=[
            SalesOrderStatus.PENDING,
            SalesOrderStatus.CONFIRMED,
            SalesOrderStatus.PROCESSING
        ]
    ).count()

    # Low stock product count
    low_stock_product_count = Inventory.objects.filter(
        is_deleted=False,
        product__is_deleted=False,
        warehouse__is_deleted=False
    ).filter(
        quantity_available__lte=F('product__reorder_level')
    ).count()

    # Top selling products (last 30 days)
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    top_products_qs = InventoryTransaction.objects.filter(
        transaction_type=TransactionType.OUTBOUND,
        created_at__gte=thirty_days_ago
    ).values('product_id', 'product__sku', 'product__name').annotate(
        total_dispatched=Sum('quantity')
    ).order_by('-total_dispatched')[:5]

    top_selling_products = []
    for tp in top_products_qs:
        top_selling_products.append({
            "product_id": tp['product_id'],
            "sku": tp['product__sku'],
            "product_name": tp['product__name'],
            "total_dispatched": tp['total_dispatched']
        })

    # Recent transactions (last 10)
    recent_txs = InventoryTransaction.objects.select_related(
        'product', 'warehouse', 'performed_by'
    ).order_by('-created_at')[:10]
    recent_transactions = InventoryTransactionSerializer(recent_txs, many=True).data

    result = {
        "total_warehouses": total_warehouses,
        "total_products": total_products,
        "total_suppliers": total_suppliers,
        "total_inventory_value": f"{total_val:.2f}",
        "open_purchase_orders": open_pos,
        "pending_sales_orders": pending_sos,
        "low_stock_product_count": low_stock_product_count,
        "top_selling_products": top_selling_products,
        "recent_transactions": recent_transactions
    }

    cache.set(cache_key, result, timeout=DASHBOARD_CACHE_TTL)
    return result


def get_inventory_valuation(warehouse_id: int = None) -> dict:
    wh_qs = Warehouse.objects.filter(is_deleted=False)
    if warehouse_id:
        wh_qs = wh_qs.filter(id=warehouse_id)

    grand_total = 0
    warehouses_data = []

    for wh in wh_qs:
        inv_records = Inventory.objects.filter(
            warehouse=wh,
            is_deleted=False,
            product__is_deleted=False
        ).select_related('product')

        products_data = []
        warehouse_total = 0
        for inv in inv_records:
            val = inv.quantity_available * inv.product.unit_price
            warehouse_total += val
            products_data.append({
                "sku": inv.product.sku,
                "product_name": inv.product.name,
                "quantity_available": inv.quantity_available,
                "unit_price": f"{inv.product.unit_price:.2f}",
                "total_value": f"{val:.2f}"
            })

        grand_total += warehouse_total
        warehouses_data.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "products": products_data,
            "warehouse_total_value": f"{warehouse_total:.2f}"
        })

    return {
        "grand_total_value": f"{grand_total:.2f}",
        "warehouses": warehouses_data
    }


def get_purchase_order_summary(start_date, end_date, supplier_id=None, status=None) -> dict:
    qs = PurchaseOrder.objects.filter(
        created_at__date__range=[start_date, end_date],
        is_deleted=False
    )
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    if status:
        qs = qs.filter(status=status)

    total_orders = qs.count()
    total_val = qs.aggregate(total=Sum('total_amount'))['total'] or 0

    breakdown_qs = qs.values('status').annotate(count=Count('id'), total=Sum('total_amount'))
    breakdown_by_status = {}
    for b in breakdown_qs:
        breakdown_by_status[b['status']] = {
            "count": b['count'],
            "total_value": f"{(b['total'] or 0):.2f}"
        }

    top_suppliers_qs = qs.values('supplier_id', 'supplier__name').annotate(
        total=Sum('total_amount')
    ).order_by('-total')[:5]

    top_suppliers = []
    for ts in top_suppliers_qs:
        top_suppliers.append({
            "supplier_id": ts['supplier_id'],
            "supplier_name": ts['supplier__name'],
            "total_value": f"{(ts['total'] or 0):.2f}"
        })

    return {
        "total_orders": total_orders,
        "total_value": f"{total_val:.2f}",
        "breakdown_by_status": breakdown_by_status,
        "top_suppliers": top_suppliers
    }


def get_sales_order_summary(start_date, end_date, warehouse_id=None, status=None) -> dict:
    qs = SalesOrder.objects.filter(
        created_at__date__range=[start_date, end_date],
        is_deleted=False
    )
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    if status:
        qs = qs.filter(status=status)

    total_orders = qs.count()
    
    delivered_qs = qs.filter(status=SalesOrderStatus.DELIVERED)
    delivered_count = delivered_qs.count()
    total_rev = delivered_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    avg_order_value = 0
    if delivered_count > 0:
        avg_order_value = total_rev / delivered_count

    breakdown_qs = qs.values('status').annotate(count=Count('id'), total=Sum('total_amount'))
    breakdown_by_status = {}
    for b in breakdown_qs:
        breakdown_by_status[b['status']] = {
            "count": b['count'],
            "total_value": f"{(b['total'] or 0):.2f}"
        }

    # Top products by revenue from SalesOrderItem where sales_order in date range
    top_products_qs = SalesOrderItem.objects.filter(
        sales_order__in=qs
    ).values('product_id', 'product__sku', 'product__name').annotate(
        revenue=Sum('total_price')
    ).order_by('-revenue')[:5]

    top_products_by_revenue = []
    for tp in top_products_qs:
        top_products_by_revenue.append({
            "product_id": tp['product_id'],
            "sku": tp['product__sku'],
            "product_name": tp['product__name'],
            "revenue": f"{(tp['revenue'] or 0):.2f}"
        })

    return {
        "total_orders": total_orders,
        "total_revenue": f"{total_rev:.2f}",
        "average_order_value": f"{avg_order_value:.2f}",
        "breakdown_by_status": breakdown_by_status,
        "top_products_by_revenue": top_products_by_revenue
    }
