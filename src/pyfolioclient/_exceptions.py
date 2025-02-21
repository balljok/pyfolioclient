"""
Custom exceptions
"""

__all__ = ["ItemNotFoundError", "BadRequestError"]


class BadRequestError(Exception):
    """Bad request error (400)"""


class ItemNotFoundError(Exception):
    """Item not found error (404)"""
