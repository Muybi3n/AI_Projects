# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for holiday stacking optimizer.
"""

from ptomax.optimizer import PtoOptimizer


def test_optimizer_bridges():
    optimizer = PtoOptimizer(2026)
    bridges = optimizer.find_all_bridge_opportunities()
    assert len(bridges) > 0
    # Every bridge should provide >= 2.0x leverage or 4 days off
    assert any(b.total_consecutive_days_off >= 9 for b in bridges)


def test_optimize_plan_budget():
    optimizer = PtoOptimizer(2026)
    plan = optimizer.optimize_plan(pto_budget=15)
    assert plan["pto_days_spent"] <= 15
    assert plan["total_consecutive_vacation_days_gained"] >= 25
    assert plan["overall_leverage_multiplier"] >= 2.0
