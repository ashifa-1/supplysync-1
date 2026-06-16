import pytest
from django.urls import reverse
from rest_framework import status

def test_dashboard_report_unauthenticated(api_client):
    url = reverse('report_dashboard')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_dashboard_report_staff_denied(authenticated_staff_client):
    # Staff is not allowed to view reports
    url = reverse('report_dashboard')
    response = authenticated_staff_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_dashboard_report_wm_allowed(authenticated_wm_client, sample_warehouse, sample_product, sample_supplier, sample_inventory):
    url = reverse('report_dashboard')
    response = authenticated_wm_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert "total_warehouses" in response.data
    assert "total_products" in response.data
    assert "total_suppliers" in response.data
    assert float(response.data['total_inventory_value']) == 100 * 10.50
