from typing import Iterator, List, Optional, Dict, Any, Union
import urllib
from rdflib import Graph, Literal, URIRef, RDF

# from dwa_client.oslc.client import OSLCClient
from dwa_client.oslc.common import OSLC, DCTERMS, RDFS, Occurs


class ResourceView:
    """Base class for a resource views in the OSLC ecosystem.

    This class provides a common interface for all OSLC views.
    It is not meant to be instantiated directly, but rather used as a base class
    for other views.
    """

    def __init__(self, client: "OSLCClient", graph: Graph, node: URIRef) -> None:
        self.client = client
        self.graph = graph
        self.node: URIRef = node

    def make_sure_populated(self) -> None:
        self.client.get_url(self.node, self.graph)


class StatementView(ResourceView):
    """View of an OSLC statement, which is a triple in the RDF graph.

    The QueryResultView uses this to represent links between requirements
    with predicates like `oslc_rm:refines`, `oslc_rm:verifies` or custom
    predicates like "http://acme.com/ns/linktypes#references".
    """

    def get_subject(self) -> URIRef:
        """Get the subject of the statement."""
        return self.graph.value(self.node, RDF.subject)

    def get_predicate(self) -> URIRef:
        """Get the predicate of the statement."""
        return self.graph.value(self.node, RDF.predicate)

    def get_object(self) -> Union[URIRef, Literal]:
        """Get the object of the statement."""
        return self.graph.value(self.node, RDF.object)


class RequirementView(ResourceView):
    """View of an OSLC requirement resource.

    This view represents a requirement in the OSLC ecosystem.
    It provides methods to access the properties of the requirement.

    Note: "Requirements" Is the term used in the OSLC ecosystem to refer to
    resources that are typically requirements in DOORS classic terms. However,
    as in DOORS Web Access, these resources can be any kind of object, such
    as "Info", "Example", "Test Case", etc.

    Note: The URIs for requirements are links to the DWA and cannot be used on
    the OSLC API. The graph therefore has to be populated already.
    """

    def make_sure_populated(self) -> None:
        """Override to do nothing, as the query result is already populated."""

    def get_title(self) -> Optional[str]:
        """Get the title of the requirement."""
        title = self.graph.value(self.node, DCTERMS.title)
        return str(title) if title else None

    def get_description(self) -> Optional[str]:
        """Get the description of the requirement."""
        desc = self.graph.value(self.node, DCTERMS.description)
        return str(desc) if desc else None


class QueryResultView(ResourceView):
    """View of a query result in the OSLC ecosystem.

    This view represents the result of a query against an OSLC service.
    It provides methods to access the resources returned by the query.
    """

    def make_sure_populated(self) -> None:
        """Override to do nothing, as the query result is already populated."""

    def get_members(self) -> Iterator[RequirementView]:
        """Get the resources from the query result."""
        for resource in self.graph.objects(self.node, RDFS.member):
            yield RequirementView(self.client, self.graph, resource)

    def get_statements(self) -> Iterator[StatementView]:
        """Get the statements (links) from the query result."""
        for statement in self.graph.subjects(RDF.type, RDF.Statement):
            yield StatementView(self.client, self.graph, statement)


