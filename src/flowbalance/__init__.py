# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
flowbalance-core - Deterministic Cash Flow Forecasting & Wealth Velocity Engine.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .engine import CashFlowForecaster, SolvencyTester
from .models import Account, AllocationRule, Expense, ForecastPoint, IncomeStream
from .storage import FinanceStore

__all__ = [
    "Account",
    "AllocationRule",
    "CashFlowForecaster",
    "Expense",
    "FinanceStore",
    "ForecastPoint",
    "IncomeStream",
    "SolvencyTester",
]
