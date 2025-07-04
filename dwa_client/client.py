from __future__ import annotations
from typing import Dict, Any, List, Optional
from dwa_client.auth import LoginSession
from dwa_client.guid import GUID
from dwa_client.transport import Transport, HTTPTransport
from dwa_client.resources import (
    Folder,
    Project,
    Document,
    DocumentObject,
    parse_doors_objects_from_html,
    RemoteResource,
)
from rdflib import Graph
import json
import logging

logger = logging.getLogger("dwa_client")


class DWAClient:
    """
    High-level façade.  Exposes handy helpers (get_root_folder, get_object…)
    and manages identity map + lazy resources.
    """

    def __init__(
        self,
        login: LoginSession,
        transport: Transport | None = None,
    ) -> None:
        self.login = login
        self.transport = transport or HTTPTransport(login)
        self._identity: Dict[GUID, RemoteResource] = {}

    # ---------- raw API helpers (was Api class) -------------------------
    def _post_json(
        self,
        path: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = f"{self.login.base_url}/{path.lstrip('/')}"
        resp = self.transport.post(url, payload, headers=headers)
        result = resp.json()
        return result

    def _post_raw(self, path: str, payload: Dict[str, Any]) -> str:
        """
        Content-type agnostic POST. Returns raw response text.
        """
        url = f"{self.login.base_url}/{path.lstrip('/')}"
        resp = self.transport.post(url, payload)
        return resp.text

    def _get_rdf(self, path: str, headers: Dict[str, str] | None = None) -> Graph:
        url = f"{self.login.base_url}/{path.lstrip('/')}"
        hdr = headers or {}
        hdr["Accept"] = "application/rdf+xml"
        resp = self.transport.get(url, headers=hdr)
        g = Graph()
        g.parse(data=resp.text, format="xml")
        return g

    # original get_children ------------------------------------------------
    def _get_children_nodes(self, parent: GUID):
        data = {
            "parentGuid": str(parent),
            "configurationContext": "",
            "isDelegatedUI": "false",
            "showBaselineInfoWithGC": "false",
            "basicInfo": "true",
            "dwaUser": self.login.user,
            "DWA_TOKEN": self.login.token,
        }
        result = self._post_json("dwa/json/doors/node/getChildren", data)
        return result

    def get_document_objects(
        self,
        document_guid: GUID,
        start_index: int = 0,
        fetch_count: int = 10000,
        view_guid: str | None = None,
    ) -> list[DocumentObject]:
        """
        Fetches and parses all objects from a document using getPage.
        Returns a list of DocumentObject.
        Raises RuntimeError if the server returns an error.
        """
        payload: dict[str, str] = {
            "documentGuid": str(document_guid),
            "startIndex": str(start_index),
            "fetchCount": str(fetch_count),
            "beforeOnly": "false",
            "firstPageFallback": "false",
            "isRefresh": "false",
            "dwaUser": self.login.user,
            "DWA_TOKEN": self.login.token,
        }

        if view_guid:
            payload["viewGuid"] = view_guid

        raw: str = self._post_raw("dwa/json/doors/documentnode/getPage", payload)
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

    def get_document_attributes(
        self,
        document_guid: GUID,
    ) -> Dict[str, Any]:
        """
        Fetches and parses all attributes for a document.
        Returns the parsed JSON document containing all attributes.
        Raises RuntimeError if the server returns an error.
        """

        payload: dict[str, str] = {
            "objectGuid": str(document_guid),
            "dwaUser": self.login.user,
            "DWA_TOKEN": self.login.token,
        }

        raw: str = self._post_raw("dwa/json/doors/node/getAttributes", payload)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse JSON response from DOORS DWA (`getAttributes` for %s). Response: %s",
                document_guid,
                raw,
            )
            return {}  # Return empty dict if parsing fails

    # ---------- public domain helpers ------------------------------------
    def get_folder(self, guid: GUID) -> Folder:
        if guid in self._identity:
            return self._identity[guid]  # type: ignore[return-value]
        # minimal metadata until first access
        proxy = Folder._from_stub(self, guid)
        self._identity[guid] = proxy
        return proxy

    def get_document(self, guid: GUID) -> Document:
        if guid in self._identity:
            return self._identity[guid]
        # minimal metadata until first access
        proxy = Document._from_stub(self, guid)
        self._identity[guid] = proxy
        return proxy

    def get_root_folder(self, guid: str | GUID) -> Folder:
        if isinstance(guid, GUID):
            return self.get_folder(guid)
        return self.get_folder(GUID.from_string(str(guid)))

    # used internally by Folder.get_children()
    def _instantiate_from_node(self, node: dict[str, Any]) -> RemoteResource:
        guid = GUID.from_string(node["guid"])
        if guid in self._identity:
            res = self._identity[guid]
            res._hydrate(node)  # type: ignore[attr-defined]
            return res
        module_type = node.get("moduleType")
        if module_type == "PROJECT":
            res = Project(self, node)
        elif module_type == "DOCUMENT":
            res = Document(self, node)
        else:
            res = Folder(self, node)
        self._identity[guid] = res
        return res
