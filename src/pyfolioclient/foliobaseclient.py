"""
Client for Folio API:s
This is a base client for Folio API:s. It handles logging into Folio, getting
and refresing tokens and provides methods for generic GET, POST, PUT and DELETE
requests.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta
from datetime import timezone as tz
from typing import Optional

from dotenv import load_dotenv
from httpx import Client

from ._decorators import exception_handler


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
        self._retrieve_token()

    def __enter__(self) -> "FolioBaseClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._logout()
        if hasattr(self, "client") and self.client:
            self.client.close()

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
    def _retrieve_token(self, refresh: bool = False) -> None:
        if refresh:
            url = f"{self.base_url}/authn/refresh"
            headers = {
                "Cookie": (
                    f"folioRefreshToken={self.refresh_token};"
                    f"folioAccessToken={self.access_token}"
                )
            }
            response = self.client.post(url, headers=headers, timeout=self.timeout)
        else:
            url = f"{self.base_url}/authn/login-with-expiry"
            payload = {
                "username": os.getenv("FOLIO_USER"),
                "password": os.getenv("FOLIO_PASSWORD"),
            }
            # If re-login after token expiration, remove old token from headers
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

    def _adjust_for_buffer(self, expiration: str) -> datetime:
        expiration_dt = datetime.fromisoformat(expiration.replace("Z", "+00:00"))

        expiration_with_buffer = expiration_dt - timedelta(
            seconds=self.TOKEN_REFRESH_BUFFER
        )

        return expiration_with_buffer

    def _manage_token(self):
        """
        Update token if necessary through refresh or re-login
        """

        now: datetime = datetime.now(tz.utc)

        # If token is about to expire, refresh it
        if self.token_expiration_with_buffer < now < self.token_expiration:
            self._retrieve_token(refresh=True)
        # If the token has already expired, login again
        elif self.token_expiration < now:
            self._retrieve_token()

    @exception_handler
    def _logout(self) -> None:
        self._manage_token()

        url = f"{self.base_url}/authn/logout"

        header = {
            "Cookie": (
                f"folioRefreshToken={self.refresh_token}; "
                f"folioAccessToken={self.access_token}"
            )
        }

        response = self.client.post(url, headers=header, timeout=self.timeout)
        response.raise_for_status()

    @exception_handler
    def get_data(
        self,
        endpoint: str,
        key: str = "",
        query: str = "",
        limit: int = 10,
    ) -> dict | list:
        self._manage_token()
        url = f"{self.base_url}{endpoint}"
        params = {"query": query} if query else {}
        if limit:
            params.update({"limit": str(limit)})
        response = self.client.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()[key] if key else response.json()

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

        while data:
            if not isinstance(data, list):
                raise RuntimeError("Invalid response format")
            yield from data  # type: ignore
            current_uuid = data[-1].get("id")
            if current_uuid:
                current_query = (
                    f"id>{current_uuid} AND ({query}) sortBy id"
                    if query
                    else f"id>{current_uuid} sortBy id"
                )
                data = self.get_data(endpoint, key, current_query, limit)

    @exception_handler
    def post_data(self, endpoint: str, payload: dict) -> dict | int:
        self._manage_token()
        url = f"{self.base_url}{endpoint}"
        response = self.client.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return int(response.status_code)

    @exception_handler
    def put_data(self, endpoint: str, payload: dict) -> dict | int:
        if not payload:
            raise ValueError("Payload cannot be empty")
        self._manage_token()
        url = f"{self.base_url}{endpoint}"
        response = self.client.put(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return int(response.status_code)

    @exception_handler
    def delete_data(self, endpoint: str) -> int:
        self._manage_token()
        url = f"{self.base_url}{endpoint}"
        response = self.client.delete(url, timeout=self.timeout)
        response.raise_for_status()
        return int(response.status_code)
