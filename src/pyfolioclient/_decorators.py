"""Decorator for managing exceptions in HTTP requests."""

import json
from functools import wraps

from httpx import ConnectError, HTTPStatusError, TimeoutException

from ._exceptions import BadRequestError, ItemNotFoundError, UnprocessableContentError


def exception_handler(func):
    """Decorator that handles common HTTP and connection exceptions in FOLIO API calls.

    This decorator wraps functions making HTTP requests to FOLIO APIs and provides
    standardized exception handling for connection, timeout and HTTP status errors.

    Args:
        func: The function to be decorated

    Returns:
        The wrapped function that includes exception handling

    Raises:
        ConnectionError: If there is a network connection error
        TimeoutError: If the server request times out
        BadRequestError: If the request is malformed (HTTP 400) - bad request/CQL syntax error
        ItemNotFoundError: If the requested resource is not found (HTTP 404) - unknown UUID
        RuntimeError: For other HTTP errors
    """

    @wraps(func)
    def wrap(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            return response
        except ConnectError as connection_err:
            raise ConnectionError("Connection error") from connection_err
        except TimeoutException as timeout_err:
            raise TimeoutError("Server timeout") from timeout_err
        except HTTPStatusError as http_err:
            if http_err.response.status_code == 400:
                raise BadRequestError("Bad request/CQL syntax error") from http_err
            if http_err.response.status_code == 404:
                raise ItemNotFoundError("Item not found") from http_err
            # In Folio, 422 sometimes contains json and sometimes plain text.
            # Instead propagating the byte object, we try to decode it.
            # This is not an elegant solution.
            if http_err.response.status_code == 422:
                try:
                    body_json = json.loads(http_err.response.content.decode("utf-8"))
                    raise UnprocessableContentError(body_json) from http_err
                except json.JSONDecodeError:
                    try:
                        body_string = http_err.response.content.decode("utf-8")
                        raise UnprocessableContentError(body_string) from http_err
                    except (UnicodeDecodeError, AttributeError, TypeError) as err:
                        raise UnprocessableContentError(
                            "Unprocessable content"
                        ) from err
            raise RuntimeError("HTTP error") from http_err

    return wrap
