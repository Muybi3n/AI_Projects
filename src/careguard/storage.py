# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local storage manager for care recipients, medical history, doctor visits, and caregiver logs.
"""

import json
from pathlib import Path
from typing import Any

from .models import (
    CaregiverNote,
    CareRecipient,
    DailyVitalsLog,
    DoctorVisit,
    MedicationSchedule,
    NoteCategory,
    PhysicianContact,
    TimingSlot,
)

DEFAULT_DATA_DIR = Path.home() / ".careguard"


class CareStore:
    """Manages persistent JSON storage for care recipient medical profiles."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.data_dir / "care_profile.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.profile_file.exists():
            default_recipient = CareRecipient(
                full_name="Family Member",
                relationship="Parent",
                year_of_birth=1952,
                primary_diagnoses=["Hypertension", "Type 2 Diabetes"],
                allergies=["Penicillin"],
                code_status="Full Code",
            )
            self.save_recipient(default_recipient)

    def load_recipient(self) -> CareRecipient:
        try:
            with open(self.profile_file, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (OSError, json.JSONDecodeError, KeyError):
            return CareRecipient()

    def save_recipient(self, recipient: CareRecipient) -> None:
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(recipient.to_dict(), f, indent=2)

    def _deserialize(self, d: dict[str, Any]) -> CareRecipient:
        physicians = [
            PhysicianContact(
                id=p["id"],
                name=p["name"],
                specialty=p.get("specialty", "Primary Care"),
                clinic_or_hospital=p.get("clinic_or_hospital", ""),
                phone=p.get("phone", ""),
                email_or_portal=p.get("email_or_portal", ""),
                notes=p.get("notes", ""),
            )
            for p in d.get("physicians", [])
        ]

        doctor_visits = [
            DoctorVisit(
                id=v["id"],
                date=v.get("date", ""),
                physician_name=v.get("physician_name", ""),
                specialty=v.get("specialty", "Primary Care"),
                reason_for_visit=v.get("reason_for_visit", ""),
                physician_findings=v.get("physician_findings", ""),
                medication_changes=v.get("medication_changes", ""),
                orders_and_tests=v.get("orders_and_tests", ""),
                next_follow_up_date=v.get("next_follow_up_date", ""),
            )
            for v in d.get("doctor_visits", [])
        ]

        medications = [
            MedicationSchedule(
                id=m["id"],
                name=m["name"],
                dosage=m.get("dosage", ""),
                timing_slot=TimingSlot(m.get("timing_slot", TimingSlot.MORNING.value)),
                purpose=m.get("purpose", ""),
                prescribed_by=m.get("prescribed_by", ""),
                special_instructions=m.get("special_instructions", ""),
                is_active=bool(m.get("is_active", True)),
            )
            for m in d.get("medications", [])
        ]

        vitals_history = [
            DailyVitalsLog(
                id=vit["id"],
                timestamp=vit.get("timestamp", ""),
                systolic_bp=int(vit.get("systolic_bp", 0)),
                diastolic_bp=int(vit.get("diastolic_bp", 0)),
                heart_rate=int(vit.get("heart_rate", 0)),
                spo2_pct=float(vit.get("spo2_pct", 0.0)),
                blood_glucose=float(vit.get("blood_glucose", 0.0)),
                weight_lbs=float(vit.get("weight_lbs", 0.0)),
                temperature_f=float(vit.get("temperature_f", 0.0)),
                pain_level=int(vit.get("pain_level", 0)),
                confusion_or_cognitive_fog=bool(vit.get("confusion_or_cognitive_fog", False)),
                notes=vit.get("notes", ""),
            )
            for vit in d.get("vitals_history", [])
        ]

        caregiver_journal = [
            CaregiverNote(
                id=n["id"],
                timestamp=n.get("timestamp", ""),
                caregiver_name=n.get("caregiver_name", "Primary Caregiver"),
                category=NoteCategory(n.get("category", NoteCategory.OBSERVATION.value)),
                note_text=n.get("note_text", ""),
            )
            for n in d.get("caregiver_journal", [])
        ]

        return CareRecipient(
            id=d.get("id", ""),
            full_name=d.get("full_name", "Family Member"),
            relationship=d.get("relationship", "Parent"),
            year_of_birth=int(d.get("year_of_birth", 1950)),
            primary_diagnoses=d.get("primary_diagnoses", []),
            allergies=d.get("allergies", []),
            blood_type=d.get("blood_type", "Unknown"),
            code_status=d.get("code_status", "Full Code"),
            emergency_contact=d.get("emergency_contact", ""),
            preferred_hospital=d.get("preferred_hospital", ""),
            physicians=physicians,
            doctor_visits=doctor_visits,
            medications=medications,
            vitals_history=vitals_history,
            caregiver_journal=caregiver_journal,
        )
