"""
cadence-calendar: Local-first calendar fatigue auditor, cognitive load analyzer, and deep-work buffer protector.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from cadence_calendar.ai_companion import CadenceCompanion
from cadence_calendar.auditor import CalendarAuditor
from cadence_calendar.models import (
    BufferPlan,
    CalendarEvent,
    DayMetrics,
    EventType,
    FatigueAuditResult,
    FatigueLevel,
    WorkHoursConfig,
)
from cadence_calendar.parser import CalendarParser
from cadence_calendar.protector import BufferProtector
from cadence_calendar.storage import CadenceStorage

__version__ = "0.1.0"

__all__ = [
    "BufferPlan",
    "BufferProtector",
    "CadenceCompanion",
    "CadenceStorage",
    "CalendarAuditor",
    "CalendarEvent",
    "CalendarParser",
    "DayMetrics",
    "EventType",
    "FatigueAuditResult",
    "FatigueLevel",
    "WorkHoursConfig",
]
