# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for investment holdings, portfolio snapshots, drift metrics, and AI companion audits.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

AssetClass = Literal[
    "us_equities",
    "intl_equities",
    "fixed_income",
    "real_estate",
    "crypto",
    "cash",
    "commodities",
    "other",
]


@dataclass
class Holding:
    """Individual security holding in a portfolio snapshot."""
    symbol: str
    name: str
    shares: float
    current_price: float
    average_cost: float = 0.0
    asset_class: AssetClass | str = "us_equities"
    sector: str = "Broad Market"
    dividend_yield_pct: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def total_cost(self) -> float:
        return self.shares * self.average_cost if self.average_cost > 0 else self.market_value

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.total_cost

    @property
    def unrealized_pnl_pct(self) -> float:
        return (self.unrealized_pnl / self.total_cost * 100.0) if self.total_cost > 0 else 0.0

    @property
    def annual_dividend_income(self) -> float:
        return self.market_value * (self.dividend_yield_pct / 100.0)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioSnapshot:
    """Complete portfolio point-in-time snapshot."""
    id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    broker_source: str = "Generic CSV"
    cash_balance: float = 0.0
    holdings: list[Holding] = field(default_factory=list)

    @property
    def total_holdings_value(self) -> float:
        return sum(h.market_value for h in self.holdings)

    @property
    def total_equity(self) -> float:
        return self.total_holdings_value + self.cash_balance

    @property
    def total_cost(self) -> float:
        return sum(h.total_cost for h in self.holdings) + self.cash_balance

    @property
    def total_unrealized_pnl(self) -> float:
        return self.total_equity - self.total_cost

    @property
    def total_unrealized_pnl_pct(self) -> float:
        return (self.total_unrealized_pnl / self.total_cost * 100.0) if self.total_cost > 0 else 0.0

    @property
    def total_annual_dividends(self) -> float:
        return sum(h.annual_dividend_income for h in self.holdings)

    @property
    def portfolio_yield_pct(self) -> float:
        return (self.total_annual_dividends / self.total_equity * 100.0) if self.total_equity > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["total_equity"] = self.total_equity
        res["total_unrealized_pnl"] = self.total_unrealized_pnl
        res["total_annual_dividends"] = self.total_annual_dividends
        return res


@dataclass
class ConcentrationMetric:
    """Concentration and diversity risk metrics."""
    hhi_score: float  # Herfindahl-Hirschman Index (0-10,000)
    top_holding_symbol: str
    top_holding_weight_pct: float
    top_3_weight_pct: float
    top_5_weight_pct: float
    risk_assessment: str


@dataclass
class DriftItem:
    """Individual asset class drift vs target allocation."""
    asset_class: str
    current_weight_pct: float
    target_weight_pct: float
    drift_pct: float
    rebalance_dollar_delta: float  # Positive = Buy, Negative = Sell


@dataclass
class StressScenario:
    """Historical crash stress-test simulation result."""
    scenario_name: str
    description: str
    projected_drawdown_pct: float
    projected_dollar_loss: float
    estimated_recovery_period: str


@dataclass
class DividendSnowballPoint:
    """Year-by-year compounding projection point."""
    year: int
    portfolio_value: float
    annual_dividend: float
    monthly_passive_income: float
