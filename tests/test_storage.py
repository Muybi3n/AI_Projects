# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for portfolio storage.
"""

from pathlib import Path

from cardroute.models import CreditCard
from cardroute.storage import PortfolioStore


def test_storage_crud(tmp_path: Path):
    store = PortfolioStore(tmp_path)
    portfolio = store.load_portfolio()
    assert len(portfolio.cards) > 0

    portfolio.cards.append(
        CreditCard(
            card_id="custom-card",
            card_name="Custom Test Card",
            issuer="Discover",
            network="Discover",
        )
    )
    store.save_portfolio(portfolio)

    reloaded = store.load_portfolio()
    assert any(c.card_id == "custom-card" for c in reloaded.cards)
