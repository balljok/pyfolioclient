# pyfolioclient

A Python client for interacting with FOLIO's APIs.

## Prerequisites

- Python 3.9+
- FOLIO Poppy release or newer (requires expiring tokens)

## Configuration

The clients requires:

- An URL to the FOLIO OKAPI (i.e. foliopath/okapi)
- The username of the tenant in FOLIO
- The username of a user with adequate permissions in FOLIO and the password for the user

## Installation

Choose your preferred installation method:

```bash
pip install pyfolioclient
# or
pip3 install pyfolioclient
# or
uv add pyfolioclient
```

## Features

### FolioBaseClient

Features:

- Authentication and token management
- Re-authentication when token expires
- Persistent connections using httpx Client
- Support for all standard HTTP methods (GET, POST, PUT, DELETE)
- Iterator implementation for paginated GET requests
- Resource cleanup through context manager

### FolioClient

Extends FolioBaseClient and provides useful methods for common operations in FOLIO. Provided for convencience. It contains convenience methods for:

- Users
- Inventory
    - Instances
    - Holdings
    - Items
- Circulation
    - Loans
    - Requests
- Data import

## Usage Examples

### FolioBaseClient

```python
from pyfolioclient import FolioBaseClient

with FolioBaseClient(base_url, tenant, user, password) as folio:
    for user in folio.iter_data("/users", key="users", cql_query="username==bob*"):
        print(user)
```

### FolioClient

```python
from pyfolioclient import FolioClient, ItemNotFoundError

with FolioClient(base_url, tenant, user, password) as folio:
    for loan in folio.get_loans("status=Open"):
        print(loan.get("dueDate"))
    
    try:
        folio.delete_user_by_id("dcf1fabc-3165-4099-b5e6-aa74f95dee73")
    except ItemNotFoundError as err:
        print("No matching user")
```

## A note on custom exceptions

A number of custom exceptions have been implemented:

- BadRequestError (HTTP status code 400)
- ItemNotFoundError (HTTP status code 404)
- UnprocessableContentError (HTTP status code 422)

Through experience we have found these useful to be able to handle explicitly and separately, rather than being raised as a general HTTP error. 

## FOLIO API Notes

FOLIO provides two types of endpoints:
1. Business Logic Modules (`/inventory/items`)
2. Storage Modules (`/item-storage/items`)

For detailed information:
- [Business vs Storage Modules](https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules)

FOLIO API endpoints can be queried using the CQL query language. For an introduction refer to:
- [CQL Query Reference](https://github.com/folio-org/raml-module-builder#cql-contextual-query-language)

Note: Query capabilities may be limited to specific JSON response fields.

## Credits

- Developed at Linköping University
- Inspired by [FOLIO-FSE/FolioClient](https://github.com/FOLIO-FSE/FolioClient) by Theodor Tolstoy [@fontanka16](https://github.com/fontanka16)
