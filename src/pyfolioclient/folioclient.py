"""
Interface for Folio API. This class provides methods to communicate with Folio using API:s

Folio provides endoints to both business logic modules and storage modules. For example:
GET /inventory/items
GET /item-storage/items

Please refer to this page to understand the differences:
https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from uuid import UUID

from pyfolioclient import FolioBaseClient

# from .foliobaseclient import FolioBaseClient


class FolioClient(FolioBaseClient):
    """
    FolioClient extends the base client with methods for the most common interactions with Folio.
    """

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
            raise ValueError("Failed to create user")
        # In addition to creating a user, we need to create an empty permissions set
        user_id = response.get("id")
        empty_permissions_set = {"userId": user_id, "permissions": []}
        self.post_data("/perms/users", payload=empty_permissions_set)
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

    # LOCATIONS

    # MISCELLANEOUS


def main():
    logging.basicConfig(level=logging.INFO)
    with FolioClient() as folio:
        users = folio.get_users("")
        print(users)


if __name__ == "__main__":
    main()
