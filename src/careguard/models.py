# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for care recipients, physician contacts, doctor visits, daily vitals, and caregiver notes.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TimingSlot(str, Enum):
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"
    BEDTIME = "bedtime"
    AS_NEEDED = "as_needed"


class NoteCategory(str, Enum):
    OBSERVATION = "observation"
    SYMPTOM = "symptom"
    INCIDENT_FALL = "incident_fall"
    FOOD_FLUID = "food_fluid"
    CAREGIVER_HANDOFF = "caregiver_handoff"


@dataclass
class PhysicianContact:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    specialty: str = "Primary Care"  # Cardiology, Neurology, Oncology, Nephrology, etc.
    clinic_or_hospital: str = ""
    phone: str = ""
    email_or_portal: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DoctorVisit:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    physician_name: str = ""
    specialty: str = "Primary Care"
    reason_for_visit: str = ""
    physician_findings: str = ""
    medication_changes: str = ""
    orders_and_tests: str = ""
    next_follow_up_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MedicationSchedule:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    dosage: str = ""  # e.g., "50mg"
    timing_slot: TimingSlot = TimingSlot.MORNING
    purpose: str = ""  # e.g., "Blood pressure control"
    prescribed_by: str = ""  # e.g., "Dr. Smith (Cardiology)"
    special_instructions: str = ""  # e.g., "Take with food, do not crush"
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["timing_slot"] = self.timing_slot.value if isinstance(self.timing_slot, Enum) else self.timing_slot
        return d


@dataclass
class DailyVitalsLog:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    systolic_bp: int = 0  # mmHg
    diastolic_bp: int = 0  # mmHg
    heart_rate: int = 0  # bpm
    spo2_pct: float = 0.0  # % (Pulse Oximeter)
    blood_glucose: float = 0.0  # mg/dL
    weight_lbs: float = 0.0  # lbs (Critical for congestive heart failure fluid check)
    temperature_f: float = 0.0  # Fahrenheit
    pain_level: int = 0  # 0 to 10
    confusion_or_cognitive_fog: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CaregiverNote:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    caregiver_name: str = "Primary Caregiver"
    category: NoteCategory = NoteCategory.OBSERVATION
    note_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value if isinstance(self.category, Enum) else self.category
        return d


@dataclass
class CareRecipient:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    full_name: str = "Family Member"
    relationship: str = "Parent"  # Mother, Father, Grandparent, Spouse
    year_of_birth: int = 1950
    primary_diagnoses: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    blood_type: str = "Unknown"
    code_status: str = "Full Code"  # Full Code, DNR (Do Not Resuscitate), POLST
    emergency_contact: str = ""
    preferred_hospital: str = ""
    physicians: list[PhysicianContact] = field(default_factory=list)
    doctor_visits: list[DoctorVisit] = field(default_factory=list)
    medications: list[MedicationSchedule] = field(default_factory=list)
    vitals_history: list[DailyVitalsLog] = field(default_factory=list)
    caregiver_journal: list[CaregiverNote] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "relationship": self.relationship,
            "year_of_birth": self.year_of_birth,
            "primary_diagnoses": self.primary_diagnoses,
            "allergies": self.allergies,
            "blood_type": self.blood_type,
            "code_status": self.code_status,
            "emergency_contact": self.emergency_contact,
            "preferred_hospital": self.preferred_hospital,
            "physicians": [p.to_dict() for p in self.physicians],
            "doctor_visits": [v.to_dict() for v in self.doctor_visits],
            "medications": [m.to_dict() for m in self.medications],
            "vitals_history": [vit.to_dict() for vit in self.vitals_history],
            "caregiver_journal": [n.to_dict() for n in self.caregiver_journal],
        }
