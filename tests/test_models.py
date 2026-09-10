# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for holding and portfolio snapshot models.
"""

from capdrift.models import Holding, PortfolioSnapshot


def test_holding_calculations():
    h = Holding(
        symbol="VOO",
        name="Vanguard S&P 500 ETF",
        shares=10.0,
        current_price=500.0,
        average_cost=400.0,
        dividend_yield_pct=1.5,
    )

    assert h.market_value == 5000.0
    assert h.total_cost == 4000.0
    assert h.unrealized_pnl == 1000.0
    assert h.unrealized_pnl_pct == 25.0
    assert h.annual_dividend_income == 75.0


def test_portfolio_snapshot_metrics():
    h1 = Holding(symbol="VOO", name="S&P 500", shares=10.0, current_price=500.0, average_cost=400.0, dividend_yield_pct=1.5)
    h2 = Holding(symbol="BND", name="Total Bond", shares=50.0, current_price=70.0, average_cost=70.0, dividend_yield_pct=3.5)

    snap = PortfolioSnapshot(id="s1", cash_balance=1500.0, holdings=[h1, h2])

    assert snap.total_holdings_value == 8500.0
    assert snap.total_equity == 10000.0
    assert snap.total_annual_dividends == (5000 * 0.015) + (3500 * 0.035)
    assert snap.portfolio_yield_pct > 0.0
