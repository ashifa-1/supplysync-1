import pytest
from django.urls import reverse
from rest_framework import status

def test_inventory_adjust_unauthenticated(api_client, sample_inventory):
    url = reverse('inventory_adjust')
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": "INBOUND",
        "quantity": 10
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_inventory_adjust_authenticated_staff(authenticated_staff_client, sample_inventory):
    url = reverse('inventory_adjust')
    data = {
        "product_id": sample_inventory.product.id,
        "warehouse_id": sample_inventory.warehouse.id,
        "transaction_type": "INBOUND",
        "quantity": 10
    }
    response = authenticated_staff_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['quantity'] == 10
