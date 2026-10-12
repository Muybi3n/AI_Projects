"""Data models and enums for ShelfWise."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AssetCategory(str, Enum):
    """Broad categories for hardware assets."""

    COMPUTING = "computing"
    NETWORKING = "networking"
    HOMELAB = "homelab"
    AUDIO_VIDEO = "audio_video"
    MOBILE = "mobile"
    APPLIANCES = "appliances"
    TOOLS = "tools"
    PERIPHERALS = "peripherals"
    OTHER = "other"


class AssetCondition(str, Enum):
    """Condition of asset upon acquisition."""

    NEW = "new"
    REFURBISHED = "refurbished"
    USED = "used"


class AssetStatus(str, Enum):
    """Current operational status of the asset."""

    ACTIVE = "active"
    STORAGE = "storage"
    DISPOSED = "disposed"
    SOLD = "sold"
    RMA = "rma"


class WarrantyTier(str, Enum):
    """Warranty urgency tiers based on expiration radar."""

    EXPIRED = "expired"
    CRITICAL = "critical"  # <= 14 days
    WARNING = "warning"  # 15 - 45 days
    ACTIVE = "active"  # > 45 days
    LIFETIME = "lifetime"


class ProofStatus(str, Enum):
    """Proof-of-purchase / receipt verification status."""

    VERIFIED = "verified"
    MISSING = "missing"
    PENDING = "pending"


class MaintenanceType(str, Enum):
    """Type of maintenance or repair event."""

    FIRMWARE = "firmware"
    REPAIR = "repair"
    BATTERY = "battery"
    CLEANING = "cleaning"
    RMA = "rma"
    UPGRADE = "upgrade"
    INSPECTION = "inspection"
    OTHER = "other"


@dataclass
class Asset:
    """Hardware device or asset record."""

    id: str
    name: str
    category: AssetCategory = AssetCategory.COMPUTING
    brand: str = ""
    model: str = ""
    serial_number: str = ""
    purchase_date: str = ""  # YYYY-MM-DD
    purchase_price: float = 0.0
    vendor: str = ""
    condition: AssetCondition = AssetCondition.NEW
    location: str = "Default"
    status: AssetStatus = AssetStatus.ACTIVE
    warranty_months: int = 12  # -1 for lifetime, 0 for none, positive int for months
    extended_warranty_months: int = 0
    extended_warranty_notes: str = ""
    receipt_path: str | None = None
    receipt_hash: str | None = None
    invoice_id: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert asset to a dictionary representation."""
        data = asdict(self)
        data["category"] = self.category.value if isinstance(self.category, AssetCategory) else str(self.category)
        data["condition"] = self.condition.value if isinstance(self.condition, AssetCondition) else str(self.condition)
        data["status"] = self.status.value if isinstance(self.status, AssetStatus) else str(self.status)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Asset:
        """Create asset from dictionary representation."""
        cleaned = dict(data)
        if "category" in cleaned and isinstance(cleaned["category"], str):
            try:
                cleaned["category"] = AssetCategory(cleaned["category"])
            except ValueError:
                cleaned["category"] = AssetCategory.OTHER

        if "condition" in cleaned and isinstance(cleaned["condition"], str):
            try:
                cleaned["condition"] = AssetCondition(cleaned["condition"])
            except ValueError:
                cleaned["condition"] = AssetCondition.NEW

        if "status" in cleaned and isinstance(cleaned["status"], str):
            try:
                cleaned["status"] = AssetStatus(cleaned["status"])
            except ValueError:
                cleaned["status"] = AssetStatus.ACTIVE

        return cls(**cleaned)


