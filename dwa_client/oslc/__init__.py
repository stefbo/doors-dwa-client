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
)
from dwa_client.oslc.common import (
    OSLC,
    OSLC_RM,
    DCTERMS,
    JD_DISC,
    RDFS,
)

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
    # Namespaces:
    "OSLC",
    "OSLC_RM",
    "DCTERMS",
    "JD_DISC",
    "RDFS",
]
