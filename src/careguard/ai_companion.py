# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
AI Caregiver Medical Advocate Companion: Context compilation, doctor visit prep, and LLM adapters.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .engine import CareEngine
from .models import CareRecipient


@dataclass
class CareAdvisorResponse:
    query: str
    advocate_summary: str
    doctor_visit_takeaways: list[str] = field(default_factory=list)
    vitals_red_flags: list[str] = field(default_factory=list)
    questions_for_specialist: list[str] = field(default_factory=list)
    caregiver_action_plan: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "advocate_summary": self.advocate_summary,
            "doctor_visit_takeaways": self.doctor_visit_takeaways,
            "vitals_red_flags": self.vitals_red_flags,
            "questions_for_specialist": self.questions_for_specialist,
            "caregiver_action_plan": self.caregiver_action_plan,
        }


def build_care_context(recipient: CareRecipient) -> dict[str, Any]:
    """Compile structured, PII-sanitized caregiving state for LLM reasoning."""
    briefing = CareEngine.generate_physician_briefing(recipient)
    pillbox = CareEngine.get_pillbox_schedule(recipient)

    return {
        "patient_relationship": recipient.relationship,
        "age": briefing.age,
        "diagnoses": recipient.primary_diagnoses,
        "allergies": recipient.allergies,
        "code_status": recipient.code_status,
        "physician_count": len(recipient.physicians),
        "doctor_visits_logged": len(recipient.doctor_visits),
        "recent_doctor_visits": [
            {
                "date": v.date,
                "physician": v.physician_name,
                "specialty": v.specialty,
                "reason": v.reason_for_visit,
                "findings": v.physician_findings,
                "changes_ordered": v.medication_changes,
            }
            for v in recipient.doctor_visits[-3:]
        ],
        "active_medication_count": len([m for m in recipient.medications if m.is_active]),
        "pillbox_schedule": pillbox,
        "vitals_averages": briefing.recent_vitals_summary,
        "flagged_vitals_anomalies": [
            {
                "time": a.timestamp,
                "metric": a.vital_metric,
                "value": str(a.observed_value),
                "severity": a.severity,
                "reason": a.clinical_rationale,
            }
            for a in briefing.flagged_anomalies
        ],
        "recent_caregiver_journal": briefing.recent_caregiver_observations,
    }


class CareCompanion:
    """AI Companion providing medical coordination and appointment prep for family caregivers."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str, recipient: CareRecipient) -> CareAdvisorResponse:
        context = build_care_context(recipient)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return CareAdvisorResponse(
                    query=query,
                    advocate_summary=data.get("advocate_summary", ""),
                    doctor_visit_takeaways=data.get("doctor_visit_takeaways", []),
                    vitals_red_flags=data.get("vitals_red_flags", []),
                    questions_for_specialist=data.get("questions_for_specialist", []),
                    caregiver_action_plan=data.get("caregiver_action_plan", []),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return CareAdvisorResponse(
                    query=query,
                    advocate_summary=raw_response,
                    questions_for_specialist=["Generated via custom LLM adapter."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> CareAdvisorResponse:
        """Deterministic reasoning engine for offline caregiving assistance."""
        q = query.lower()
        diag = ", ".join(context["diagnoses"]) if context["diagnoses"] else "Chronic Care"
        anomalies = context["flagged_vitals_anomalies"]
        visits = context["recent_doctor_visits"]
        pillbox = context["pillbox_schedule"]

        takeaways: list[str] = []
        red_flags: list[str] = []
        questions: list[str] = []
        plan: list[str] = []

        for a in anomalies:
            red_flags.append(f"[{a['severity']}] {a['metric']} = {a['value']} -> {a['reason']}")

        # Query Intent 1: Doctor Visit Prep & Synthesis
        if any(
            w in q for w in ["doctor", "visit", "prep", "appointment", "specialist", "ask", "cardiolog", "neurolog"]
        ):
            summary = (
                f"Preparation briefing for {context['patient_relationship']} (Age {context['age']}), "
                f"diagnosed with {diag}. Total active medications: {context['active_medication_count']}."
            )
            if visits:
                last_v = visits[-1]
                takeaways.append(f"Last Visit ({last_v['date']} - {last_v['specialty']}): {last_v['findings']}")
                if last_v["changes_ordered"]:
                    takeaways.append(f"Changes Ordered: {last_v['changes_ordered']}")

            questions.append("Are current medication dosages aligned with recent renal and metabolic function?")
            questions.append("What specific symptoms should prompt an immediate call to your clinic vs an ER visit?")
            if red_flags:
                questions.append(
                    "Review home vitals log: several blood pressure/oxygen readings exceeded baseline limits."
                )
            plan.append(
                "Print or export 'careguard brief' to hand directly to the physician at the appointment check-in."
            )

        # Query Intent 2: Medications & Daily Care Schedule
        elif any(w in q for w in ["med", "pill", "schedule", "dose", "morning", "night", "give"]):
            summary = f"Active daily medication regimen contains {context['active_medication_count']} prescribed items across {len(pillbox)} timing slots."
            for slot, items in pillbox.items():
                med_names = ", ".join(f"{it['name']} ({it['dosage']})" for it in items)
                takeaways.append(f"{slot.capitalize()} Slot: {med_names}")
            plan.append("Ensure pillbox is loaded at the beginning of each week to prevent missed or double doses.")
            plan.append("Report any new dizziness, nausea, or lethargy following recent medication adjustments.")

        # Query Intent 3: Vitals & Emergency Warning Signs
        elif any(w in q for w in ["vital", "pressure", "oxygen", "spo2", "weight", "warning", "emergency", "red flag"]):
            summary = f"Vitals log analysis across recent entries for {context['patient_relationship']}."
            if red_flags:
                plan.append("Contact primary physician or on-call triage line regarding flagged vitals deviations.")
            else:
                takeaways.append("All recent vital signs fall within acceptable historical home monitoring thresholds.")
            plan.append("Continue daily morning blood pressure and pulse oximeter monitoring before medication.")

        # Default Overview
        else:
            summary = (
                f"Caregiving overview for {context['patient_relationship']} (Age {context['age']}). "
                f"Managing {len(context['diagnoses'])} condition(s) across {context['physician_count']} physician specialist(s)."
            )
            questions.append("Run 'careguard brief' to generate a consolidated 1-page visit sheet for doctors.")
            plan.append("Log daily vitals and caregiver shift notes regularly to track longitudinal recovery trends.")

        return CareAdvisorResponse(
            query=query,
            advocate_summary=summary,
            doctor_visit_takeaways=takeaways,
            vitals_red_flags=red_flags,
            questions_for_specialist=questions,
            caregiver_action_plan=plan,
        )
