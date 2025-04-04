"""Tests of client methods related to circulation"""

import os
from datetime import datetime, timedelta

import pytest
from dotenv import load_dotenv
from pytest import raises

from pyfolioclient import FolioClient

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

load_dotenv()
FOLIO_BASE_URL = os.environ["FOLIO_BASE_URL"]
FOLIO_TENANT = os.environ["FOLIO_TENANT"]
FOLIO_USER = os.environ["FOLIO_USER"]
FOLIO_PASSWORD = os.environ["FOLIO_PASSWORD"]

NOW = datetime.today().strftime("%Y-%m-%d")
A_WEEK_FROM_NOW = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
def test_loans():
    """Test fetching loans"""
    with FolioClient(FOLIO_BASE_URL, FOLIO_TENANT, FOLIO_USER, FOLIO_PASSWORD) as folio:
        # Get loans
        data = folio.get_loans(cql_query="status.name==Open")
        assert isinstance(data, list)

        # Get all open loans using generator/iterator
        for item in folio.iter_loans(cql_query="status.name==Open"):
            assert isinstance(item, dict)

        # Get loans with a given due date
        data = folio.get_open_loans_by_due_date(NOW)
        assert isinstance(data, list)

        # Get loans with a given due date using generator/iterator
        for item in folio.iter_open_loans_by_due_date(start=NOW, end=A_WEEK_FROM_NOW):
            assert isinstance(item, dict)

        # Test invalid date range
        with raises(ValueError):
            folio.get_open_loans_by_due_date(start=A_WEEK_FROM_NOW, end=NOW)

        # Test invalid date format
        with raises(ValueError):
            folio.get_open_loans_by_due_date(start="2025-02-10T10:06:32Z")

        # Test invalid date
        with raises(ValueError):
            folio.get_open_loans_by_due_date(start="2025-02-31")


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions")
def test_requests():
    """Test fetching requests"""
    with FolioClient(FOLIO_BASE_URL, FOLIO_TENANT, FOLIO_USER, FOLIO_PASSWORD) as folio:
        # Get requests
        data = folio.get_requests(cql_query="status=Open")
        assert isinstance(data, list)

        # Get all open requests using generator/iterator
        for item in folio.iter_requests(cql_query="status=Open"):
            assert isinstance(item, dict)
