from dwa_client.oslc.client import OSLCClient
from dwa_client.oslc.views import (
    ResourceView,
    StatementView,
    RequirementView,
    QueryResultView,
    QueryCapabilityView,
    AllowedValueView,
    PropertyView,
    ResourceShapeView,
    ServiceProviderView,
    ServiceProviderCatalogView,
    Occurs,
)
from dwa_client.oslc.common import (
    OSLC,
    OSLC_RM,
    DCTERMS,
    JD_DISC,
    RDFS,
)
from dwa_client.oslc.urn import URN

__all__ = [
    "OSLCClient",
    "ResourceView",
    "StatementView",
    "RequirementView",
    "QueryResultView",
    "QueryCapabilityView",
    "AllowedValueView",
    "PropertyView",
    "ResourceShapeView",
    "ServiceProviderView",
    "ServiceProviderCatalogView",
    "Occurs",
    # Namespaces:
    "OSLC",
    "OSLC_RM",
    "DCTERMS",
    "JD_DISC",
    "RDFS",
    # Utils:
    "URN",
]
