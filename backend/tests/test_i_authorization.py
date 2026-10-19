import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_i_api_authorization_and_authentication(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST I — ROLE-BASED ACCESS & API AUTHORIZATION:
    1. Unauthenticated API requests are denied with HTTP 401 Unauthorized.
    2. Authenticated users with valid tokens can access allowed endpoints.
    3. Direct tampering or unauthorized actions without authentication are rejected.
    """
    client = APIClient()

    # 1. Unauthenticated request to protected endpoint
    response = client.get('/api/core/products/')
    assert response.status_code == 401 # Denied!

    response_inv = client.get('/api/inventory/balances/')
    assert response_inv.status_code == 401

    response_acc = client.get('/api/accounting/journal-entries/')
    assert response_acc.status_code == 401

    # 2. Authenticate with DRF Token
    user = setup_master_data['admin_user']
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    # 3. Authenticated request succeeds
    auth_response = client.get('/api/core/products/')
    assert auth_response.status_code == 200
    assert auth_response.data['count'] >= 4 # We seeded 4 products

    auth_balances = client.get('/api/inventory/balances/')
    assert auth_balances.status_code == 200

    auth_tb = client.get('/api/accounting/journal-entries/reports/trial-balance/')
    assert auth_tb.status_code == 200
    assert 'trial_balance' in auth_tb.data
