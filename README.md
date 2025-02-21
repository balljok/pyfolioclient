# pyfolioclient

This package provides a client for interacting with Folio's APIs. 

The package requires a .env file with the following parameters:

```
FOLIO_BASE_URL="https://your.folio.instance/okapi"
FOLIO_TENANT="folio_tenant"
FOLIO_USER="user_in_folio_with_adequate_permissions"
FOLIO_PASSWORD="password_for_folio_user"
```

## FolioBaseClient

FolioBaseClient provides core functionality for logging in and out of Folio, and keeping the access token alive. It also provides wrappers for GET, POST, PUT and DELETE. Getting large amounts of data is supported through a generator function.

### Features

* Login and logout
* Keeping token alive - only sending password over network when necessary
* HTTPX client for efficient interaction
* Implemented as a context manager
* Useful exception management

### Requirements

* Python 3.9 or higher
* Folio Poppy release or higher since it only supports tokens with expiry

## FolioClient

FolioClient extends the base client with methods for the most common interactions with Folio.

* Users
    * Getting users
    * Updating user information
    * Creating new users
    * Deleting users
* Inventory
* Circulation

## Installation

```
pip install pyfolioclient
```

or 

```
pip3 install pyfolioclient
```

or 

```
uv add pyfolioclient
```

## Usage

### FolioBaseClient

```
from pyfolioclient import FolioBaseClient

with FolioBaseClient(timeout=120) as folio:
    for user in folio.iter_data(query = "username==bob*"):
        print(user)
```


### FolioClient

```
from pyfolioclient import FolioClient

with FolioClient() as folio:
    for entry in folio.get_instances_by_query("title==Love*"):
        print(entry)
```

## About Folio API:s

Folio provides endoints to both business logic modules and storage modules. For example:
/inventory/items
/item-storage/items

Please refer to this page to understand the differences:
<https://folio-org.atlassian.net/wiki/spaces/FOLIOtips/pages/5673472/Understanding+Business+Logic+Modules+versus+Storage+Modules>

The query language used is CQL. Please refer to this page for a brief reference:
<https://github.com/folio-org/raml-module-builder#cql-contextual-query-language>

Do note that not all parts of a JSON reply from Folio are adressable in queries. 


## Acknowledgement

The code based was initially developed for internal use at Linköping university. However, the following project by Theodor Tolstoy (@fontanka16) has provided inspiration for improvements:

<https://github.com/FOLIO-FSE/FolioClient>