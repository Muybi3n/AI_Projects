"""Data models and enums for nasroute-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StorageTier(str, Enum):
    """Storage tier hierarchy for homelab & NAS architectures."""

    HOT_NVME = "HOT_NVME"
    WARM_SSD = "WARM_SSD"
    COLD_NAS = "COLD_NAS"
    GLACIER_BACKUP = "GLACIER_BACKUP"


class RouteAction(str, Enum):
    """File operation action for routing engine."""

    MOVE = "MOVE"
    COPY = "COPY"
    SYMLINK = "SYMLINK"
    HARDLINK = "HARDLINK"
    DRY_RUN = "DRY_RUN"


class DocumentCategory(str, Enum):
    """Standardized taxonomy classification categories."""

    TAX_FINANCE = "TAX_FINANCE"
    MEDICAL_HEALTH = "MEDICAL_HEALTH"
    LEGAL_ESTATE = "LEGAL_ESTATE"
    HOMELAB_SYSADMIN = "HOMELAB_SYSADMIN"
    RECEIPTS_INVOICES = "RECEIPTS_INVOICES"
    SCANS_DOCS = "SCANS_DOCS"
    RESEARCH_PAPERS = "RESEARCH_PAPERS"
    UNCATEGORIZED = "UNCATEGORIZED"


@dataclass
class DocumentMetadata:
    """Extracted metadata and cryptographic checksums for an ingested file."""

    file_path: str
    file_name: str
    size_bytes: int
    sha256: str
    blake2b: str
    mime_type: str = "application/octet-stream"
    created_at: str = ""
    modified_at: str = ""
    tags: list[str] = field(default_factory=list)
    extracted_date: str | None = None
    suggested_category: str = DocumentCategory.UNCATEGORIZED.value
    suggested_tier: str = StorageTier.COLD_NAS.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentMetadata:
        return cls(**data)


@dataclass
class TaxonomyRule:
    """Rule for deterministic document classification and path routing."""

    rule_id: str
    name: str
    category: str
    target_tier: str
    destination_subpath: str
    name_keywords: list[str] = field(default_factory=list)
    content_keywords: list[str] = field(default_factory=list)
    path_pattern: str | None = None
    priority: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaxonomyRule:
        return cls(**data)


@dataclass
class RouteExecution:
    """Result record of an executed or simulated routing operation."""

    source_path: str
    dest_path: str
    action: str
    category: str
    tier: str
    sha256: str
    status: str
    message: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RouteExecution:
        return cls(**data)


@dataclass
class StorageTierConfig:
    """Mount configuration for a specific storage tier."""

    tier_name: str
    mount_path: str
    speed_class: str = "7200RPM_SATA"
    max_capacity_bytes: int = 0
    current_used_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StorageTierConfig:
        return cls(**data)


@dataclass
class AuditReport:
    """Summary audit report of scanned, routed, and deduplicated documents."""

    total_files_scanned: int
    total_bytes_scanned: int
    routed_files_count: int
    duplicate_files_count: int
    space_saved_bytes: int
    tier_breakdown: dict[str, int] = field(default_factory=dict)
    category_breakdown: dict[str, int] = field(default_factory=dict)
    executions: list[RouteExecution] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files_scanned": self.total_files_scanned,
            "total_bytes_scanned": self.total_bytes_scanned,
            "routed_files_count": self.routed_files_count,
            "duplicate_files_count": self.duplicate_files_count,
            "space_saved_bytes": self.space_saved_bytes,
            "tier_breakdown": self.tier_breakdown,
            "category_breakdown": self.category_breakdown,
            "executions": [e.to_dict() for e in self.executions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditReport:
        executions = [RouteExecution.from_dict(e) for e in data.get("executions", [])]
        return cls(
            total_files_scanned=data.get("total_files_scanned", 0),
            total_bytes_scanned=data.get("total_bytes_scanned", 0),
            routed_files_count=data.get("routed_files_count", 0),
            duplicate_files_count=data.get("duplicate_files_count", 0),
            space_saved_bytes=data.get("space_saved_bytes", 0),
            tier_breakdown=data.get("tier_breakdown", {}),
            category_breakdown=data.get("category_breakdown", {}),
            executions=executions,
        )