@dataclass
class MaintenanceRecord:
    """Historical maintenance, repair, or RMA record for an asset."""

    id: str
    asset_id: str
    date: str  # YYYY-MM-DD
    maintenance_type: MaintenanceType = MaintenanceType.INSPECTION
    cost: float = 0.0
    description: str = ""
    performed_by: str = "Self"
    rma_ticket: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert maintenance record to dictionary."""
        data = asdict(self)
        data["maintenance_type"] = (
            self.maintenance_type.value
            if isinstance(self.maintenance_type, MaintenanceType)
            else str(self.maintenance_type)
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaintenanceRecord:
        """Create maintenance record from dictionary."""
        cleaned = dict(data)
        if "maintenance_type" in cleaned and isinstance(cleaned["maintenance_type"], str):
            try:
                cleaned["maintenance_type"] = MaintenanceType(cleaned["maintenance_type"])
            except ValueError:
                cleaned["maintenance_type"] = MaintenanceType.OTHER
        return cls(**cleaned)


@dataclass
class WarrantyEvaluation:
    """Evaluation result of an asset's warranty status."""

    asset_id: str
    asset_name: str
    purchase_date: str
    expiration_date: str | None
    days_remaining: int | None
    tier: WarrantyTier
    cc_extension_eligible: bool = False
    total_warranty_months: int = 12
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert warranty evaluation to dictionary."""
        data = asdict(self)
        data["tier"] = self.tier.value if isinstance(self.tier, WarrantyTier) else str(self.tier)
        return data


@dataclass
class DepreciationRecord:
    """Calculated depreciation and replacement value for an asset."""

    asset_id: str
    asset_name: str
    purchase_price: float
    purchase_date: str
    age_years: float
    depreciated_value: float
    replacement_cost_estimate: float
    depreciation_method: str = "tech_curve"

    def to_dict(self) -> dict[str, Any]:
        """Convert depreciation record to dictionary."""
        return asdict(self)


@dataclass
class InsuranceClaimItem:
    """Single item formatted for insurance or warranty claim documentation."""

    asset_id: str
    name: str
    category: str
    brand: str
    model: str
    serial_number: str
    purchase_date: str
    purchase_price: float
    replacement_estimate: float
    depreciated_value: float
    receipt_status: ProofStatus
    receipt_hash: str | None = None
    receipt_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert claim item to dictionary."""
        data = asdict(self)
        data["receipt_status"] = (
            self.receipt_status.value if isinstance(self.receipt_status, ProofStatus) else str(self.receipt_status)
        )
        return data


@dataclass
class InsuranceClaimPack:
    """Full insurance or warranty loss/damage claim bundle."""

    claim_id: str
    incident_type: str
    incident_date: str
    generated_at: str
    total_original_cost: float
    total_replacement_cost: float
    total_depreciated_value: float
    items: list[InsuranceClaimItem]
    verified_receipts_count: int
    missing_receipts_count: int
    checklist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert claim pack to dictionary."""
        return {
            "claim_id": self.claim_id,
            "incident_type": self.incident_type,
            "incident_date": self.incident_date,
            "generated_at": self.generated_at,
            "total_original_cost": self.total_original_cost,
            "total_replacement_cost": self.total_replacement_cost,
            "total_depreciated_value": self.total_depreciated_value,
            "items": [item.to_dict() for item in self.items],
            "verified_receipts_count": self.verified_receipts_count,
            "missing_receipts_count": self.missing_receipts_count,
            "checklist": list(self.checklist),
        }


@dataclass
class AuditReport:
    """Fleet-wide hardware audit and risk summary report."""

    total_assets: int
    total_purchase_value: float
    total_depreciated_value: float
    active_warranties_count: int
    expiring_warranties_count: int  # critical + warning
    expired_warranties_count: int
    lifetime_warranties_count: int
    missing_receipts_count: int
    missing_receipts_high_value_count: int
    total_maintenance_spend: float
    active_rma_count: int
    by_category: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    by_location: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert audit report to dictionary."""
        return asdict(self)


@dataclass
class AdvisorResponse:
    """Response from the ShelfWise hardware AI advisor."""

    query: str
    summary: str
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    pii_scrubbed_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert advisor response to dictionary."""
        return asdict(self)
