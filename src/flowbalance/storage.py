# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local storage manager for accounts, income streams, expenses, and allocations.
"""

import json
from pathlib import Path
from typing import Any

from .models import Account, AllocationRule, Expense, IncomeStream

DEFAULT_DATA_DIR = Path.home() / ".flowbalance"


class FinanceStore:
    """Manages local JSON file repository for privacy-first personal finance state."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "profile.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.state_file.exists():
            initial_data = {
                "accounts": [],
                "incomes": [],
                "expenses": [],
                "allocations": [],
            }
            self._save_raw(initial_data)

    def _load_raw(self) -> dict[str, Any]:
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"accounts": [], "incomes": [], "expenses": [], "allocations": []}

    def _save_raw(self, data: dict[str, Any]) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # --- Accounts ---
    def list_accounts(self) -> list[Account]:
        raw = self._load_raw()
        return [Account(**item) for item in raw.get("accounts", [])]

    def add_account(self, account: Account) -> None:
        raw = self._load_raw()
        accounts = [a for a in raw.get("accounts", []) if a["id"] != account.id]
        accounts.append(account.to_dict())
        raw["accounts"] = accounts
        self._save_raw(raw)

    def remove_account(self, account_id: str) -> bool:
        raw = self._load_raw()
        before_len = len(raw.get("accounts", []))
        raw["accounts"] = [a for a in raw.get("accounts", []) if a["id"] != account_id]
        self._save_raw(raw)
        return len(raw["accounts"]) < before_len

    # --- Incomes ---
    def list_incomes(self) -> list[IncomeStream]:
        raw = self._load_raw()
        return [IncomeStream(**item) for item in raw.get("incomes", [])]

    def add_income(self, income: IncomeStream) -> None:
        raw = self._load_raw()
        incomes = [i for i in raw.get("incomes", []) if i["id"] != income.id]
        incomes.append(income.to_dict())
        raw["incomes"] = incomes
        self._save_raw(raw)

    def remove_income(self, income_id: str) -> bool:
        raw = self._load_raw()
        before_len = len(raw.get("incomes", []))
        raw["incomes"] = [i for i in raw.get("incomes", []) if i["id"] != income_id]
        self._save_raw(raw)
        return len(raw["incomes"]) < before_len

    # --- Expenses ---
    def list_expenses(self) -> list[Expense]:
        raw = self._load_raw()
        return [Expense(**item) for item in raw.get("expenses", [])]

    def add_expense(self, expense: Expense) -> None:
        raw = self._load_raw()
        expenses = [e for e in raw.get("expenses", []) if e["id"] != expense.id]
        expenses.append(expense.to_dict())
        raw["expenses"] = expenses
        self._save_raw(raw)

    def remove_expense(self, expense_id: str) -> bool:
        raw = self._load_raw()
        before_len = len(raw.get("expenses", []))
        raw["expenses"] = [e for e in raw.get("expenses", []) if e["id"] != expense_id]
        self._save_raw(raw)
        return len(raw["expenses"]) < before_len

    # --- Allocations ---
    def list_allocations(self) -> list[AllocationRule]:
        raw = self._load_raw()
        return [AllocationRule(**item) for item in raw.get("allocations", [])]

    def set_allocations(self, rules: list[AllocationRule]) -> None:
        raw = self._load_raw()
        raw["allocations"] = [r.to_dict() for r in rules]
        self._save_raw(raw)
