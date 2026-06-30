from django.db import models
from core.models import BaseModel
from apps.products.models import Product
from apps.warehouses.models import Warehouse
from apps.accounts.models import User

class Inventory(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    quantity_available = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)
    quantity_damaged = models.IntegerField(default=0)
    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory'
        unique_together = [('product', 'warehouse')]

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name}: Avail={self.quantity_available}, Res={self.quantity_reserved}"


class TransactionType(models.TextChoices):
    INBOUND = 'INBOUND', 'Inbound'
    OUTBOUND = 'OUTBOUND', 'Outbound'
    ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
    TRANSFER = 'TRANSFER', 'Transfer'
    DAMAGE_REPORT = 'DAMAGE_REPORT', 'Damage Report'


class InventoryTransaction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    quantity = models.IntegerField()
    reference_id = models.CharField(max_length=100, null=True, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_transactions'

    def __str__(self):
        return f"TX {self.id}: {self.transaction_type} {self.quantity} x {self.product.sku} at {self.warehouse.warehouse_code}"
