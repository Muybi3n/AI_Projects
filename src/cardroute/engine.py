# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Card routing optimization engine, bank churning rule evaluators, and wallet value audit.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from .models import CardPortfolio


class CardRoutingEngine:
    """Core mathematical optimization and bank policy verification engine."""

    def __init__(self, portfolio: CardPortfolio) -> None:
        self.portfolio = portfolio

    def route_purchase(
        self,
        category: str,
        amount: float,
        merchant: str = "",
        prioritize_sub: bool = True,
    ) -> dict[str, Any]:
        """Determine the optimal credit card for a specific transaction."""
        if not self.portfolio.cards:
            return {
                "recommended_card": None,
                "reason": "No credit cards in portfolio.",
                "estimated_return_pct": 0.0,
                "estimated_value_dollars": 0.0,
            }

        # Check for active SUB requirement first
        if prioritize_sub:
            active_subs = [
                s
                for s in self.portfolio.sub_trackers
                if not s.is_completed and s.remaining_spend > 0
            ]
            if active_subs:
                # Pick the most urgent SUB
                sub = min(active_subs, key=lambda s: s.days_remaining())
                sub_card = next((c for c in self.portfolio.cards if c.card_id == sub.card_id), None)
                if sub_card:
                    # Estimate effective SUB return: e.g. $800 bonus on $4,000 spend = 20% baseline return!
                    sub_effective_bonus_val = sub.bonus_points * (
                        sub_card.point_valuation_cents / 100.0
                    )
                    sub_return_rate = (
                        (sub_effective_bonus_val / sub.target_spend) * 100.0
                        if sub.target_spend > 0
                        else 0.0
                    )
                    total_effective_pct = sub_return_rate + sub_card.get_effective_return_pct(
                        category
                    )
                    est_val = amount * (total_effective_pct / 100.0)

                    return {
                        "recommended_card": sub_card.to_dict(),
                        "strategy": "SIGNUP_BONUS_PRIORITY",
                        "reason": f"Active Sign-Up Bonus on {sub_card.card_name}: ${sub.remaining_spend:.2f} remaining to unlock {sub.bonus_points:,} {sub.bonus_point_type}.",
                        "multiplier": sub_card.get_effective_multiplier(category),
                        "point_type": sub_card.point_type,
                        "estimated_return_pct": round(total_effective_pct, 2),
                        "estimated_value_dollars": round(est_val, 2),
                        "sub_tracker": sub.to_dict(),
                    }

        # Standard highest return percentage routing
        ranked = []
        for card in self.portfolio.cards:
            ret_pct = card.get_effective_return_pct(category)
            mult = card.get_effective_multiplier(category)
            val = amount * (ret_pct / 100.0)
            ranked.append((ret_pct, val, mult, card))

        ranked.sort(key=lambda x: x[0], reverse=True)
        best_ret, best_val, best_mult, best_card = ranked[0]

        return {
            "recommended_card": best_card.to_dict(),
            "strategy": "MAX_CATEGORY_RETURN",
            "reason": f"Top category yield: {best_mult}x {best_card.point_type} ({best_ret:.1f}% net return).",
            "multiplier": best_mult,
            "point_type": best_card.point_type,
            "estimated_return_pct": round(best_ret, 2),
            "estimated_value_dollars": round(best_val, 2),
            "alternatives": [
                {
                    "card_name": c.card_name,
                    "multiplier": m,
                    "return_pct": round(r, 2),
                    "dollar_value": round(v, 2),
                }
                for r, v, m, c in ranked[1:4]
            ],
        }

    def evaluate_bank_rules(self) -> dict[str, Any]:
        """Audit Chase 5/24, Amex limits, and bank application rules."""
        now = datetime.now(timezone.utc)
        two_years_ago = now - timedelta(days=730)

        # Chase 5/24: Personal cards opened in the last 24 months
        personal_cards_24m = []
        for c in self.portfolio.cards:
            if not c.is_business and c.opened_date:
                try:
                    od = datetime.strptime(c.opened_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if od >= two_years_ago:
                        personal_cards_24m.append((od, c))
                except ValueError:
                    pass

        personal_cards_24m.sort(key=lambda x: x[0])
        count_524 = len(personal_cards_24m)
        is_under_524 = count_524 < 5

        next_dropoff = None
        if count_524 >= 5 and personal_cards_24m:
            oldest_in_24 = personal_cards_24m[0][0]
            drop_date = oldest_in_24 + timedelta(days=730)
            next_dropoff = drop_date.strftime("%Y-%m-%d")

        # Amex credit card count (typically 4-5 max credit cards, charge cards excluded)
        amex_credit_cards = [
            c
            for c in self.portfolio.cards
            if c.issuer.lower() == "amex" and "charge" not in c.notes.lower()
        ]

        return {
            "chase_524_status": {
                "count": count_524,
                "status": f"{count_524}/24",
                "is_eligible_for_chase": is_under_524,
                "slots_available": max(0, 5 - count_524),
                "next_slot_dropoff_date": next_dropoff,
                "guidance": "Eligible for Chase personal & business cards"
                if is_under_524
                else f"In Chase 5/24 jail. Wait until {next_dropoff} for slots to open.",
            },
            "amex_portfolio_status": {
                "active_amex_cards": len(amex_credit_cards),
                "estimated_card_limit": 5,
                "slots_remaining": max(0, 5 - len(amex_credit_cards)),
            },
            "total_portfolio_cards": len(self.portfolio.cards),
        }

    def audit_wallet_value(self) -> dict[str, Any]:
        """Compute net portfolio economics: fees vs credits vs annual points yield."""
        total_fees = sum(c.annual_fee for c in self.portfolio.cards)
        total_credits = sum(c.annual_credits_value for c in self.portfolio.cards)
        net_effective_fee = total_fees - total_credits

        # Project annual points from monthly spend
        annual_points_value = 0.0
        spend_breakdown = {}

        for cat, monthly_amt in self.portfolio.monthly_spend_profile.items():
            annual_spend = monthly_amt * 12.0
            route_res = self.route_purchase(cat, annual_spend, prioritize_sub=False)
            val = route_res.get("estimated_value_dollars", 0.0)
            annual_points_value += val
            rec_c = route_res.get("recommended_card") or {}
            spend_breakdown[cat] = {
                "annual_spend": annual_spend,
                "best_card": rec_c.get("card_name", "N/A"),
                "annual_return_dollars": round(val, 2),
            }

        net_wallet_gain = annual_points_value - net_effective_fee

        # Identify cards with poor ROI
        card_assessments = []
        for c in self.portfolio.cards:
            net_card_cost = c.annual_fee - c.annual_credits_value
            status = "KEEP"
            if net_card_cost > 100:
                status = "EVALUATE_RETENTION"
            card_assessments.append(
                {
                    "card_name": c.card_name,
                    "annual_fee": c.annual_fee,
                    "credits": c.annual_credits_value,
                    "net_fee": net_card_cost,
                    "recommendation": status,
                }
            )

        return {
            "total_annual_fees": total_fees,
            "total_annual_credits": total_credits,
            "net_effective_annual_fee": net_effective_fee,
            "projected_annual_rewards_value": round(annual_points_value, 2),
            "net_annual_wallet_profit": round(net_wallet_gain, 2),
            "category_spend_breakdown": spend_breakdown,
            "card_assessments": card_assessments,
        }
