# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for portfolio concentration, drift, rebalancing, dividend snowball, and stress-tests.
"""

from capdrift.analytics import PortfolioAnalyzer
from capdrift.models import Holding, PortfolioSnapshot


def test_concentration_hhi():
    # 1 single holding = 100% = HHI 10,000 (Maximum concentration)
    h1 = Holding(symbol="AAPL", name="Apple", shares=100.0, current_price=200.0)
    snap = PortfolioSnapshot(id="s1", holdings=[h1])

    conc = PortfolioAnalyzer.evaluate_concentration(snap)
    assert conc.hhi_score == 10000.0
    assert conc.top_holding_symbol == "AAPL"
    assert "High Single-Asset" in conc.risk_assessment


def test_drift_and_rebalancing():
    h1 = Holding(symbol="VOO", name="S&P", shares=10.0, current_price=800.0, asset_class="us_equities")  # $8000 (80%)
    h2 = Holding(symbol="BND", name="Bond", shares=10.0, current_price=200.0, asset_class="fixed_income")  # $2000 (20%)
    snap = PortfolioSnapshot(id="s2", holdings=[h1, h2])

    target = {"us_equities": 60.0, "fixed_income": 40.0}
    drift = PortfolioAnalyzer.evaluate_drift(snap, target_allocation=target)

    voo_drift = next(d for d in drift if d.asset_class == "us_equities")
    bnd_drift = next(d for d in drift if d.asset_class == "fixed_income")

    assert voo_drift.current_weight_pct == 80.0
    assert voo_drift.drift_pct == 20.0
    assert voo_drift.rebalance_dollar_delta == -2000.0  # Trim $2,000

    assert bnd_drift.current_weight_pct == 20.0
    assert bnd_drift.drift_pct == -20.0
    assert bnd_drift.rebalance_dollar_delta == 2000.0  # Buy $2,000


def test_dividend_snowball_projection():
    h = Holding(symbol="SCHD", name="Dividend ETF", shares=100.0, current_price=80.0, dividend_yield_pct=3.5)
    snap = PortfolioSnapshot(id="s3", holdings=[h])

    points = PortfolioAnalyzer.project_dividend_snowball(snap, years=3)
    assert len(points) == 3
    assert points[0].year == 1
    assert points[2].portfolio_value > points[0].portfolio_value


def test_macro_stress_testing():
    h1 = Holding(symbol="VOO", name="S&P", shares=10.0, current_price=1000.0, asset_class="us_equities")
    snap = PortfolioSnapshot(id="s4", holdings=[h1])

    scenarios = PortfolioAnalyzer.run_stress_test(snap)
    assert len(scenarios) == 3
    assert scenarios[0].projected_drawdown_pct < 0.0
    assert scenarios[0].projected_dollar_loss > 0.0
