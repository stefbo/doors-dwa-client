from enum import Enum

from rdflib import Namespace

OSLC = Namespace("http://open-services.net/ns/core#")
OSLC_RM = Namespace("http://open-services.net/xmlns/rm/1.0/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
JD_DISC = Namespace("http://jazz.net/xmlns/prod/jazz/discovery/1.0/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


class Occurs(Enum):
    EXACTLY_ONE = "http://open-services.net/ns/core#Exactly-one"
    ZERO_OR_ONE = "http://open-services.net/ns/core#Zero-or-one"
    ZERO_OR_MANY = "http://open-services.net/ns/core#Zero-or-many"
    ONE_OR_MANY = "http://open-services.net/ns/core#One-or-many"
    UNKNOWN = "unknown"
