# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
flowbalance-core - Deterministic Cash Flow Forecasting, AI Contextualization & Search Engine.
"""

__version__ = "0.2.0"
__author__ = "bi3n"
__license__ = "MIT"

from .advisor import FinancialAdvisor, build_financial_context
from .engine import CashFlowForecaster, SolvencyTester
from .models import (
    Account,
    AdvisoryResponse,
    AllocationRule,
    Expense,
    ForecastPoint,
    IncomeStream,
    SearchHit,
    SolvencyReport,
    Transaction,
)
from .search import SearchEngine
from .storage import FinanceStore

__all__ = [
    "Account",
    "AdvisoryResponse",
    "AllocationRule",
    "CashFlowForecaster",
    "Expense",
    "FinanceStore",
    "FinancialAdvisor",
    "ForecastPoint",
    "IncomeStream",
    "SearchEngine",
    "SearchHit",
    "SolvencyReport",
    "SolvencyTester",
    "Transaction",
    "build_financial_context",
]
