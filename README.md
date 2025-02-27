# pyfolioclient

A Python client for interacting with FOLIO's APIs.

## Overview

This package provides a streamlined interface for FOLIO API interactions.

## Prerequisites

- Python 3.9+
- FOLIO Poppy release or newer (token expiry support required)
- Environment configuration file (.env)

## Configuration

Create a `.env` file with:

```env
FOLIO_BASE_URL="https://your.folio.instance/okapi"
FOLIO_TENANT="folio_tenant"
FOLIO_USER="user_in_folio_with_adequate_permissions"
FOLIO_PASSWORD="password_for_folio_user"
```

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

Implements useful methods for common operations in FOLIO. Provided for convencience. Focus on:

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
    for user in folio.iter_data("/users", key="users", query="username==bob*"):
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

## FOLIO API Notes

FOLIO provides two types of endpoints:
1. Business Logic Modules (`/inventory/items`)
2. Storage Modules (`/item-storage/items`)

For detailed information:
- [Business vs Storage Modules](https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules)

FOLIO API endpoints uses the CQL query language. For an introduction refer to:
- [CQL Query Reference](https://github.com/folio-org/raml-module-builder#cql-contextual-query-language)

Note: Query capabilities may be limited to specific JSON response fields.

## Credits

- Developed at Linköping University
- Inspired by [FOLIO-FSE/FolioClient](https://github.com/FOLIO-FSE/FolioClient) by Theodor Tolstoy (@fontanka16)
