# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Longitudinal clinical note timeline & chronological progress tracker.
"""

from dataclasses import dataclass, field
from typing import Any

from .models import CareRecipient


@dataclass
class TimelineEncounter:
    date: str
    physician: str
    specialty: str
    chief_complaint: str
    clinical_summary: str
    medications_altered: list[str] = field(default_factory=list)
    tests_requested: list[str] = field(default_factory=list)


@dataclass
class LongitudinalTimelineReport:
    patient_name: str
    total_encounters: int
    first_recorded_encounter: str
    latest_recorded_encounter: str
    encounters: list[TimelineEncounter] = field(default_factory=list)
    cumulative_diagnoses: list[str] = field(default_factory=list)
    active_medications: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_name": self.patient_name,
            "total_encounters": self.total_encounters,
            "first_recorded_encounter": self.first_recorded_encounter,
            "latest_recorded_encounter": self.latest_recorded_encounter,
            "encounters": [e.__dict__ for e in self.encounters],
            "cumulative_diagnoses": self.cumulative_diagnoses,
            "active_medications": self.active_medications,
        }


class ClinicalTimelineEngine:
    """Constructs longitudinal timelines of physician encounters and clinical readings."""

    @staticmethod
    def build_timeline(recipient: CareRecipient) -> LongitudinalTimelineReport:
        sorted_visits = sorted(recipient.doctor_visits, key=lambda v: v.date)
        encounters: list[TimelineEncounter] = []

        for v in sorted_visits:
            med_list = [c.strip() for c in v.medication_changes.split(",") if c.strip()] if v.medication_changes else []
            test_list = [t.strip() for t in v.orders_and_tests.split(",") if t.strip()] if v.orders_and_tests else []

            encounters.append(
                TimelineEncounter(
                    date=v.date,
                    physician=v.physician_name,
                    specialty=v.specialty,
                    chief_complaint=v.reason_for_visit or "Follow-up",
                    clinical_summary=v.physician_findings,
                    medications_altered=med_list,
                    tests_requested=test_list,
                )
            )

        first_date = sorted_visits[0].date if sorted_visits else "N/A"
        latest_date = sorted_visits[-1].date if sorted_visits else "N/A"

        active_meds = [f"{m.name} ({m.dosage})" for m in recipient.medications if m.is_active]

        return LongitudinalTimelineReport(
            patient_name=recipient.full_name,
            total_encounters=len(encounters),
            first_recorded_encounter=first_date,
            latest_recorded_encounter=latest_date,
            encounters=encounters,
            cumulative_diagnoses=recipient.primary_diagnoses,
            active_medications=active_meds,
        )
