# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local storage manager for personal health profiles, biomarkers, medications, and telemetry.
"""

import json
from pathlib import Path
from typing import Any

from .models import (
    BiomarkerCategory,
    BiomarkerRecord,
    EmergencyProfile,
    HealthProfile,
    MedicationItem,
    WearableTelemetryPoint,
)

DEFAULT_DATA_DIR = Path.home() / ".medcadence"


class HealthStore:
    """Manages local JSON storage for health telemetry and medical timelines."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.data_dir / "health_profile.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.profile_file.exists():
            default_profile = HealthProfile()
            self.save_profile(default_profile)

    def load_profile(self) -> HealthProfile:
        try:
            with open(self.profile_file, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (OSError, json.JSONDecodeError, KeyError):
            return HealthProfile()

    def save_profile(self, profile: HealthProfile) -> None:
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def _deserialize(self, d: dict[str, Any]) -> HealthProfile:
        biomarkers = [
            BiomarkerRecord(
                id=b["id"],
                name=b["name"],
                category=BiomarkerCategory(b.get("category", BiomarkerCategory.LIPID_PANEL.value)),
                value=float(b.get("value", 0.0)),
                unit=b.get("unit", "mg/dL"),
                ref_low=float(b.get("ref_low", 0.0)),
                ref_high=float(b.get("ref_high", 0.0)),
                date=b.get("date", ""),
                notes=b.get("notes", ""),
            )
            for b in d.get("biomarkers", [])
        ]

        medications = [
            MedicationItem(
                id=m["id"],
                name=m["name"],
                dosage=m.get("dosage", ""),
                frequency=m.get("frequency", "daily"),
                is_supplement=bool(m.get("is_supplement", False)),
                active_compounds=m.get("active_compounds", []),
                start_date=m.get("start_date", ""),
                notes=m.get("notes", ""),
            )
            for m in d.get("medications", [])
        ]

        telemetry = [
            WearableTelemetryPoint(
                id=t["id"],
                date=t.get("date", ""),
                resting_heart_rate=float(t.get("resting_heart_rate", 0.0)),
                hrv_rmssd=float(t.get("hrv_rmssd", 0.0)),
                sleep_duration_hours=float(t.get("sleep_duration_hours", 0.0)),
                deep_sleep_pct=float(t.get("deep_sleep_pct", 0.0)),
                rem_sleep_pct=float(t.get("rem_sleep_pct", 0.0)),
                sleep_score=float(t.get("sleep_score", 0.0)),
                vo2_max=float(t.get("vo2_max", 0.0)),
                step_count=int(t.get("step_count", 0)),
            )
            for t in d.get("telemetry", [])
        ]

        emergency_data = d.get("emergency", {})
        emergency = EmergencyProfile(
            blood_type=emergency_data.get("blood_type", "Unknown"),
            allergies=emergency_data.get("allergies", []),
            chronic_conditions=emergency_data.get("chronic_conditions", []),
            emergency_contacts=emergency_data.get("emergency_contacts", []),
            advance_directive_recorded=bool(emergency_data.get("advance_directive_recorded", False)),
            organ_donor=bool(emergency_data.get("organ_donor", False)),
        )

        return HealthProfile(
            id=d.get("id", ""),
            user_label=d.get("user_label", "Primary User"),
            biological_sex=d.get("biological_sex", "unspecified"),
            year_of_birth=int(d.get("year_of_birth", 1990)),
            biomarkers=biomarkers,
            medications=medications,
            telemetry=telemetry,
            emergency=emergency,
        )
