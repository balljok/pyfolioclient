"""Tests for the base client"""

import time

from pytest import raises

from pyfolioclient import BadRequestError, FolioBaseClient

FOLIO_TOKEN_TIMEOUT = 600 + 10  # add 10 second buffer


def test_login():
    """Test to ensure that the login works"""
    with FolioBaseClient() as folio:
        assert folio.client.headers.get("x-okapi-tenant") is not None


# def test_token_refresh():
#     """Test to ensure that the automatic token refresh works"""
#     with FolioBaseClient() as folio:
#         aggregated_time = 0
#         sleep_time = 8
#         while aggregated_time < FOLIO_TOKEN_TIMEOUT:
#             assert isinstance(folio.get_data("/users", key="users", limit=1), list)
#             time.sleep(sleep_time)
#             aggregated_time += sleep_time


# def test_relogin():
#     """Test to ensure that the client makes a re-login if the token has expired"""
#     with FolioBaseClient() as folio:
#         time.sleep(FOLIO_TOKEN_TIMEOUT)
#         assert isinstance(folio.get_data("/users", key="users", limit=1), list)


def test_bad_requests():
    """Test to ensure that the client raises an error when a bad request is made"""
    with FolioBaseClient() as folio:
        with raises(BadRequestError):
            folio.get_data("/users", query=")")

        with raises(BadRequestError):
            for user in folio.iter_data("/users", key="users", query=")"):
                assert user is not None
