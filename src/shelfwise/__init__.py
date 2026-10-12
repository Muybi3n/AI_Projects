"""ShelfWise: Local-first hardware asset inventory, warranty radar & insurance claims packager."""

from shelfwise.models import (
    AdvisorResponse,
    Asset,
    AssetCategory,
    AssetCondition,
    AssetStatus,
    AuditReport,
    DepreciationRecord,
    InsuranceClaimPack,
    MaintenanceRecord,
    MaintenanceType,
    ProofStatus,
    WarrantyEvaluation,
    WarrantyTier,
)

__version__ = "0.1.0"
__all__ = [
    "AdvisorResponse",
    "Asset",
    "AssetCategory",
    "AssetCondition",
    "AssetStatus",
    "AuditReport",
    "DepreciationRecord",
    "InsuranceClaimPack",
    "MaintenanceRecord",
    "MaintenanceType",
    "ProofStatus",
    "WarrantyEvaluation",
    "WarrantyTier",
    "__version__",
]
