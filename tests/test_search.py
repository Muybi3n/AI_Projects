# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for SQLite FTS5 search indexing across accounts, incomes, expenses, and transactions.
"""

from pathlib import Path

from flowbalance.models import Account, Expense, IncomeStream, Transaction
from flowbalance.search import SearchEngine


def test_fts5_indexing_and_search(tmp_path: Path):
    db_file = tmp_path / "search.db"
    engine = SearchEngine(db_file)

    accounts = [Account(id="a1", name="High Yield Vault", balance=25000.0)]
    incomes = [IncomeStream(id="i1", name="Software Retainer", amount=7000.0, frequency="monthly", start_date="2026-01-01")]
    expenses = [Expense(id="e1", name="AWS Cloud Server", amount=300.0, frequency="monthly", category="needs", start_date="2026-01-01")]
    transactions = [
        Transaction(id="t1", date_str="2026-01-15", amount=-120.0, description="Supermarket Whole Foods", category="needs", tags=["food", "grocery"]),
        Transaction(id="t2", date_str="2026-01-18", amount=-45.0, description="Coffee Roaster Subscription", category="wants", tags=["subscription"]),
    ]

    engine.index_all(accounts, incomes, expenses, transactions)

    # Search for transaction
    hits = engine.search("Whole Foods")
    assert len(hits) == 1
    assert hits[0].item_type == "transaction"
    assert hits[0].item_id == "t1"

    # Search for income
    hits_inc = engine.search("Retainer")
    assert len(hits_inc) == 1
    assert hits_inc[0].item_type == "income"

    # Search for expense
    hits_exp = engine.search("AWS")
    assert len(hits_exp) == 1
    assert hits_exp[0].item_type == "expense"
