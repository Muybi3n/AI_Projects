# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
trustguard-core - Estate Planning, Trust Asset Ledger & AI Fiduciary Companion.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .engine import EstateEngine
from .models import (
    BeneficiaryRule,
    FiduciaryLogEntry,
    ScheduleAsset,
    TrustEntity,
    WaterfallResult,
)

__all__ = [
    "BeneficiaryRule",
    "EstateEngine",
    "FiduciaryLogEntry",
    "ScheduleAsset",
    "TrustEntity",
    "WaterfallResult",
    "__version__",
]
