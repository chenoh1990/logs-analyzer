from fastapi import APIRouter, HTTPException
from app.dynamo_db.models import OktaUser
from app.dynamo_db.repositories import UserRepository
from app.dynamo_db.service import UserService
from app.api.utils import parse_datetime, serialize_okta_user, read_csv_from_s3, DataProcessor
from pynamodb.exceptions import ScanError
from datetime import datetime, timedelta
from app.api.okta import OktaClient
from app_config import OKTA_DOMAIN, OKTA_API_TOKEN, OKTA_ADMIN_GROUP_ID

# create users route.
users = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)

# initialize the UserRepository & UserService outside the route handlers.
user_repository = UserRepository(OktaUser)
user_service = UserService(user_repository)

# initialize OktaClient & DataProcessor outside the route handlers.
okta_client = OktaClient(OKTA_DOMAIN, OKTA_API_TOKEN)
data_processor = DataProcessor(okta_client)


@users.get("/")
def insert_okta_users_to_db():
    """
    when client login to url 'http://localhost/users/' we insert the scan results we get from Okta api.
    :return:
    """
    try:
        # get users from Okta api and .
        okta_users_data = okta_client.get_users_data()
        data_processor.extract_data(okta_users_data, {"id", "statusChanged", "lastLogin", "passwordChanged",
                                                      "name", "email"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get users from Okta API: {str(e)}")

    # upload the okta_users_data to db.

    raw_users_data = okta_client.get_admin_users(OKTA_ADMIN_GROUP_ID)
    users_data_list = data_processor.extract_data(raw_users_data, {"id", "statusChanged", "lastLogin",
                                                                   "passwordChanged", "name", "email"})

    data_processor.update_admin_field(raw_users_data, users_data_list)

    # upload_user_data_to_db(okta_users_data)
    user_repository.upload_user_data_to_db(users_data_list)

    return {"okta users insert successfully."}


@users.get("/results")
def get_users_scan_results():
    """
    displays the results of the last scan on this route.
    :return:
    """
    try:
        response = user_repository.scan_table()
        return [serialize_okta_user(res) for res in response]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal server error. details:{e}")


@users.get("/{email}")
def get_last_user_login(email):
    """
    function get user_id from client and return the last login event for this user.

    :return:
    """
    try:
        # get user details from DynamoDB.
        user_details = user_repository.get_user_by_email(email)

        if user_details.lastLogin == "":
            return {f"user {user_details.name}, has not logged in yet."}
        else:
            return {"user": user_details.name, "last_login": user_details.lastLogin}

    except Exception:
        raise HTTPException(status_code=404, detail="User not found.")


@users.get("/admin/{email}")
def show_last_password_changed_for_admins(email):
    """
    The function receives A email and returns when the password was last changed.
    The function returns the appropriate value only for those who are defined as admin in the system.

    Admin settings in the system:
    1. in DynamoDb, only admin have the field 'admin': True.
    2. in Okta, only those who are admins are in a group called 'admins'.

    :return: The last time the password was changed.
    """
    try:
        # get user details from DynamoDB.
        user_details = user_repository.get_user_by_email(email)

    except Exception:
        raise HTTPException(status_code=404, detail="User not found.")

    else:
        # check if this user is admin.
        if user_details.admin:

            response = user_details.passwordChanged
            if response == '':
                return {f"{user_details.name} hasn't changed his password yet."}
            return {f"password changed last time at: {response}"}
        else:
            return {f"only the admin user has permissions to see when the password was last changed."}


@users.get("/admin/")
def highlight_admins_with_old_password():
    # get all admins in organization.
    try:
        admins = user_repository.get_admins_list()
        expired_admins = {}

        # check for all admins if they had an old password:
        for admin in admins:
            if admin.passwordChanged:
                last_changed_date = parse_datetime(admin.passwordChanged)

                if last_changed_date < (datetime.now() - timedelta(days=7)):
                    expired_admins[admin.name] = admin.passwordChanged

        return expired_admins

    except ScanError as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB Scan Error: {str(e)}")


@users.post("/scan/")
def initiate_new_scan_from_s3_link(scan_request: str):
    """
    1. get s3 link to .csv file from client.
    2. parse the data from file to list[dict].
    3. upload the data to dynamoDB table.

    command for testing this function:
    curl -X POST "http://127.0.0.1:8001/users/scan/" -H "Content-Type: application/json" -d
     '{"s3_link": "https://breeze-home-assigment.s3.eu-west-1.amazonaws.com/HomeAssigment-2.csv"}'



    :param scan_request: link to AWS S3 link with .csv file to parse.
    :return:
    """
    # get the s3 link file from client.
    s3_link = scan_request.s3_link

    try:
        # parse it to list of dictionaries.
        users_data_list = read_csv_from_s3(s3_link)

    except Exception as e:
        HTTPException(status_code=500, detail=f"An error occurred while processing the CSV file: {str(e)}")

    else:
        try:
            # update the users data to DB.
            user_service.update_users_from_csv(users_data_list)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while processing the CSV file: {str(e)}")
        return ".csv results updated successfully in DB."
