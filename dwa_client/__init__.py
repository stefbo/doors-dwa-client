"""Top-level package for the DOORS DWA client library."""

from dwa_client.client import DWAClient
from dwa_client.resources import Folder, GUID, Document, DocumentObject

__version__ = "0.1.0"

__all__ = ["DWAClient", "Folder", "GUID", "Document", "DocumentObject"]
