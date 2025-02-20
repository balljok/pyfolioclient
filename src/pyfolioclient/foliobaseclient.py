"""
Client for Folio API:s
This is a base client for Folio API:s. It handles logging into Folio, getting
and refresing tokens and provides methods for generic GET, POST, PUT and DELETE
requests.
"""

# TODO: Add async support?
# TODO: Merge login and refresh_token to a single method
# TODO: Modify token_handler to not be a wrapper

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta
from datetime import timezone as tz
from functools import wraps
from time import time
from typing import Optional

from dotenv import load_dotenv
from httpx import Client, ConnectError, HTTPStatusError, TimeoutException


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print("func:%r args:[%r, %r] took: %2.4f sec" % (f.__name__, args, kw, te - ts))
        return result

    return wrap


def exception_handler(func):
    """
    Decorator for managing exceptions
    """

    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            return response
        except ConnectError as connection_err:
            logging.error("Connection error: %s", connection_err)
            raise ConnectionError("Folio seems to be down") from connection_err
        except TimeoutException as timeout_err:
            logging.error("Server timeout.")
            raise TimeoutError("Folio seems to be down") from timeout_err
        except HTTPStatusError as http_err:
            logging.error(
                "HTTP [%s] %s: %s",
                http_err.response.status_code,
                http_err.response.content,
                http_err,
            )
            return int(http_err.response.status_code)

    return wrapper


def token_handler(func):
    """
    Decorator for managing token (refreshing).
    """

    def wrapper(self, *args, **kwargs):
        now: datetime = datetime.now(tz.utc)

        # If token is about to expire, refresh it
        if now > self.token_expiration_with_buffer and now < self.token_expiration:
            self._refresh_token()
        # If the token has already expired, login again
        elif now > self.token_expiration:
            self._login()

        response = func(self, *args, **kwargs)
        return response

    return wrapper


