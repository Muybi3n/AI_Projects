# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for flowbalance-core.
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .engine import CashFlowForecaster, SolvencyTester
from .models import Account, Expense, IncomeStream
from .reporting import format_forecast_markdown, render_ascii_sparkline
from .storage import FinanceStore


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  flowbalance v{__version__:<10}                                    │
│  Deterministic Cash Flow & Wealth Velocity Engine           │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="flowbalance",
        description="Deterministic Local-First Cash Flow Forecasting & Solvency Runway Engine.",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=None, help="Custom data storage directory."
    )
    parser.add_argument("--version", "-v", action="version", version=f"flowbalance {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Account commands ---
    acc_p = subparsers.add_parser("account", help="Manage cash & savings accounts.")
    acc_sub = acc_p.add_subparsers(dest="subcommand", required=True)

    acc_add = acc_sub.add_parser("add", help="Add account.")
    acc_add.add_argument("--name", required=True, help="Account name.")
    acc_add.add_argument("--balance", type=float, required=True, help="Initial balance.")
    acc_add.add_argument("--illiquid", action="store_true", help="Mark as illiquid/locked.")

    acc_sub.add_parser("list", help="List accounts.")
    acc_rm = acc_sub.add_parser("rm", help="Remove account.")
    acc_rm.add_argument("id", help="Account ID.")

    # --- Income commands ---
    inc_p = subparsers.add_parser("income", help="Manage income streams.")
    inc_sub = inc_p.add_subparsers(dest="subcommand", required=True)

    inc_add = inc_sub.add_parser("add", help="Add recurring income.")
    inc_add.add_argument("--name", required=True, help="Income stream name.")
    inc_add.add_argument("--amount", type=float, required=True, help="Gross amount.")
    inc_add.add_argument(
        "--frequency",
        choices=["daily", "weekly", "biweekly", "monthly", "quarterly", "annually"],
        default="monthly",
    )
    inc_add.add_argument("--tax-pct", type=float, default=0.0, help="Tax withholding percentage.")
    inc_add.add_argument("--start", default=None, help="Start date (YYYY-MM-DD).")

    inc_sub.add_parser("list", help="List income streams.")
    inc_rm = inc_sub.add_parser("rm", help="Remove income stream.")
    inc_rm.add_argument("id", help="Income stream ID.")

    # --- Expense commands ---
    exp_p = subparsers.add_parser("expense", help="Manage recurring expenses.")
    exp_sub = exp_p.add_subparsers(dest="subcommand", required=True)

    exp_add = exp_sub.add_parser("add", help="Add recurring expense.")
    exp_add.add_argument("--name", required=True, help="Expense name.")
    exp_add.add_argument("--amount", type=float, required=True, help="Amount.")
    exp_add.add_argument(
        "--frequency",
        choices=["daily", "weekly", "biweekly", "monthly", "quarterly", "annually"],
        default="monthly",
    )
    exp_add.add_argument(
        "--category",
        choices=["needs", "wants", "investments", "taxes", "debt", "emergency"],
        default="needs",
    )
    exp_add.add_argument(
        "--non-essential", action="store_true", help="Mark as discretionary/non-essential."
    )
    exp_add.add_argument("--start", default=None, help="Start date (YYYY-MM-DD).")

    exp_sub.add_parser("list", help="List expenses.")
    exp_rm = exp_sub.add_parser("rm", help="Remove expense.")
    exp_rm.add_argument("id", help="Expense ID.")

    # --- Forecast command ---
    fc_p = subparsers.add_parser("forecast", help="Run forward cash balance projection.")
    fc_p.add_argument("--days", type=int, default=180, help="Projection duration in days.")
    fc_p.add_argument("--json", action="store_true", help="Output raw JSON timeline.")
    fc_p.add_argument("--out", type=Path, default=None, help="Save report to Markdown file.")

    # --- Stress-test command ---
    stress_p = subparsers.add_parser("stress-test", help="Evaluate runway under income shock.")
    stress_p.add_argument(
        "--haircut", type=float, default=100.0, help="Income reduction percentage (0-100%)."
    )

    args = parser.parse_args(argv)
    store = FinanceStore(args.data_dir)

    # --- Handle Account ---
    if args.command == "account":
        if args.subcommand == "add":
            acc_id = str(uuid.uuid4())[:8]
            acc = Account(
                id=acc_id, name=args.name, balance=args.balance, is_liquid=not args.illiquid
            )
            store.add_account(acc)
            print(f"[✓] Added Account: '{acc.name}' (${acc.balance:,.2f}) [ID: {acc.id}]")
        elif args.subcommand == "list":
            accounts = store.list_accounts()
            print(f"\nAccounts ({len(accounts)} total):")
            print("─" * 55)
            for a in accounts:
                liq = "Liquid" if a.is_liquid else "Illiquid"
                print(f"[{a.id}] {a.name:<25} ${a.balance:>12,.2f}  ({liq})")
        elif args.subcommand == "rm":
            if store.remove_account(args.id):
                print(f"[✓] Removed account {args.id}")
            else:
                print(f"Error: Account {args.id} not found.", file=sys.stderr)
                return 1

    # --- Handle Income ---
    elif args.command == "income":
        if args.subcommand == "add":
            inc_id = str(uuid.uuid4())[:8]
            start_d = args.start or datetime.now(timezone.utc).date().isoformat()
            inc = IncomeStream(
                id=inc_id,
                name=args.name,
                amount=args.amount,
                frequency=args.frequency,
                start_date=start_d,
                tax_withholding_pct=args.tax_pct,
            )
            store.add_income(inc)
            print(
                f"[✓] Added Income: '{inc.name}' (${inc.amount:,.2f} {inc.frequency}) [ID: {inc.id}]"
            )
        elif args.subcommand == "list":
            incomes = store.list_incomes()
            print(f"\nIncome Streams ({len(incomes)} total):")
            print("─" * 60)
            for i in incomes:
                print(
                    f"[{i.id}] {i.name:<20} ${i.amount:>10,.2f}  ({i.frequency}) Net: ${i.net_amount:,.2f}"
                )
        elif args.subcommand == "rm":
            if store.remove_income(args.id):
                print(f"[✓] Removed income {args.id}")
            else:
                print(f"Error: Income {args.id} not found.", file=sys.stderr)
                return 1

    # --- Handle Expense ---
    elif args.command == "expense":
        if args.subcommand == "add":
            exp_id = str(uuid.uuid4())[:8]
            start_d = args.start or datetime.now(timezone.utc).date().isoformat()
            exp = Expense(
                id=exp_id,
                name=args.name,
                amount=args.amount,
                frequency=args.frequency,
                category=args.category,
                start_date=start_d,
                is_essential=not args.non_essential,
            )
            store.add_expense(exp)
            print(
                f"[✓] Added Expense: '{exp.name}' (${exp.amount:,.2f} {exp.frequency}) [ID: {exp.id}]"
            )
        elif args.subcommand == "list":
            expenses = store.list_expenses()
            print(f"\nRecurring Expenses ({len(expenses)} total):")
            print("─" * 65)
            for e in expenses:
                ess = "Essential" if e.is_essential else "Discretionary"
                print(
                    f"[{e.id}] {e.name:<20} ${e.amount:>10,.2f}  ({e.frequency:<10}) [{e.category}] ({ess})"
                )
        elif args.subcommand == "rm":
            if store.remove_expense(args.id):
                print(f"[✓] Removed expense {args.id}")
            else:
                print(f"Error: Expense {args.id} not found.", file=sys.stderr)
                return 1

    # --- Handle Forecast ---
    elif args.command == "forecast":
        accounts = store.list_accounts()
        incomes = store.list_incomes()
        expenses = store.list_expenses()

        forecaster = CashFlowForecaster(accounts, incomes, expenses)
        points = forecaster.project(days=args.days)
        solvency = SolvencyTester.evaluate(accounts, incomes, expenses)

        if args.json:
            out_data = {
                "solvency": solvency.__dict__,
                "timeline": [p.__dict__ for p in points],
            }
            print(json.dumps(out_data, indent=2))
            return 0

        if args.out:
            md_doc = format_forecast_markdown(accounts, incomes, expenses, solvency, points)
            args.out.write_text(md_doc, encoding="utf-8")
            print(f"[✓] Saved forecast report to: {args.out}")
            return 0

        # Terminal output
        start_b = points[0].starting_balance if points else 0.0
        end_b = points[-1].ending_balance if points else 0.0
        diff = end_b - start_b
        spark = render_ascii_sparkline([p.ending_balance for p in points], width=24)

        print("\n" + "=" * 60)
        print("                  CASH FLOW FORECAST                    ")
        print("=" * 60)
        print(f"  Starting Balance     : ${start_b:,.2f}")
        print(f"  Projected Balance    : ${end_b:,.2f}  ({'+' if diff >= 0 else ''}${diff:,.2f})")
        print(f"  Monthly Burn Rate    : ${solvency.monthly_burn_rate:,.2f}/mo")
        print(f"  Solvency Rating      : {solvency.solvency_rating}")
        print(f"  Emergency Runway     : {solvency.essential_runway_months} Months")
        print(f"  Projection Sparkline : [{spark}]")
        print("=" * 60)

    # --- Handle Stress-Test ---
    elif args.command == "stress-test":
        accounts = store.list_accounts()
        incomes = store.list_incomes()
        expenses = store.list_expenses()

        solvency = SolvencyTester.evaluate(
            accounts, incomes, expenses, income_haircut_pct=args.haircut
        )
        print("\n" + "=" * 60)
        print(f"       SOLVENCY STRESS TEST ({args.haircut:.0f}% Income Loss)       ")
        print("=" * 60)
        print(f"  Available Liquid Capital : ${solvency.liquid_capital:,.2f}")
        print(f"  Baseline Monthly Burn    : ${solvency.monthly_burn_rate:,.2f}")
        print(f"  Essential Monthly Burn   : ${solvency.essential_monthly_burn:,.2f}")
        print(f"  Full Runway Duration     : {solvency.full_runway_months} Months")
        print(f"  Essential Runway         : {solvency.essential_runway_months} Months")
        print(f"  Solvency Rating          : {solvency.solvency_rating}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
