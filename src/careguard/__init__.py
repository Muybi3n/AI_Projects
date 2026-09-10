# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
careguard-core - Family Medical Caregiver Journal, Multi-Doctor Coordinator & AI Clinical Companion.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .engine import CareEngine
from .models import (
    CaregiverNote,
    CareRecipient,
    DailyVitalsLog,
    DoctorVisit,
    MedicationSchedule,
    PhysicianContact,
)

__all__ = [
    "CareEngine",
    "CareRecipient",
    "CaregiverNote",
    "DailyVitalsLog",
    "DoctorVisit",
    "MedicationSchedule",
    "PhysicianContact",
    "__version__",
]
