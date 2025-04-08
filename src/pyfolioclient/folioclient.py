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
    with FolioClient(base_url, tenant, user, password) as folio:
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
        # API docs (v16.1) for /users does not properly document required fields
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

    def get_instances(self, cql_query: str = "") -> list:
        """Get all instances. Query can be used to filter results."""
        return list(
            self.iter_data(
                "/instance-storage/instances", key="instances", cql_query=cql_query
            )
        )

    def iter_instances(self, cql_query: str = "") -> Generator:
        """Get all instances, yielding results one by one"""
        yield from self.iter_data(
            "/instance-storage/instances", key="instances", cql_query=cql_query
        )

    def get_instance_by_id(self, uuid: str) -> dict:
        """
        Retrieves instance information by UUID from FOLIO.
        Args:
            uuid (str): The UUID of the instance to retrieve.
        Returns:
            dict: A dictionary containing instance information if found, empty dict if not found.
        """
        response = self.get_data(f"/instance-storage/instances/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def create_instance(self, payload: dict) -> dict:
        """
        Create a new instance in FOLIO.
        Args:
            payload (dict): Dictionary containing the instance data to be created.
        Returns:
            dict: Response from FOLIO containing the created instance data.
        Raises:
            RuntimeError: If the instance creation fails.
        """
        # Required fields according to API docs (v11.0)
        if not (
            "instanceTypeId" in payload and "source" in payload and "title" in payload
        ):
            raise ValueError("Required fields missing in payload")
        response = self.post_data("/instance-storage/instances", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to create instance")
        return response

    def update_instance(self, uuid: str, payload: dict) -> dict | int:
        """Updates an instance in FOLIO.
        Args:
            uuid (str): The UUID of the instance to update.
            payload (dict): Dictionary containing the updated instance data.
        Returns:
            Union[dict, int]: Response from the API containing the updated data or status code.
        Raises:
            BadRequestError: If the payload contains issues.
            ItemNotFoundError: If the instance with the given UUID is not found.
            RuntimeError: If there is a general failure in updating the instance.
        """
        try:
            response = self.put_data(
                f"/instance-storage/instances/{uuid}", payload=payload
            )
        except BadRequestError as req_err:
            raise BadRequestError(f"Failed to update instance: {req_err}") from req_err
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Holding not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to update instance: {run_err}") from run_err
        return response

    def delete_instance(self, uuid: str) -> int:
        """Delete an instance from FOLIO.
        Args:
            uuid (str): UUID of the instance to delete
        Returns:
            int: HTTP status code of the delete operation if successful
        Raises:
            ItemNotFoundError: If instance with given UUID is not found
            RuntimeError: If deletion operation fails for any other reason
        """
        try:
            response = self.delete_data(f"/instance-storage/instances/{uuid}")
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Instance not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to delete instance: {run_err}") from run_err
        return response

    # HOLDINGS

    def get_holdings(self, cql_query: str = "") -> list:
        """Get all holdings. Query can be used to filter results."""
        return list(
            self.iter_data(
                "/holdings-storage/holdings", key="holdingsRecords", cql_query=cql_query
            )
        )

    def iter_holdings(self, cql_query: str = "") -> Generator:
        """Get all holdings, yielding results one by one"""
        yield from self.iter_data(
            "/holdings-storage/holdings", key="holdingsRecords", cql_query=cql_query
        )

    def get_holding_by_id(self, uuid: str) -> dict:
        """
        Retrieves holding information by UUID from FOLIO.
        Args:
            uuid (str): The UUID of the holding to retrieve.
        Returns:
            dict: A dictionary containing holding information if found, empty dict if not found.
        """
        response = self.get_data(f"/holdings-storage/holdings/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def create_holding(self, payload: dict) -> dict:
        """
        Create a new holding in FOLIO.
        Args:
            payload (dict): Dictionary containing the holding data to be created.
        Returns:
            dict: Response from FOLIO containing the created holding data.
        Raises:
            RuntimeError: If the holding creation fails.
        """
        # Required fields according to API docs (v6.0)
        if not ("instanceId" in payload and "permanentLocationId" in payload):
            raise ValueError("Required fields missing in payload")
        response = self.post_data("/holdings-storage/holdings", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to create holding")
        return response

    def update_holding(self, uuid: str, payload: dict) -> dict | int:
        """Updates a holding in FOLIO.
        Args:
            uuid (str): The UUID of the holding to update.
            payload (dict): Dictionary containing the updated holding data.
        Returns:
            Union[dict, int]: Response from the API containing the updated data or status code.
        Raises:
            BadRequestError: If the payload contains issues.
            ItemNotFoundError: If the holding with the given UUID is not found.
            RuntimeError: If there is a general failure in updating the holding.
        """
        try:
            response = self.put_data(
                f"/holdings-storage/holdings/{uuid}", payload=payload
            )
        except BadRequestError as req_err:
            raise BadRequestError(f"Failed to update holding: {req_err}") from req_err
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Holding not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to update holding: {run_err}") from run_err
        return response

    def delete_holding(self, uuid: str) -> int:
        """Delete a holding from FOLIO.
        Args:
            uuid (str): UUID of the holding to delete
        Returns:
            int: HTTP status code of the delete operation if successful
        Raises:
            ItemNotFoundError: If holding with given UUID is not found
            RuntimeError: If deletion operation fails for any other reason
        """
        try:
            response = self.delete_data(f"/holdings-storage/holdings/{uuid}")
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Holding not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to delete holding: {run_err}") from run_err
        return response

    # ITEMS

    def get_items(self, cql_query: str = "") -> list:
        """Get all items. Query can be used to filter results."""
        return list(
            self.iter_data("/item-storage/items", key="items", cql_query=cql_query)
        )

    def iter_items(self, cql_query: str = "") -> Generator:
        """Get all items, yielding results one by one"""
        yield from self.iter_data(
            "/item-storage/items", key="items", cql_query=cql_query
        )

    def get_item_by_id(self, uuid: str) -> dict:
        """
        Retrieves item information by UUID from FOLIO.
        Args:
            uuid (str): The UUID of the item to retrieve.
        Returns:
            dict: A dictionary containing item information if found, empty dict if not found.
        """
        response = self.get_data(f"/item-storage/items/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def create_item(self, payload: dict) -> dict:
        """
        Create a new item in FOLIO.
        Args:
            payload (dict): Dictionary containing the item data to be created.
        Returns:
            dict: Response from FOLIO containing the created item data.
        Raises:
            RuntimeError: If the item creation fails.
        """
        # Required fields according to API docs (v10.0)
        if not (
            "permanentLoanTypeId" in payload
            and "holdingsRecordId" in payload
            and "materialTypeId" in payload
            and "status" in payload
            and "name" in payload["status"]
        ):
            raise ValueError("Required fields missing in payload")
        response = self.post_data("/item-storage/items", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to create item")
        return response

    def update_item(self, uuid: str, payload: dict) -> dict | int:
        """Updates an item in FOLIO.
        Args:
            uuid (str): The UUID of the item to update.
            payload (dict): Dictionary containing the updated item data.
        Returns:
            Union[dict, int]: Response from the API containing the updated data or status code.
        Raises:
            BadRequestError: If the payload contains issues.
            ItemNotFoundError: If the item with the given UUID is not found.
            RuntimeError: If there is a general failure in updating the item.
        """
        try:
            response = self.put_data(f"/item-storage/items/{uuid}", payload=payload)
        except BadRequestError as req_err:
            raise BadRequestError(f"Failed to update item: {req_err}") from req_err
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Item not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to update item: {run_err}") from run_err
        return response

    def delete_item(self, uuid: str) -> int:
        """Delete an item from FOLIO.
        Args:
            uuid (str): UUID of the item to delete
        Returns:
            int: HTTP status code of the delete operation if successful
        Raises:
            ItemNotFoundError: If item with given UUID is not found
            RuntimeError: If deletion operation fails for any other reason
        """
        try:
            response = self.delete_data(f"/item-storage/items/{uuid}")
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Instance not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to delete item: {run_err}") from run_err
        return response

    # LOANS

    def get_loans(self, cql_query: str = "") -> list:
        """Get all loans. Query can be used to filter results."""
        return list(
            self.iter_data("/loan-storage/loans", key="loans", cql_query=cql_query)
        )

    def get_loans_bl(self, cql_query: str = "") -> list:
        """Get all loans. Query can be used to filter results. Uses business logic API."""
        return list(
            self.iter_data("/circulation/loans", key="loans", cql_query=cql_query)
        )

    def iter_loans(self, cql_query: str = "") -> Generator:
        """Get all loans, yielding results one by one"""
        yield from self.iter_data(
            "/loan-storage/loans", key="loans", cql_query=cql_query
        )

    def iter_loans_bl(self, cql_query: str = "") -> Generator:
        """Get all loans, yielding results one by one. Uses business logic API."""
        yield from self.iter_data(
            "/circulation/loans", key="loans", cql_query=cql_query
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

    def get_open_loans_by_due_date_bl(self, start: str, end: str | None = None) -> list:
        """Get loans with a given due date. Suppors both intervals and single dates.
        Uses business logic API.

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
            self.iter_data("/circulation/loans", key="loans", cql_query=cql_query)
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

    def iter_open_loans_by_due_date_bl(
        self, start: str, end: str | None = None
    ) -> Generator:
        """Yield loans with a given due date. Suppors both intervals and single dates.
        Uses business logic API.

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
            "/circulation/loans", key="loans", cql_query=cql_query
        )

    def renew_loan_by_barcode(self, item_barcode: str, user_barcode: str) -> dict:
        """
        Renews a loan by using item and user barcodes.
        Args:
            item_barcode (str): The barcode of the item to be renewed
            user_barcode (str): The barcode of the user who wants to renew the loan
        Returns:
            dict: Response from the FOLIO circulation API containing the renewed loan details
        Raises:
            RuntimeError: If the renewal request fails
        """

        payload: dict = {
            "itemBarcode": item_barcode,
            "userBarcode": user_barcode,
        }

        response = self.post_data("circulation/renew-by-barcode", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to renew loan")
        return response

    def renew_loan_by_id(self, item_uuid: str, user_uuid: str) -> dict:
        """
        Renews a loan by using item and user UUID:s.
        Args:
            item_barcode (str): The UUID of the item to be renewed
            user_barcode (str): The UUID of the user who wants to renew the loan
        Returns:
            dict: Response from the FOLIO circulation API containing the renewed loan details
        Raises:
            RuntimeError: If the renewal request fails
        """

        payload: dict = {
            "itemId": item_uuid,
            "userId": user_uuid,
        }

        response = self.post_data("circulation/renew-by-id", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to renew loan")
        return response

    # REQUESTS

    def get_requests(self, cql_query: str = "") -> list:
        """Get all requests. Query can be used to filter results."""
        return list(
            self.iter_data(
                "/request-storage/requests", key="requests", cql_query=cql_query
            )
        )

    def iter_requests(self, cql_query: str = "") -> Generator:
        """Get all requests, yielding results one by one"""
        yield from self.iter_data(
            "/request-storage/requests", key="requests", cql_query=cql_query
        )

    def get_request_by_id(self, uuid: str) -> dict:
        """
        Retrieves request information by UUID from FOLIO.
        Args:
            uuid (str): The UUID of the request to retrieve.
        Returns:
            dict: A dictionary containing request information if found, empty dict if not found.
        """
        response = self.get_data(f"/request-storage/requests/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def create_request(self, payload: dict) -> dict:
        """
        Create a new request in FOLIO.
        Args:
            payload (dict): Dictionary containing the request data to be created.
        Returns:
            dict: Response from FOLIO containing the created request data.
        Raises:
            RuntimeError: If the request creation fails.
        """
        # Required fields according to API docs (v5.0)
        if not (
            "fulfillmentPreference" in payload
            and "instanceId" in payload
            and "requestDate" in payload
            and "status" in payload
            and "requestLevel" in payload
            and "requesterId" in payload
            and "requestType" in payload
        ):
            raise ValueError("Required fields missing in payload")
        response = self.post_data("/request-storage/requests", payload=payload)
        if isinstance(response, int):
            raise RuntimeError("Failed to create request")
        return response

    def update_request(self, uuid: str, payload: dict) -> dict | int:
        """Updates a request in FOLIO.
        Args:
            uuid (str): The UUID of the request to update.
            payload (dict): Dictionary containing the updated request data.
        Returns:
            Union[dict, int]: Response from the API containing the updated data or status code.
        Raises:
            BadRequestError: If the payload contains issues.
            ItemNotFoundError: If the request with the given UUID is not found.
            RuntimeError: If there is a general failure in updating the request.
        """
        try:
            response = self.put_data(
                f"/request-storage/requests/{uuid}", payload=payload
            )
        except BadRequestError as req_err:
            raise BadRequestError(f"Failed to update request: {req_err}") from req_err
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Request not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to update request: {run_err}") from run_err
        return response

    def delete_request(self, uuid: str) -> int:
        """Delete a request from FOLIO.
        Args:
            uuid (str): UUID of the request to delete
        Returns:
            int: HTTP status code of the delete operation if successful
        Raises:
            ItemNotFoundError: If request with given UUID is not found
            RuntimeError: If deletion operation fails for any other reason
        """
        try:
            response = self.delete_data(f"/request-storage/requests/{uuid}")
        except ItemNotFoundError as item_err:
            raise ItemNotFoundError(f"Request not found: {item_err}") from item_err
        except RuntimeError as run_err:
            raise RuntimeError(f"Failed to delete request: {run_err}") from run_err
        return response

    # LOCATIONS

    def get_locations(self, cql_query: str = "") -> list:
        """Retrieves a list of locations from FOLIO.
        Args:
            cql_query (str, optional): CQL query string to filter results. Defaults to empty string.
        Returns:
            list: List of location records matching the query criteria.

        """
        return list(self.iter_data("/locations", key="locations", cql_query=cql_query))

    # MISCELLANEOUS

    def get_contributor_name_types(self, cql_query: str = "") -> list:
        """Retrieves a list of contributor name types from the FOLIO system.
        Args:
            cql_query (str, optional): CQL query string to filter results. Defaults to empty string.
        Returns:
            list: A list of contributor name type objects.
        """

        return list(
            self.iter_data(
                "/contributor-name-types",
                key="contributorNameTypes",
                cql_query=cql_query,
            )
        )
