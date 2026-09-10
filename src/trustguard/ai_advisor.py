# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI Fiduciary & Estate Planning Companion: Natural-language trust queries, probate audit synthesis, and LLM adapters.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .engine import EstateEngine
from .models import TrustEntity


@dataclass
class EstateAdvisorResponse:
    query: str
    executive_summary: str
    fiduciary_findings: list[str] = field(default_factory=list)
    probate_risk_items: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    statutory_citations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "executive_summary": self.executive_summary,
            "fiduciary_findings": self.fiduciary_findings,
            "probate_risk_items": self.probate_risk_items,
            "action_items": self.action_items,
            "statutory_citations": self.statutory_citations,
        }


def build_estate_context(trust: TrustEntity) -> dict[str, Any]:
    """Compile structured, PII-sanitized estate state for LLM reasoning."""
    audit = EstateEngine.audit_funding(trust)
    waterfall = EstateEngine.calculate_waterfall(trust)

    return {
        "trust_name": trust.trust_name,
        "trust_type": trust.trust_type.value if hasattr(trust.trust_type, "value") else str(trust.trust_type),
        "jurisdiction": trust.jurisdiction_state,
        "grantor": trust.grantor_settlor,
        "current_trustee": trust.current_trustee,
        "successor_trustee": trust.successor_trustee,
        "total_estate_value_usd": audit.total_estate_value,
        "funding_metrics": {
            "funded_to_trust_usd": audit.funded_to_trust_value,
            "funded_to_trust_pct": audit.funded_to_trust_pct,
            "unfunded_probate_risk_usd": audit.unfunded_probate_risk_value,
            "unfunded_probate_risk_pct": audit.unfunded_probate_risk_pct,
            "risk_tier": audit.probate_risk_tier,
        },
        "at_risk_unfunded_assets": [
            {
                "asset_name": a.name,
                "category": a.category.value if hasattr(a.category, "value") else str(a.category),
                "value": a.estimated_value,
            }
            for a in audit.at_risk_assets
        ],
        "beneficiary_distribution_waterfall": [
            {
                "beneficiary": p.beneficiary_name,
                "share_pct": p.allocation_pct,
                "total_dollars": p.total_dollar_amount,
                "immediate_payout": p.immediate_payout,
                "milestone_count": len(p.milestone_tranches),
            }
            for p in waterfall.payouts
        ],
        "fiduciary_log_count": len(trust.fiduciary_logs),
    }


class EstateAdvisor:
    """AI Companion providing contextualized analysis over estate plans, trust schedules, and fiduciary duties."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str, trust: TrustEntity) -> EstateAdvisorResponse:
        context = build_estate_context(trust)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return EstateAdvisorResponse(
                    query=query,
                    executive_summary=data.get("executive_summary", ""),
                    fiduciary_findings=data.get("fiduciary_findings", []),
                    probate_risk_items=data.get("probate_risk_items", []),
                    action_items=data.get("action_items", []),
                    statutory_citations=data.get("statutory_citations", ""),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return EstateAdvisorResponse(
                    query=query,
                    executive_summary=raw_response,
                    fiduciary_findings=["Generated via custom LLM adapter."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> EstateAdvisorResponse:
        """Deterministic reasoning engine for offline estate analysis."""
        q = query.lower()
        val = context["total_estate_value_usd"]
        fund = context["funding_metrics"]
        unfunded = context["at_risk_unfunded_assets"]

        findings: list[str] = []
        risks: list[str] = []
        actions: list[str] = []
        citation = ""

        # Query Intent 1: Probate & Titling Risk
        if any(w in q for w in ["probate", "title", "unfunded", "deed", "risk", "pour over"]):
            summary = (
                f"Estate holds ${val:,.2f} in total assets across Schedule A. "
                f"Funding status is rated '{fund['risk_tier']}' with {fund['unfunded_probate_risk_pct']}% "
                f"(${fund['unfunded_probate_risk_usd']:,.2f}) at risk of probate court delays."
            )
            if unfunded:
                for a in unfunded:
                    risks.append(
                        f"Asset '{a['asset_name']}' (${a['value']:,.2f}) is not titled to the trust and relies on pour-over will."
                    )
                actions.append(
                    "Execute deed transfer / change of ownership to formally re-title real estate into the Trust."
                )
                actions.append(
                    "Update financial institution Transfer on Death (TOD) / Pay on Death (POD) beneficiary designations."
                )
            else:
                findings.append(
                    "All scheduled assets are formally titled to the trust or have direct beneficiary designations."
                )
            citation = "Uniform Probate Code (UPC) § 6-101; Restatement (Third) of Trusts § 86."

        # Query Intent 2: Waterfall / Distribution / Beneficiaries
        elif any(w in q for w in ["waterfall", "distribut", "beneficiar", "split", "payout", "age", "tranche"]):
            summary = f"Distribution waterfall models the division of ${val:,.2f} among named beneficiaries."
            for p in context["beneficiary_distribution_waterfall"]:
                findings.append(f"Beneficiary '{p['beneficiary']}': {p['share_pct']}% (${p['total_dollars']:,.2f}).")
                if p["milestone_count"] > 0:
                    findings.append(f"  → Payout staged across {p['milestone_count']} age milestone tranches.")
            actions.append("Ensure designated successor trustee has copy of current Schedule A and beneficiary roster.")
            citation = "Uniform Trust Code (UTC) § 801 (Duty to Administer Trust in Accordance with Terms)."

        # Query Intent 3: Fiduciary Duty & Trustee Responsibilities
        elif any(w in q for w in ["fiduciary", "trustee", "duty", "accounting", "incapacity", "successor"]):
            summary = (
                f"Current Trustee '{context['current_trustee']}' owes strict fiduciary duties of loyalty, "
                f"prudence, and impartiality under {context['jurisdiction']} law. Successor: '{context['successor_trustee']}'."
            )
            findings.append(f"Fiduciary audit trail contains {context['fiduciary_log_count']} logged action(s).")
            actions.append("Maintain contemporaneous accounting ledger of all trust disbursements and tax filings.")
            actions.append("Conduct annual asset re-titling and valuation review with legal counsel.")
            citation = "Uniform Prudent Investor Act (UPIA) § 2; UTC § 802 (Duty of Loyalty)."

        # Default Estate Overview
        else:
            summary = (
                f"Trust '{context['trust_name']}' ({context['trust_type']}) in {context['jurisdiction']}. "
                f"Total estate asset valuation: ${val:,.2f}. Funded: {fund['funded_to_trust_pct']}%."
            )
            findings.append(f"Probate exposure rating: {fund['risk_tier']}.")
            actions.append("Run 'trustguard asset audit' to inspect titling deficiencies.")
            citation = "General Fiduciary Standards & Estate Planning Best Practices."

        return EstateAdvisorResponse(
            query=query,
            executive_summary=summary,
            fiduciary_findings=findings,
            probate_risk_items=risks,
            action_items=actions,
            statutory_citations=citation,
        )
