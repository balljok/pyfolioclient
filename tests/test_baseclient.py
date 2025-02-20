"""Tests for the base client"""

import time

from pyfolioclient import FolioBaseClient


def test_login():
    """Test to ensure that the login works and tokens are successfully retrieved"""
    with FolioBaseClient() as folio:
        assert folio.access_token is not None
        assert folio.refresh_token is not None


def test_token_refresh():
    """Test to ensure that the automatic token refresh works - takes over 10 minutes to run"""
    with FolioBaseClient() as folio:
        pass
