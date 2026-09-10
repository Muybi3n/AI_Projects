# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for credit cards, multipliers, signup bonuses, and portfolio wallets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SpendCategory(str, Enum):
    DINING = "dining"
    GROCERIES = "groceries"
    TRAVEL = "travel"
    GAS = "gas"
    TRANSIT = "transit"
    STREAMING = "streaming"
    UTILITIES = "utilities"
    ONLINE_RETAIL = "online_retail"
    PHARMACY = "pharmacy"
    CATCH_ALL = "catch_all"


@dataclass
class CreditCard:
    card_id: str
    card_name: str
    issuer: str  # Chase, Amex, Citi, Capital One, Discover, Bank of America, US Bank
    network: str  # Visa, Mastercard, Amex, Discover
    annual_fee: float = 0.0
    opened_date: str = ""  # YYYY-MM-DD
    is_business: bool = False
    multipliers: dict[str, float] = field(default_factory=lambda: {"catch_all": 1.0})
    point_type: str = "Cash Back"  # Chase UR, Amex MR, Citi TYP, CapOne Miles, Cash Back
    point_valuation_cents: float = 1.0  # e.g., 2.0 cents/point for MR/UR transfer partners
    annual_credits_value: float = 0.0
    notes: str = ""

    def get_effective_multiplier(self, category: str) -> float:
        """Returns the multiplier for a category, falling back to catch_all."""
        cat_lower = category.lower().strip()
        return self.multipliers.get(cat_lower, self.multipliers.get("catch_all", 1.0))

    def get_effective_return_pct(self, category: str) -> float:
        """Calculates expected net return percentage (multiplier * valuation / 100)."""
        mult = self.get_effective_multiplier(category)
        return mult * self.point_valuation_cents

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "card_name": self.card_name,
            "issuer": self.issuer,
            "network": self.network,
            "annual_fee": self.annual_fee,
            "opened_date": self.opened_date,
            "is_business": self.is_business,
            "multipliers": self.multipliers,
            "point_type": self.point_type,
            "point_valuation_cents": self.point_valuation_cents,
            "annual_credits_value": self.annual_credits_value,
            "notes": self.notes,
        }


@dataclass
class SubTracker:
    """Sign-Up Bonus (SUB) Minimum Spend Requirement (MSR) Tracker."""

    card_id: str
    card_name: str
    target_spend: float
    current_spend: float = 0.0
    deadline_date: str = ""  # YYYY-MM-DD
    bonus_points: int = 0
    bonus_point_type: str = "Chase UR"
    is_completed: bool = False

    @property
    def remaining_spend(self) -> float:
        return max(0.0, self.target_spend - self.current_spend)

    @property
    def progress_pct(self) -> float:
        if self.target_spend <= 0:
            return 100.0
        return min(100.0, (self.current_spend / self.target_spend) * 100.0)

    def days_remaining(self) -> int:
        if not self.deadline_date:
            return 0
        try:
            dl = datetime.strptime(self.deadline_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return max(0, (dl - now).days)
        except ValueError:
            return 0

    def required_daily_spend(self) -> float:
        days = self.days_remaining()
        if days <= 0:
            return self.remaining_spend
        return self.remaining_spend / days

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "card_name": self.card_name,
            "target_spend": self.target_spend,
            "current_spend": self.current_spend,
            "deadline_date": self.deadline_date,
            "bonus_points": self.bonus_points,
            "bonus_point_type": self.bonus_point_type,
            "is_completed": self.is_completed,
            "remaining_spend": self.remaining_spend,
            "progress_pct": round(self.progress_pct, 1),
            "days_remaining": self.days_remaining(),
            "required_daily_spend": round(self.required_daily_spend(), 2),
        }


@dataclass
class CardPortfolio:
    cards: list[CreditCard] = field(default_factory=list)
    sub_trackers: list[SubTracker] = field(default_factory=list)
    monthly_spend_profile: dict[str, float] = field(
        default_factory=lambda: {
            "dining": 500.0,
            "groceries": 600.0,
            "travel": 250.0,
            "gas": 150.0,
            "streaming": 50.0,
            "online_retail": 300.0,
            "catch_all": 1000.0,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cards": [c.to_dict() for c in self.cards],
            "sub_trackers": [s.to_dict() for s in self.sub_trackers],
            "monthly_spend_profile": self.monthly_spend_profile,
        }
