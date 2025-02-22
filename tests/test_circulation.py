"""Tests of client methods related to circulation"""

from datetime import datetime, timedelta

from pytest import raises

from pyfolioclient import FolioClient

NOW = datetime.today().strftime("%Y-%m-%d")
A_WEEK_FROM_NOW = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")


def test_loans():
    """Test fetching loans"""
    with FolioClient() as folio:
        # Get loans
        data = folio.get_loans(query="status.name==Open")
        assert isinstance(data, list)

        # Get all loans using generator/iterator
        for item in folio.iter_loans(query="status.name==Open"):
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
