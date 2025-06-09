from abc import ABC, abstractmethod
import os
from typing import Any, Dict, Optional
import requests
import re
import time
from io import StringIO

from dwa_client.cache import SQLiteCache


class Transport(ABC):
    """Abstract base class for transport layer, defining the interface for HTTP operations.

    Note: This transport is used for both the Web Access and the OSLC API."""

    @abstractmethod
    def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> requests.Response: ...

    @abstractmethod
    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> requests.Response: ...


class HTTPTransport(Transport):
    """
    Thin veneer around requests – *no* business logic, only retries etc.
    """

    def __init__(self, login: "LoginSession") -> None:
        self._login = login
        self._session: requests.Session = login.raw_session()

    def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        hdr = self._login.prepare_headers(headers)
        r = self._session.post(url, data=data, headers=hdr)
        r.raise_for_status()
        return r

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        hdr: Dict[str, str] = self._login.prepare_headers(headers)
        r: requests.Response = self._session.get(
            url, headers=hdr, allow_redirects=False
        )
        r.raise_for_status()
        return r


class DebugTransport(Transport):
    def __init__(self, wrapped: Transport) -> None:
        self._wrapped = wrapped

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        print(f"[DebugTransport] GET {url} with headers: {headers}")
        resp = self._wrapped.get(url, headers)
        print(f"[DebugTransport] GET {url} -> {resp.status_code}")
        return resp

    def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        print(f"[DebugTransport] POST {url} with headers: {headers} and data: {data}")
        resp = self._wrapped.post(url, data, headers)
        print(f"[DebugTransport] POST {url} -> {resp.status_code}")
        return resp


class SQLiteCacheTransport(Transport):
    def __init__(
        self,
        wrapped: Transport,
        cache_db_path: str = "transport_cache.db",
        ttl: Optional[int] = 3600,
    ) -> None:
        self._wrapped = wrapped
        self._cache = SQLiteCache(cache_db_path)
        self._ttl = ttl

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        cached_content = self._cache.get(url)
        if cached_content is not None:
            resp = requests.Response()
            resp.status_code = 200
            resp.url = url
            if isinstance(cached_content, str):
                resp._content = cached_content.encode("utf-8")
            else:
                resp._content = cached_content
            resp.headers["X-Cache"] = "HIT"
            return resp

        resp = self._wrapped.get(url, headers)
        resp.raise_for_status()
        # Store as string for compatibility with SQLiteCache
        self._cache.put(
            url, resp.content.decode("utf-8", errors="replace"), ttl=self._ttl
        )
        resp.headers["X-Cache"] = "MISS"
        return resp

    def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        return self._wrapped.post(url, data, headers)
