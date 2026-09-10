# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI Healthcare Companion: Clinical biomarker synthesis, medication safety queries, and LLM adapters.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .interactions import InteractionSafetyEngine
from .labs import BiomarkerLabEngine
from .models import HealthProfile


@dataclass
class HealthAdvisorResponse:
    query: str
    clinical_synthesis: str
    abnormal_biomarkers: list[str] = field(default_factory=list)
    medication_safety_flags: list[str] = field(default_factory=list)
    questions_for_physician: list[str] = field(default_factory=list)
    lifestyle_considerations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "clinical_synthesis": self.clinical_synthesis,
            "abnormal_biomarkers": self.abnormal_biomarkers,
            "medication_safety_flags": self.medication_safety_flags,
            "questions_for_physician": self.questions_for_physician,
            "lifestyle_considerations": self.lifestyle_considerations,
        }


def build_health_context(profile: HealthProfile) -> dict[str, Any]:
    """Compile structured, PII-sanitized health state for LLM reasoning."""
    trends = BiomarkerLabEngine.analyze_trends(profile)
    interactions = InteractionSafetyEngine.audit_profile(profile)

    return {
        "user_age": 2026 - profile.year_of_birth,
        "biological_sex": profile.biological_sex,
        "total_biomarkers_logged": len(profile.biomarkers),
        "biomarker_trends": [
            {
                "biomarker": t.name,
                "latest_value": t.latest_value,
                "status": t.latest_status.value if hasattr(t.latest_status, "value") else str(t.latest_status),
                "unit": t.unit,
                "historical_readings": t.historical_count,
                "delta_pct": t.delta_pct,
            }
            for t in trends
        ],
        "active_medications": [
            {"name": m.name, "dosage": m.dosage, "frequency": m.frequency, "is_supplement": m.is_supplement}
            for m in profile.medications
        ],
        "interaction_alerts": [
            {"item_a": i.item_a, "item_b": i.item_b, "severity": i.severity.value, "note": i.clinical_note}
            for i in interactions
        ],
        "emergency_summary": {
            "blood_type": profile.emergency.blood_type,
            "allergies_count": len(profile.emergency.allergies),
            "chronic_conditions_count": len(profile.emergency.chronic_conditions),
        },
    }


class HealthAdvisor:
    """AI Companion providing contextualized analysis over health biomarkers, telemetry, and safety interactions."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str, profile: HealthProfile) -> HealthAdvisorResponse:
        context = build_health_context(profile)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return HealthAdvisorResponse(
                    query=query,
                    clinical_synthesis=data.get("clinical_synthesis", ""),
                    abnormal_biomarkers=data.get("abnormal_biomarkers", []),
                    medication_safety_flags=data.get("medication_safety_flags", []),
                    questions_for_physician=data.get("questions_for_physician", []),
                    lifestyle_considerations=data.get("lifestyle_considerations", []),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return HealthAdvisorResponse(
                    query=query,
                    clinical_synthesis=raw_response,
                    questions_for_physician=["Generated via custom LLM adapter."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> HealthAdvisorResponse:
        """Deterministic reasoning engine for offline health and lab analysis."""
        q = query.lower()
        trends = context["biomarker_trends"]
        meds = context["active_medications"]
        alerts = context["interaction_alerts"]

        out_of_range = [t for t in trends if "optimal" not in t["status"].lower() and "normal" not in t["status"].lower()]
        abnormal_list: list[str] = []
        safety_flags: list[str] = []
        questions: list[str] = []
        lifestyle: list[str] = []

        for o in out_of_range:
            abnormal_list.append(f"{o['biomarker']}: {o['latest_value']} {o['unit']} (Status: {o['status']})")

        for a in alerts:
            safety_flags.append(f"[{a['severity'].upper()}] {a['item_a']} + {a['item_b']} -> {a['note']}")

        # Query Intent 1: Labs & Bloodwork
        if any(w in q for w in ["lab", "blood", "cholesterol", "glucose", "hba1c", "biomarker", "test"]):
            synthesis = (
                f"Health record contains {len(trends)} tracked lab biomarker(s). "
                f"Currently, {len(out_of_range)} biomarker(s) fall outside standard reference ranges."
            )
            if out_of_range:
                questions.append("What follow-up testing schedule is appropriate for out-of-range biomarkers?")
                questions.append("Are there specific dietary or lifestyle interventions recommended before pharmacological changes?")
            else:
                lifestyle.append("All logged biomarkers remain within standard physiological reference ranges.")
            lifestyle.append("Maintain routine annual comprehensive metabolic and lipid panel screening.")

        # Query Intent 2: Medications & Interactions
        elif any(w in q for w in ["med", "drug", "supplement", "interaction", "pill", "safe"]):
            synthesis = (
                f"Current regimen contains {len(meds)} active medication(s) and supplement(s). "
                f"Safety audit flagged {len(alerts)} potential clinical interaction(s)."
            )
            if alerts:
                questions.append("Should medication administration timing be spaced to avoid absorption antagonism?")
                questions.append("Is a dose titration or substitute compound appropriate to eliminate interaction risk?")
            else:
                lifestyle.append("No known contraindications or severe drug-drug interactions detected.")

        # Default Overview
        else:
            synthesis = (
                f"Health profile overview: {len(meds)} active medications, {len(trends)} tracked biomarkers "
                f"({len(out_of_range)} out-of-range), and {len(alerts)} interaction warnings."
            )
            questions.append("Please review my consolidated health summary during our next scheduled consultation.")
            lifestyle.append("Continue tracking longitudinal lab changes to identify subtle multi-year metabolic shifts.")

        return HealthAdvisorResponse(
            query=query,
            clinical_synthesis=synthesis,
            abnormal_biomarkers=abnormal_list,
            medication_safety_flags=safety_flags,
            questions_for_physician=questions,
            lifestyle_considerations=lifestyle,
        )
