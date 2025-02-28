"""Tests for the base client"""

import os
import time

import pytest
from dotenv import load_dotenv
from pytest import raises

from pyfolioclient import BadRequestError, FolioBaseClient

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

load_dotenv()
FOLIO_BASE_URL = os.environ["FOLIO_BASE_URL"]
FOLIO_TENANT = os.environ["FOLIO_TENANT"]
FOLIO_USER = os.environ["FOLIO_USER"]
FOLIO_PASSWORD = os.environ["FOLIO_PASSWORD"]


FOLIO_TOKEN_TIMEOUT = 600 + 10  # add 10 second buffer


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
def test_login():
    """Test to ensure that the login works"""
    with FolioBaseClient(
        FOLIO_BASE_URL, FOLIO_TENANT, FOLIO_USER, FOLIO_PASSWORD
    ) as folio:
        assert folio.client.headers.get("x-okapi-tenant") is not None


# @pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
# def test_token_refresh():
#     """Test to ensure that the automatic token refresh works"""
#     with FolioBaseClient() as folio:
#         aggregated_time = 0
#         sleep_time = 8
#         while aggregated_time < FOLIO_TOKEN_TIMEOUT:
#             assert isinstance(folio.get_data("/users", key="users", limit=1), list)
#             time.sleep(sleep_time)
#             aggregated_time += sleep_time


# @pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
# def test_relogin():
#     """Test to ensure that the client makes a re-login if the token has expired"""
#     with FolioBaseClient() as folio:
#         time.sleep(FOLIO_TOKEN_TIMEOUT)
#         assert isinstance(folio.get_data("/users", key="users", limit=1), list)


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
def test_bad_requests():
    """Test to ensure that the client raises an error when a bad request is made"""
    with FolioBaseClient(
        FOLIO_BASE_URL, FOLIO_TENANT, FOLIO_USER, FOLIO_PASSWORD
    ) as folio:
        with raises(BadRequestError):
            folio.get_data("/users", cql_query=")")

        with raises(BadRequestError):
            for user in folio.iter_data("/users", key="users", cql_query=")"):
                assert user is not None
