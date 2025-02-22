"""
Custom exceptions for handling FOLIO API errors.

This module provides custom exception classes for handling specific HTTP error responses
from the FOLIO API. These exceptions help provide more meaningful error handling for
common API interaction scenarios.

Classes:
    BadRequestError: Exception for 400 Bad Request responses
    ItemNotFoundError: Exception for 404 Not Found responses
"""

__all__ = ["ItemNotFoundError", "BadRequestError"]


class BadRequestError(Exception):
    """Exception raised when the server returns a 400 Bad Request error.
    For FOLIO, typically means a CQL syntax error or missing required parameters in payload.
    """


class ItemNotFoundError(Exception):
    """Exception is raised when the server returns a 404 Item Not Found.
    For FOLIO, typically means endpoint targets an UUID that does not exist."""
