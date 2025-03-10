from fastapi import APIRouter, HTTPException
from app.dynamo_db.models import OktaUser, ScanRequest
from app.dynamo_db.repositories import UserRepository
from app.dynamo_db.service import UserService
from app.api.utils import parse_datetime, serialize_okta_user, read_csv_from_s3, DataProcessor
from pynamodb.exceptions import ScanError
from datetime import datetime, timedelta
from app.api.okta import OktaClient
from app_config import OKTA_DOMAIN, OKTA_API_TOKEN
from app.services.identity_service import IdentityService
from app.services.redis_service import RedisService
import json


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

# initialize IdentityService.
identity_service = IdentityService(api_service=okta_client, data_processor=data_processor)

# initialize redis service for cache handling.
redis_service = RedisService()


@users.get("/")
def insert_okta_users_to_db():
    """
    when client login to url 'http://localhost/users/' we insert the scan results we get from Okta api.
    :return:
    """
    relevant_fields = {"id", "statusChanged", "lastLogin", "passwordChanged",
                                                           "name", "email"}
    cache_key = "okta_users_data"

    # get cache data from redis.
    cached_data = redis_service.get(cache_key)

    if cached_data:
        return {"okta users fetched from cache."}

    try:
        # get users from external api and data processor and extract this data.
        users_data_dict = identity_service.get_users_data(relevant_fields)
        # insert relevant data to redis.
        redis_service.set(cache_key, json.dumps(users_data_dict), ex=500)

        # upload_user_data_to_db(okta_users_data)
        user_repository.upload_user_data_to_db(users_data_dict)
        return {"okta users insert successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get users from Okta API: {str(e)}")


@users.get("/results")
def get_users_scan_results():
    """
    displays the results of the last scan on this route.
    :return:
    """
    cache_scan_key = 'scan results'
    cached_data = redis_service.get(cache_scan_key)

    if cached_data is not None:
        return json.loads(cached_data)

    try:
        response = user_repository.scan_table()
        results = [serialize_okta_user(res) for res in response]

        # save results in redis for 500 seconds in json format.
        redis_service.set(cache_scan_key, json.dumps(results), ex=60)
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"internal server error. details:{e}")


@users.get("/{email}")
def get_last_user_login(email):
    """
    function get user_id from client and return the last login event for this user.

    :return:
    """
    last_login_cache_key = f"user_details:{email}"
    cached_data = redis_service.get(last_login_cache_key)

    if cached_data:
        return json.loads(cached_data)

    try:
        # get user details from DynamoDB.
        user_details = user_repository.get_user_by_email(email)

        if user_details.lastLogin == "":
            response = {f"user {user_details.name}, has not logged in yet."}
        else:
            response = {"user": user_details.name, "last_login": user_details.lastLogin}

        # save result in redis.
        redis_service.set(last_login_cache_key, json.dumps(response), ex=60)

        return response

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
    cache_key = f"user_details:{email}"
    cached_data = redis_service.get(cache_key)

    if cached_data:
        user_details = json.loads(cached_data)
    else:
        try:
            # get user details from DynamoDB.
            user_details = user_repository.get_user_by_email(email)
            # save user details in Redis for cache use.
            redis_service.set(cache_key, json.dumps(user_details), ex=3600)

        except Exception:
            raise HTTPException(status_code=404, detail="User not found.")

    # check if this user is admin.
    if user_details['attribute_values'].get("admin"):
        response = user_details['attribute_values'].get("'passwordChanged'")
        redis_service.set(cache_key, json.dumps(user_details))

        if response == '':
            return {f"{user_details['attribute_values'].get("name")} hasn't changed his password yet."}
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
def initiate_new_scan_from_s3_link(scan_request: ScanRequest):
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
    cache_key = f"s3_cache:{s3_link}"

    # check if file from s3 exist in redis.
    cached_data = redis_service.get(cache_key)

    if cached_data:
        # if file already in cache -> return message to client.
        return {"message": "Data already cached, skipping S3 and DB update."}

    else:
        try:
            # parse it to list of dictionaries.
            users_data_list = read_csv_from_s3(s3_link)

            # Store parsed data in Redis.
            redis_service.set(cache_key, json.dumps(users_data_list), ex=6000)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while processing the CSV file: {str(e)}")

    try:
        # update the users data to DB.
        user_service.update_users_from_csv(users_data_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while updating users in the database: {str(e)}")

    return ".csv results updated successfully in DB."
