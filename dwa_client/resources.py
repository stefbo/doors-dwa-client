from __future__ import annotations
from typing import Any, Dict, Iterator, List, TYPE_CHECKING
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from typing import Optional
import json

# -------------------------------------------------------------------
# Avoid a run-time import loop: only import DWAClient when a
# static type checker (mypy / pyright / pylance) is analysing the file
# -------------------------------------------------------------------
if TYPE_CHECKING:
    from dwa_client.client import DWAClient


class RemoteResource:
    def __init__(
        self, client: DWAClient, guid: "Guid", meta: Dict[str, Any] | None = None
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
    def __init__(self, client: DWAClient, node: Dict[str, Any]):
        super().__init__(client, Guid(node["guid"]), node)

    @classmethod
    def _from_stub(cls, client: DWAClient, guid: "Guid"):
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
        payload: dict[str, str] = {
            "documentGuid": str(self.guid),
            "startIndex": str(start_index),
            "fetchCount": str(fetch_count),
            "beforeOnly": "false",
            "firstPageFallback": "false",
            "isRefresh": "false",
            "dwaUser": self._client.login.user,
            "DWA_TOKEN": self._client.login.token,
        }

        if view_guid:
            payload["viewGuid"] = view_guid

        raw: str = self._client._post_raw(
            "dwa/json/doors/documentnode/getPage", payload
        )
        try:
            resp_json = json.loads(raw)
        except json.JSONDecodeError:
            # Not JSON, so treat as HTML
            return parse_doors_objects_from_html(raw)
        if isinstance(resp_json, dict) and resp_json.get("success") == "false":
            reason = resp_json.get("failureReason", {})
            msg = reason.get("logMsg") or reason.get("msgKey") or "Unknown error"
            raise RuntimeError(f"DOORS DWA error: {msg}")
        raise RuntimeError("Unexpected JSON response from DOORS DWA.")


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
    soup = BeautifulSoup(html, "lxml")
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


class Object(RemoteResource):
    """
    Represents a requirement (“object”) row inside a module.
    """

    def __init__(self, client: DWAClient, node: Dict[str, Any]):
        super().__init__(client, Guid(node["guid"]), node)

    # module-specific helpers here: get_text(), links(), etc.

    def _lazy_load(self):
        # placeholder – real call similar to _get_page
        self._loaded = True


class Guid(str):
    """
    Simple value-object wrapper.  Sub-classing str lets us keep
    hashing/comparison fast & natural: Guid("…") == "…"  ➜ True
    """

    def __new__(cls, value: str) -> "Guid":
        return str.__new__(cls, value)
        # placeholder – real call similar to _get_page
        self._loaded = True
