# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Portfolio analytics: Concentration HHI, Capital Drift, Rebalancing, Dividend Snowball, and Macro Stress Testing.
"""

from collections import defaultdict

from .models import (
    ConcentrationMetric,
    DividendSnowballPoint,
    DriftItem,
    PortfolioSnapshot,
    StressScenario,
)

# Standard target allocation defaults (e.g. Core 4 / Boglehead / Tech-Balanced)
DEFAULT_TARGET_ALLOCATION: dict[str, float] = {
    "us_equities": 60.0,
    "intl_equities": 20.0,
    "fixed_income": 10.0,
    "crypto": 5.0,
    "cash": 5.0,
}


class PortfolioAnalyzer:
    """Computes risk concentration, allocation drift, rebalance targets, and dividend projections."""

    @staticmethod
    def evaluate_concentration(snapshot: PortfolioSnapshot) -> ConcentrationMetric:
        """Calculate Herfindahl-Hirschman Index (HHI) and top asset weights."""
        total = snapshot.total_equity
        if total <= 0 or not snapshot.holdings:
            return ConcentrationMetric(
                hhi_score=0.0,
                top_holding_symbol="N/A",
                top_holding_weight_pct=0.0,
                top_3_weight_pct=0.0,
                top_5_weight_pct=0.0,
                risk_assessment="Empty Portfolio",
            )

        sorted_holdings = sorted(snapshot.holdings, key=lambda h: h.market_value, reverse=True)
        weights = [(h.symbol, (h.market_value / total * 100.0)) for h in sorted_holdings]

        # HHI is the sum of squared percentage weights (0 to 10,000)
        hhi = sum((w ** 2) for _, w in weights)
        top_symbol, top_weight = weights[0]
        top_3_weight = sum(w for _, w in weights[:3])
        top_5_weight = sum(w for _, w in weights[:5])

        # Department of Justice & Financial benchmarks:
        # < 1500 = Highly Diversified
        # 1500 - 2500 = Moderately Concentrated
        # > 2500 = Highly Concentrated (Idiosyncratic Risk)
        if hhi < 1500:
            assessment = "Highly Diversified (Low Single-Stock Risk)"
        elif hhi <= 2500:
            assessment = "Moderately Concentrated (Acceptable for Growth)"
        else:
            assessment = "High Single-Asset Concentration (Elevated Idiosyncratic Risk)"

        return ConcentrationMetric(
            hhi_score=round(hhi, 1),
            top_holding_symbol=top_symbol,
            top_holding_weight_pct=round(top_weight, 1),
            top_3_weight_pct=round(top_3_weight, 1),
            top_5_weight_pct=round(top_5_weight, 1),
            risk_assessment=assessment,
        )

    @staticmethod
    def evaluate_drift(
        snapshot: PortfolioSnapshot,
        target_allocation: dict[str, float] | None = None,
    ) -> list[DriftItem]:
        """Compute allocation drift against target weights and calculate rebalance delta."""
        targets = target_allocation or DEFAULT_TARGET_ALLOCATION
        total_equity = snapshot.total_equity
        if total_equity <= 0:
            return []

        # Current breakdown by asset class
        current_totals: dict[str, float] = defaultdict(float)
        current_totals["cash"] = snapshot.cash_balance
        for h in snapshot.holdings:
            current_totals[h.asset_class] += h.market_value

        all_classes = sorted(set(list(targets.keys()) + list(current_totals.keys())))
        drift_items: list[DriftItem] = []

        for ac in all_classes:
            curr_val = current_totals.get(ac, 0.0)
            curr_pct = curr_val / total_equity * 100.0
            target_pct = targets.get(ac, 0.0)
            drift_pct = curr_pct - target_pct

            # Positive delta means under target (Buy), Negative means over target (Sell/Trim)
            target_dollar = total_equity * (target_pct / 100.0)
            dollar_delta = target_dollar - curr_val

            drift_items.append(
                DriftItem(
                    asset_class=ac,
                    current_weight_pct=round(curr_pct, 1),
                    target_weight_pct=round(target_pct, 1),
                    drift_pct=round(drift_pct, 1),
                    rebalance_dollar_delta=round(dollar_delta, 2),
                )
            )

        return drift_items

    @staticmethod
    def project_dividend_snowball(
        snapshot: PortfolioSnapshot,
        years: int = 5,
        annual_growth_rate_pct: float = 6.0,
        dividend_growth_rate_pct: float = 5.0,
    ) -> list[DividendSnowballPoint]:
        """Simulate compounding dividend reinvestment snowball over N years."""
        equity = snapshot.total_equity
        current_yield = snapshot.portfolio_yield_pct / 100.0 if snapshot.portfolio_yield_pct > 0 else 0.015

        points: list[DividendSnowballPoint] = []

        for y in range(1, years + 1):
            annual_div = equity * current_yield
            # Reinvest dividends + capital appreciation
            equity = (equity + annual_div) * (1.0 + (annual_growth_rate_pct / 100.0))
            current_yield *= (1.0 + (dividend_growth_rate_pct / 100.0))

            points.append(
                DividendSnowballPoint(
                    year=y,
                    portfolio_value=round(equity, 2),
                    annual_dividend=round(annual_div, 2),
                    monthly_passive_income=round(annual_div / 12.0, 2),
                )
            )

        return points

    @staticmethod
    def run_stress_test(snapshot: PortfolioSnapshot) -> list[StressScenario]:
        """Simulate portfolio impact across notable historical market shocks."""
        equity = snapshot.total_equity
        if equity <= 0:
            return []

        # Asset class weights
        weights: dict[str, float] = defaultdict(float)
        weights["cash"] = snapshot.cash_balance / equity
        for h in snapshot.holdings:
            weights[h.asset_class] += h.market_value / equity

        # Historical Drawdown Benchmarks per asset class
        # (US Equities, Intl, Bonds, Crypto, Cash)
        scenarios = [
            {
                "name": "2008 Global Financial Crisis (GFC)",
                "desc": "Severe liquidity & banking collapse, credit freeze.",
                "shocks": {"us_equities": -0.50, "intl_equities": -0.55, "fixed_income": 0.05, "crypto": -0.80, "cash": 0.0},
                "recovery": "3.5 - 4.5 Years",
            },
            {
                "name": "2020 COVID Flash Crash",
                "desc": "Rapid global lockdown shock followed by monetary stimulus.",
                "shocks": {"us_equities": -0.34, "intl_equities": -0.32, "fixed_income": 0.02, "crypto": -0.50, "cash": 0.0},
                "recovery": "5 - 6 Months",
            },
            {
                "name": "2022 Fed Rate Hike & Tech Drawdown",
                "desc": "Aggressive quantitative tightening and multiple compression.",
                "shocks": {"us_equities": -0.22, "intl_equities": -0.18, "fixed_income": -0.13, "crypto": -0.65, "cash": 0.0},
                "recovery": "1.5 - 2 Years",
            },
        ]

        results: list[StressScenario] = []
        for sc in scenarios:
            weighted_drop = sum(weights[ac] * sc["shocks"].get(ac, -0.25) for ac in weights)
            loss_dollars = equity * abs(weighted_drop)
            results.append(
                StressScenario(
                    scenario_name=sc["name"],
                    description=sc["desc"],
                    projected_drawdown_pct=round(weighted_drop * 100.0, 1),
                    projected_dollar_loss=round(loss_dollars, 2),
                    estimated_recovery_period=sc["recovery"],
                )
            )

        return results
