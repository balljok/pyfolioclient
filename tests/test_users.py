"""Tests of client methods"""

import os
import random
import string
from uuid import UUID

import pytest
from dotenv import load_dotenv
from pytest import raises

from pyfolioclient import FolioClient, ItemNotFoundError

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

load_dotenv()
FOLIO_BASE_URL = os.environ["FOLIO_BASE_URL"]
FOLIO_TENANT = os.environ["FOLIO_TENANT"]
FOLIO_USER = os.environ["FOLIO_USER"]
FOLIO_PASSWORD = os.environ["FOLIO_PASSWORD"]


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
def test_users_positive():
    """Test for the fetching, updating, adding and deleting users"""
    with FolioClient(
        FOLIO_BASE_URL, FOLIO_TENANT, FOLIO_USER, FOLIO_PASSWORD, timeout=30
    ) as folio:

        # Get all users
        users = folio.get_users()
        assert isinstance(users, list)
        assert len(users) > 0

        # Get all users using generator/iterator
        for user in folio.iter_users("barcode=123"):
            assert isinstance(user, dict)

        # Get folio user used for login to the system
        user_name = os.getenv("FOLIO_USER")
        user_data = folio.get_users(f"username=={user_name}")
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
        response = folio.update_user(user_id, user_data)
        assert response == 204

        # Get user by
        user_data = folio.get_user_by_barcode(new_barcode)
        assert isinstance(user_data, dict)

        # Get data for the updated user using the business logic API
        user_data = folio.get_user_bl_by_id(user_id)
        assert isinstance(user_data, dict)
        user_data = user_data.get("user")
        assert isinstance(user_data, dict)
        assert user_data.get("barcode") == new_barcode

        # Delete the user
        response = folio.delete_user(user_id)
        assert response == 204

        # Get data for deleted user
        with raises(ItemNotFoundError):
            folio.get_user_by_id(user_id)
            # assert bool(user_data) is False


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
def test_users_negative():
    """Test cases that should raise exceptions"""
    with raises(ValueError):
        with FolioClient(
            FOLIO_BASE_URL, FOLIO_TENANT, FOLIO_USER, FOLIO_PASSWORD
        ) as folio:
            user_data = {}
            folio.create_user(user_data)
