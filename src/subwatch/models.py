"""Domain models for subwatch-engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class BillingCycle(str, Enum):
    """Supported subscription billing cycles."""

    MONTHLY = "monthly"
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"

    @property
    def multiplier_to_annual(self) -> float:
        """Multiplier to convert single charge to annual run-rate."""
        mapping = {
            BillingCycle.MONTHLY: 12.0,
            BillingCycle.ANNUAL: 1.0,
            BillingCycle.QUARTERLY: 4.0,
            BillingCycle.SEMI_ANNUAL: 2.0,
            BillingCycle.WEEKLY: 52.0,
            BillingCycle.BI_WEEKLY: 26.0,
        }
        return mapping[self]

    @property
    def multiplier_to_monthly(self) -> float:
        """Multiplier to convert single charge to monthly run-rate."""
        return self.multiplier_to_annual / 12.0


class Category(str, Enum):
    """Categorization for subscriptions."""

    PRODUCTIVITY = "productivity"
    ENTERTAINMENT = "entertainment"
    DEVELOPER_CLOUD = "developer_cloud"
    SECURITY = "security"
    UTILITIES = "utilities"
    HEALTH_FITNESS = "health_fitness"
    NEWS_MEDIA = "news_media"
    AI_ML = "ai_ml"
    OTHER = "other"


class SubscriptionStatus(str, Enum):
    """Lifecycle status of a subscription."""

    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    TRIAL = "trial"


@dataclass
class ChargeRecord:
    """Historical billing transaction record."""

    id: str
    subscription_id: str
    amount: float
    date: str  # YYYY-MM-DD
    payment_method: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChargeRecord:
        return cls(
            id=data["id"],
            subscription_id=data["subscription_id"],
            amount=float(data["amount"]),
            date=data["date"],
            payment_method=data.get("payment_method", ""),
            notes=data.get("notes", ""),
        )


@dataclass
class Subscription:
    """Core subscription entity."""

    id: str
    name: str
    vendor: str
    category: Category
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    current_price: float
    currency: str = "USD"
    start_date: str = ""  # YYYY-MM-DD
    next_renewal_date: str = ""  # YYYY-MM-DD
    cancellation_notice_days: int = 3
    payment_method: str = ""
    autopay: bool = True
    usage_rating: int = 3  # 1 (rarely used / dormant) to 5 (daily core)
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    charge_history: list[ChargeRecord] = field(default_factory=list)

    @property
    def annual_cost(self) -> float:
        """Total projected cost per year."""
        return round(self.current_price * self.billing_cycle.multiplier_to_annual, 2)

    @property
    def monthly_cost(self) -> float:
        """Total projected cost per month."""
        return round(self.current_price * self.billing_cycle.multiplier_to_monthly, 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        data["status"] = self.status.value
        data["billing_cycle"] = self.billing_cycle.value
        data["charge_history"] = [record.to_dict() for record in self.charge_history]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Subscription:
        records = [
            ChargeRecord.from_dict(item) if isinstance(item, dict) else item
            for item in data.get("charge_history", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            vendor=data.get("vendor", data["name"]),
            category=Category(data.get("category", Category.OTHER.value)),
            status=SubscriptionStatus(data.get("status", SubscriptionStatus.ACTIVE.value)),
            billing_cycle=BillingCycle(data.get("billing_cycle", BillingCycle.MONTHLY.value)),
            current_price=float(data["current_price"]),
            currency=data.get("currency", "USD"),
            start_date=data.get("start_date", ""),
            next_renewal_date=data.get("next_renewal_date", ""),
            cancellation_notice_days=int(data.get("cancellation_notice_days", 3)),
            payment_method=data.get("payment_method", ""),
            autopay=bool(data.get("autopay", True)),
            usage_rating=int(data.get("usage_rating", 3)),
            tags=list(data.get("tags", [])),
            notes=data.get("notes", ""),
            charge_history=records,
        )


@dataclass
class CreepReport:
    """Analysis of historical price creep for a single subscription."""

    subscription_id: str
    subscription_name: str
    initial_price: float
    current_price: float
    absolute_increase: float
    percent_increase: float
    annualized_dollar_impact: float
    first_charge_date: str
    latest_charge_date: str
    is_stealth_creep: bool  # True if increase >= 5.0%

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenewalAlert:
    """Upcoming renewal deadline notification."""

    subscription_id: str
    subscription_name: str
    renewal_date: str
    days_until_renewal: int
    cancel_by_date: str
    amount: float
    currency: str
    urgency: str  # "CRITICAL", "WARNING", "UPCOMING", "PAST_DUE"
    is_trial: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RedundancyCluster:
    """Detected overlapping subscriptions in the same category."""

    category: Category
    subscription_ids: list[str]
    subscription_names: list[str]
    total_annual_cost: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


@dataclass
class ZombieSubscription:
    """Low-usage or dormant subscription wasting capital."""

    subscription_id: str
    subscription_name: str
    usage_rating: int
    annual_cost: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditSummary:
    """Complete portfolio subscription audit."""

    total_active_subscriptions: int
    total_monthly_spend: float
    total_annual_spend: float
    category_breakdown: dict[str, float]
    creep_alerts: list[CreepReport]
    upcoming_renewals: list[RenewalAlert]
    redundancies: list[RedundancyCluster]
    zombie_subscriptions: list[ZombieSubscription]
    potential_annual_savings: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_active_subscriptions": self.total_active_subscriptions,
            "total_monthly_spend": round(self.total_monthly_spend, 2),
            "total_annual_spend": round(self.total_annual_spend, 2),
            "category_breakdown": self.category_breakdown,
            "creep_alerts": [alert.to_dict() for alert in self.creep_alerts],
            "upcoming_renewals": [renewal.to_dict() for renewal in self.upcoming_renewals],
            "redundancies": [cluster.to_dict() for cluster in self.redundancies],
            "zombie_subscriptions": [zombie.to_dict() for zombie in self.zombie_subscriptions],
            "potential_annual_savings": round(self.potential_annual_savings, 2),
        }
