# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI PTO Planner & Work-Life Balance Advisor.
"""

import json
from collections.abc import Callable
from typing import Any

from .accrual import AccrualEngine
from .models import PtoProfile
from .optimizer import PtoOptimizer


class PtoAdvisor:
    """Provides strategy for maximizing vacation days, OOO coverage, and leave burn plans."""

    def __init__(
        self,
        profile: PtoProfile,
        year: int = 2026,
        custom_llm_callable: Callable[[str], str] | None = None,
    ) -> None:
        self.profile = profile
        self.year = year
        self.optimizer = PtoOptimizer(year, profile.custom_holidays)
        self.accrual_engine = AccrualEngine(profile)
        self.custom_llm_callable = custom_llm_callable

    def build_context(self) -> dict[str, Any]:
        """Compile sanitized PTO state into structured context."""
        opt_plan = self.optimizer.optimize_plan(int(self.profile.current_balance_days))
        accrual_info = self.accrual_engine.project_year_end_balance()
        coverages = [c.to_dict() for c in self.profile.coverage_handovers]

        return {
            "year": self.year,
            "current_pto_balance_days": self.profile.current_balance_days,
            "annual_allowance_days": self.profile.total_annual_allowance_days,
            "accrual_summary": accrual_info,
            "optimized_holiday_bridges": opt_plan["recommended_breaks"][:4],
            "total_days_off_possible": opt_plan["total_consecutive_vacation_days_gained"],
            "coverage_delegates": coverages,
        }

    def consult(self, query: str) -> dict[str, Any]:
        """Answer PTO optimization and vacation planning queries."""
        context = self.build_context()

        if self.custom_llm_callable:
            prompt = (
                f"You are PtoMax AI, a work-life balance and PTO optimization strategist.\n"
                f"User Profile & Leave Context:\n{json.dumps(context, indent=2)}\n\n"
                f"User Question: {query}\n"
                f"Provide actionable holiday stacking advice, coverage delegation tips, or leave planning."
            )
            raw = self.custom_llm_callable(prompt)
            return {
                "query": query,
                "mode": "CUSTOM_LLM",
                "response": raw,
                "context": context,
            }

        # Deterministic Heuristic Advisor
        q = query.lower()
        recommendations = []
        action_plan = []

        if "maximize" in q or "holiday" in q or "bridge" in q or "hack" in q:
            recommendations.append(
                f"By stacking your {context['current_pto_balance_days']:.0f} PTO days around federal holidays, "
                f"you can achieve up to {context['total_days_off_possible']} total consecutive days off in {self.year}."
            )
            for b in context["optimized_holiday_bridges"][:3]:
                action_plan.append(
                    f"• {b['break_name']} ({b['start_date']} to {b['end_date']}): Burn {b['pto_days_required']} PTO → Get {b['total_consecutive_days_off']} days off ({b['leverage_multiplier']}x leverage)."
                )

        if "lose" in q or "cap" in q or "rollover" in q or "forfeit" in q or "cliff" in q:
            acc = context["accrual_summary"]
            if acc["days_at_risk_of_forfeiture"] > 0:
                recommendations.append(
                    f"🚨 You are projected to lose {acc['days_at_risk_of_forfeiture']} days of PTO at year-end."
                )
                action_plan.append(
                    "Schedule at least 1 holiday bridge in Q3/Q4 before December 31."
                )
            else:
                recommendations.append(
                    "Your PTO balance is healthy and within your rollover limit."
                )

        if "cover" in q or "handover" in q or "delegate" in q or "ooo" in q:
            covs = context["coverage_delegates"]
            if covs:
                recommendations.append(
                    f"You have {len(covs)} project coverage handovers configured."
                )
                for c in covs:
                    action_plan.append(
                        f"• {c['project_or_domain']} assigned to {c['primary_cover_name']}."
                    )
            else:
                recommendations.append(
                    "No coverage delegates configured. Run 'ptomax coverage add' before going OOO."
                )

        if not action_plan:
            recommendations.append(
                "Plan your time off early in the year to lock in calendar holds and prevent burnout."
            )
            action_plan.append("Top 2026 Opportunity: Thanksgiving (Burn 3 PTO → Get 9 Days Off).")
            action_plan.append(
                "Top 2026 Opportunity: Memorial Day / Labor Day (Burn 4 PTO → Get 9 Days Off)."
            )

        return {
            "query": query,
            "mode": "DETERMINISTIC_HEURISTIC",
            "summary": f"PTO optimization plan for {self.year}. Current balance: {context['current_pto_balance_days']:.0f} days.",
            "recommendations": recommendations,
            "action_plan": action_plan,
        }
