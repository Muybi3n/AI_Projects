# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI Credit Card Portfolio Companion & Card Churning Strategy Advisor.
"""

import json
from collections.abc import Callable
from typing import Any

from .engine import CardRoutingEngine
from .models import CardPortfolio


class CardAdvisor:
    """Provides heuristic and LLM-powered credit card strategy guidance."""

    def __init__(
        self,
        portfolio: CardPortfolio,
        custom_llm_callable: Callable[[str], str] | None = None,
    ) -> None:
        self.portfolio = portfolio
        self.engine = CardRoutingEngine(portfolio)
        self.custom_llm_callable = custom_llm_callable

    def build_context(self) -> dict[str, Any]:
        """Compile sanitized wallet cards, 5/24 status, and SUB goals into structured context."""
        bank_rules = self.engine.evaluate_bank_rules()
        audit = self.engine.audit_wallet_value()
        subs = [s.to_dict() for s in self.portfolio.sub_trackers]

        return {
            "total_cards": len(self.portfolio.cards),
            "cards": [
                {
                    "card_name": c.card_name,
                    "issuer": c.issuer,
                    "annual_fee": c.annual_fee,
                    "opened_date": c.opened_date,
                    "multipliers": c.multipliers,
                    "point_type": c.point_type,
                }
                for c in self.portfolio.cards
            ],
            "chase_524_status": bank_rules["chase_524_status"],
            "active_sub_goals": subs,
            "wallet_net_profit": audit["net_annual_wallet_profit"],
            "net_effective_annual_fee": audit["net_effective_annual_fee"],
        }

    def consult(self, query: str) -> dict[str, Any]:
        """Answer credit card strategy questions using deterministic heuristics or pluggable LLM."""
        context = self.build_context()

        if self.custom_llm_callable:
            prompt = (
                f"You are CardRoute AI, an expert credit card rewards and churning optimizer.\n"
                f"Current Wallet Context:\n{json.dumps(context, indent=2)}\n\n"
                f"User Question: {query}\n"
                f"Provide actionable, points-maximizing recommendations while adhering to bank rules."
            )
            raw_response = self.custom_llm_callable(prompt)
            return {
                "query": query,
                "mode": "CUSTOM_LLM",
                "response": raw_response,
                "context": context,
            }

        # Deterministic Heuristic Advisor
        q = query.lower()
        recommendations = []
        action_plan = []
        c524 = context["chase_524_status"]

        if "5/24" in q or "chase" in q or "eligible" in q:
            status_text = f"Your current Chase 5/24 status is {c524['status']} ({c524['slots_available']} slots available)."
            if c524["is_eligible_for_chase"]:
                recommendations.append(
                    "You are UNDER 5/24. Prioritize Chase cards before other issuers (e.g. Ink Business Unlimited, Sapphire Preferred)."
                )
            else:
                recommendations.append(
                    f"You are OVER 5/24. Focus on business cards or Amex/Citi/Capital One until your next slot drops on {c524['next_slot_dropoff_date']}."
                )
            action_plan.append(status_text)

        if "sub" in q or "bonus" in q or "spend" in q or "target" in q:
            if context["active_sub_goals"]:
                for sub in context["active_sub_goals"]:
                    action_plan.append(
                        f"MSR Alert: ${sub['remaining_spend']:.2f} left on {sub['card_name']} to earn {sub['bonus_points']:,} {sub['bonus_point_type']}. Target daily spend: ${sub['required_daily_spend']:.2f}/day."
                    )
            else:
                recommendations.append(
                    "No active Sign-Up Bonus trackers. Consider opening a new card if you have upcoming large purchases."
                )

        if "dining" in q or "food" in q or "restaurant" in q:
            route = self.engine.route_purchase("dining", 100.0)
            rec_card = (
                route["recommended_card"]["card_name"] if route.get("recommended_card") else "None"
            )
            action_plan.append(
                f"Optimal card for Dining: {rec_card} ({route['estimated_return_pct']}% net return)."
            )

        if "grocery" in q or "groceries" in q or "supermarket" in q:
            route = self.engine.route_purchase("groceries", 100.0)
            rec_card = (
                route["recommended_card"]["card_name"] if route.get("recommended_card") else "None"
            )
            action_plan.append(
                f"Optimal card for Groceries: {rec_card} ({route['estimated_return_pct']}% net return)."
            )

        if not action_plan:
            action_plan.append(
                f"Current wallet net annual profit: ${context['wallet_net_profit']:.2f}."
            )
            action_plan.append(
                "Use 'cardroute route --category <cat> --amount <amt>' to find optimal card at checkout."
            )

        return {
            "query": query,
            "mode": "DETERMINISTIC_HEURISTIC",
            "summary": f"Portfolio analysis for {context['total_cards']} cards. Net annual value: ${context['wallet_net_profit']:.2f}.",
            "recommendations": recommendations
            or ["Optimize merchant routing on all recurring expenses."],
            "action_plan": action_plan,
            "chase_524": c524["status"],
        }
