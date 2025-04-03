"""
Custom exceptions for handling FOLIO API errors.

This module provides custom exception classes for handling specific HTTP error responses
from the FOLIO API. These exceptions help provide more meaningful error handling for
common API interaction scenarios.

Classes:
    BadRequestError: Exception for 400 Bad Request responses
    ItemNotFoundError: Exception for 404 Not Found responses
    UnprocessableContentError: Exception for 422 Unprocessable Content responses
"""

__all__ = ["ItemNotFoundError", "BadRequestError", "UnprocessableContentError"]


class BadRequestError(Exception):
    """Exception raised when the server returns a 400 Bad Request error.
    For FOLIO, typically means a CQL syntax error or missing required parameters in payload.
    """


class ItemNotFoundError(Exception):
    """Exception is raised when the server returns a 404 Item Not Found.
    For FOLIO, typically means endpoint targets an UUID that does not exist."""


class UnprocessableContentError(Exception):
    """Exception is raised when the server returns a 422 Unprocessable Content.
    For FOLIO, typically means that the payload does not validate, i.e. misses some required
    field, or that the request cannot be processed (e.g. a renewal cannot be performed since there
    are requests on the item).
    """