class FolioBaseClient:
    """
    Class providing methods to communicate with Folio using API:s
    """

    DEFAULT_TIMEOUT: int = 60
    TOKEN_REFRESH_BUFFER: int = 10
    MAX_LIMIT: int = 1_000_000_000
    REQUIRED_ENV_VARS = [
        "FOLIO_BASE_URL",
        "FOLIO_TENANT",
        "FOLIO_USER",
        "FOLIO_PASSWORD",
    ]

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("Timeout must be a positive integer")

        # Load environment variables
        load_dotenv()
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            raise RuntimeError(
                f"Missing environment variables: {', '.join(missing_vars)}"
            )

        self.base_url: str = os.getenv("FOLIO_BASE_URL")  # type: ignore
        self.timeout: int = timeout
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiration: datetime = datetime.now(tz.utc)  # only initialization
        self.token_expiration_with_buffer: datetime = datetime.now(
            tz.utc
        )  # only initialization

        # Initialize client for persistent connections
        self.client = Client()
        self.client.headers.update(
            {
                "x-okapi-tenant": os.getenv("FOLIO_TENANT"),
            }  # type: ignore
        )

        # Fetch authentication token
        self._login()

    def __enter__(self) -> "FolioBaseClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._logout()
        if hasattr(self, "client") and self.client:
            self.client.close()
        del self.client
        del self.base_url
        del self.access_token
        del self.refresh_token

    def __repr__(self) -> str:
        auth_status = "authenticated" if self.access_token else "not authenticated"
        return (
            f"<{self.__class__.__name__}("
            f"folio='{self.base_url}', "
            f"tenant='{os.getenv('FOLIO_TENANT')}', "
            f"user='{os.getenv('FOLIO_USER')}', "
            f"status={auth_status}, "
            f"timeout={self.timeout})"
            ">"
        )

    @exception_handler
    def _login(self) -> None:
        url = f"{self.base_url}/authn/login-with-expiry"

        payload = {
            "username": os.getenv("FOLIO_USER"),
            "password": os.getenv("FOLIO_PASSWORD"),
        }

        # If re-login after token expiration, remove old token
        if self.client.headers.get("x-okapi-token"):
            self.client.headers.pop("x-okapi-token")

        response = self.client.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        if not response.cookies.get("folioAccessToken"):
            raise RuntimeError("No access token received")

        response_json = response.json()
        self.access_token = response.cookies.get("folioAccessToken")
        self.refresh_token = response.cookies.get("folioRefreshToken")
        self.token_expiration = datetime.fromisoformat(
            response_json.get("accessTokenExpiration").replace("Z", "+00:00")
        )
        self.token_expiration_with_buffer = self._adjust_for_buffer(
            response_json.get("accessTokenExpiration")
        )

        if self.access_token:
            self.client.headers.update({"x-okapi-token": self.access_token})
        else:
            raise RuntimeError("Failed to authenticate with Folio API.")

    @exception_handler
    def _refresh_token(self):
        url = f"{self.base_url}/authn/refresh"

        headers = {
            "Cookie": (
                f"folioRefreshToken={self.refresh_token};"
                f"folioAccessToken={self.access_token}"
            )
        }

        response = self.client.post(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        if not response.cookies.get("folioAccessToken"):
            raise RuntimeError("No access token received")

        response_json = response.json()
        self.access_token = response.cookies.get("folioAccessToken")
        self.refresh_token = response.cookies.get("folioRefreshToken")
        self.token_expiration = datetime.fromisoformat(
            response_json.get("accessTokenExpiration").replace("Z", "+00:00")
        )
        self.token_expiration_with_buffer = self._adjust_for_buffer(
            response_json.get("accessTokenExpiration")
        )

        self.client.headers.update({"x-okapi-token": self.access_token})  # type: ignore

    def _adjust_for_buffer(self, expiration: str) -> datetime:
        expiration_dt = datetime.fromisoformat(expiration.replace("Z", "+00:00"))

        expiration_with_buffer = expiration_dt - timedelta(
            seconds=self.TOKEN_REFRESH_BUFFER
        )

        return expiration_with_buffer

    @token_handler
    @exception_handler
    def _logout(self) -> None:
        if not (self.access_token and self.refresh_token):
            raise ValueError("No valid tokens to logout")

        url = f"{self.base_url}/authn/logout"

        header = {
            "Cookie": (
                f"folioRefreshToken={self.refresh_token}; "
                f"folioAccessToken={self.access_token}"
            )
        }

        response = self.client.post(url, headers=header, timeout=self.timeout)
        response.raise_for_status()

    @token_handler
    @exception_handler
    def get_data(
        self,
        endpoint: str,
        key: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> dict | list | int:
        url = f"{self.base_url}{endpoint}"
        params = {"query": query} if query else {}
        if limit:
            params.update({"limit": str(limit)})
        response = self.client.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()[key] if key else response.json()

    @token_handler
    @exception_handler
    def iter_data(
        self,
        endpoint: str,
        key: str,
        query: str = "",
        limit: int = 100,
    ) -> Generator:

        current_uuid = uuid.UUID(int=0)
        current_query = (
            f"id>{current_uuid} AND ({query}) sortBy id"
            if query
            else f"id>{current_uuid} sortBy id"
        )

        data = self.get_data(endpoint, key, current_query, limit)  # Initialize data

        if not isinstance(data, list):
            raise ValueError("Invalid response format")

        while data:
            yield from data  # type: ignore
            current_uuid = data[-1].get("id")
            if current_uuid:
                current_query = (
                    f"id>{current_uuid} AND ({query}) sortBy id"
                    if query
                    else f"id>{current_uuid} sortBy id"
                )
                data = self.get_data(endpoint, key, current_query, limit)

            if not isinstance(data, list):
                raise ValueError("Invalid response format")

    @token_handler
    @exception_handler
    def post_data(self, endpoint: str, payload: dict) -> dict | int:
        url = f"{self.base_url}{endpoint}"
        response = self.client.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return int(response.status_code)

    @token_handler
    @exception_handler
    def put_data(self, endpoint: str, payload: dict) -> dict | int:
        if not payload:
            raise ValueError("Payload cannot be empty")

        url = f"{self.base_url}{endpoint}"
        response = self.client.put(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return int(response.status_code)

    @token_handler
    @exception_handler
    def delete_data(self, endpoint: str) -> int:
        url = f"{self.base_url}{endpoint}"
        response = self.client.delete(url, timeout=self.timeout)
        response.raise_for_status()
        return int(response.status_code)


@timing
def main():
    logging.basicConfig(level=logging.ERROR)
    with FolioBaseClient() as folio:
        pass


if __name__ == "__main__":
    main()
