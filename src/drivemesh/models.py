"""Data models for drivemesh-core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ClusterCategory(str, Enum):
    """Taxonomy categories for file grouping."""

    FINANCIAL_TAX = "Financial & Tax"
    LEGAL_CONTRACTS = "Legal & Contracts"
    HEALTH_MEDICAL = "Health & Medical"
    ENGINEERING_DEV = "Engineering & Code"
    WORK_PROJECTS = "Work & Operations"
    ACADEMIC_RESEARCH = "Academic & Research"
    PERSONAL_ADMIN = "Personal & Admin"
    MEDIA_ASSETS = "Media & Assets"
    UNCATEGORIZED = "General / Uncategorized"


class DuplicateType(str, Enum):
    """Classification of duplicate file relationships."""

    EXACT_CHECKSUM = "EXACT_CHECKSUM"
    NAME_AND_SIZE = "NAME_AND_SIZE"
    FUZZY_VERSION = "FUZZY_VERSION"
    ORPHAN_ZERO_BYTE = "ORPHAN_ZERO_BYTE"


class ResolutionAction(str, Enum):
    """Recommended cleanup action for duplicates."""

    KEEP_NEWEST = "KEEP_NEWEST"
    KEEP_CANONICAL = "KEEP_CANONICAL"
    DELETE_DUPLICATES = "DELETE_DUPLICATES"
    ARCHIVE_HISTORICAL = "ARCHIVE_HISTORICAL"
    PURGE_EMPTY = "PURGE_EMPTY"


@dataclass
class DriveFile:
    """Represents a cloud or local drive file metadata record."""

    id: str
    name: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    md5_checksum: str = ""
    sha256_checksum: str = ""
    modified_time: str = ""
    created_time: str = ""
    parents: list[str] = field(default_factory=list)
    path_hierarchy: str = "/"
    owners: list[str] = field(default_factory=list)
    shared: bool = False
    starred: bool = False
    trashed: bool = False
    web_view_link: str = ""
    assigned_category: ClusterCategory = ClusterCategory.UNCATEGORIZED
    cluster_label: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        data = asdict(self)
        data["assigned_category"] = self.assigned_category.value
        return data


@dataclass
class DriveFolder:
    """Represents a folder node in the directory tree."""

    id: str
    name: str
    parents: list[str] = field(default_factory=list)
    path: str = "/"
    modified_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FileCluster:
    """Group of related files discovered by taxonomy / subject mesh."""

    cluster_id: str
    category: ClusterCategory
    label: str
    file_ids: list[str] = field(default_factory=list)
    total_size_bytes: int = 0
    suggested_target_path: str = "/"
    confidence_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


@dataclass
class DuplicateGroup:
    """Group of files identified as exact or fuzzy duplicates."""

    group_id: str
    canonical_file_id: str
    duplicate_file_ids: list[str]
    duplicate_type: DuplicateType
    wasted_bytes: int
    resolution_suggestion: ResolutionAction
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["duplicate_type"] = self.duplicate_type.value
        data["resolution_suggestion"] = self.resolution_suggestion.value
        return data


@dataclass
class DriveAuditReport:
    """Comprehensive health & storage audit summary."""

    total_files: int = 0
    total_folders: int = 0
    total_storage_bytes: int = 0
    reclaimable_bytes: int = 0
    duplicate_groups_count: int = 0
    orphaned_root_files_count: int = 0
    zero_byte_files_count: int = 0
    shared_files_count: int = 0
    health_score: int = 100
    top_categories: dict[str, int] = field(default_factory=dict)
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["duplicate_groups"] = [g.to_dict() for g in self.duplicate_groups]
        return data


@dataclass
class MeshMoveOperation:
    """Single proposed file relocation."""

    file_id: str
    file_name: str
    current_path: str
    proposed_path: str
    reason: str


@dataclass
class MeshPlan:
    """Complete restructuring & cleanup execution plan."""

    plan_id: str
    generated_at: str
    proposed_moves: list[MeshMoveOperation] = field(default_factory=list)
    proposed_deletions: list[str] = field(default_factory=list)
    total_reclaimable_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
