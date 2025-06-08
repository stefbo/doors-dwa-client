from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import requests


class Transport(ABC):
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
        self._session = login.raw_session()

    def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        hdr = self._login.prepare_headers(headers)
        r = self._session.post(url, data=data, headers=hdr)
        r.raise_for_status()
        print(f"POST {url} -> {r.status_code}, resp: {r.text}")
        return r

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        hdr = self._login.prepare_headers(headers)
        r = self._session.get(url, headers=hdr)
        r.raise_for_status()
        print(f"GET {url} -> {r.status_code}, resp: {r.text}")
        return r


class StubTransport(Transport):
    """
    Feed canned JSON to unit-tests; no network required.
    """

    def __init__(self, fixtures: Dict[str, Any] | None = None) -> None:
        self._fx = fixtures or {}

    def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        key = (url, tuple(sorted(data.items())))
        if key not in self._fx:
            raise RuntimeError(f"Missing stub for {url}")
        # Create a fake Response object
        resp = requests.Response()
        resp.status_code = 200
        resp._content = (
            self._fx[key].encode("utf-8")
            if isinstance(self._fx[key], str)
            else self._fx[key]
        )
        return resp

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        raise NotImplementedError("StubTransport does not support get yet")
