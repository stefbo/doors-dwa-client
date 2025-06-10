# doors-dwa-client

**doors-dwa-client** is a Python library for interacting with IBM DOORS Classic via the Web Access (DWA) and OSLC APIs. It provides a high-level, Pythonic interface for navigating DOORS folder structures, querying requirements, and working with OSLC resource shapes and data.

## Features

- **DWA API support**: Navigate folders, projects, and documents in DOORS Classic.
- **OSLC API support**: Query requirements, retrieve resource shapes, and interact with OSLC-compliant resources.

## Installation

Install from PyPI:

```bash
pip install doors-dwa-client
```

Alternatively, install from source:

```bash
git clone https://github.com/stefbo/doors-dwa-client.git
cd doors-dwa-client
pip install .
```

## Requirements

Requires Python 3.10+.

## Getting Started

You will need access to a DOORS Web Access server and valid credentials. The library does not include any domain-specific logic and is suitable for generic DOORS Classic installations.

### Authentication

All interactions require a login session:

```python
from dwa_client.auth import LoginSession

login = LoginSession(base_url, username, password)
login.login()
```

Below are some tutorials for the main features:

### 1. Print the DOORS Project Tree

This script logs in, navigates to a folder (such as the "Projects" root), and prints the folder/document hierarchy in a tree format.

```python
from dwa_client.auth import LoginSession
from dwa_client import DWAClient, Guid
from dwa_client.printers import FolderTreePrinter
from dwa_client.cache import SQLiteCache

# Setup login and client
login = LoginSession(base_url, username, password)
login.login()
client = DWAClient(login)

# Get the root folder (replace with your folder GUID)
projects_guid = Guid("YOUR_PROJECTS_FOLDER_GUID")
root_folder = client.get_root_folder(projects_guid)

# Print the folder tree
FolderTreePrinter(show_objects=False).print_tree(root_folder)
```

### 2. List Objects in a Document

This script retrieves all objects (requirements, headings, etc.) from a specific DOORS document.

```python
from dwa_client.auth import LoginSession
from dwa_client import DWAClient, Guid

login = LoginSession(base_url, username, password)
login.login()
client = DWAClient(login)

# Replace with your document GUID
document_guid = Guid("YOUR_DOCUMENT_GUID")
doc = client.get_document(document_guid)

objects = doc.get_objects(start_index=0, fetch_count=100)
for obj in objects:
    print(obj)
print(f"Total objects: {len(objects)}")
```

### 3. Query OSLC Resource Shapes and Requirements

This script demonstrates how to use the OSLC API to discover resource shapes and query requirements.

```python
from dwa_client.auth import LoginSession
from dwa_client.oslc import OSLCClient
from dwa_client.transport import HTTPTransport, SQLiteCacheTransport

login = LoginSession(base_url, username, password)
login.login()

# Use OSLCClient with optional caching
client = OSLCClient(login)

# Get the root OSLC catalog
root_catalog = client.get_root_catalog()

# Traverse catalogs and providers (replace with your own path and module title)
catalogs_path = ["Projects", "Your Folder", "Your Project"]
module_title = "Your Module"

cur_catalog = root_catalog
for p in catalogs_path:
    cur_catalog = cur_catalog.get_service_provider_catalog_by_title(p)
    if not cur_catalog:
        raise Exception(f"Catalog '{p}' not found.")

module_provider = next(
    (p for p in cur_catalog.get_service_providers() if p.get_title() == module_title), None
)
if not module_provider:
    raise Exception(f"Module provider '{module_title}' not found.")

# Get resource shape and print properties
tsr_qc = module_provider.get_query_capabilities()
tsr_shape = tsr_qc.get_resource_shape()
for prop in tsr_shape.get_properties():
    print(f"Property: {prop.get_name()} - {prop.get_title()}")

# Query requirements
query_result = tsr_qc.query(use_enum_labels=True)
for member in query_result.get_members():
    print(f"Requirement: {member.get_title()} - {member.get_description()}")
```

## Documentation

- API documentation is available in the source code via docstrings.
- See the `examples/` directory for more usage patterns.

## Contributing

Contributions are welcome! Please open issues or pull requests for bug fixes, improvements, or new features.

## License

Copyright, 2025, Stefan Bolus

This project is licensed under the MIT License.

---

**doors-dwa-client** is not affiliated with or endorsed by IBM. Use at your own risk.
