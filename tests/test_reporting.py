# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for reporting sparklines and Markdown document generators.
"""

from flowbalance.engine import CashFlowForecaster, SolvencyTester
from flowbalance.models import Account, Expense, IncomeStream
from flowbalance.reporting import format_forecast_markdown, render_ascii_sparkline


def test_ascii_sparkline():
    vals = [10, 20, 30, 40, 50, 60, 70, 80]
    spark = render_ascii_sparkline(vals, width=8)
    assert len(spark) == 8
    assert spark[0] == " "
    assert spark[-1] == "█"

    empty_spark = render_ascii_sparkline([])
    assert empty_spark == ""


def test_format_forecast_markdown():
    accounts = [Account(id="a1", name="Checking", balance=15000.0)]
    incomes = [
        IncomeStream(
            id="i1", name="Salary", amount=5000.0, frequency="monthly", start_date="2026-01-01"
        )
    ]
    expenses = [
        Expense(
            id="e1",
            name="Rent",
            amount=1500.0,
            frequency="monthly",
            category="needs",
            start_date="2026-01-01",
        )
    ]

    forecaster = CashFlowForecaster(accounts, incomes, expenses)
    points = forecaster.project(days=30)
    solvency = SolvencyTester.evaluate(accounts, incomes, expenses)

    md = format_forecast_markdown(accounts, incomes, expenses, solvency, points)
    assert "# 📊 Wealth & Cash Flow Projection Audit" in md
    assert "$15,000.00" in md
    assert "Checking" in md
    assert "Salary" in md
    assert "Rent" in md
