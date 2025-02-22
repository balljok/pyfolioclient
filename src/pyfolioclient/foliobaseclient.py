"""
Client for Folio API:s
A base client for Folio API:s. It manages access tokens and provides generic methods for GET,
POST, PUT and DELETE. It also provides an iterator for GET.

The client requires the following environment variables to be set:
    - FOLIO_BASE_URL: Base URL of the FOLIO installation
    - FOLIO_TENANT: Name of the FOLIO tenant
    - FOLIO_USER: Username for authentication
    - FOLIO_PASSWORD: Password for authentication

The client handles:
    - Authentication and token management
    - Token refresh before expiration
    - Re-authentication when token expires
    - Connection persistence
    - Exception handling through decorators
    - Resource cleanup through context manager

Features:
    - Automatic token refresh with configurable buffer time
    - Persistent connections using httpx Client
    - Support for all standard HTTP methods (GET, POST, PUT, DELETE)
    - Iterator implementation for paginated GET requests
    - Configurable timeout settings
    - Comprehensive error handling

Example:
    ```python
    with FolioBaseClient() as client:
        # Get data from an endpoint
        data = client.get_data("/users", "users", query="active=true", limit=10)
        
        # Iterate through large datasets
        for item in client.iter_data("/inventory/items", "items"):
            process_item(item)
    ```

Attributes:
    DEFAULT_TIMEOUT (int): Default timeout for API requests in seconds (60)
    TOKEN_REFRESH_BUFFER (int): Buffer time before token expiration in seconds (10)
    REQUIRED_ENV_VARS (list): Required environment variables for client initialization


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
    A base client class for interacting with FOLIO API endpoints.

    This class handles token management, authentication, and provides generic methods for API
    interactions.

    Attributes:
        DEFAULT_TIMEOUT (int): Default timeout value for API requests in seconds (60)
        TOKEN_REFRESH_BUFFER (int): Buffer time (seconds) before token expiration (10)
        REQUIRED_ENV_VARS (list): Required environment variables for FOLIO authentication
            - FOLIO_BASE_URL: Base URL of the FOLIO instance
            - FOLIO_TENANT: FOLIO tenant ID
            - FOLIO_USER: FOLIO username
            - FOLIO_PASSWORD: FOLIO password

    Usage:
        ```python
        with FolioBaseClient() as folio:
            data = folio.get_data("/some-endpoint")
        ```

    The client will automatically handle:
        - Environment variable validation
        - Authentication and token management
        - Token refresh before expiration
        - Connection cleanup
        - Exception handling for API requests

    Methods:
        get_data: Fetch data from FOLIO endpoints
        iter_data: Iterate through paginated FOLIO data
        post_data: Create new records in FOLIO
        put_data: Update existing records in FOLIO
        delete_data: Remove records from FOLIO

    The client uses context management to ensure proper resource cleanup:
        - Automatically logs out when exiting context
        - Closes HTTP connections
        - Handles token refresh and re-authentication

        ValueError: If timeout value is not a positive integer
        RuntimeError: If required environment variables are missing
        RuntimeError: If no access token is received during authentication
        ConnectionError: If connection fails
        TimeoutError: If server times out
        BadRequestError: 400 error - possibly due to CQL syntax error
        ItemNotFoundError: 404 error - possibly due to adressing UUID that does not exist
        RuntimeError: For HTTP errors not explicitly handled as named exceptions
    """

    DEFAULT_TIMEOUT: int = 60
    TOKEN_REFRESH_BUFFER: int = 10
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
        self._base_url: str = os.getenv("FOLIO_BASE_URL")  # type: ignore
        self.timeout: int = timeout
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiration: datetime = datetime.now(tz.utc)  # only initialization
        self._token_expiration_with_buffer: datetime = datetime.now(
            tz.utc
        )  # only initialization
        self.client = Client()
        self.client.headers.update(
            {
                "x-okapi-tenant": os.getenv("FOLIO_TENANT"),
            }  # type: ignore
        )
        self._retrieve_token()

    def __enter__(self) -> "FolioBaseClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._logout()
        if hasattr(self, "client") and self.client:
            self.client.close()

    def __repr__(self) -> str:
        auth_status = "authenticated" if self._access_token else "not authenticated"
        return (
            f"<{self.__class__.__name__}("
            f"folio='{self._base_url}', "
            f"tenant='{os.getenv('FOLIO_TENANT')}', "
            f"user='{os.getenv('FOLIO_USER')}', "
            f"status={auth_status}, "
            f"timeout={self.timeout})"
            ">"
        )

    @exception_handler
    def _retrieve_token(self, refresh: bool = False) -> None:
        """Retrieves or refreshes authentication token for FOLIO API access.
        This method handles both initial token retrieval and token refresh scenarios. For initial
        authentication, it uses username/password credentials from environment variables. For
        refresh, it uses existing refresh and access tokens.
        Args:
            refresh (bool, optional): If True, refreshes existing token. If False, performs
                login/re-login. Defaults to False.
        Raises:
            RuntimeError: If no access token is received in response
            ConnectionError: If connection fails
            TimeoutError: If server times out
            RuntimeError: If loging/refresh returns an error status code.
        Side Effects:
            - Updates self._access_token with new access token
            - Updates self._refresh_token with new refresh token
            - Updates self._token_expiration with token expiration timestamp
            - Updates self._token_expiration_with_buffer with adjusted expiration time
            - Updates client headers with new access token
        Returns:
            None
        """
        if refresh:
            url = f"{self._base_url}/authn/refresh"
            headers = {
                "Cookie": (
                    f"folioRefreshToken={self._refresh_token};"
                    f"folioAccessToken={self._access_token}"
                )
            }
            response = self.client.post(url, headers=headers, timeout=self.timeout)
        else:
            url = f"{self._base_url}/authn/login-with-expiry"
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
        self._access_token = response.cookies.get("folioAccessToken")
        self._refresh_token = response.cookies.get("folioRefreshToken")
        self._token_expiration = datetime.fromisoformat(
            response_json.get("accessTokenExpiration").replace("Z", "+00:00")
        )
        self._token_expiration_with_buffer = self._adjust_for_buffer(
            response_json.get("accessTokenExpiration")
        )
        if self._access_token:
            self.client.headers.update({"x-okapi-token": self._access_token})

    def _adjust_for_buffer(self, expiration: str) -> datetime:
        """Adjusts token expiration time by subtracting a buffer period.

        This method takes an ISO format expiration timestamp and subtracts a predefined
        buffer period to ensure token refresh happens before actual expiration.

            expiration (str): ISO format timestamp string representing token expiration time

        Returns:
            datetime: Adjusted expiration datetime with buffer period subtracted
        """
        expiration_dt = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
        expiration_with_buffer = expiration_dt - timedelta(
            seconds=self.TOKEN_REFRESH_BUFFER
        )
        return expiration_with_buffer

    def _manage_token(self):
        """
        Manages authentication token lifecycle.
        Checks token expiration and either refreshes it or retrieves a new one based on timing:
        - If current time is within buffer period before expiration, refreshes token
        - If token has already expired, retrieves new token via fresh login
        - Otherwise leaves existing token unchanged
        This internal method is called before API requests to ensure valid authentication.
        Returns:
            None
        """
        now: datetime = datetime.now(tz.utc)
        # If token is about to expire, refresh it
        if self._token_expiration_with_buffer < now < self._token_expiration:
            self._retrieve_token(refresh=True)
        # If the token has already expired, login again
        elif self._token_expiration < now:
            self._retrieve_token()

    @exception_handler
    def _logout(self) -> None:
        """Logs out the authenticated user from FOLIO.
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If server times out
            RuntimeError: If the logout returns an error status code.
        """
        self._manage_token()
        url = f"{self._base_url}/authn/logout"
        header = {
            "Cookie": (
                f"folioRefreshToken={self._refresh_token}; "
                f"folioAccessToken={self._access_token}"
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
        """
        Retrieves data from a specified FOLIO endpoint.
        Args:
            endpoint (str): The API endpoint to query.
            key (str, optional): JSON key to extract from response. If empty, returns full response.
            query (str, optional): CQL query string to filter results.
            limit (int, optional): Maximum number of records to return. Defaults to 10.
        Returns:
            Union[dict, list]: Response data, either filtered by key or complete response
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If server times out
            BadRequestError: 400 error - possibly due to CQL syntax error
            ItemNotFoundError: 404 error - possibly due to adressing UUID that does not exist
            RuntimeError: For HTTP errors not explicitly handled as named exceptions
        Example:
            >>> client.get_data("/users", key="users", query="username=test*", limit=5)
            [{'username': 'test1'}, {'username': 'test2'}]
        """
        self._manage_token()
        url = f"{self._base_url}{endpoint}"
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
        """Iterator for paginated data from FOLIO API endpoints.

        This method provides a generator to iterate through paginated data from FOLIO endpoints.
        It uses UUID-based pagination to fetch records in batches.

        Args:
            endpoint (str): The API endpoint to query.
            key (str): The key in the response that contains the data array.
            query (str, optional): CQL query string to filter results.
            limit (int, optional): Number of records to fetch per request. Defaults to 100.

        Yields:
            Generator: Individual records from the paginated response.

        Raises:
            ValueError: If limit is set to 0.
            RuntimeError: If the response format is invalid (not a list).
        """
        if limit == 0:
            raise ValueError("Limit cannot be 0 for iterator")
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
        """Posts data to a FOLIO endpoint.
        Args:
            endpoint (str): The API endpoint to post to
            payload (dict): The data payload to send in the request body
        Returns:
            Union[dict, int]: The JSON response from the API if successful and response contains JSON,
                              or the HTTP status code if response does not contain JSON
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If server times out
            BadRequestError: 400 error - possibly due to error in payload
            RuntimeError: For HTTP errors not explicitly handled as named exceptions
        """
        self._manage_token()
        url = f"{self._base_url}{endpoint}"
        response = self.client.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return int(response.status_code)

    @exception_handler
    def put_data(self, endpoint: str, payload: dict) -> dict | int:
        """
        Makes a PUT request to specified FOLIO API endpoint with given payload.
        Args:
            endpoint (str): The API endpoint to send the PUT request to
            payload (dict): The data to be sent in the request body
        Returns:
            Union[dict, int]: The JSON response from the API if successful and response contains JSON,
                              or the HTTP status code if response body is empty
        Raises:
            ValueError: If payload is empty
            ConnectionError: If connection fails
            TimeoutError: If server times out
            BadRequestError: 400 error - possibly due to error in payload
            ItemNotFoundError: 404 error - possibly due to adressing UUID that does not exist
            RuntimeError: For HTTP errors not explicitly handled as named exceptions
        """
        if not payload:
            raise ValueError("Payload cannot be empty")
        self._manage_token()
        url = f"{self._base_url}{endpoint}"
        response = self.client.put(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return int(response.status_code)

    @exception_handler
    def delete_data(self, endpoint: str) -> int:
        """
        Performs a DELETE request to the specified endpoint.
        Args:
            endpoint (str): The API endpoint to send the DELETE request to.
                           Will be appended to the base URL.
        Returns:
            int: The HTTP status code of the response.
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If server times out
            BadRequestError: 400 error - bad request
            ItemNotFoundError: 404 error - possibly due to adressing UUID that does not exist
            RuntimeError: For HTTP errors not explicitly handled as named exceptions
        """
        self._manage_token()
        url = f"{self._base_url}{endpoint}"
        response = self.client.delete(url, timeout=self.timeout)
        response.raise_for_status()
        return int(response.status_code)
