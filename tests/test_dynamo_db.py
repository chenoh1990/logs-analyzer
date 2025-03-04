import pytest
from moto import mock_aws
from app.dynamo_db.models import OktaUser
from app.dynamo_db.repositories import UserRepository
from app.dynamo_db.service import UserService


@pytest.fixture(scope="module", autouse=True)
def setup_dynamodb():
    """Setup DynamoDB environment before running tests in this module."""
    with mock_aws():
        # create table
        OktaUser.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True
        )
        # create list with 2 users.
        users = [
            OktaUser(
                email="user1@example.com",
                admin="False",
                lastLogin="2024-03-01",
                name="User One",
                passwordChanged="2024-02-28",
                statusChanged="2024-03-01",
                id="user_1"
            ),
            OktaUser(
                email="user2@example.com",
                admin="True",
                lastLogin="2024-03-02",
                name="User Two",
                passwordChanged="2024-02-27",
                statusChanged="2024-03-02",
                id="user_2"
            ),
        ]
        for user in users:
            user.save()
        yield


# tests for UserRepository class.
def test_scan_table(setup_dynamodb):
    # initialize repository class.
    repository = UserRepository(OktaUser)

    users = repository.scan_table()

    assert len(users) == 2

    emails = [user.email for user in users]
    assert "user1@example.com" in emails
    assert "user2@example.com" in emails


def test_get_admins_list(setup_dynamodb):
    # initialize repository class.
    repository = UserRepository(OktaUser)

    admins = repository.get_admins_list()

    assert len(admins) == 1

    admin_emails = [admin.email for admin in admins]
    assert ['user1@example.com'] not in admin_emails

    assert ['user2@example.com'] == admin_emails


def test_get_user_by_email(setup_dynamodb):

    user_repo = UserRepository(OktaUser)

    # create new user.
    test_user = OktaUser(
        email='testtest@example.com',
        id='12345',
        name='test User',
        admin='True',
        lastLogin='2025-01-01',
        statusChanged='2025-01-01',
        passwordChanged='2025-01-01'
    )
    test_user.save()

    user = user_repo.get_user_by_email('testtest@example.com')

    assert user is not None
    assert user.email == 'testtest@example.com'
    assert user.name == 'test User'


def test_user_not_found(setup_dynamodb):
    user_repo = UserRepository(OktaUser)

    user = user_repo.get_user_by_email('nonexistent@example.com')

    assert user is None


# tests for UserService class.
def test_update_users_from_csv_admin_role_granted(setup_dynamodb):
    user_repository = UserRepository(OktaUser)
    user_service = UserService(user_repository)

    users_data = [
        {
            "User Email": "user1@example.com",
            "Timestamp": "1677660000",  # Some valid timestamp
            "Event Description": "Admin Role Granted"
        }
    ]

    response = user_service.update_users_from_csv(users_data)

    # Fetch user and check if admin field was updated
    user = user_repository.get_user_by_email("user1@example.com")

    assert user.admin == "True"
    assert response == "users details changes successfully in DB."
