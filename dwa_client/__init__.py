"""Top-level package for the DOORS DWA client library."""

from dwa_client.client import DWAClient
from dwa_client.resources import Folder, Guid, Document, DocumentObject

__version__ = "0.1.0"

__all__ = ["DWAClient", "Folder", "Guid", "Document", "DocumentObject", "__version__"]
