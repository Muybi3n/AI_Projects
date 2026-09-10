# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
medcadence-core - Personal Health Telemetry, Lab Biomarker Ledger & AI Medical Companion.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .interactions import InteractionSafetyEngine
from .labs import BiomarkerLabEngine
from .models import (
    BiomarkerRecord,
    HealthProfile,
    InteractionAlert,
    MedicationItem,
    WearableTelemetryPoint,
)

__all__ = [
    "BiomarkerLabEngine",
    "BiomarkerRecord",
    "HealthProfile",
    "InteractionAlert",
    "InteractionSafetyEngine",
    "MedicationItem",
    "WearableTelemetryPoint",
    "__version__",
]
