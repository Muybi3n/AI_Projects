# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Financial data models for accounts, income streams, recurring expenses, and forecast projections.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Frequency = Literal["daily", "weekly", "biweekly", "monthly", "quarterly", "annually"]
ExpenseCategory = Literal["needs", "wants", "investments", "taxes", "debt", "emergency"]


@dataclass
class Account:
    """Represents a cash, checking, or savings account."""

    id: str
    name: str
    balance: float
    is_liquid: bool = True
    currency: str = "USD"
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IncomeStream:
    """Recurring or scheduled income source."""

    id: str
    name: str
    amount: float
    frequency: Frequency
    start_date: str
    end_date: str | None = None
    tax_withholding_pct: float = 0.0

    @property
    def net_amount(self) -> float:
        """Net cash inflow after estimated tax withholding."""
        return self.amount * (1.0 - (self.tax_withholding_pct / 100.0))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Expense:
    """Recurring or fixed expense outflow."""

    id: str
    name: str
    amount: float
    frequency: Frequency
    category: ExpenseCategory
    start_date: str
    end_date: str | None = None
    is_essential: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AllocationRule:
    """Rules for routing net income into specific wealth buckets."""

    bucket_name: str
    percentage: float
    target_cap: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastPoint:
    """Single-day financial state in the forward projection timeline."""

    date_str: str
    starting_balance: float
    total_inflows: float
    total_outflows: float
    ending_balance: float
    events: list[str] = field(default_factory=list)


@dataclass
class SolvencyReport:
    """Runway and stress-test evaluation."""

    liquid_capital: float
    monthly_burn_rate: float
    essential_monthly_burn: float
    full_runway_months: float
    essential_runway_months: float
    solvency_rating: str
    savings_rate_pct: float
