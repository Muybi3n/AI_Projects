# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Caregiver engine: Vitals anomaly auditing, medication pillbox schedule organization, and physician visit prep briefings.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .models import CareRecipient, TimingSlot


@dataclass
class VitalsAnomaly:
    timestamp: str
    vital_metric: str
    observed_value: Any
    severity: str  # "URGENT_ATTENTION", "WARNING", "EVALUATE"
    clinical_rationale: str


@dataclass
class PhysicianBriefing:
    patient_name: str
    age: int
    relationship: str
    primary_diagnoses: list[str]
    allergies: list[str]
    code_status: str
    active_medications: list[dict[str, str]]
    recent_vitals_summary: dict[str, Any]
    flagged_anomalies: list[VitalsAnomaly]
    recent_caregiver_observations: list[str]
    recommended_discussion_points: list[str] = field(default_factory=list)


class CareEngine:
    """Computes vitals anomalies, pillbox schedules, and physician appointment briefings."""

    @staticmethod
    def audit_vitals(recipient: CareRecipient) -> list[VitalsAnomaly]:
        """Scan historical vitals logs for red-flag deviations."""
        anomalies: list[VitalsAnomaly] = []
        if not recipient.vitals_history:
            return anomalies

        sorted_vitals = sorted(recipient.vitals_history, key=lambda v: v.timestamp)

        for idx, v in enumerate(sorted_vitals):
            # Blood Pressure checks
            if v.systolic_bp >= 180 or v.diastolic_bp >= 120:
                anomalies.append(
                    VitalsAnomaly(
                        timestamp=v.timestamp,
                        vital_metric="Blood Pressure",
                        observed_value=f"{v.systolic_bp}/{v.diastolic_bp} mmHg",
                        severity="URGENT_ATTENTION",
                        clinical_rationale="Hypertensive crisis threshold (>180/120 mmHg). Evaluate for emergency medical care.",
                    )
                )
            elif (0 < v.systolic_bp < 90) or (0 < v.diastolic_bp < 60):
                anomalies.append(
                    VitalsAnomaly(
                        timestamp=v.timestamp,
                        vital_metric="Blood Pressure",
                        observed_value=f"{v.systolic_bp}/{v.diastolic_bp} mmHg",
                        severity="WARNING",
                        clinical_rationale="Hypotension / low blood pressure risk. Elevated fall risk upon standing (orthostasis).",
                    )
                )

            # Oxygen Saturation (SpO2)
            if 0 < v.spo2_pct < 92.0:
                anomalies.append(
                    VitalsAnomaly(
                        timestamp=v.timestamp,
                        vital_metric="Oxygen Saturation (SpO2)",
                        observed_value=f"{v.spo2_pct}%",
                        severity="URGENT_ATTENTION",
                        clinical_rationale="Hypoxia threshold (<92% SpO2). Check supplemental oxygen or contact prescribing doctor.",
                    )
                )

            # Weight Fluid Retention Check (Congestive Heart Failure indicator)
            if v.weight_lbs > 0 and idx > 0:
                prev = sorted_vitals[idx - 1]
                if prev.weight_lbs > 0:
                    weight_gain = v.weight_lbs - prev.weight_lbs
                    if weight_gain >= 3.0:
                        anomalies.append(
                            VitalsAnomaly(
                                timestamp=v.timestamp,
                                vital_metric="Weight Gain (Fluid Retention)",
                                observed_value=f"+{weight_gain:.1f} lbs",
                                severity="WARNING",
                                clinical_rationale="Rapid weight gain (>3 lbs in recent readings). Possible fluid retention / heart failure exacerbation.",
                            )
                        )

            # Cognitive Confusion Episode
            if v.confusion_or_cognitive_fog:
                anomalies.append(
                    VitalsAnomaly(
                        timestamp=v.timestamp,
                        vital_metric="Cognitive Status",
                        observed_value="Acute Confusion / Brain Fog Flagged",
                        severity="WARNING",
                        clinical_rationale="Sudden cognitive change. Screen for UTI, medication side effect, or electrolyte imbalance.",
                    )
                )

        return anomalies

    @staticmethod
    def get_pillbox_schedule(recipient: CareRecipient) -> dict[str, list[dict[str, str]]]:
        """Group active medications into Morning, Noon, Evening, and Bedtime slots."""
        schedule: dict[str, list[dict[str, str]]] = defaultdict(list)
        for m in recipient.medications:
            if not m.is_active:
                continue
            slot_key = m.timing_slot.value if isinstance(m.timing_slot, TimingSlot) else str(m.timing_slot)
            schedule[slot_key].append(
                {
                    "name": m.name,
                    "dosage": m.dosage,
                    "purpose": m.purpose,
                    "instructions": m.special_instructions,
                    "prescribed_by": m.prescribed_by,
                }
            )
        return dict(schedule)

    @staticmethod
    def generate_physician_briefing(
        recipient: CareRecipient,
        specialty_filter: str | None = None,
    ) -> PhysicianBriefing:
        """Compile a concise 1-page clinical summary for an upcoming specialist or doctor visit."""
        anomalies = CareEngine.audit_vitals(recipient)
        recent_anomalies = anomalies[-5:] if anomalies else []

        active_meds = [
            {
                "name": m.name,
                "dosage": m.dosage,
                "timing": m.timing_slot.value if isinstance(m.timing_slot, TimingSlot) else str(m.timing_slot),
                "purpose": m.purpose,
                "prescribed_by": m.prescribed_by,
            }
            for m in recipient.medications
            if m.is_active
        ]

        # Recent vitals statistics
        vitals_summary: dict[str, Any] = {}
        if recipient.vitals_history:
            recent_v = recipient.vitals_history[-7:]  # past 7 entries
            avg_sys = sum(v.systolic_bp for v in recent_v if v.systolic_bp > 0) / max(
                1, sum(1 for v in recent_v if v.systolic_bp > 0)
            )
            avg_dia = sum(v.diastolic_bp for v in recent_v if v.diastolic_bp > 0) / max(
                1, sum(1 for v in recent_v if v.diastolic_bp > 0)
            )
            avg_hr = sum(v.heart_rate for v in recent_v if v.heart_rate > 0) / max(
                1, sum(1 for v in recent_v if v.heart_rate > 0)
            )
            avg_spo2 = sum(v.spo2_pct for v in recent_v if v.spo2_pct > 0) / max(
                1, sum(1 for v in recent_v if v.spo2_pct > 0)
            )

            vitals_summary = {
                "recent_reading_count": len(recent_v),
                "avg_blood_pressure": f"{avg_sys:.0f}/{avg_dia:.0f} mmHg" if avg_sys > 0 else "N/A",
                "avg_heart_rate": f"{avg_hr:.0f} bpm" if avg_hr > 0 else "N/A",
                "avg_spo2": f"{avg_spo2:.1f}%" if avg_spo2 > 0 else "N/A",
            }

        # Caregiver recent notes
        recent_notes = [f"[{n.timestamp[:10]}] {n.note_text}" for n in recipient.caregiver_journal[-5:]]

        # Discussion questions for the doctor
        discussion: list[str] = []
        if recent_anomalies:
            discussion.append("Review recent vitals deviations flagged in the home monitoring log.")
        if any("confusion" in n.lower() for n in recent_notes):
            discussion.append(
                "Evaluate recent episodes of confusion/memory fog for underlying causes (UTI, medication interaction)."
            )
        discussion.append(
            "Review complete medication roster to verify if any dosages can be deprescribed or simplified."
        )

        return PhysicianBriefing(
            patient_name=recipient.full_name,
            age=2026 - recipient.year_of_birth,
            relationship=recipient.relationship,
            primary_diagnoses=recipient.primary_diagnoses,
            allergies=recipient.allergies,
            code_status=recipient.code_status,
            active_medications=active_meds,
            recent_vitals_summary=vitals_summary,
            flagged_anomalies=recent_anomalies,
            recent_caregiver_observations=recent_notes,
            recommended_discussion_points=discussion,
        )
