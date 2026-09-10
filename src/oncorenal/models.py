# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for oncology chemotherapy regimens, toxicities, renal dialysis sessions, and fluid balances.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DialysisModality(str, Enum):
    IN_CENTER_HEMODIALYSIS = "in_center_hemodialysis"
    HOME_HEMODIALYSIS = "home_hemodialysis"
    PERITONEAL_DIALYSIS = "peritoneal_dialysis"


class AccessSiteType(str, Enum):
    AV_FISTULA = "av_fistula"
    AV_GRAFT = "av_graft"
    CENTRAL_VENOUS_CATHETER = "central_venous_catheter"
    PD_CATHETER = "pd_catheter"


@dataclass
class ChemoCycle:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    regimen_name: str = "Standard Protocol"  # e.g., FOLFOX, AC-T, R-CHOP, Carboplatin/Paclitaxel
    cycle_number: int = 1
    total_planned_cycles: int = 6
    infusion_date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    cycle_length_days: int = 21  # Standard 14, 21, or 28 day cycle
    nadir_start_day: int = 7
    nadir_end_day: int = 14
    antiemetics_prescribed: list[str] = field(default_factory=lambda: ["Ondansetron (Zofran)", "Dexamethasone"])
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SymptomToxicityLog:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    cycle_number: int = 1
    cycle_day: int = 1
    temperature_f: float = 98.6  # Critical for neutropenic fever screening (>= 100.4F is an emergency)
    nausea_ctcae_grade: int = 0  # 0: None, 1: Mild, 2: Moderate, 3: Severe, 4: Life-threatening
    fatigue_ctcae_grade: int = 0  # 0: Normal energy, 1: Mild, 2: Moderate, 3: Bedridden >50% of day
    neuropathy_ctcae_grade: int = 0  # 0: None, 1: Tingling, 2: Sensory loss affecting function, 3: Severe
    mucositis_mouth_sores_grade: int = (
        0  # 0: None, 1: Painless ulcers, 2: Painful ulcers/soft diet, 3: Liquid diet only
    )
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DialysisSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    modality: DialysisModality = DialysisModality.IN_CENTER_HEMODIALYSIS
    pre_dialysis_weight_kg: float = 0.0
    post_dialysis_weight_kg: float = 0.0
    pre_dialysis_bp_sys: int = 0
    pre_dialysis_bp_dia: int = 0
    post_dialysis_bp_sys: int = 0
    post_dialysis_bp_dia: int = 0
    ultrafiltration_removed_liters: float = 0.0
    kt_v_adequacy: float = 0.0  # Standard dialysis adequacy clearance target >= 1.2 for HD, >= 1.7 for PD
    access_site_bruit_thrill_normal: bool = True
    cramping_or_hypotension: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["modality"] = self.modality.value if isinstance(self.modality, Enum) else self.modality
        return d


@dataclass
class FluidIntakeLog:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    fluid_intake_ml: float = 0.0  # e.g. 1000 mL daily limit
    potassium_mg: float = 0.0  # e.g. < 2000 mg limit
    phosphorus_mg: float = 0.0  # e.g. < 800-1000 mg limit
    sodium_mg: float = 0.0  # e.g. < 2000 mg limit
    phosphate_binders_taken_with_meals: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SpecialtyLabRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    # Oncology CBC
    white_blood_cells: float = 0.0  # x10^3/uL (Normal 4.0 - 11.0)
    absolute_neutrophil_count_anc: float = 0.0  # /uL (Normal > 1500; < 500 = Severe Neutropenia)
    platelets: float = 0.0  # x10^3/uL (Normal 150 - 450)
    hemoglobin: float = 0.0  # g/dL (Normal 12.0 - 17.0)
    # Renal Panel
    serum_potassium: float = 0.0  # mEq/L (Normal 3.5 - 5.0; > 5.5 = Hyperkalemia Alert)
    serum_phosphorus: float = 0.0  # mg/dL (Target in ESRD 3.5 - 5.5)
    serum_creatinine: float = 0.0  # mg/dL
    egfr: float = 0.0  # mL/min/1.73m2
    bun: float = 0.0  # mg/dL
    serum_albumin: float = 0.0  # g/dL (Target in ESRD >= 4.0 g/dL for protein nutrition)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OncoRenalProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    patient_name: str = "Family Member"
    relationship: str = "Parent"
    primary_oncology_dx: str = ""  # e.g. Colorectal Cancer, Breast Cancer, Lymphoma
    primary_renal_dx: str = ""  # e.g. End-Stage Renal Disease (ESRD), Stage 4 CKD
    target_dry_weight_kg: float = 70.0  # Baseline dry weight in kg
    daily_fluid_limit_ml: float = 1200.0  # Standard fluid restriction in mL
    access_type: AccessSiteType = AccessSiteType.AV_FISTULA
    chemo_cycles: list[ChemoCycle] = field(default_factory=list)
    toxicity_logs: list[SymptomToxicityLog] = field(default_factory=list)
    dialysis_sessions: list[DialysisSession] = field(default_factory=list)
    fluid_logs: list[FluidIntakeLog] = field(default_factory=list)
    specialty_labs: list[SpecialtyLabRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "relationship": self.relationship,
            "primary_oncology_dx": self.primary_oncology_dx,
            "primary_renal_dx": self.primary_renal_dx,
            "target_dry_weight_kg": self.target_dry_weight_kg,
            "daily_fluid_limit_ml": self.daily_fluid_limit_ml,
            "access_type": self.access_type.value if isinstance(self.access_type, Enum) else self.access_type,
            "chemo_cycles": [c.to_dict() for c in self.chemo_cycles],
            "toxicity_logs": [t.to_dict() for t in self.toxicity_logs],
            "dialysis_sessions": [d.to_dict() for d in self.dialysis_sessions],
            "fluid_logs": [f.to_dict() for f in self.fluid_logs],
            "specialty_labs": [lab.to_dict() for lab in self.specialty_labs],
        }
