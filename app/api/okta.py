import requests


class OktaClient:
    """
        The OktaAPIClient class is responsible for fetching user data from the Okta API.

        It handles the construction of the API request, making the HTTP GET call to retrieve user data,
        and processing the response. The class ensures that the interaction with the Okta API is abstracted
        and centralized, making it easier to maintain and modify.
    """

    def __init__(self, okta_domain: str, api_key: str):
        self.okta_domain = okta_domain
        self.api_key = api_key

    def get_users_data(self):
        """
        get users from Okta API.
        """
        url = f"https://{self.okta_domain}/api/v1/users"
        headers = {"Authorization": f"SSWS {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)

            # Raise exception for bad responses
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching users data: {e}")
            return []

    def get_admin_users(self, admin_group_id):
        """
            :param admin_group_id:

            return: function get list if all users and insert for admin field only for admin users in organization.
        """
        url = "https://" + self.okta_domain + f"/api/v1/groups/{admin_group_id}/users"
        headers = {"Authorization": f"SSWS {self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException:
            return []
