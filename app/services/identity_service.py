class IdentityService:
    """
    The IdentityService class acts as an intermediary between the client and the external API (e.g., Okta).
    It fetches and processes user data, extracting relevant fields, while delegating data manipulation to the
    DataProcessor class. This separates the business logic from the data handling.

    """
    def __init__(self, api_service, data_processor):
        self.api_service = api_service
        self.data_processor = data_processor

    def get_users_data(self, relevant_fields):
        try:
            users_data = self.api_service.get_users_data()
            return self.data_processor.extract_data(users_data, relevant_fields)

        except Exception as e:
            raise ValueError(f"Failed to retrieve users data: {str(e)}")

    def get_admin_users(self, admin_group_id, relevant_fields):
        try:
            admin_users = self.api_service.get_admin_users(admin_group_id)
            return self.data_processor.extract_data(admin_users, relevant_fields)

        except Exception as e:
            raise ValueError(f"Failed to retrieve admin users: {str(e)}")