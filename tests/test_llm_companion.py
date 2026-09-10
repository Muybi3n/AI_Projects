# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for LLM Portfolio Companion and AI advisory features.
"""

from capdrift.llm_companion import PortfolioCompanion, build_portfolio_context
from capdrift.models import Holding, PortfolioSnapshot


def test_build_portfolio_context():
    h = Holding(symbol="VOO", name="S&P 500", shares=10.0, current_price=500.0, asset_class="us_equities")
    snap = PortfolioSnapshot(id="s1", holdings=[h])

    ctx = build_portfolio_context(snap)
    assert ctx["total_equity_usd"] == 5000.0
    assert ctx["concentration"]["top_holding"] == "VOO"


def test_heuristic_companion_query():
    h = Holding(symbol="NVDA", name="Nvidia", shares=50.0, current_price=100.0, asset_class="us_equities")
    snap = PortfolioSnapshot(id="s2", holdings=[h])

    companion = PortfolioCompanion()
    resp = companion.consult("Where is my biggest concentration risk?", snap)

    assert "NVDA" in resp.executive_thesis
    assert len(resp.risk_flags) > 0


def test_custom_llm_adapter():
    snap = PortfolioSnapshot(id="s3", holdings=[])

    def mock_llm(query: str, ctx: dict) -> str:
        return '{"executive_thesis": "Custom AI Portfolio Thesis", "risk_flags": ["Tech overexposure"]}'

    companion = PortfolioCompanion(custom_llm_callable=mock_llm)
    resp = companion.consult("How is my portfolio?", snap)

    assert resp.executive_thesis == "Custom AI Portfolio Thesis"
    assert "Tech overexposure" in resp.risk_flags
