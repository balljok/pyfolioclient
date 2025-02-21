"""
Interface for Folio API. This class provides methods to communicate with Folio using API:s

Folio provides endoints to both business logic modules and storage modules. For example:
GET /inventory/items
GET /item-storage/items

Please refer to this page to understand the differences:
https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules

Many get methods use iterators to avoid loading all data at once and risking timeouts or exceptions.
"""

from __future__ import annotations

from collections.abc import Generator

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

    def get_users(self, query: str = "") -> list:
        """Get all users. Query can be used to filter results."""
        return list(self.iter_data("/users", key="users", query=query))

    def iter_users(self, query: str = "") -> Generator:
        """Get all users, yielding results one by one"""
        yield from self.iter_data("/users", key="users", query=query)

    def get_user_by_id(self, uuid: str) -> dict:
        """Get user by id"""
        response = self.get_data(f"/users/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def get_user_bl_by_id(self, uuid: str) -> dict:
        """Get user by id using business logic API"""
        response = self.get_data(f"/bl-users/by-id/{uuid}", limit=0)
        return response if isinstance(response, dict) else {}

    def get_user_by_barcode(self, barcode: str) -> dict:
        """Get user by barcode"""
        response = self.get_data(
            "/users", key="users", query=f"barcode=={barcode}", limit=1
        )
        if isinstance(response, list) and len(response) > 1:
            raise RuntimeError("Multiple users found with the same barcode")
        return response[0] if isinstance(response, list) else {}

    def create_user(self, payload: dict) -> dict:
        """Create user and add an empty permissions set"""
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

    def update_user_by_id(self, uuid: str, payload: dict) -> dict | int:
        """Update user by uuid"""
        response = self.put_data(f"/users/{uuid}", payload=payload)
        if isinstance(response, int) and not response == 204:
            raise RuntimeError("Failed to update user")
        return response

    def delete_user_by_id(self, uuid: str) -> int:
        """Delete user by uuid"""
        response = self.delete_data(f"/users/{uuid}")
        if response != 204:
            raise RuntimeError("Failed to update user")
        return response

    # INSTANCES

    # HOLDINGS

    # ITEMS

    # LOANS

    def get_loans(self, query: str = "") -> list:
        """Get all loans. Query can be used to filter results."""
        return list(self.iter_data("/loan-storage/loans", key="loans", query=query))

    def iter_loans(self, query: str = "") -> Generator:
        """Get all loans, yielding results one by one"""
        yield from self.iter_data("/loan-storage/loans", key="loans", query=query)

    def get_open_loans_by_due_date(self, start: str, end: str | None = None) -> list:
        """Get loans with a given due date. Suppors both intervals and single dates"""
        if end:
            query = (
                f"(((dueDate>{start} and dueDate<{end}) "
                f"or dueDate={start} or dueDate={end}) "
                "and status.name==Open)"
            )
        else:
            query = f"dueDate={start} and status.name==Open"
        return list(self.iter_data("/loan-storage/loans", key="loans", query=query))

    def iter_open_loans_by_due_date(
        self, start: str, end: str | None = None
    ) -> Generator:
        """Iterate over loans with a given due date. Supports both intervals and single dates"""
        if end:
            query = (
                f"(((dueDate>{start} and dueDate<{end}) "
                f"or dueDate={start} or dueDate={end}) "
                "and status.name==Open)"
            )
        else:
            query = f"dueDate={start} and status.name==Open"
        yield from self.iter_data("/loan-storage/loans", key="loans", query=query)

    # LOCATIONS

    # MISCELLANEOUS
