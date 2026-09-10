# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for LLM contextualization and AI financial advisory logic.
"""

from flowbalance.advisor import FinancialAdvisor, build_financial_context
from flowbalance.engine import SolvencyTester
from flowbalance.models import Account, Expense, IncomeStream, Transaction


def test_build_financial_context():
    accounts = [Account(id="a1", name="Checking", balance=12000.0)]
    incomes = [IncomeStream(id="i1", name="Consulting", amount=6000.0, frequency="monthly", start_date="2026-01-01")]
    expenses = [Expense(id="e1", name="Rent", amount=2000.0, frequency="monthly", category="needs", start_date="2026-01-01")]
    transactions = [Transaction(id="t1", date_str="2026-01-10", amount=-50.0, description="Groceries", category="needs")]

    solvency = SolvencyTester.evaluate(accounts, incomes, expenses)
    ctx = build_financial_context(accounts, incomes, expenses, transactions, solvency)

    assert ctx["liquid_capital_usd"] == 12000.0
    assert ctx["emergency_runway_months"] == 6.0
    assert "needs" in ctx["category_monthly_breakdown"]


def test_heuristic_advisor_runway_query():
    accounts = [Account(id="a1", name="Checking", balance=5000.0)]
    incomes = [IncomeStream(id="i1", name="Salary", amount=4000.0, frequency="monthly", start_date="2026-01-01")]
    expenses = [Expense(id="e1", name="Living Cost", amount=2000.0, frequency="monthly", category="needs", start_date="2026-01-01")]
    solvency = SolvencyTester.evaluate(accounts, incomes, expenses)

    advisor = FinancialAdvisor()
    resp = advisor.consult("What happens to my runway if I lose my job?", accounts, incomes, expenses, [], solvency)

    assert "runway" in resp.executive_summary.lower()
    assert len(resp.recommendations) > 0


def test_custom_llm_adapter():
    accounts = [Account(id="a1", name="Checking", balance=10000.0)]
    solvency = SolvencyTester.evaluate(accounts, [], [])

    def mock_llm(query: str, ctx: dict) -> str:
        return '{"executive_summary": "Custom AI advice", "recommendations": ["Invest surplus"]}'

    advisor = FinancialAdvisor(custom_llm_callable=mock_llm)
    resp = advisor.consult("How should I invest?", accounts, [], [], [], solvency)

    assert resp.executive_summary == "Custom AI advice"
    assert resp.recommendations == ["Invest surplus"]
