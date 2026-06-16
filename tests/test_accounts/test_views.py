import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User

def test_register_creates_user(api_client, db):
    url = reverse('auth_register')
    data = {
        "username": "newuser",
        "email": "newuser@test.com",
        "password": "Password123!",
        "full_name": "New User",
        "role": "STAFF"
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(email="newuser@test.com").exists()
    assert "access_token" in response.data


def test_login_returns_tokens(api_client, staff_user):
    url = reverse('auth_login')
    # Use password set in fixture (Password123!)
    data = {
        "email": staff_user.email,
        "password": "Password123!"
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.data
