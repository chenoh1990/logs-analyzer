from pynamodb.exceptions import ScanError


class UserRepository:
    """
    The UserRepository class is responsible for managing the interaction between the application and the DynamoDB
     database for user-related operations.

    Its main role is to provide an abstraction layer for querying, updating, and scanning user data in the database,
     while ensuring that the database interactions
    are centralized in one place. This improves maintainability and scalability, as any changes to the database model
     or logic can be managed within this class.

    Key functionalities provided by this class include:
    - Fetching a user by email (partition key in DynamoDB).
    - Scanning the database to retrieve a list of all users.
    - Updating user attributes, such as setting a user as an admin.

    By using this repository pattern, it is easier to test the application and modify database access logic
     without affecting the rest of the application.
    """

    def __init__(self, okta_user_model):
        self.okta_user_model = okta_user_model

    def get_user_by_email(self, email):
        """
        :param email: email (str)
        :return: the relevant user values by the given email(partition key in dynamoDB table).
        """
        try:
            user = self.okta_user_model.get(hash_key=email)
            return user

        except self.okta_user_model.DoesNotExist:
            return None

    def scan_table(self):
        """
        :return: return list if all users in Users table, in case of error - raise ScanError.
        """
        try:
            res = list(self.okta_user_model.scan())
            return res

        except ScanError as e:
            raise ScanError(f"An error occurred during the scan operation: {str(e)}")

    def get_admins_list(self):
        """
        :return: return list of all admins in organization.
        """
        try:
            # get all admins from DB.
            admins = list(self.okta_user_model.scan(filter_condition=(self.okta_user_model.admin == "True")))

        except ScanError as e:
            raise ScanError(f"An error occurred during the scan operation: {str(e)}")

        else:
            return admins

    def upload_user_data_to_db(self, users):
        """
        upload users to dynamodb table -> if they exist -> update to recent values.
        :param users:
        :return:
        """
        for user_id, user_data in users.items():
            try:
                email = user_data["email"]

                # Check if the user already exists in the DB
                existing_user = self.okta_user_model.get(email, consistent_read=True)

                # if user exists, update relevant fields
                existing_user.lastLogin = user_data.get("lastLogin", existing_user.lastLogin) or ""
                existing_user.passwordChanged = user_data.get("passwordChanged", existing_user.passwordChanged) or ""
                existing_user.statusChanged = user_data.get("statusChanged", existing_user.statusChanged) or ""

                existing_user.save()

            except self.okta_user_model.DoesNotExist:
                try:
                    # Create a new user if not found
                    new_user = self.okta_user_model(
                        email=email,
                        admin=str(user_data.get("admin", False)),
                        lastLogin=user_data.get("lastLogin") or "",
                        name=user_data.get("name") or "",
                        passwordChanged=user_data.get("passwordChanged") or "",
                        statusChanged=user_data.get("statusChanged") or "",
                        id=user_id
                    )
                    new_user.save()

                except Exception as e:
                    print(e)

            except Exception as e:
                print(f"Error processing user {email}: {str(e)}")
