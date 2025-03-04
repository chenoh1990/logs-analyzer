import pytest
from unittest.mock import patch
from requests.models import Response
from app.api.okta import OktaClient


@pytest.fixture
def okta_client():
    return OktaClient(okta_domain="example.okta.com", api_key="fake_api_key")


@pytest.fixture
def mocked_okta_users_response():
    mock_response = Response()
    mock_response.status_code = 200
    mock_response._content = b'''
    [
        {"id": "user1", "profile": {"email": "user1@example.com", "firstName": "User", "lastName": "One"}},
        {"id": "user2", "profile": {"email": "user2@example.com", "firstName": "User", "lastName": "Two"}}
    ]
    '''
    return mock_response


def test_get_users_data(okta_client, mocked_okta_users_response):
    with patch('requests.get', return_value=mocked_okta_users_response) as mock_get:
        users = okta_client.get_users_data()

        assert len(users) == 2

        mock_get.assert_called_once_with(
            "https://example.okta.com/api/v1/users",
            headers={"Authorization": "SSWS fake_api_key"}
        )


def test_get_admin_users(okta_client, mocked_okta_users_response):

    admin_group_id = 'group_example_123'

    with patch('requests.get', return_value=mocked_okta_users_response) as mock_get:
        admin_users = okta_client.get_admin_users(admin_group_id)

        assert len(admin_users) == 2

        mock_get.assert_called_once_with(
            f"https://example.okta.com/api/v1/groups/{admin_group_id}/users",
            headers={"Authorization": "SSWS fake_api_key"}
        )
