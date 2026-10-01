"""
socmesh-audit: Homelab & Mini-SOC Telemetry Normalizer, Threat Correlation Engine & Alert Triage Governor.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .ai_companion import SocmeshAIAdvisor
from .correlator import ThreatCorrelationEngine
from .models import (
    CorrelatedIncident,
    EventSource,
    MitreTactic,
    SecurityEvent,
    SeverityLevel,
    ThreatReport,
)
from .normalizer import TelemetryNormalizer
from .storage import SocmeshCatalog
from .triage import AlertTriageGovernor

__all__ = [
    "AlertTriageGovernor",
    "CorrelatedIncident",
    "EventSource",
    "MitreTactic",
    "SecurityEvent",
    "SeverityLevel",
    "SocmeshAIAdvisor",
    "SocmeshCatalog",
    "TelemetryNormalizer",
    "ThreatCorrelationEngine",
    "ThreatReport",
]
