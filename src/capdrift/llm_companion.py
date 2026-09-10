# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI Portfolio Companion: Natural-language portfolio audits, uncompensated risk discovery, and LLM adapters.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .analytics import PortfolioAnalyzer
from .models import PortfolioSnapshot


@dataclass
class CompanionResponse:
    query: str
    executive_thesis: str
    observations: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    rebalance_actions: list[str] = field(default_factory=list)
    macro_context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "executive_thesis": self.executive_thesis,
            "observations": self.observations,
            "risk_flags": self.risk_flags,
            "rebalance_actions": self.rebalance_actions,
            "macro_context": self.macro_context,
        }


def build_portfolio_context(snapshot: PortfolioSnapshot) -> dict[str, Any]:
    """Compile structured, PII-sanitized portfolio state for LLM reasoning."""
    concentration = PortfolioAnalyzer.evaluate_concentration(snapshot)
    drift = PortfolioAnalyzer.evaluate_drift(snapshot)
    stress = PortfolioAnalyzer.run_stress_test(snapshot)

    holdings_summary = [
        {
            "symbol": h.symbol,
            "name": h.name,
            "market_value_usd": round(h.market_value, 2),
            "weight_pct": round(h.market_value / snapshot.total_equity * 100.0, 1) if snapshot.total_equity > 0 else 0.0,
            "unrealized_pnl_pct": round(h.unrealized_pnl_pct, 1),
            "asset_class": h.asset_class,
            "dividend_yield_pct": h.dividend_yield_pct,
        }
        for h in sorted(snapshot.holdings, key=lambda x: x.market_value, reverse=True)[:15]
    ]

    return {
        "total_equity_usd": round(snapshot.total_equity, 2),
        "cash_balance_usd": round(snapshot.cash_balance, 2),
        "total_holdings_count": len(snapshot.holdings),
        "annual_dividends_usd": round(snapshot.total_annual_dividends, 2),
        "portfolio_yield_pct": round(snapshot.portfolio_yield_pct, 2),
        "concentration": {
            "hhi_score": concentration.hhi_score,
            "top_holding": concentration.top_holding_symbol,
            "top_holding_weight_pct": concentration.top_holding_weight_pct,
            "top_3_weight_pct": concentration.top_3_weight_pct,
            "risk_tier": concentration.risk_assessment,
        },
        "drift_vs_target": [
            {"asset_class": d.asset_class, "current_pct": d.current_weight_pct, "target_pct": d.target_weight_pct, "drift_pct": d.drift_pct}
            for d in drift
        ],
        "top_holdings": holdings_summary,
        "historical_stress_scenarios": [
            {"scenario": s.scenario_name, "drawdown_pct": s.projected_drawdown_pct, "dollar_loss": s.projected_dollar_loss}
            for s in stress
        ],
    }


class PortfolioCompanion:
    """AI Companion providing contextualized analysis over investment snapshots."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str, snapshot: PortfolioSnapshot) -> CompanionResponse:
        context = build_portfolio_context(snapshot)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return CompanionResponse(
                    query=query,
                    executive_thesis=data.get("executive_thesis", ""),
                    observations=data.get("observations", []),
                    risk_flags=data.get("risk_flags", []),
                    rebalance_actions=data.get("rebalance_actions", []),
                    macro_context=data.get("macro_context", ""),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return CompanionResponse(
                    query=query,
                    executive_thesis=raw_response,
                    observations=["Generated via custom LLM adapter."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> CompanionResponse:
        """Deterministic reasoning engine for offline portfolio analysis."""
        q = query.lower()
        equity = context["total_equity_usd"]
        conc = context["concentration"]
        hhi = conc["hhi_score"]
        drift = context["drift_vs_target"]

        obs: list[str] = []
        risks: list[str] = []
        actions: list[str] = []
        macro = ""

        # Query Intent: Risk & Concentration
        if any(w in q for w in ["risk", "concentrat", "uncompensated", "safe", "crash"]):
            thesis = (
                f"Portfolio holds ${equity:,.2f} in total equity with an HHI concentration score of "
                f"{hhi} ({conc['risk_tier']}). Top holding '{conc['top_holding']}' represents "
                f"{conc['top_holding_weight_pct']}% of total capital."
            )
            obs.append(f"Top 3 assets comprise {conc['top_3_weight_pct']}% of overall portfolio weight.")
            if hhi > 2500:
                risks.append(f"High concentration in {conc['top_holding']} exposes capital to single-company idiosyncratic risk.")
                actions.append(f"Consider trimming {conc['top_holding']} to cap single-asset exposure under 15-20%.")
            else:
                obs.append("Concentration levels remain balanced across broad market holdings.")
            macro = "Broad diversification insulates core capital from sector-specific multiple compression."

        # Query Intent: Rebalance & Drift
        elif any(w in q for w in ["rebalance", "drift", "allocate", "target", "fix"]):
            out_of_bounds = [d for d in drift if abs(d["drift_pct"]) > 5.0]
            thesis = (
                f"Portfolio asset allocation shows {len(out_of_bounds)} asset class(es) with >5% drift "
                f"from target benchmarks."
            )
            for d in drift:
                if d["drift_pct"] > 5.0:
                    risks.append(f"{d['asset_class']} is OVER target by +{d['drift_pct']}% (Current: {d['current_pct']}%, Target: {d['target_pct']}%).")
                    actions.append(f"Trim {d['asset_class']} or redirect new cash deposits to underweight classes.")
                elif d["drift_pct"] < -5.0:
                    obs.append(f"{d['asset_class']} is UNDER target by {d['drift_pct']}% (Current: {d['current_pct']}%, Target: {d['target_pct']}%).")
                    actions.append(f"Deploy capital into {d['asset_class']} to restore baseline asset allocation.")
            macro = "Systematic rebalancing forces buying low and selling high over market cycles."

        # Query Intent: Dividends & Cash Flow
        elif any(w in q for w in ["dividend", "passive", "income", "snowball", "yield"]):
            divs = context["annual_dividends_usd"]
            yld = context["portfolio_yield_pct"]
            thesis = (
                f"Portfolio generates ${divs:,.2f}/year in gross annual dividend cash flow "
                f"(effective portfolio yield: {yld}%)."
            )
            obs.append(f"Monthly passive dividend cash flow: ${divs / 12.0:,.2f}/month.")
            actions.append("Keep Dividend Reinvestment (DRIP) active to accelerate share compounding.")
            actions.append("Audit dividend payout stability across top yielding positions.")
            macro = "Reinvesting dividends during market pullbacks captures lower cost basis automatically."

        # Default Overview
        else:
            thesis = (
                f"Portfolio overview: ${equity:,.2f} total equity across {context['total_holdings_count']} "
                f"holding(s). Concentration status: {conc['risk_tier']} (HHI: {hhi})."
            )
            obs.append(f"Annual passive dividend generation: ${context['annual_dividends_usd']:,.2f} ({context['portfolio_yield_pct']}% yield).")
            actions.append("Run 'capdrift audit' to review full stress scenarios and drift deltas.")

        return CompanionResponse(
            query=query,
            executive_thesis=thesis,
            observations=obs,
            risk_flags=risks,
            rebalance_actions=actions,
            macro_context=macro,
        )
