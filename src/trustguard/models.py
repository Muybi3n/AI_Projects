# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for trusts, estate schedules, beneficiary waterfall rules, and fiduciary logs.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TrustType(str, Enum):
    REVOCABLE_LIVING = "revocable_living"
    IRREVOCABLE = "irrevocable"
    TESTAMENTARY = "testamentary"
    SPECIAL_NEEDS = "special_needs"
    CHARITABLE_REMAINDER = "charitable_remainder"


class TitlingStatus(str, Enum):
    TITLED_TO_TRUST = "titled_to_trust"
    BENEFICIARY_DESIGNATED = "beneficiary_designated"
    POUR_OVER_WILL_ONLY = "pour_over_will_only"
    UNFUNDED_PROBATE_RISK = "unfunded_probate_risk"


class AssetCategory(str, Enum):
    REAL_ESTATE = "real_estate"
    BROKERAGE_ACCOUNT = "brokerage_account"
    BANK_CHECKING_SAVINGS = "bank_checking_savings"
    BUSINESS_EQUITY_LLC = "business_equity_llc"
    DIGITAL_CRYPTO_ASSETS = "digital_crypto_assets"
    VEHICLES_VESSELS = "vehicles_vessels"
    PERSONAL_PROPERTY = "personal_property"


class DistributionScheme(str, Enum):
    OUTRIGHT_PERCENTAGE = "outright_percentage"
    SPECIFIC_DOLLAR_BEQUEST = "specific_dollar_bequest"
    AGE_MILESTONE_TRANCHES = "age_milestone_tranches"
    DISCRETIONARY_HEMS = "discretionary_hems"  # Health, Education, Maintenance, Support


@dataclass
class ScheduleAsset:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: AssetCategory = AssetCategory.REAL_ESTATE
    estimated_value: float = 0.0
    titling_status: TitlingStatus = TitlingStatus.TITLED_TO_TRUST
    institution_or_parcel: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value if isinstance(self.category, Enum) else self.category
        d["titling_status"] = (
            self.titling_status.value if isinstance(self.titling_status, Enum) else self.titling_status
        )
        return d


@dataclass
class GuardianshipDirective:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    child_name: str = ""
    date_of_birth: str = ""
    primary_guardian: str = ""
    alternate_guardian: str = ""
    special_care_instructions: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BeneficiaryRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    beneficiary_name: str = ""
    relationship: str = "child"  # spouse, child, sibling, charity
    scheme: DistributionScheme = DistributionScheme.OUTRIGHT_PERCENTAGE
    share_pct: float = 0.0
    specific_dollar_amount: float = 0.0
    # Age milestone releases, e.g. [(25, 0.33), (30, 0.33), (35, 0.34)]
    milestone_schedule: list[dict[str, float]] = field(default_factory=list)
    contingent_beneficiary: str = ""
    is_primary: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scheme"] = self.scheme.value if isinstance(self.scheme, Enum) else self.scheme
        return d


@dataclass
class FiduciaryLogEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trustee_name: str = ""
    action_category: str = "accounting"  # distribution, tax_filing, appraisal, asset_retitle, accounting
    description: str = ""
    dollar_impact: float = 0.0
    supporting_doc_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BeneficiaryPayout:
    beneficiary_name: str
    allocation_pct: float
    total_dollar_amount: float
    immediate_payout: float
    milestone_tranches: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WaterfallResult:
    gross_estate_value: float
    administrative_reserve_pct: float
    administrative_reserve_dollars: float
    distributable_net_estate: float
    payouts: list[BeneficiaryPayout] = field(default_factory=list)
    unallocated_remainder: float = 0.0


@dataclass
class FundingAuditReport:
    total_estate_value: float
    funded_to_trust_value: float
    funded_to_trust_pct: float
    beneficiary_designated_value: float
    unfunded_probate_risk_value: float
    unfunded_probate_risk_pct: float
    at_risk_assets: list[ScheduleAsset] = field(default_factory=list)
    probate_risk_tier: str = "Low"


@dataclass
class TrustEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trust_name: str = "Family Revocable Living Trust"
    trust_type: TrustType = TrustType.REVOCABLE_LIVING
    jurisdiction_state: str = "Delaware"
    grantor_settlor: str = "Grantor"
    current_trustee: str = "Trustee"
    successor_trustee: str = "Successor Trustee"
    created_date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    assets: list[ScheduleAsset] = field(default_factory=list)
    beneficiaries: list[BeneficiaryRule] = field(default_factory=list)
    guardianship_directives: list[GuardianshipDirective] = field(default_factory=list)
    fiduciary_logs: list[FiduciaryLogEntry] = field(default_factory=list)

    @property
    def total_estate_value(self) -> float:
        return sum(a.estimated_value for a in self.assets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trust_name": self.trust_name,
            "trust_type": self.trust_type.value if isinstance(self.trust_type, Enum) else self.trust_type,
            "jurisdiction_state": self.jurisdiction_state,
            "grantor_settlor": self.grantor_settlor,
            "current_trustee": self.current_trustee,
            "successor_trustee": self.successor_trustee,
            "created_date": self.created_date,
            "assets": [a.to_dict() for a in self.assets],
            "beneficiaries": [b.to_dict() for b in self.beneficiaries],
            "guardianship_directives": [g.to_dict() for g in self.guardianship_directives],
            "fiduciary_logs": [log.to_dict() for log in self.fiduciary_logs],
        }
