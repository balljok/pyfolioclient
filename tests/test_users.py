"""Tests of client methods"""

import os
import random
import string
from uuid import UUID

from pyfolioclient import FolioClient


def test_users():
    """Test for the fetching, updating, adding and deleting users"""
    with FolioClient(timeout=30) as folio:

        assert isinstance(folio, FolioClient)

        # Get all users
        users = folio.get_all_users()
        assert isinstance(users, list)
        assert len(users) > 0

        # Get all users using generator/iterator
        for user in folio.iter_users("barcode=123"):
            assert isinstance(user, dict)

        # Get folio user used for login to the system
        user_name = os.getenv("FOLIO_USER")
        user_data = folio.get_users_by_query(f"username=={user_name}")
        assert isinstance(user_data, list)
        assert len(user_data) == 1

        # Create a new user
        patrongroup_id = user_data[0].get("patronGroup")
        user_name = "".join(random.choices(string.ascii_uppercase, k=32))
        barcode = "".join(random.choices(string.digits, k=32))
        user_data = {
            "username": user_name,
            "barcode": barcode,
            "active": True,
            "patronGroup": patrongroup_id,
            "personal": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com",
                "preferredContactTypeId": "002",
            },
        }
        user_data = folio.create_user(user_data)
        assert isinstance(user_data, dict)
        assert user_data.get("username") == user_name

        # Get data for the created user
        user_id = user_data.get("id")
        assert isinstance(user_id, str)
        assert UUID(user_id)
        user_data = folio.get_user_by_id(user_id)
        assert isinstance(user_data, dict)
        assert user_data.get("username") == user_name

        # Update the user with new information
        new_barcode = "".join(random.choices(string.digits, k=32))
        user_data.update(
            {
                "barcode": new_barcode,
            }
        )
        response = folio.update_user_by_id(user_id, user_data)
        assert response == 204

        # Get data for the updated user using the business logic API
        user_data = folio.get_user_bl_by_id(user_id)
        assert isinstance(user_data, dict)
        user_data = user_data.get("user")
        assert isinstance(user_data, dict)
        assert user_data.get("barcode") == new_barcode

        # Delete the user
        response = folio.delete_user_by_id(user_id)
        assert response == 204

        # Get data for deleted user
        user_data = folio.get_user_by_id(user_id)
        assert user_data is None
