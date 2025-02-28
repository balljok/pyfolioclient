"""
Interface for Folio API providing comprehensive methods to interact with various FOLIO modules.

This class extends FolioBaseClient and implements methods for common FOLIO operations,
particularly focusing on users, inventory, circulation, and related functionalities. It utilizes
both business logic and storage module endpoints for different operations.

The client implements iterator patterns for most GET operations to handle large datasets
efficiently and avoid timeout issues. It provides both direct retrieval methods (get_*)
and iterator methods (iter_*) for flexibility in data handling.

Attributes:
    Inherits all attributes from FolioBaseClient

Usage Example:
    ```python
    with FolioClient() as folio:
        for user in folio.iter_users("active==True"):
            print(user["username"])
    ```

Notes:
    - Methods use iterators to avoid loading all data at once and risking timeouts or exceptions.
    
References:
    Folio provides endoints to both business logic modules and storage modules. For example:
    GET /inventory/items
    GET /item-storage/items

    Please refer to this page to understand the differences:
    https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from ._exceptions import BadRequestError, ItemNotFoundError
from .foliobaseclient import FolioBaseClient


class FolioClient(FolioBaseClient):
    """
    FolioClient contains methods for the most common interactions with Folio.
    It can be used as is, for inspiration, or simply ignored.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __enter__(self) -> "FolioClient":
        return self

    # USERS

    def get_users(self, cql_query: str = "") -> list:
        """Get users.

        Args:
            query (str, optional): CQL query string to filter results.

        Returns:
            list: List of user objects.
        """
        return list(self.iter_data("/users", key="users", cql_query=cql_query))

    def iter_users(self, cql_query: str = "") -> Generator:
        """
        Iterate over users.
        This method provides a generator to iterate through all users that match the given query.
        Args:
            query (str, optional): CQL query string to filter users. Defaults to empty string,
                which returns all users.
        Yields:
            dict: A dictionary containing user data for each matching user record.
        """
        yield from self.iter_data("/users", key="users", cql_query=cql_query)

    def get_user_by_id(self, uuid: str) -> dict:
        """
        Retrieves user information by UUID from FOLIO.
        Args:
            uuid (str): The UUID of the user to retrieve.
        Returns:
            dict: A dictionary containing user information if found, empty dict if not found.
        """
        response = self.get_data(f"/users/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def get_user_bl_by_id(self, uuid: str) -> dict:
        """
        Retrieves user information by UUID from FOLIO using business logic API.
        Args:
            uuid (str): The UUID of the user to retrieve.
        Returns:
            dict: A dictionary containing user information if found, empty dict if not found.
        """
        response = self.get_data(f"/bl-users/by-id/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def get_user_by_barcode(self, barcode: str) -> dict:
        """
        Retrieves user information by barcode from FOLIO.
        Args:
            uuid (str): The barcode of the user to retrieve.
        Returns:
            dict: A dictionary containing user information if found, empty dict if not found.
        """
        response = self.get_data(
            "/users", key="users", cql_query=f"barcode=={barcode}", limit=1
        )
        if isinstance(response, list) and len(response) > 1:
            raise RuntimeError("Multiple users found with the same barcode")
        return response[0] if isinstance(response, list) else {}

    def create_user(self, payload: dict) -> dict:
        """Creates a new user in FOLIO and initializes their permissions.
        This method creates a new user account in FOLIO and adds an empty permissions set.
        The user creation requires certain mandatory fields in the payload.
        Args:
            payload (dict): A dictionary containing the user information with required fields:
                - username
                - patronGroup
                - personal (dict) containing:
                    - lastName
                    - email
                    - preferredContactTypeId
        Returns:
            dict: The response from the user creation API containing the created user's information
        Raises:
            ValueError: If any required fields are missing in the payload
            RuntimeError: If user creation fails or if permission initialization fails
        """
        # Require the same fields that are required when creating a new user in the Folio UI
        if not (
            "username" in payload
            and "patronGroup" in payload
            and "personal" in payload
            and "lastName" in payload["personal"]
            and "email" in payload["personal"]
            and "preferredContactTypeId" in payload["personal"]
        ):
            raise ValueError("Required fields missing in payload")

        response = self.post_data("/users", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to create user")
        # In addition to creating a user, we need to create an empty permissions set
        user_id = response.get("id")
        empty_permissions_set = {"userId": user_id, "permissions": []}
        perms_response = self.post_data("/perms/users", payload=empty_permissions_set)
        if isinstance(perms_response, int):
            raise RuntimeError(f"Failed to create permissions for user {user_id}")
        return response

    def update_user(self, uuid: str, payload: dict) -> dict | int:
        """Updates a user in FOLIO.
        Args:
            uuid (str): The UUID of the user to update.
            payload (dict): Dictionary containing the updated user data.
        Returns:
            Union[dict, int]: Response from the API containing the updated user data or status code.
        Raises:
            BadRequestError: If the payload contains issues.
            ItemNotFoundError: If the user with the given UUID is not found.
            RuntimeError: If there is a general failure in updating the user.
        """
        try:
            response = self.put_data(f"/users/{uuid}", payload=payload)
        except BadRequestError as req_err:
            raise BadRequestError(f"Failed to update user: {req_err}") from req_err
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"User not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to update user: {run_err}") from run_err
        return response

    def delete_user(self, uuid: str) -> int:
        """Delete a user from FOLIO.
        Args:
            uuid (str): UUID of the user to delete
        Returns:
            int: HTTP status code of the delete operation if successful
        Raises:
            ItemNotFoundError: If user with given UUID is not found
            RuntimeError: If deletion operation fails for any other reason
        """
        try:
            response = self.delete_data(f"/users/{uuid}")
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"User not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to delete user: {run_err}") from run_err
        return response

    # INSTANCES

    # HOLDINGS

    # ITEMS

    # LOANS

    def get_loans(self, cql_query: str = "") -> list:
        """Get all loans. Query can be used to filter results."""
        return list(
            self.iter_data("/loan-storage/loans", key="loans", cql_query=cql_query)
        )

    def iter_loans(self, cql_query: str = "") -> Generator:
        """Get all loans, yielding results one by one"""
        yield from self.iter_data(
            "/loan-storage/loans", key="loans", cql_query=cql_query
        )

    def get_open_loans_by_due_date(self, start: str, end: str | None = None) -> list:
        """Get loans with a given due date. Suppors both intervals and single dates.

        Args:
            start (str): Start date for interval or single date. Format: "YYYY-MM-DD"
            end (str | None, optional): End date for interval. Format: "YYYY-MM-DD".

        Raises:
            ValueError: Invalid date format
            ValueError: Start date cannot be after end date

        Returns:
            list: Loans with a given due date or within a given interval
        """
        try:
            datetime.strptime(start, "%Y-%m-%d")
            if end:
                datetime.strptime(end, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Invalid date format") from exc
        if end and start > end:
            raise ValueError("Start date cannot be after end date")
        if end:
            cql_query = (
                f"(((dueDate>{start} and dueDate<{end}) "
                f"or dueDate={start} or dueDate={end}) "
                "and status.name==Open)"
            )
        else:
            cql_query = f"dueDate={start} and status.name==Open"
        return list(
            self.iter_data("/loan-storage/loans", key="loans", cql_query=cql_query)
        )

    def iter_open_loans_by_due_date(
        self, start: str, end: str | None = None
    ) -> Generator:
        """Yield loans with a given due date. Suppors both intervals and single dates.

        Args:
            start (str): Start date for interval or single date. Format: "YYYY-MM-DD"
            end (str | None, optional): End date for interval. Format: "YYYY-MM-DD".

        Raises:
            ValueError: Invalid date format
            ValueError: Start date cannot be after end date

        Yields:
            Generator: Yields one matched loan at a time
        """
        try:
            datetime.strptime(start, "%Y-%m-%d")
            if end:
                datetime.strptime(end, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Invalid date format") from exc
        if end and start > end:
            raise ValueError("Start date cannot be after end")
        if end:
            cql_query = (
                f"(((dueDate>{start} and dueDate<{end}) "
                f"or dueDate={start} or dueDate={end}) "
                "and status.name==Open)"
            )
        else:
            cql_query = f"dueDate={start} and status.name==Open"
        yield from self.iter_data(
            "/loan-storage/loans", key="loans", cql_query=cql_query
        )

    # LOCATIONS

    # MISCELLANEOUS
