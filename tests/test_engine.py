# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for cardroute spend routing and 5/24 bank evaluation engine.
"""

from cardroute.engine import CardRoutingEngine
from cardroute.models import CardPortfolio, CreditCard


def test_card_routing_best_category():
    cards = [
        CreditCard(
            card_id="c1",
            card_name="Card A",
            issuer="Chase",
            network="Visa",
            multipliers={"dining": 3.0, "catch_all": 1.0},
            point_valuation_cents=2.0,  # 6.0% on dining
        ),
        CreditCard(
            card_id="c2",
            card_name="Card B",
            issuer="Citi",
            network="Mastercard",
            multipliers={"catch_all": 2.0},
            point_valuation_cents=1.0,  # 2.0% catch-all
        ),
    ]
    portfolio = CardPortfolio(cards=cards)
    engine = CardRoutingEngine(portfolio)

    route = engine.route_purchase("dining", 100.0, prioritize_sub=False)
    assert route["recommended_card"]["card_id"] == "c1"
    assert route["estimated_return_pct"] == 6.0
    assert route["estimated_value_dollars"] == 6.0


def test_chase_524_rule_evaluation():
    cards = [
        CreditCard(
            card_id="c1",
            card_name="Card 1",
            issuer="Chase",
            network="Visa",
            opened_date="2025-01-01",
        ),
        CreditCard(
            card_id="c2",
            card_name="Card 2",
            issuer="Amex",
            network="Amex",
            opened_date="2025-03-01",
        ),
        CreditCard(
            card_id="c3",
            card_name="Card 3",
            issuer="Citi",
            network="Mastercard",
            opened_date="2025-05-01",
        ),
    ]
    portfolio = CardPortfolio(cards=cards)
    engine = CardRoutingEngine(portfolio)

    eval_res = engine.evaluate_bank_rules()
    assert eval_res["chase_524_status"]["count"] == 3
    assert eval_res["chase_524_status"]["is_eligible_for_chase"] is True
    assert eval_res["chase_524_status"]["slots_available"] == 2
