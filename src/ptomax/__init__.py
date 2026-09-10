# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
ptomax-core: PTO Holiday Stacking Optimizer, School Syllabus Synchronizer & Leave Handover Planner.
"""

__version__ = "0.2.0"

from .academic import AcademicEvent, AcademicEventType, FamilyCalendarBridge, SyllabusParser
from .accrual import AccrualEngine
from .advisor import PtoAdvisor
from .coverage import CoverageMatrix
from .emails import OooEmailGenerator
from .models import Holiday, HolidayCalendar, PtoBreak, PtoProfile, WorkCoverage
from .optimizer import PtoOptimizer

__all__ = [
    "AcademicEvent",
    "AcademicEventType",
    "AccrualEngine",
    "CoverageMatrix",
    "FamilyCalendarBridge",
    "Holiday",
    "HolidayCalendar",
    "OooEmailGenerator",
    "PtoAdvisor",
    "PtoBreak",
    "PtoOptimizer",
    "PtoProfile",
    "SyllabusParser",
    "WorkCoverage",
]
