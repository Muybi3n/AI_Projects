# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local storage manager for oncology chemotherapy cycles, toxicities, and dialysis logs.
"""

import json
from pathlib import Path
from typing import Any

from .models import (
    AccessSiteType,
    ChemoCycle,
    DialysisModality,
    DialysisSession,
    FluidIntakeLog,
    OncoRenalProfile,
    SpecialtyLabRecord,
    SymptomToxicityLog,
)

DEFAULT_DATA_DIR = Path.home() / ".oncorenal"


class SpecialtyStore:
    """Manages local JSON storage for specialty cancer and dialysis records."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.data_dir / "oncorenal_profile.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.profile_file.exists():
            default_prof = OncoRenalProfile(
                patient_name="Family Member",
                relationship="Parent",
                primary_oncology_dx="Oncology Care",
                primary_renal_dx="End-Stage Renal Disease (ESRD)",
                target_dry_weight_kg=68.0,
                daily_fluid_limit_ml=1000.0,
                access_type=AccessSiteType.AV_FISTULA,
            )
            self.save_profile(default_prof)

    def load_profile(self) -> OncoRenalProfile:
        try:
            with open(self.profile_file, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (OSError, json.JSONDecodeError, KeyError):
            return OncoRenalProfile()

    def save_profile(self, profile: OncoRenalProfile) -> None:
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def _deserialize(self, d: dict[str, Any]) -> OncoRenalProfile:
        cycles = [
            ChemoCycle(
                id=c["id"],
                regimen_name=c.get("regimen_name", "Standard Regimen"),
                cycle_number=int(c.get("cycle_number", 1)),
                total_planned_cycles=int(c.get("total_planned_cycles", 6)),
                infusion_date=c.get("infusion_date", ""),
                cycle_length_days=int(c.get("cycle_length_days", 21)),
                nadir_start_day=int(c.get("nadir_start_day", 7)),
                nadir_end_day=int(c.get("nadir_end_day", 14)),
                antiemetics_prescribed=c.get("antiemetics_prescribed", []),
                notes=c.get("notes", ""),
            )
            for c in d.get("chemo_cycles", [])
        ]

        toxicities = [
            SymptomToxicityLog(
                id=t["id"],
                date=t.get("date", ""),
                cycle_number=int(t.get("cycle_number", 1)),
                cycle_day=int(t.get("cycle_day", 1)),
                temperature_f=float(t.get("temperature_f", 98.6)),
                nausea_ctcae_grade=int(t.get("nausea_ctcae_grade", 0)),
                fatigue_ctcae_grade=int(t.get("fatigue_ctcae_grade", 0)),
                neuropathy_ctcae_grade=int(t.get("neuropathy_ctcae_grade", 0)),
                mucositis_mouth_sores_grade=int(t.get("mucositis_mouth_sores_grade", 0)),
                notes=t.get("notes", ""),
            )
            for t in d.get("toxicity_logs", [])
        ]

        sessions = [
            DialysisSession(
                id=s["id"],
                date=s.get("date", ""),
                modality=DialysisModality(s.get("modality", DialysisModality.IN_CENTER_HEMODIALYSIS.value)),
                pre_dialysis_weight_kg=float(s.get("pre_dialysis_weight_kg", 0.0)),
                post_dialysis_weight_kg=float(s.get("post_dialysis_weight_kg", 0.0)),
                pre_dialysis_bp_sys=int(s.get("pre_dialysis_bp_sys", 0)),
                pre_dialysis_bp_dia=int(s.get("pre_dialysis_bp_dia", 0)),
                post_dialysis_bp_sys=int(s.get("post_dialysis_bp_sys", 0)),
                post_dialysis_bp_dia=int(s.get("post_dialysis_bp_dia", 0)),
                ultrafiltration_removed_liters=float(s.get("ultrafiltration_removed_liters", 0.0)),
                kt_v_adequacy=float(s.get("kt_v_adequacy", 0.0)),
                access_site_bruit_thrill_normal=bool(s.get("access_site_bruit_thrill_normal", True)),
                cramping_or_hypotension=bool(s.get("cramping_or_hypotension", False)),
                notes=s.get("notes", ""),
            )
            for s in d.get("dialysis_sessions", [])
        ]

        fluid_logs = [
            FluidIntakeLog(
                id=f["id"],
                date=f.get("date", ""),
                fluid_intake_ml=float(f.get("fluid_intake_ml", 0.0)),
                potassium_mg=float(f.get("potassium_mg", 0.0)),
                phosphorus_mg=float(f.get("phosphorus_mg", 0.0)),
                sodium_mg=float(f.get("sodium_mg", 0.0)),
                phosphate_binders_taken_with_meals=bool(f.get("phosphate_binders_taken_with_meals", True)),
                notes=f.get("notes", ""),
            )
            for f in d.get("fluid_logs", [])
        ]

        specialty_labs = [
            SpecialtyLabRecord(
                id=lab["id"],
                date=lab.get("date", ""),
                white_blood_cells=float(lab.get("white_blood_cells", 0.0)),
                absolute_neutrophil_count_anc=float(lab.get("absolute_neutrophil_count_anc", 0.0)),
                platelets=float(lab.get("platelets", 0.0)),
                hemoglobin=float(lab.get("hemoglobin", 0.0)),
                serum_potassium=float(lab.get("serum_potassium", 0.0)),
                serum_phosphorus=float(lab.get("serum_phosphorus", 0.0)),
                serum_creatinine=float(lab.get("serum_creatinine", 0.0)),
                egfr=float(lab.get("egfr", 0.0)),
                bun=float(lab.get("bun", 0.0)),
                serum_albumin=float(lab.get("serum_albumin", 0.0)),
            )
            for lab in d.get("specialty_labs", [])
        ]

        return OncoRenalProfile(
            id=d.get("id", ""),
            patient_name=d.get("patient_name", "Family Member"),
            relationship=d.get("relationship", "Parent"),
            primary_oncology_dx=d.get("primary_oncology_dx", ""),
            primary_renal_dx=d.get("primary_renal_dx", ""),
            target_dry_weight_kg=float(d.get("target_dry_weight_kg", 70.0)),
            daily_fluid_limit_ml=float(d.get("daily_fluid_limit_ml", 1200.0)),
            access_type=AccessSiteType(d.get("access_type", AccessSiteType.AV_FISTULA.value)),
            chemo_cycles=cycles,
            toxicity_logs=toxicities,
            dialysis_sessions=sessions,
            fluid_logs=fluid_logs,
            specialty_labs=specialty_labs,
        )
