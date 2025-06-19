from typing import Optional, Union
from dwa_client.auth import LoginSession
from dwa_client.transport import HTTPTransport, Transport
from dwa_client.cache import Cache, NullCache
from rdflib import Graph, URIRef

from dwa_client.oslc.views import ServiceProviderCatalogView, ServiceProviderView


class OSLCClient:
    def __init__(
        self,
        login: LoginSession,
        transport: Optional[Transport] = None,
        cache: Optional[Cache] = None,
    ) -> None:
        self.login = login
        self.transport = transport or HTTPTransport(login)
        self.base_url = login.base_url.rstrip("/")
        self.cache = cache or NullCache()
        self._headers = {
            "Accept": "application/rdf+xml",  #
            "OSLC-Core-Version": "2.0",  #
            # Additional headers to handle large responses for queries:
            "Accept-Encoding": "gzip, deflate",
        }

    def _urn_or_url_to_url(self, urn_or_url: Union[URIRef, str], path: str) -> str:
        if isinstance(urn_or_url, str) and urn_or_url.startswith("urn:"):
            return f"{self.base_url}{path.rstrip('/')}/{urn_or_url}"
        return str(urn_or_url)

    def get_url(self, abs_url: Union[URIRef, str], g: Optional[Graph] = None) -> Graph:
        """Retrieve a resource from the given absolute URL, with caching of raw response.

        If a graph is provided, it will be used to parse the response. Otherwise,
        a new graph will be created.

        Returns g (if provided) or a new Graph instance with the parsed data.
        """
        url = str(abs_url)
        cached_content = self.cache.get(url)
        if cached_content is not None:
            if g is None:
                g = Graph()
            g.parse(data=cached_content, format="xml")
            return g
        resp = self.transport.get(abs_url, headers=self._headers)
        resp.raise_for_status()
        if g is None:
            g = Graph()
        g.parse(data=resp.content, format="xml")
        self.cache.put(url, resp.text)  # str required
        return g

    def get_root_catalog(self) -> "ServiceProviderCatalogView":
        """
        Retrieve the root service provider catalog.
        This is typically the catalog that contains all service providers.
        """
        url = f"{self.base_url}/dwa/rm/discovery/catalog"
        cached_content = self.cache.get(url)
        if cached_content is not None:
            graph = Graph()
            graph.parse(data=cached_content, format="xml")
            return ServiceProviderCatalogView(self, graph, url)
        resp = self.transport.get(url, headers=self._headers)
        resp.raise_for_status()
        graph = Graph()
        graph.parse(data=resp.content, format="xml")
        self.cache.put(url, resp.content)

        return ServiceProviderCatalogView(self, graph, URIRef(resp.url))
