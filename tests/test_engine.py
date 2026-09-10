# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for deterministic cash flow forecasting, frequency conversions, and solvency stress testing.
"""

from datetime import date

from flowbalance.engine import (
    CashFlowForecaster,
    SolvencyTester,
    is_scheduled_date,
    normalize_to_monthly,
)
from flowbalance.models import Account, Expense, IncomeStream


def test_is_scheduled_date_frequencies():
    start_d = "2026-01-01"  # Thursday

    # Daily
    assert is_scheduled_date(date(2026, 1, 5), start_d, None, "daily") is True

    # Weekly
    assert is_scheduled_date(date(2026, 1, 8), start_d, None, "weekly") is True
    assert is_scheduled_date(date(2026, 1, 9), start_d, None, "weekly") is False

    # Biweekly
    assert is_scheduled_date(date(2026, 1, 15), start_d, None, "biweekly") is True
    assert is_scheduled_date(date(2026, 1, 8), start_d, None, "biweekly") is False

    # Monthly
    assert is_scheduled_date(date(2026, 2, 1), start_d, None, "monthly") is True
    assert is_scheduled_date(date(2026, 2, 2), start_d, None, "monthly") is False

    # Quarterly
    assert is_scheduled_date(date(2026, 4, 1), start_d, None, "quarterly") is True
    assert is_scheduled_date(date(2026, 3, 1), start_d, None, "quarterly") is False

    # Annually
    assert is_scheduled_date(date(2027, 1, 1), start_d, None, "annually") is True
    assert is_scheduled_date(date(2026, 6, 1), start_d, None, "annually") is False

    # End date limit & invalid format
    assert is_scheduled_date(date(2026, 3, 1), start_d, "2026-02-15", "monthly") is False
    assert is_scheduled_date(date(2026, 1, 1), "invalid_date", None, "monthly") is False


def test_normalize_to_monthly():
    assert normalize_to_monthly(1000, "monthly") == 1000.0
    assert round(normalize_to_monthly(100, "daily"), 2) == round(100 * 30.416, 2)
    assert round(normalize_to_monthly(100, "weekly"), 2) == round(100 * (52 / 12), 2)
    assert round(normalize_to_monthly(500, "biweekly"), 2) == round(500 * (26 / 12), 2)
    assert normalize_to_monthly(3000, "quarterly") == 1000.0
    assert normalize_to_monthly(12000, "annually") == 1000.0


def test_cash_flow_forecaster():
    accounts = [Account(id="a1", name="Checking", balance=10000.0)]
    incomes = [
        IncomeStream(
            id="i1",
            name="Salary",
            amount=5000.0,
            frequency="monthly",
            start_date="2026-01-01",
            tax_withholding_pct=20.0,  # Net $4,000
        )
    ]
    expenses = [
        Expense(
            id="e1",
            name="Rent",
            amount=2000.0,
            frequency="monthly",
            category="needs",
            start_date="2026-01-01",
        )
    ]

    forecaster = CashFlowForecaster(accounts, incomes, expenses)
    points = forecaster.project(start_date=date(2026, 1, 1), days=60)

    assert len(points) == 60
    assert points[0].starting_balance == 10000.0
    # Day 0: +4000 net income, -2000 rent -> ending = 12000
    assert points[0].ending_balance == 12000.0
    # Day 31 (Feb 1): +4000, -2000 -> ending = 14000
    feb_point = next(p for p in points if p.date_str == "2026-02-01")
    assert feb_point.ending_balance == 14000.0


def test_solvency_ratings_scale():
    # AAA: >= 12 mos
    rep_aaa = SolvencyTester.evaluate(
        [Account(id="a1", name="S", balance=36000.0)],
        [],
        [
            Expense(
                id="e",
                name="E",
                amount=2000.0,
                frequency="monthly",
                category="needs",
                start_date="2026-01-01",
            )
        ],
    )
    assert "AAA" in rep_aaa.solvency_rating

    # AA: 6-12 mos
    rep_aa = SolvencyTester.evaluate(
        [Account(id="a1", name="S", balance=16000.0)],
        [],
        [
            Expense(
                id="e",
                name="E",
                amount=2000.0,
                frequency="monthly",
                category="needs",
                start_date="2026-01-01",
            )
        ],
    )
    assert "AA" in rep_aa.solvency_rating

    # A: 3-6 mos
    rep_a = SolvencyTester.evaluate(
        [Account(id="a1", name="S", balance=8000.0)],
        [],
        [
            Expense(
                id="e",
                name="E",
                amount=2000.0,
                frequency="monthly",
                category="needs",
                start_date="2026-01-01",
            )
        ],
    )
    assert "A (" in rep_a.solvency_rating

    # BBB: 1-3 mos
    rep_bbb = SolvencyTester.evaluate(
        [Account(id="a1", name="S", balance=4000.0)],
        [],
        [
            Expense(
                id="e",
                name="E",
                amount=2000.0,
                frequency="monthly",
                category="needs",
                start_date="2026-01-01",
            )
        ],
    )
    assert "BBB" in rep_bbb.solvency_rating

    # C: < 1 mo
    rep_c = SolvencyTester.evaluate(
        [Account(id="a1", name="S", balance=500.0)],
        [],
        [
            Expense(
                id="e",
                name="E",
                amount=2000.0,
                frequency="monthly",
                category="needs",
                start_date="2026-01-01",
            )
        ],
    )
    assert "C" in rep_c.solvency_rating
