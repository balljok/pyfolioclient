"""Decorator for managing exceptions"""

import logging
from functools import wraps

from httpx import ConnectError, HTTPStatusError, TimeoutException

from .exceptions import ItemNotFoundError


def exception_handler(func):
    """Decorator for managing exceptions"""

    @wraps(func)
    def wrap(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            return response
        except ConnectError as connection_err:
            logging.error("Connection error: %s", connection_err)
            raise ConnectionError("Connection error") from connection_err
        except TimeoutException as timeout_err:
            logging.error("Server timeout: %s", timeout_err)
            raise TimeoutError("Server timeout") from timeout_err
        except HTTPStatusError as http_err:
            logging.error(
                "HTTP [%s] %s: %s",
                http_err.response.status_code,
                http_err.response.content,
                http_err,
            )
            if http_err.response.status_code == 404:
                raise ItemNotFoundError("Item not found") from http_err
            return int(http_err.response.status_code)

    return wrap
