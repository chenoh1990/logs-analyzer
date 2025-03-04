from datetime import datetime, timezone


class UserService:
    """
      This class contains the business logic for managing user data in the system.
      It acts as a bridge between the user data repository (UserRepository) and the client-facing
      application. The responsibilities of this class include processing user data, applying business
      rules, and coordinating updates to the user data in the database.

      The UserService class should not be concerned with direct database access. Instead, it delegates
      all database interactions to the UserRepository class. This ensures that the service layer focuses
      on business logic, while the repository layer is responsible for handling data persistence.

      Note:
      The UserService should never directly interact with the database. All database access is handled
      by the UserRepository class. This separation of concerns ensures that the service layer is focused
      on applying the business rules and the repository layer is dedicated to handling data storage
      and retrieval operations.
      """

    def __init__(self, user_repository):
        self.user_repository = user_repository

    def update_users_from_csv(self, users_data):
        """
        get users_data and update the relevant users in DB.
        - if user get admin role -> changed the field in DB to True.
        - if user login in system -> update the lasLogin field in db.
        - if password changed -> update the passwordChanged field in db.

        :param users_data:list[dict] data from s3 link we received from client.

        :return: message of successful update.
        """

        for user in users_data:
            email = user.get("User Email")
            timestamp = user.get("Timestamp")
            event_description = user.get("Event Description")

            # skip invalid events
            if not email or not timestamp or not event_description:
                continue

            try:
                formatted_timestamp = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat() + "Z"

            except ValueError:
                continue

            # Fetch user from DB.
            try:
                res = self.user_repository.get_user_by_email(email)
            except self.user_repository.DoesNotExist:
                continue

            if res:
                # update lastLogin field.
                if "Login" in event_description:
                    res.lastLogin = formatted_timestamp

                # update passwordChanged field
                elif "Password" in event_description:
                    res.passwordChanged = formatted_timestamp

                # update admin field if "Admin Role Granted" event occurs
                elif event_description == "Admin Role Granted":
                    res.admin = "True"

                else:
                    # for other events -> change in user_events field
                    if not res.user_events:
                        res.user_events = []
                    res.user_events.append({
                        'Timestamp': datetime.utcfromtimestamp(int(timestamp)).isoformat(),
                        'Event Description': event_description
                    })

                # save changes.
                res.save()

        return "users details changes successfully in DB."
