# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for cardroute data models.
"""

from cardroute.models import CreditCard, SubTracker


def test_credit_card_effective_return():
    card = CreditCard(
        card_id="amex-gold",
        card_name="American Express Gold Card",
        issuer="Amex",
        network="Amex",
        annual_fee=325.0,
        multipliers={"dining": 4.0, "groceries": 4.0, "catch_all": 1.0},
        point_type="Amex MR",
        point_valuation_cents=2.0,
    )
    assert card.get_effective_multiplier("dining") == 4.0
    assert card.get_effective_multiplier("unknown_cat") == 1.0
    assert card.get_effective_return_pct("dining") == 8.0
    assert card.get_effective_return_pct("catch_all") == 2.0


def test_sub_tracker_progress():
    sub = SubTracker(
        card_id="chase-csp",
        card_name="Chase Sapphire Preferred",
        target_spend=4000.0,
        current_spend=2000.0,
        bonus_points=60000,
        deadline_date="2026-12-31",
    )
    assert sub.remaining_spend == 2000.0
    assert sub.progress_pct == 50.0
    assert sub.days_remaining() > 0
