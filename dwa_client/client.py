from __future__ import annotations
from typing import Dict, Any, List
from dwa_client.auth import LoginSession
from dwa_client.transport import Transport, HTTPTransport
from dwa_client.cache import Cache, NullCache
from dwa_client.resources import Folder, Object, Guid, Project, Document
from rdflib import Graph


class DWAClient:
    """
    High-level façade.  Exposes handy helpers (get_root_folder, get_object…)
    and manages identity map + lazy resources.
    """

    def __init__(
        self,
        login: LoginSession,
        transport: Transport | None = None,
        cache: Cache | None = None,
    ) -> None:
        self.login = login
        self.transport = transport or HTTPTransport(login)
        self.cache = cache or NullCache()
        self._identity: Dict[Guid, "RemoteResource"] = {}

    # ---------- raw API helpers (was Api class) -------------------------
    def _post_json(self, path: str, payload: Dict[str, Any]) -> Any:
        url = f"{self.login.base_url}/{path.lstrip('/')}"
        cached = self.cache.get(url + str(sorted(payload.items())))
        if cached:
            return cached
        resp = self.transport.post(url, payload)
        result = resp.json()
        self.cache.put(url + str(sorted(payload.items())), result)
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
    def _get_children_nodes(self, parent: Guid):
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

    # ---------- public domain helpers ------------------------------------
    def get_folder(self, guid: Guid) -> Folder:
        if guid in self._identity:
            return self._identity[guid]  # type: ignore[return-value]
        # minimal metadata until first access
        proxy = Folder._from_stub(self, guid)
        self._identity[guid] = proxy
        return proxy

    def get_document(self, guid: Guid) -> Document:
        if guid in self._identity:
            return self._identity[guid]
        # minimal metadata until first access
        proxy = Document._from_stub(self, guid)
        self._identity[guid] = proxy
        return proxy

    def get_root_folder(self, guid: str | Guid) -> Folder:
        return self.get_folder(Guid(str(guid)))

    # used internally by Folder.get_children()
    def _instantiate_from_node(self, node: dict[str, Any]) -> "RemoteResource":
        guid = Guid(node["guid"])
        if guid in self._identity:
            res = self._identity[guid]
            res._hydrate(node)  # type: ignore[attr-defined]
            return res
        module_type = node.get("moduleType")
        if module_type == "FOLDER":
            res = Folder(self, node)
        elif module_type == "PROJECT":
            res = Project(self, node)
        elif module_type == "DOCUMENT":
            res = Document(self, node)
        else:
            res = Object(self, node)
        self._identity[guid] = res
        return res
