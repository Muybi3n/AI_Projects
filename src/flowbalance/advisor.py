# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
LLM Contextualization & Natural Language Financial Advisor.
"""

import json
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .engine import normalize_to_monthly
from .models import (
    Account,
    AdvisoryResponse,
    Expense,
    IncomeStream,
    SolvencyReport,
    Transaction,
)


def build_financial_context(
    accounts: list[Account],
    incomes: list[IncomeStream],
    expenses: list[Expense],
    transactions: list[Transaction],
    solvency: SolvencyReport,
) -> dict[str, Any]:
    """Compile structured, PII-sanitized financial state for LLM context."""
    # Group expenses by category
    category_totals: dict[str, float] = defaultdict(float)
    for e in expenses:
        category_totals[e.category] += normalize_to_monthly(e.amount, e.frequency)

    return {
        "liquid_capital_usd": solvency.liquid_capital,
        "monthly_burn_rate_usd": solvency.monthly_burn_rate,
        "essential_monthly_burn_usd": solvency.essential_monthly_burn,
        "emergency_runway_months": solvency.essential_runway_months,
        "solvency_rating": solvency.solvency_rating,
        "savings_rate_pct": solvency.savings_rate_pct,
        "accounts_count": len(accounts),
        "income_streams": [
            {"name": i.name, "gross": i.amount, "frequency": i.frequency, "net": i.net_amount}
            for i in incomes
        ],
        "category_monthly_breakdown": dict(category_totals),
        "recent_transactions_count": len(transactions),
    }


class FinancialAdvisor:
    """Provides natural language querying and contextual analysis over personal finance state."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(
        self,
        query: str,
        accounts: list[Account],
        incomes: list[IncomeStream],
        expenses: list[Expense],
        transactions: list[Transaction],
        solvency: SolvencyReport,
    ) -> AdvisoryResponse:
        """Analyze financial state in response to user natural language query."""
        context = build_financial_context(accounts, incomes, expenses, transactions, solvency)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return AdvisoryResponse(
                    query=query,
                    executive_summary=data.get("executive_summary", ""),
                    observations=data.get("observations", []),
                    recommendations=data.get("recommendations", []),
                    risk_flags=data.get("risk_flags", []),
                    simulated_impact=data.get("simulated_impact", ""),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return AdvisoryResponse(
                    query=query,
                    executive_summary=raw_response,
                    observations=["Response generated via custom LLM adapter."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> AdvisoryResponse:
        """Built-in deterministic reasoning engine for offline queries."""
        q = query.lower()
        runway = context["emergency_runway_months"]
        burn = context["monthly_burn_rate_usd"]
        savings = context["savings_rate_pct"]
        breakdown = context["category_monthly_breakdown"]

        obs: list[str] = []
        recs: list[str] = []
        risks: list[str] = []
        impact = ""

        # Query Intent 1: Runway / Emergency / Solvency
        if any(w in q for w in ["runway", "emergency", "lose job", "income loss", "survive"]):
            summary = (
                f"With ${context['liquid_capital_usd']:,.2f} in liquid capital, your emergency runway "
                f"stands at {runway} months of essential expenses (${context['essential_monthly_burn_usd']:,.2f}/mo)."
            )
            obs.append(f"Solvency rating is currently evaluated as {context['solvency_rating']}.")
            if runway < 6.0:
                risks.append("Runway is under the recommended 6-month baseline for full financial resilience.")
                recs.append("Prioritize allocating 20%+ of monthly net surplus directly into the emergency vault.")
            else:
                obs.append("Emergency capital buffer exceeds standard 6-month safety threshold.")
            impact = f"In the event of a total income shock, core obligations are protected through {runway:.1f} months."

        # Query Intent 2: Spending / Categories / Expenses
        elif any(w in q for w in ["spend", "burn", "category", "where is", "cut", "reduce"]):
            top_cat = max(breakdown.items(), key=lambda x: x[1]) if breakdown else ("needs", 0.0)
            summary = (
                f"Total monthly burn is ${burn:,.2f}. The largest outflow category is '{top_cat[0]}' "
                f"at ${top_cat[1]:,.2f}/month ({ (top_cat[1]/burn*100.0 if burn else 0):.1f}% of total outflow)."
            )
            obs.append(f"Current net savings rate is {savings:.1f}%.")
            if "wants" in breakdown and breakdown["wants"] > 0.25 * burn:
                risks.append(f"Discretionary 'wants' represent ${breakdown['wants']:,.2f}/mo, exceeding 25% of total burn.")
                recs.append("Cap discretionary spend to accelerate investment compounding.")
            recs.append("Audit recurring subscription expenses for inactive services.")
            impact = "Trimming discretionary outflows by 15% would expand monthly wealth velocity."

        # Query Intent 3: Investing / Wealth / Surplus
        elif any(w in q for w in ["invest", "wealth", "compound", "surplus", "save"]):
            monthly_surplus = max(0.0, burn * (savings / (100.0 - savings))) if savings < 100.0 else 0.0
            summary = (
                f"Your net savings rate is {savings:.1f}%, generating an estimated monthly capital surplus "
                f"of ${monthly_surplus:,.2f} for compounding."
            )
            obs.append(f"Liquid capital base: ${context['liquid_capital_usd']:,.2f}.")
            recs.append("Automate scheduled transfers into index funds on each pay cycle.")
            recs.append("Ensure tax reserve allocations are isolated before calculating deployable surplus.")
            impact = "Consistent monthly compounding accelerates long-term financial independence."

        # Default General Overview
        else:
            summary = (
                f"Financial health snapshot: {context['solvency_rating']} with {runway} months of emergency runway "
                f"and a {savings:.1f}% net savings rate."
            )
            obs.append(f"Active monthly burn: ${burn:,.2f}/mo across {context['accounts_count']} account(s).")
            recs.append("Run forward 180-day forecast to monitor upcoming quarterly cash obligations.")

        return AdvisoryResponse(
            query=query,
            executive_summary=summary,
            observations=obs,
            recommendations=recs,
            risk_flags=risks,
            simulated_impact=impact,
        )
