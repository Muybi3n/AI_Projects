"""nasroute-core: Homelab & document storage routing engine with deterministic taxonomy, integrity hashing, and tier management.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from nasroute.ai_companion import CompanionResponse, NASRouteCompanion
from nasroute.cli import main
from nasroute.engine import NASRouter, TaxonomyClassifier, compute_hashes, extract_metadata
from nasroute.models import (
    AuditReport,
    DocumentCategory,
    DocumentMetadata,
    RouteAction,
    RouteExecution,
    StorageTier,
    StorageTierConfig,
    TaxonomyRule,
)
from nasroute.storage import NASRouteStore

__version__ = "0.1.0"

__all__ = [
    "AuditReport",
    "CompanionResponse",
    "DocumentCategory",
    "DocumentMetadata",
    "NASRouteCompanion",
    "NASRouter",
    "NASRouteStore",
    "RouteAction",
    "RouteExecution",
    "StorageTier",
    "StorageTierConfig",
    "TaxonomyClassifier",
    "TaxonomyRule",
    "__version__",
    "compute_hashes",
    "extract_metadata",
    "main",
]