class QueryCapabilityView(ResourceView):

    def get_label(self) -> Optional[str]:
        """Get the label of the query capability."""
        label = self.graph.value(self.node, OSLC.label)
        return label if label else None

    def get_resource_shape(self) -> Optional["ResourceShapeView"]:
        """Get the resource shape from the query capability."""

        shape = self.graph.value(self.node, OSLC.resourceShape)
        if not shape:
            # Typically, the resource shape is already populated in the service provider,
            # so we can try to fetch it from the graph. So the query is on demand here.
            self.make_sure_populated()
            shape = self.graph.value(self.node, OSLC.resourceShape)

        if shape:
            return ResourceShapeView(self.client, self.graph, shape)
        return None

    def query(
        self,
        query: Optional[Dict[str, Any]] = None,
        use_enum_labels=False,
    ) -> QueryResultView:
        """Executes a query against the query capability.

        Allows to query the query the service for resources. These are typically
        requirements and/or related resources in the OSLC ecosystem via links.

        The query uses one or multiple parameters, which are typically
        `oslc.where` and`oslc.select`. DWA does not support all OSLC query
        parameters. See the compatibility table below for details.

        By default, the query does not resolve enum labels, but instead provides
        the enum URLs, which can then be resolved to enum labels. If you want
        to resolve enum labels inside the query, set `use_enum_labels` to `True`,
        which might be more convenient.

        Raises `ValueError` if the query base URL is not found in the query capability.

        Depending on the size of the result set, the query might take a considerable
        amount of time to complete. The server does not support paging, so the entire
        result set will be returned in a single response. Be patient and maybe use
        `oslc.query` to reduce the result size.

        Args:
            query (Dict[str, Any]): The optional query string. If not provided, it defaults
                to `oslc.select=*` to select all resources.
            use_enum_labels (bool): Whether to use enum labels in the query.

         Parameter / feature                                       | Works?            | Notes for DWA 9.5 → 9.7.2                                                                                |
        -----------------------------------------------------------|-------------------|-----------------------------------------------------------------------------------------------------------|
         `oslc.prefix`                                             | ✔︎                | Mandatory when filtering on custom attributes (`doorsAttribute:…`, `rm_property:…`); without it queries fail to parse. |
         `oslc.where`                                              | ✔︎ (with limits)  | Supports equality/inequality, `< > <= >=`, and `in {…}`; only `and` is allowed (no `or`); wild-cards unsupported. |
         `rdf:type` filter (`rdf:type=oslc_rm:Requirement`)        | ✔︎                | Correct way to retrieve only Requirement objects from a module collection.                               |
         `oslc:instanceShape` filter                               | ✖︎                | Ignored—DWA does not expose resource shapes.                                                             |
         Custom attribute filter (`rm_property:attrDef-1234="Foo"`)| ✔︎                | Works; enumeration values are returned as URIs—add `useEnumLabel=true` to receive the literal labels.     |
         `oslc.select`                                             | ✔︎ (mostly)       | Implemented from 9.4; early builds sometimes ignore it with JSON-LD—prefer `application/rdf+xml` or upgrade. |
         `oslc.searchTerms`                                        | ✖︎                | Full-text search not implemented; calls return HTTP 400.                                                 |
         `oslc.orderBy`                                            | ✖︎                | Accepted but silently ignored—results remain unsorted.                                                   |
         Paging (`oslc.paging`, `oslc.pageSize`)                   | ✖︎                | Server streams the whole result; no server-side paging.                                                  |
         `oslc:nextPage` / `_startIndex`                           | ✖︎                | Absent because paging is not implemented.                                                                |
         Query capability location                                 | ✔︎ (module-only)  | Use each module’s `queryBase`; the database-level capability returns only link relations.                |
         Vendor extra `useEnumLabel=true`                          | ✔︎                | Converts enumeration URIs into human-readable strings in the response.                                   |
        """
        url = self.graph.value(self.node, OSLC.queryBase)
        if not url:
            # Typically, the resource shape is already populated in the service provider,
            # so we can try to fetch it from the graph. So the query is on demand here.
            self.make_sure_populated()
            url = self.graph.value(self.node, OSLC.queryBase)

        if not url:
            raise ValueError("Query base URL not found in the query capability.")

        if query is None:
            query = {"oslc.select": "*"}

        if use_enum_labels:
            query["useEnumLabel"] = "true"

        query_url = f"{url}?{urllib.parse.urlencode(query)}"
        resp = self.client.get_url(query_url)

        # The identifier does not have the query params attached.
        return QueryResultView(self.client, resp, URIRef(url))


class AllowedValueView(ResourceView):
    """View for an allowed value URI, providing label and description if available."""

    def get_label(self) -> Optional[str]:
        """Get the label (rdfs:label or dcterms:title) of the allowed value."""
        self.make_sure_populated()

        label = self.graph.value(self.node, OSLC.label)
        if label:
            return str(label)
        # Try DCTERMS.title as fallback
        title = self.graph.value(self.node, DCTERMS.title)
        return str(title) if title else None

    def get_description(self) -> Optional[str]:
        """Get the description (dcterms:description) of the allowed value."""
        desc = self.graph.value(self.node, DCTERMS.description)
        return str(desc) if desc else None


