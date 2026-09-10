# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
capdrift-engine - Portfolio Analytics, Capital Drift Auditor & AI Companion.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .analytics import PortfolioAnalyzer
from .ingest import PortfolioIngester
from .llm_companion import PortfolioCompanion
from .models import Holding, PortfolioSnapshot
from .storage import SnapshotStore

__all__ = [
    "Holding",
    "PortfolioAnalyzer",
    "PortfolioCompanion",
    "PortfolioIngester",
    "PortfolioSnapshot",
    "SnapshotStore",
]
