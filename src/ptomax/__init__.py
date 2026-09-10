# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
ptomax-core: PTO Holiday Stacking Optimizer & Leave Handover Planner.
"""

__version__ = "0.1.0"

from .accrual import AccrualEngine
from .advisor import PtoAdvisor
from .coverage import CoverageMatrix
from .emails import OooEmailGenerator
from .models import Holiday, HolidayCalendar, PtoBreak, PtoProfile, WorkCoverage
from .optimizer import PtoOptimizer

__all__ = [
    "AccrualEngine",
    "CoverageMatrix",
    "Holiday",
    "HolidayCalendar",
    "OooEmailGenerator",
    "PtoAdvisor",
    "PtoBreak",
    "PtoOptimizer",
    "PtoProfile",
    "WorkCoverage",
]
