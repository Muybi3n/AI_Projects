# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for local storage layer.
"""

from pathlib import Path

from flowbalance.models import Account, AllocationRule, Expense, IncomeStream
from flowbalance.storage import FinanceStore


def test_finance_store_crud(tmp_path: Path):
    store = FinanceStore(tmp_path)

    # Accounts
    acc = Account(id="acc_1", name="Vault Checking", balance=5000.0)
    store.add_account(acc)
    accounts = store.list_accounts()
    assert len(accounts) == 1
    assert accounts[0].name == "Vault Checking"

    # Income
    inc = IncomeStream(
        id="inc_1",
        name="Tech Consulting",
        amount=8000.0,
        frequency="monthly",
        start_date="2026-01-01",
    )
    store.add_income(inc)
    incomes = store.list_incomes()
    assert len(incomes) == 1
    assert incomes[0].amount == 8000.0

    # Expense
    exp = Expense(
        id="exp_1",
        name="Office Lease",
        amount=1500.0,
        frequency="monthly",
        category="needs",
        start_date="2026-01-01",
    )
    store.add_expense(exp)
    expenses = store.list_expenses()
    assert len(expenses) == 1
    assert expenses[0].amount == 1500.0

    # Allocations
    rules = [AllocationRule(bucket_name="Tax Reserve", percentage=30.0)]
    store.set_allocations(rules)
    allocs = store.list_allocations()
    assert len(allocs) == 1
    assert allocs[0].bucket_name == "Tax Reserve"

    # Removals
    assert store.remove_account("acc_1") is True
    assert store.remove_income("inc_1") is True
    assert store.remove_expense("exp_1") is True
    assert len(store.list_accounts()) == 0
