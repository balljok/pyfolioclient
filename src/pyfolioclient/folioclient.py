"""
Interface for Folio API. This class provides methods to communicate with Folio using API:s

Folio provides endoints to both business logic modules and storage modules. For example:
GET /inventory/items
GET /item-storage/items

Please refer to this page to understand the differences:
https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules

Naming guidelines (other variants are possible):

get = GET
iter = GET yielding results
update = PUT
create = POST
delete = DELETE

_bl = Uses business logic endpoints (i.e. not storage modules)

_all = No query and limit set to MAX_LIMIT
_by_query = Query set and limit set to MAX_LIMIT
_by_id = Get based on object UUID, limit = 0 to be excluded from parameters

"""

from __future__ import annotations

import logging
from collections.abc import Generator
from uuid import UUID

from pyfolioclient import FolioBaseClient

# from .foliobaseclient import FolioBaseClient


class FolioClient(FolioBaseClient):
    """
    Interface for Folio API. This class provides methods to communicate with Folio using API:s
    """

    # USERS

    def get_all_users(self) -> list:
        """Get all users"""
        response = self.get_data("/users", key="users", limit=self.MAX_LIMIT)

        if not isinstance(response, list):
            raise ValueError("Invalid response format")

        return response

    def iter_users(self, query: str = "") -> Generator:
        """Get all users, yielding results one by one"""
        yield from self.iter_data("/users", key="users", query=query)

    def get_users_by_query(self, query) -> list:
        """Get all users"""
        response = self.get_data(
            "/users", key="users", query=query, limit=self.MAX_LIMIT
        )

        if not isinstance(response, list):
            raise ValueError("Invalid response format")

        return response

    def get_user_by_id(self, uuid: str) -> dict | None:
        """Get user by uuid"""
        response = self.get_data(f"/users/{uuid}", limit=0)

        if not (isinstance(response, dict) or isinstance(response, int)):
            raise ValueError("Invalid response format")

        return response if not isinstance(response, int) else None

    def get_user_bl_by_id(self, uuid: str) -> dict | None:
        """Get user by uuid using business logic API"""
        response = self.get_data(f"/bl-users/by-id/{uuid}", limit=0)

        if not isinstance(response, (dict, int)):
            raise ValueError("Invalid response format")

        return response if not isinstance(response, int) else None

    def get_user_by_barcode(self, barcode: str) -> dict | None:
        """Get user by barcode"""
        response = self.get_data(
            "/users", key="users", query=f"barcode=={barcode}", limit=1
        )

        if not (
            (isinstance(response, list) and len(response) == 1)
            or isinstance(response, int)
        ):
            raise ValueError("Invalid response format")

        return response[0] if response else None

    def create_user(self, payload: dict) -> dict | int:
        """Create user and add an empty permissions set"""
        user_data = self.post_data("/users", payload=payload)

        # In addition to creating a user, we need to create an empty permissions set
        if isinstance(user_data, dict):
            user_id = user_data.get("id")
            empty_permissions_set = {"userId": user_id, "permissions": []}
            self.post_data("/perms/users", payload=empty_permissions_set)

        return user_data

    def update_user_by_id(self, uuid: str, payload: dict) -> dict | int:
        """Update user by uuid"""
        return self.put_data(f"/users/{uuid}", payload=payload)

    def delete_user_by_id(self, uuid: str) -> int:
        """Delete user by uuid"""
        return self.delete_data(f"/users/{uuid}")

    # INSTANCES

    def get_all_instances(self) -> list:
        """Get all instances"""
        # TODO: Behöver ha metoder som stöder iterativ hämtning och yield av resultat
        return []

    def get_instances_by_query(self, query: str) -> list:
        """Get instances by query"""

        response = self.get_data(
            "/instance-storage/instances",
            key="instances",
            query=query,
            limit=self.MAX_LIMIT,
        )

        if not isinstance(response, list):
            raise ValueError("Invalid response format")

        return response

    def get_instance_by_id(self, uuid: UUID) -> dict | None:
        """Get instance by uuid"""

        try:
            UUID(uuid)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}") from e

        response = self.get_data(f"/instance-storage/instances/{uuid}", limit=0)

        if not (isinstance(response, dict) or isinstance(response, int)):
            raise ValueError("Invalid response format")

        return response if not isinstance(response, int) else None

    # HOLDINGS

    def get_holdings_by_query(self, query: str) -> list:
        """Get holdings by query"""
        response = self.get_data(
            "/holdings-storage/holdings",
            key="holdingsRecords",
            query=query,
            limit=self.MAX_LIMIT,
        )

        if not isinstance(response, list):
            raise ValueError("Invalid response format")

        return response

    def get_holdings_by_id(self, uuid: UUID) -> dict | None:
        """Get holdings by id"""

        try:
            UUID(uuid)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}") from e

        response = self.get_data(f"/holdings-storage/holdings/{uuid}", limit=0)

        if not (isinstance(response, dict) or isinstance(response, int)):
            raise ValueError("Invalid response format")

        return response if not isinstance(response, int) else None

    def update_holding_by_id(self, uuid: UUID, payload: dict) -> int:
        """Update holding by uuid"""
        return self.put_data(f"/holdings-storage/holdings/{uuid}", payload=payload)

    # ITEMS

    def get_items_by_query(self, query) -> list | None:
        """Get items by query"""
        return self.get_data(
            "/item-storage/items", key="items", query=query, limit=self.MAX_LIMIT
        )

    def get_item_by_id(self, uuid: UUID) -> dict | None:
        """Get items by id"""

        try:
            UUID(uuid)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}") from e

        response = self.get_data(f"/item-storage/items/{uuid}", limit=0)

        if not (isinstance(response, dict) or isinstance(response, int)):
            raise ValueError("Invalid response format")

        return response if not isinstance(response, int) else None

    def update_item_by_id(self, uuid: UUID, payload: dict) -> int:
        """Update holding by uuid"""
        return self.put_data(f"/item-storage/items/{uuid}", payload=payload)

    # LOANS

    def get_all_loans(self) -> list:
        """Get all loans"""
        return self.get_data("/loan-storage/loans", key="loans", limit=self.MAX_LIMIT)

    def iter_loans(self, query: str = "") -> Generator:
        """Get all loans, yielding results one by one"""
        yield from self.iter_data("/loan-storage/loans", key="loans", query=query)

    def get_loans_by_query(self, query: str) -> list:
        """Get loans by query"""
        return self.get_data(
            "/loan-storage/loans", key="loans", query=query, limit=self.MAX_LIMIT
        )

    def get_loans_by_due_date(self, start: str, end: str | None = None) -> list:
        """Get loans with a given due date. Can be used both with intervals and single dates"""
        if end:
            query = (
                f"(((dueDate>{start} and dueDate<{end}) "
                f"or dueDate={start} or dueDate={end}) "
                "and status.name==Open)"
            )
        else:
            query = f"dueDate={start} and status.name==Open"
        return self.get_data(
            "/loan-storage/loans", key="loans", query=query, limit=self.MAX_LIMIT
        )

    # LOCATIONS

    def get_all_locations(self) -> list:
        """Get all locations"""
        return self.get_data("/locations", key="locations", limit=self.MAX_LIMIT)

    # MISCELLANEOUS

    def get_all_contributor_name_types(self) -> list:
        """Get all contributor name types"""
        return self.get_data(
            "/contributor-name-types", key="contributorNameTypes", limit=self.MAX_LIMIT
        )


def main():
    logging.basicConfig(level=logging.INFO)
    with FolioClient() as folio:
        for entry in folio.iter_loans("lostItemPolicyId==e6*"):
            print(entry)


if __name__ == "__main__":
    main()
