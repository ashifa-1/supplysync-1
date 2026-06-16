from django.db import models
from core.models import BaseModel

class Warehouse(BaseModel):
    warehouse_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    location = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    capacity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'warehouses'

    def __str__(self):
        return f"{self.name} ({self.warehouse_code})"
