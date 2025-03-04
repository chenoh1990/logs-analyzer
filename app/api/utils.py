from datetime import datetime, timezone
import requests
from pynamodb.models import Model
from io import StringIO
import csv
from typing import Dict, Any


def read_csv_from_s3(s3_url: str):
    """
       read a CSV file from a public S3 URL and return the contents as a list of dictionaries.

       :param s3_url: The public S3 URL of the file to read.
       :return: List of dictionaries representing the CSV rows.
       """
    try:
        # Fetch the CSV file using the public URL.
        response = requests.get(s3_url)

        # Check if the request was successful
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve file: {response.status_code}")

        # Get the CSV content.
        csv_content = response.text

        # Use StringIO to simulate a file object from the CSV content.
        file_like_object = StringIO(csv_content)

        # Use csv.DictReader to read the CSV as a dictionary
        reader = csv.DictReader(file_like_object)
        return [row for row in reader]

    except requests.exceptions.RequestException as e:
        # Handle any exceptions raised by the requests library
        raise requests.exceptions.RequestException(f"Error fetching the file from S3: {str(e)}")

    except Exception as e:
        # General error handling for unexpected issues (e.g., CSV parsing errors)
        raise requests.exceptions.RequestException(f"An error occurred while processing the CSV file: {str(e)}")


def parse_datetime(date):
    """

    :param date:date of last time that password changed in str format.
    :return: the date in datetime format.
    """
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")


def serialize_okta_user(instance: Model) -> Dict[str, Any]:

    """
    Convert any PynamoDB model instance to a dictionary dynamically.

    :param instance: An instance of a PynamoDB model.
    :return: Dictionary representation of the model.
    """
    if not isinstance(instance, Model):
        raise ValueError("The provided instance is not a valid PynamoDB model.")

    return {attr: getattr(instance, attr) for attr in instance._get_attributes().keys()}


class DataProcessor:
    """
    The DataProcessor class is responsible for processing the user data retrieved from external APIs
    and preparing it for further use, such as storing it in a database.

    This class provides an abstraction layer that simplifies the management of user data and ensures that
    only relevant data is passed along to the next stages of processing (such as database storage).

    """

    def __init__(self, api_client):
        self.api_client = api_client

    @staticmethod
    def extract_data(raw_users_data, relevant_fields):
        """

        :param raw_users_data:
        :param relevant_fields: field we would like to include in DB.

        :return: list of all users with relevant data.
        """
        users_data = {}

        for user in raw_users_data:
            user_dict = {}

            for field in relevant_fields:
                if field in user:
                    user_dict[field] = user[field]

                # combine the fields 'name', 'last name' into one field in DB.
                elif (field == "name" and "profile" in user and "firstName" in user["profile"]
                      and "lastName" in user["profile"]):
                    user_dict["name"] = f"{user['profile']['firstName']} {user['profile']['lastName']}"

                # get email field from user['profile']
                elif field == "email" and "profile" in user and "email" in user["profile"]:
                    user_dict["email"] = user["profile"]["email"]

            users_data[user['id']] = user_dict

        return users_data

    @staticmethod
    def update_admin_field(group_members, users_data):
        """
        update admin field for updating in DB.
        - if is admin user -> update to True.
        :return:
        """
        admin_users_id = {user['id'] for user in group_members}

        for user_id, user_info in users_data.items():
            if user_id in admin_users_id:
                user_info['admin'] = True
            else:
                user_info['admin'] = False
