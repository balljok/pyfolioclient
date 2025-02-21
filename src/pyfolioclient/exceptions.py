"""
Custom exceptions
"""

from httpx import HTTPStatusError

__all__ = ["ItemNotFoundError"]


class ItemNotFoundError(Exception):
    """Item not found error"""
