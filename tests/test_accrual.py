# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for accrual engine and AI advisor.
"""

from ptomax.accrual import AccrualEngine
from ptomax.advisor import PtoAdvisor
from ptomax.models import PtoProfile


def test_accrual_engine_forfeiture_risk():
    profile = PtoProfile(
        current_balance_days=25.0,
        accrual_hours_per_pay_period=8.0,
        max_rollover_cap_days=5.0,
    )
    engine = AccrualEngine(profile)
    res = engine.project_year_end_balance()
    assert res["days_at_risk_of_forfeiture"] > 0
    assert res["status"] == "USE_IT_OR_LOSE_IT_ALERT"


def test_pto_advisor_consult():
    profile = PtoProfile(current_balance_days=15.0)
    advisor = PtoAdvisor(profile)
    res = advisor.consult("How can I maximize my holiday breaks in 2026?")
    assert "optimized_holiday_bridges" in res["summary"] or len(res["action_plan"]) > 0
