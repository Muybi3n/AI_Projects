# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for cardroute AI Advisor.
"""

from cardroute.advisor import CardAdvisor
from cardroute.models import CardPortfolio, CreditCard


def test_advisor_heuristic():
    cards = [
        CreditCard(
            card_id="c1",
            card_name="Chase Sapphire Preferred",
            issuer="Chase",
            network="Visa",
            annual_fee=95.0,
            opened_date="2025-01-01",
            multipliers={"dining": 3.0, "catch_all": 1.0},
            point_valuation_cents=2.0,
        )
    ]
    portfolio = CardPortfolio(cards=cards)
    advisor = CardAdvisor(portfolio)

    res = advisor.consult("What is my Chase 5/24 status?")
    assert "chase_524" in res
    assert "action_plan" in res


def test_advisor_custom_llm():
    portfolio = CardPortfolio()
    advisor = CardAdvisor(
        portfolio, custom_llm_callable=lambda p: "LLM recommendation: Apply for Freedom Flex."
    )
    res = advisor.consult("Which card next?")
    assert res["mode"] == "CUSTOM_LLM"
    assert "Apply for Freedom Flex" in res["response"]
