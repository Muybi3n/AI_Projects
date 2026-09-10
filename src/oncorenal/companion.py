# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI Oncology & Renal Specialty Companion: Context compilation, protocol queries, and LLM adapters.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .dialysis import DialysisEngine
from .models import OncoRenalProfile
from .oncology import OncologyEngine


@dataclass
class SpecialtyAdvisorResponse:
    query: str
    clinical_summary: str
    oncology_protocols: list[str] = field(default_factory=list)
    dialysis_and_fluid_guidelines: list[str] = field(default_factory=list)
    urgent_red_flags: list[str] = field(default_factory=list)
    caregiver_specialty_checklist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "clinical_summary": self.clinical_summary,
            "oncology_protocols": self.oncology_protocols,
            "dialysis_and_fluid_guidelines": self.dialysis_and_fluid_guidelines,
            "urgent_red_flags": self.urgent_red_flags,
            "caregiver_specialty_checklist": self.caregiver_specialty_checklist,
        }


def build_specialty_context(profile: OncoRenalProfile) -> dict[str, Any]:
    """Compile structured, PII-sanitized specialty oncology & dialysis state for LLM reasoning."""
    nadir = OncologyEngine.get_current_nadir_status(profile)
    onco_alerts = OncologyEngine.audit_oncology_toxicities(profile)
    idwg = DialysisEngine.calculate_idwg(profile)
    renal_alerts = DialysisEngine.audit_renal_safety(profile)

    return {
        "patient_relationship": profile.relationship,
        "primary_oncology_dx": profile.primary_oncology_dx or "Oncology Patient",
        "primary_renal_dx": profile.primary_renal_dx or "Renal / Dialysis Patient",
        "target_dry_weight_kg": profile.target_dry_weight_kg,
        "daily_fluid_limit_ml": profile.daily_fluid_limit_ml,
        "chemo_nadir_status": nadir.__dict__ if nadir else None,
        "interdialytic_weight_gain": idwg.__dict__ if idwg else None,
        "active_oncology_alerts": [a.__dict__ for a in onco_alerts],
        "active_renal_alerts": [r.__dict__ for r in renal_alerts],
        "total_toxicity_logs": len(profile.toxicity_logs),
        "total_dialysis_sessions": len(profile.dialysis_sessions),
    }


