# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local JSON storage manager for credit card portfolio and SUB trackers.
"""

import json
from pathlib import Path
from typing import Any

from .models import CardPortfolio, CreditCard, SubTracker


class PortfolioStore:
    """Manages local persistence for card portfolio in ~/.cardroute/."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            self.base_dir = Path.home() / ".cardroute"
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.portfolio_file = self.base_dir / "portfolio.json"

    def load_portfolio(self) -> CardPortfolio:
        """Load portfolio from JSON file or return default preset."""
        if not self.portfolio_file.is_file():
            return self._create_default_preset()

        try:
            with open(self.portfolio_file, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (json.JSONDecodeError, OSError):
            return self._create_default_preset()

    def save_portfolio(self, portfolio: CardPortfolio) -> None:
        """Save portfolio to disk atomically."""
        temp_file = self.portfolio_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(portfolio.to_dict(), f, indent=2)
        temp_file.replace(self.portfolio_file)

    def _create_default_preset(self) -> CardPortfolio:
        """Generate a baseline starter trifecta portfolio."""
        cards = [
            CreditCard(
                card_id="chase-csp",
                card_name="Chase Sapphire Preferred",
                issuer="Chase",
                network="Visa",
                annual_fee=95.0,
                opened_date="2025-06-15",
                is_business=False,
                multipliers={
                    "dining": 3.0,
                    "travel": 2.0,
                    "streaming": 3.0,
                    "online_groceries": 3.0,
                    "catch_all": 1.0,
                },
                point_type="Chase UR",
                point_valuation_cents=2.0,
                annual_credits_value=50.0,
            ),
            CreditCard(
                card_id="chase-cff",
                card_name="Chase Freedom Flex",
                issuer="Chase",
                network="Mastercard",
                annual_fee=0.0,
                opened_date="2025-08-10",
                is_business=False,
                multipliers={"dining": 3.0, "pharmacy": 3.0, "catch_all": 1.0},
                point_type="Chase UR",
                point_valuation_cents=2.0,
            ),
            CreditCard(
                card_id="amex-gold",
                card_name="American Express Gold Card",
                issuer="Amex",
                network="Amex",
                annual_fee=325.0,
                opened_date="2026-01-20",
                is_business=False,
                multipliers={"dining": 4.0, "groceries": 4.0, "travel": 3.0, "catch_all": 1.0},
                point_type="Amex MR",
                point_valuation_cents=2.0,
                annual_credits_value=240.0,
            ),
            CreditCard(
                card_id="citi-double-cash",
                card_name="Citi Double Cash",
                issuer="Citi",
                network="Mastercard",
                annual_fee=0.0,
                opened_date="2024-03-01",
                is_business=False,
                multipliers={"catch_all": 2.0},
                point_type="Cash Back",
                point_valuation_cents=1.0,
            ),
        ]
        sub_trackers = [
            SubTracker(
                card_id="amex-gold",
                card_name="American Express Gold Card",
                target_spend=6000.0,
                current_spend=2850.0,
                deadline_date="2026-07-20",
                bonus_points=90000,
                bonus_point_type="Amex MR",
            )
        ]
        portfolio = CardPortfolio(cards=cards, sub_trackers=sub_trackers)
        self.save_portfolio(portfolio)
        return portfolio

    def _deserialize(self, data: dict[str, Any]) -> CardPortfolio:
        raw_cards = data.get("cards", [])
        cards = [
            CreditCard(
                card_id=c.get("card_id", ""),
                card_name=c.get("card_name", ""),
                issuer=c.get("issuer", "Other"),
                network=c.get("network", "Visa"),
                annual_fee=float(c.get("annual_fee", 0.0)),
                opened_date=c.get("opened_date", ""),
                is_business=bool(c.get("is_business", False)),
                multipliers=dict(c.get("multipliers", {})),
                point_type=c.get("point_type", "Cash Back"),
                point_valuation_cents=float(c.get("point_valuation_cents", 1.0)),
                annual_credits_value=float(c.get("annual_credits_value", 0.0)),
                notes=c.get("notes", ""),
            )
            for c in raw_cards
        ]
        raw_subs = data.get("sub_trackers", [])
        subs = [
            SubTracker(
                card_id=s.get("card_id", ""),
                card_name=s.get("card_name", ""),
                target_spend=float(s.get("target_spend", 0.0)),
                current_spend=float(s.get("current_spend", 0.0)),
                deadline_date=s.get("deadline_date", ""),
                bonus_points=int(s.get("bonus_points", 0)),
                bonus_point_type=s.get("bonus_point_type", "Points"),
                is_completed=bool(s.get("is_completed", False)),
            )
            for s in raw_subs
        ]
        return CardPortfolio(
            cards=cards,
            sub_trackers=subs,
            monthly_spend_profile=dict(data.get("monthly_spend_profile", {})),
        )
