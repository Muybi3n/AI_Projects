# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for health biomarkers, medications, wearable telemetry, and safety alerts.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class BiomarkerCategory(str, Enum):
    LIPID_PANEL = "lipid_panel"
    METABOLIC_GLYCEMIC = "metabolic_glycemic"
    HORMONAL_ENDOCRINE = "hormonal_endocrine"
    INFLAMMATORY_CARDIO = "inflammatory_cardio"
    KIDNEY_LIVER_RENAL = "kidney_liver_renal"
    VITAMINS_MINERALS = "vitamins_minerals"
    COMPLETE_BLOOD_COUNT = "complete_blood_count"


class BiomarkerStatus(str, Enum):
    NORMAL = "normal"
    OPTIMAL = "optimal"
    BORDERLINE_LOW = "borderline_low"
    BORDERLINE_HIGH = "borderline_high"
    CRITICALLY_LOW = "critically_low"
    CRITICALLY_HIGH = "critically_high"


class InteractionSeverity(str, Enum):
    MILD_CAUTION = "mild_caution"
    MODERATE = "moderate"
    SEVERE = "severe"
    CONTRAINDICATED = "contraindicated"


@dataclass
class BiomarkerRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: BiomarkerCategory = BiomarkerCategory.LIPID_PANEL
    value: float = 0.0
    unit: str = "mg/dL"
    ref_low: float = 0.0
    ref_high: float = 0.0
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    notes: str = ""

    @property
    def status(self) -> BiomarkerStatus:
        if self.ref_low == 0.0 and self.ref_high == 0.0:
            return BiomarkerStatus.NORMAL

        if self.value < (self.ref_low * 0.7):
            return BiomarkerStatus.CRITICALLY_LOW
        elif self.value < self.ref_low:
            return BiomarkerStatus.BORDERLINE_LOW
        elif self.ref_high > 0 and self.value > (self.ref_high * 1.3):
            return BiomarkerStatus.CRITICALLY_HIGH
        elif self.ref_high > 0 and self.value > self.ref_high:
            return BiomarkerStatus.BORDERLINE_HIGH
        return BiomarkerStatus.OPTIMAL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value if isinstance(self.category, Enum) else self.category
        d["status"] = self.status.value
        return d


@dataclass
class MedicationItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    dosage: str = ""  # e.g., "10mg"
    frequency: str = "daily"  # daily, twice_daily, as_needed
    is_supplement: bool = False
    active_compounds: list[str] = field(default_factory=list)
    start_date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WearableTelemetryPoint:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    resting_heart_rate: float = 0.0  # bpm
    hrv_rmssd: float = 0.0  # ms
    sleep_duration_hours: float = 0.0  # hours
    deep_sleep_pct: float = 0.0  # %
    rem_sleep_pct: float = 0.0  # %
    sleep_score: float = 0.0  # 0-100
    vo2_max: float = 0.0  # mL/kg/min
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergencyProfile:
    blood_type: str = "Unknown"
    allergies: list[str] = field(default_factory=list)
    chronic_conditions: list[str] = field(default_factory=list)
    emergency_contacts: list[str] = field(default_factory=list)
    advance_directive_recorded: bool = False
    organ_donor: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InteractionAlert:
    item_a: str
    item_b: str
    severity: InteractionSeverity
    mechanism: str
    clinical_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_a": self.item_a,
            "item_b": self.item_b,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "mechanism": self.mechanism,
            "clinical_note": self.clinical_note,
        }


@dataclass
class HealthProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_label: str = "Primary User"
    biological_sex: str = "unspecified"
    year_of_birth: int = 1990
    biomarkers: list[BiomarkerRecord] = field(default_factory=list)
    medications: list[MedicationItem] = field(default_factory=list)
    telemetry: list[WearableTelemetryPoint] = field(default_factory=list)
    emergency: EmergencyProfile = field(default_factory=EmergencyProfile)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_label": self.user_label,
            "biological_sex": self.biological_sex,
            "year_of_birth": self.year_of_birth,
            "biomarkers": [b.to_dict() for b in self.biomarkers],
            "medications": [m.to_dict() for m in self.medications],
            "telemetry": [t.to_dict() for t in self.telemetry],
            "emergency": self.emergency.to_dict(),
        }