class SpecialtyCareCompanion:
    """AI Companion providing protocol guidance for cancer chemotherapy and renal dialysis."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str, profile: OncoRenalProfile) -> SpecialtyAdvisorResponse:
        context = build_specialty_context(profile)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return SpecialtyAdvisorResponse(
                    query=query,
                    clinical_summary=data.get("clinical_summary", ""),
                    oncology_protocols=data.get("oncology_protocols", []),
                    dialysis_and_fluid_guidelines=data.get("dialysis_and_fluid_guidelines", []),
                    urgent_red_flags=data.get("urgent_red_flags", []),
                    caregiver_specialty_checklist=data.get("caregiver_specialty_checklist", []),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return SpecialtyAdvisorResponse(
                    query=query,
                    clinical_summary=raw_response,
                    caregiver_specialty_checklist=["Generated via custom LLM adapter."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> SpecialtyAdvisorResponse:
        """Deterministic reasoning engine for offline oncology and dialysis care."""
        q = query.lower()
        nadir = context["chemo_nadir_status"]
        idwg = context["interdialytic_weight_gain"]
        onco_alerts = context["active_oncology_alerts"]
        renal_alerts = context["active_renal_alerts"]

        onco_proto: list[str] = []
        renal_proto: list[str] = []
        red_flags: list[str] = []
        checklist: list[str] = []

        for a in onco_alerts:
            red_flags.append(f"[{a['severity']}] {a['category']}: {a['message']} -> {a['action_required']}")

        for r in renal_alerts:
            red_flags.append(f"[{r['severity']}] {r['category']}: {r['message']} -> {r['action_required']}")

        # Query Intent 1: Chemotherapy / Nadir / Cancer Care
        is_onco_query = any(
            w in q
            for w in [
                "chemo",
                "cancer",
                "nadir",
                "infusion",
                "fever",
                "neutropen",
                "antiemetic",
                "zofran",
                "tumor",
                "oncolog",
            ]
        )
        # Query Intent 2: Dialysis / Fluid Restriction / Dry Weight
        is_renal_query = any(
            w in q
            for w in [
                "dialysis",
                "fluid",
                "dry weight",
                "idwg",
                "potassium",
                "phosphorus",
                "binder",
                "fistula",
                "renal",
                "kidney",
                "ultrafiltration",
            ]
        )

        # Combined intake/fluid queries touch both domains
        if ("fluid" in q or "intake" in q or "water" in q) and ("chemo" in q or "nausea" in q):
            is_onco_query = True
            is_renal_query = True

        if is_onco_query and is_renal_query:
            summary = (
                f"Integrated oncology + renal management plan for {context['patient_relationship']} "
                f"({context['primary_oncology_dx']} / {context['primary_renal_dx']}). "
            )
        elif is_onco_query:
            summary = f"Oncology management for {context['patient_relationship']} ({context['primary_oncology_dx']}). "
        elif is_renal_query:
            summary = (
                f"Renal dialysis management for {context['patient_relationship']} ({context['primary_renal_dx']}). "
            )
        else:
            summary = (
                f"Integrated specialty care overview: Managing {context['primary_oncology_dx']} and "
                f"{context['primary_renal_dx']}. Total active red flags: {len(red_flags)}."
            )

        if is_onco_query:
            if nadir:
                summary += f"Currently on Cycle {nadir['cycle_number']} ({nadir['regimen_name']}), Day {nadir['current_cycle_day']}. "
                onco_proto.append(nadir["precaution_advisory"])
                if nadir["is_in_nadir_window"]:
                    onco_proto.append("Strict food safety: no unpasteurized dairy, raw meats, or unwashed produce.")
            else:
                onco_proto.append("No active chemotherapy cycle scheduled.")

            checklist.append("Take antiemetic medications (Zofran/Dexamethasone) proactively before nausea escalates.")
            checklist.append("Check oral cavity daily for signs of mucositis / mouth ulcers.")
            checklist.append("Take oral temperature twice daily. Seek immediate emergency care for T >= 100.4°F.")

        if is_renal_query:
            summary += (
                f"Target dry weight: {context['target_dry_weight_kg']} kg | "
                f"Daily fluid limit: {context['daily_fluid_limit_ml']} mL. "
            )
            if idwg:
                renal_proto.append(
                    f"Interdialytic Weight Gain: +{idwg['interdialytic_weight_gain_lbs']} lbs ({idwg['weight_gain_pct_of_dry_weight']}%) - Status: {idwg['fluid_overload_tier']}."
                )
                renal_proto.append(idwg["clinical_risk_note"])
            checklist.append("Take phosphate binders (Renvela / PhosLo) strictly with the first bite of every meal.")
            checklist.append(
                "Check AV fistula / graft daily for healthy 'thrill' (vibration) and 'bruit' (whooshing sound)."
            )
            checklist.append("Use ice chips or small spray bottles to manage thirst without exceeding daily fluid cap.")

        if not is_onco_query and not is_renal_query:
            checklist.append("Review 'oncorenal chemo nadir' to monitor immune white blood cell nadir timing.")
            checklist.append("Review 'oncorenal dialysis idwg' to audit fluid accumulation between dialysis sessions.")

        return SpecialtyAdvisorResponse(
            query=query,
            clinical_summary=summary,
            oncology_protocols=onco_proto,
            dialysis_and_fluid_guidelines=renal_proto,
            urgent_red_flags=red_flags,
            caregiver_specialty_checklist=checklist,
        )