class PropertyView(ResourceView):
    """View of an OSLC property."""

    def get_title(self) -> Optional[str]:
        """Get the title (DCTERMS) of the property."""
        title = self.graph.value(self.node, DCTERMS.title)
        return str(title) if title else None

    def get_name(self) -> Optional[str]:
        """Get the name (OSLC) of the property, e.g. `attrDef-1009`."""
        value = self.graph.value(self.node, OSLC.name)
        return str(value) if value else None

    def get_description(self) -> Optional[str]:
        """Get the description (DCTERMS) of the property."""
        desc = self.graph.value(self.node, DCTERMS.description)
        return str(desc) if desc else None

    def get_property_definition(self) -> Optional[str]:
        """Get the oslc:propertyDefinition URI of the property."""
        uri = self.graph.value(self.node, OSLC.propertyDefinition)
        return str(uri) if uri else None

    def get_value_type(self) -> Optional[str]:
        """Get the oslc:valueType URI of the property."""
        uri = self.graph.value(self.node, OSLC.valueType)
        return str(uri) if uri else None

    def get_occurs(self) -> Optional[Occurs]:
        """Get the oslc:occurs cardinality constraint as an Occurs enum."""
        uri = self.graph.value(self.node, OSLC.occurs)
        if uri is None:
            return None
        uri_str = str(uri)
        if uri_str == Occurs.EXACTLY_ONE.value:
            return Occurs.EXACTLY_ONE
        elif uri_str == Occurs.ZERO_OR_ONE.value:
            return Occurs.ZERO_OR_ONE
        elif uri_str == Occurs.ZERO_OR_MANY.value:
            return Occurs.ZERO_OR_MANY
        elif uri_str == Occurs.ONE_OR_MANY.value:
            return Occurs.ONE_OR_MANY
        else:
            return Occurs.UNKNOWN

    def get_read_only(self) -> Optional[bool]:
        """Get whether the property is read-only (oslc:readOnly)."""
        val = self.graph.value(self.node, OSLC.readOnly)
        if isinstance(val, Literal):
            return val.toPython() in (True, "true", "1")
        return None

    def get_hidden(self) -> Optional[bool]:
        """Get whether the property is hidden (oslc:hidden)."""
        val = self.graph.value(self.node, OSLC.hidden)
        if isinstance(val, Literal):
            return val.toPython() in (True, "true", "1")
        return None

    def get_default_value(self) -> Optional[str]:
        """Get the default value (oslc:defaultValue)."""
        val = self.graph.value(self.node, OSLC.defaultValue)
        return str(val) if val else None

    def get_is_member_property(self) -> Optional[bool]:
        """Get oslc:isMemberProperty as a boolean, if set."""
        val = self.graph.value(self.node, OSLC.isMemberProperty)
        if isinstance(val, Literal):
            return val.toPython() in (True, "true", "1")
        return None

    def get_range(self) -> List[str]:
        """Get oslc:range URI(s), can be multiple."""
        return [str(o) for o in self.graph.objects(self.node, OSLC.range)]

    def get_representation(self) -> Optional[str]:
        """Get oslc:representation URI, if present."""
        uri = self.graph.value(self.node, OSLC.representation)
        return str(uri) if uri else None

    def get_value_shape(self) -> Optional[str]:
        """Get oslc:valueShape URI, if present."""
        uri = self.graph.value(self.node, OSLC.valueShape)
        return str(uri) if uri else None

    def get_allowed_values(self) -> list[AllowedValueView]:
        """Get list of AllowedValueView for oslc:allowedValue URIs."""
        return [
            AllowedValueView(self.client, self.graph, o)
            for o in self.graph.objects(self.node, OSLC.allowedValue)
        ]


class ResourceShapeView(ResourceView):
    """View of the OSLC Resource Shape.

    A resource shape defines the structure of a resource, which are usually
    objects like requirements in DOORS classic terms.
    """

    def get_properties(self) -> List[PropertyView]:
        """Get the properties defined in the resource shape."""
        self.make_sure_populated()

        results = []
        for prop in self.graph.objects(self.node, OSLC.property):
            results.append(PropertyView(self.client, self.graph, prop))
        return results


class ServiceProviderView(ResourceView):
    """View of the OSLC Service Provider.

    This view provides methods to interact with the service provider.
    A service provider provides one or more OSLC services, to read
    and modify resources in the OSLC ecosystem. For reading resources,
    the service provider typically offers a "query capability". See
    `get_query_capabilities`.
    """

    def get_title(self) -> Optional[str]:
        """Get the title of the service provider."""
        title = self.graph.value(self.node, DCTERMS.title)
        return str(title) if title else None

    def get_query_capabilities(self) -> Optional[QueryCapabilityView]:
        """Get the query capabilities of the service provider.

        If there are multiple services in the service provider,
        it will return the first query capability found.
        """
        self.make_sure_populated()

        for service in self.graph.objects(self.node, OSLC.service):
            for qc in self.graph.objects(service, OSLC.queryCapability):
                return QueryCapabilityView(self.client, self.graph, qc)
        return None


class ServiceProviderCatalogView(ResourceView):
    """View of the OSLC Service Provider Catalog.

    This view provides methods to interact with the service provider catalog.
    A service provider catalog contains one or more service providers, which
    provide OSLC services to read and modify resources in the OSLC ecosystem.

    Catalogs are hierarchical, meaning that a catalog can contain other, e.g.
    for the folders and projects in DOORS classic. Use the
    `get_service_provider_catalogs` method to get all catalogs
    in the catalog.
    """

    def get_title(self) -> Optional[str]:
        """Get the title of the service provider catalog."""
        title = self.graph.value(self.node, DCTERMS.title)
        return str(title) if title else None

    def get_description(self) -> Optional[str]:
        """Get the description of the service provider catalog."""
        description = self.graph.value(self.node, DCTERMS.description)
        return str(description) if description else None

    def get_service_providers(self) -> List[ServiceProviderView]:
        self.make_sure_populated()

        results: list[ServiceProviderView] = []
        for sp in self.graph.objects(self.node, OSLC.serviceProvider):
            results.append(ServiceProviderView(self.client, self.graph, sp))
        return results

    def get_service_provider_catalogs(self) -> List["ServiceProviderCatalogView"]:
        self.make_sure_populated()

        results: list["ServiceProviderCatalogView"] = []
        for _, _, spc in self.graph.triples(
            (self.node, OSLC.serviceProviderCatalog, None)
        ):
            results.append(ServiceProviderCatalogView(self.client, self.graph, spc))
        return results

    def get_service_provider_catalog_by_title(
        self, title: str
    ) -> Optional["ServiceProviderCatalogView"]:
        for spc in self.get_service_provider_catalogs():
            if spc.get_title() == title:
                return spc

        return None
