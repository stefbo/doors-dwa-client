from __future__ import annotations
from typing import Any, Dict, Iterator, List, TYPE_CHECKING
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from typing import Optional
from dwa_client.guid import GUID
import json

# -------------------------------------------------------------------
# Avoid a run-time import loop: only import DWAClient when a
# static type checker (mypy / pyright / pylance) is analysing the file
# -------------------------------------------------------------------
if TYPE_CHECKING:
    from dwa_client.client import DWAClient


class RemoteResource:
    """Base class for all remote resources (Folder, Project, Document, etc.) in DOORS Web Access (DWA).

    This class provides common functionality for handling remote resources,
    including lazy loading, hydration, and basic metadata access.

    Hydration is the process of populating the resource's metadata from the server.
    """

    def __init__(
        self, client: "DWAClient", guid: "GUID", meta: Dict[str, Any] | None = None
    ) -> None:
        self._client = client
        self.guid = guid
        self._meta = meta or {}
        self._loaded = bool(meta)

    # ---------- hydration helpers -------------------------
    def _hydrate(self, meta: Dict[str, Any]) -> None:
        """Merge newer meta in place (identity map keeps object alive)."""
        self._meta.update(meta)
        self._loaded = True

    # ---------- common convenience ------------------------
    @property
    def name(self) -> str:
        if not self._loaded:
            self._lazy_load()
        return self._meta.get("mainAttribute", "")

    def _lazy_load(self):  # overriden by subclasses
        raise NotImplementedError


@dataclass(init=False)
class Folder(RemoteResource):
    _children_cache: List["RemoteResource"] | None = field(default=None, init=False)

    # used only by DWAClient
    def __init__(self, client: "DWAClient", node: Dict[str, Any]):
        super().__init__(client, GUID.from_string(node["guid"]), node)

    @classmethod
    def _from_stub(cls, client: "DWAClient", guid: "GUID"):
        return cls(client, {"guid": str(guid), "mainAttribute": str(guid)})

    # --------------- navigation ---------------------------
    def get_children(self, refresh: bool = False) -> List["RemoteResource"]:
        if self._children_cache is None or refresh:
            nodes = self._client._get_children_nodes(self.guid)
            self._children_cache = [
                self._client._instantiate_from_node(n) for n in nodes
            ]
        return self._children_cache

    def walk(self) -> Iterator["Folder"]:
        yield self
        for child in self.get_children():
            if isinstance(child, Folder):
                yield from child.walk()

    # --------------- private ------------------------------
    def _lazy_load(self):
        # a folder's own meta isn’t available via DWA JSON
        # without its parent, so we do nothing for now
        self._loaded = True


@dataclass(init=False)
class Project(Folder):
    # Inherits everything from Folder, but can be extended for project-specific logic
    pass


@dataclass(init=False)
class Document(Folder):
    """
    Represents a DOORS document (moduleType == "DOCUMENT").
    """

    def get_objects(
        self,
        start_index: int = 0,
        fetch_count: int = 10000,
        view_guid: Optional[str] = None,
    ) -> list["DocumentObject"]:
        """
        Fetches and parses all objects from this document using getPage.
        Returns a list of DocumentObject.
        Raises RuntimeError if the server returns an error.

        :param view_guid: Optional GUID of a specific view to fetch objects from.
        """
        return self._client.get_document_objects(
            self.guid,
            start_index=start_index,
            fetch_count=fetch_count,
            view_guid=view_guid,
        )


class DocumentObject:
    """
    Represents a single object/row returned by getPage (parsed from HTML).
    """

    def __init__(
        self,
        urn: str,
        object_id: str,
        paragraph_number: str,
        heading_num: Optional[str],
        heading_text: Optional[str],
        identifier: Optional[str],
    ) -> None:
        self.urn = urn
        self.object_id = object_id
        self.paragraph_number = paragraph_number
        self.heading_num = heading_num
        self.heading_text = heading_text
        self.identifier = identifier

    def __repr__(self) -> str:
        return (
            f"DocumentObject(urn={self.urn!r}, object_id={self.object_id!r}, "
            f"paragraph_number={self.paragraph_number!r}, heading_num={self.heading_num!r}, "
            f"heading_text={self.heading_text!r}, identifier={self.identifier!r})"
        )


def parse_doors_objects_from_html(html: str) -> List[DocumentObject]:
    soup = BeautifulSoup(html, "xml")
    artifacts: List[DocumentObject] = []
    for table in soup.find_all(
        "table", attrs={"guid": True, "urn": True, "objectid": True}
    ):
        urn = table.get("urn")
        object_id = table.get("objectid")
        paragraph_number = table.get("paragraphnumber")

        identifier = None
        col5 = table.find("td", class_="column5")
        if col5:
            identifier = "".join(col5.stripped_strings)

        heading_num = None
        heading_text = None
        col6 = table.find("td", class_="column6")
        if col6:
            heading_span = col6.find("span", class_="headingNum")
            if heading_span:
                heading_num = heading_span.get_text(strip=True)
            heading_div = col6.find(
                "div", class_=lambda x: x and x.startswith("heading")
            )
            if heading_div:
                full_heading = heading_div.get_text(strip=True)
                if heading_num and full_heading.startswith(heading_num):
                    heading_text = full_heading[len(heading_num) :].strip()
                else:
                    heading_text = full_heading

        artifacts.append(
            DocumentObject(
                urn=urn,
                object_id=object_id,
                paragraph_number=paragraph_number,
                heading_num=heading_num,
                heading_text=heading_text,
                identifier=identifier,
            )
        )
    return artifacts
