import pytest
from app.api.utils import DataProcessor, parse_datetime, serialize_okta_user, read_csv_from_s3
from datetime import datetime
from app.dynamo_db.models import OktaUser
from unittest.mock import patch
import requests


def test_extract_data():
    raw_users_data = [
        {
            "id": "user1",
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com"
            },
            "status": "ACTIVE"
        },
        {
            "id": "user2",
            "profile": {
                "firstName": "Jane",
                "lastName": "Smith",
                "email": "jane.smith@example.com"
            },
            "status": "INACTIVE"
        }
    ]

    relevant_fields = ["email"]

    response = DataProcessor.extract_data(raw_users_data, relevant_fields)

    # check fields that not in relevant data do not exist.
    assert response["user1"].get("status") is None
    assert response["user2"].get("name") is None

    assert response["user1"].get("email") == 'john.doe@example.com'
    assert response["user2"].get("email") == 'jane.smith@example.com'


def test_update_admin_field():
    raw_users_data = [
        {
            "id": "user1",
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com"
            },
            "status": "ACTIVE"
        },
        {
            "id": "user2",
            "profile": {
                "firstName": "Jane",
                "lastName": "Smith",
                "email": "jane.smith@example.com"
            },
            "status": "INACTIVE"
        }
    ]

    relevant_fields = ["id", "name", "email", "status"]

    processor = DataProcessor(api_client=None)
    users_data = processor.extract_data(raw_users_data, relevant_fields)

    # update user1 to admin.
    admin_users = [{"id": "user1"}]

    processor.update_admin_field(admin_users, users_data)

    assert users_data["user1"]["admin"] is True
    assert users_data["user2"]["admin"] is False


def test_parse_datetime_success():
    date_str = "2025-03-04T12:34:56.789123Z"
    expected_result = datetime(2025, 3, 4, 12, 34, 56, 789123)

    result = parse_datetime(date_str)

    assert result == expected_result


def test_parse_datetime_failure():
    date_str = "2025-03-04 12:34:56"

    with pytest.raises(ValueError):
        parse_datetime(date_str)


def test_serialize_okta_user_success():
    user = OktaUser(id="123", name="John Doe", email="john.doe@example.com", admin="True",
                    lastLogin="2025-03-01T12:00:00Z", passwordChanged="2025-03-01T12:00:00Z",
                    statusChanged="2025-03-01T12:00:00Z", user_events=["login", "password_change"])

    expected_result = {
        'id': '123',
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'admin': 'True',
        'lastLogin': '2025-03-01T12:00:00Z',
        'passwordChanged': '2025-03-01T12:00:00Z',
        'statusChanged': '2025-03-01T12:00:00Z',
        'user_events': ['login', 'password_change']
    }

    result = serialize_okta_user(user)

    assert result == expected_result


def test_serialize_okta_user_value_error():
    not_model_type = {"id": "123", "name": "John Doe"}

    # raise ValueError
    with pytest.raises(ValueError, match="The provided instance is not a valid PynamoDB model."):
        serialize_okta_user(not_model_type)


def test_read_csv_from_s3_error():

    with patch('requests.get') as mock_get:

        mock_get.return_value.status_code = 500
        mock_get.return_value.text = 'Internal Server Error'

        with pytest.raises(requests.exceptions.RequestException) as ex:
            read_csv_from_s3("https://fake-s3-url.com/fakefile.csv")

        assert str(ex.value) == 'An error occurred while processing the CSV file: Failed to retrieve file: 500'


def test_read_csv_from_s3_success():
    with patch('requests.get') as mock_get:

        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "User Email,Timestamp,Event Description\njohn.doe@example.com,1616152892,login\n"

        result = read_csv_from_s3("https://fake-s3-url.com/fakefile.csv")

        expected_result = [{
            'User Email': 'john.doe@example.com',
            'Timestamp': '1616152892',
            'Event Description': 'login'
        }]

        assert result == expected_result
