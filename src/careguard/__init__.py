# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
careguard-core - Family Medical Caregiver Journal, Multi-Doctor Coordinator & AI Clinical Companion.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .ai_companion import CareCompanion
from .deid import ClinicalRedactor
from .engine import CareEngine
from .extractor import NoteExtractor
from .jargon import JargonTranslator
from .models import (
    CaregiverNote,
    CareRecipient,
    DailyVitalsLog,
    DoctorVisit,
    MedicationSchedule,
    PhysicianContact,
)
from .timeline import ClinicalTimelineEngine

__all__ = [
    "CareCompanion",
    "CareEngine",
    "CareRecipient",
    "CaregiverNote",
    "ClinicalRedactor",
    "ClinicalTimelineEngine",
    "DailyVitalsLog",
    "DoctorVisit",
    "JargonTranslator",
    "MedicationSchedule",
    "NoteExtractor",
    "PhysicianContact",
    "__version__",
]
