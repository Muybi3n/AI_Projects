# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Core forecasting engine, multi-bucket allocator, and solvency stress tester.
"""

from datetime import date, datetime, timedelta, timezone

from .models import (
    Account,
    Expense,
    ForecastPoint,
    Frequency,
    IncomeStream,
    SolvencyReport,
)


def is_scheduled_date(
    current_date: date, start_date_str: str, end_date_str: str | None, frequency: Frequency
) -> bool:
    """Determine if a recurring cash flow event lands on current_date."""
    try:
        start_d = date.fromisoformat(start_date_str)
    except ValueError:
        return False

    if current_date < start_d:
        return False

    if end_date_str:
        try:
            end_d = date.fromisoformat(end_date_str)
            if current_date > end_d:
                return False
        except ValueError:
            pass

    delta_days = (current_date - start_d).days

    if frequency == "daily":
        return True
    elif frequency == "weekly":
        return delta_days % 7 == 0
    elif frequency == "biweekly":
        return delta_days % 14 == 0
    elif frequency == "monthly":
        # Fires on the same day-of-month or last day of month if day exceeds length
        return current_date.day == start_d.day
    elif frequency == "quarterly":
        return current_date.day == start_d.day and (current_date.month - start_d.month) % 3 == 0
    elif frequency == "annually":
        return current_date.day == start_d.day and current_date.month == start_d.month

    return False


def normalize_to_monthly(amount: float, frequency: Frequency) -> float:
    """Convert any cash flow frequency into an annualized monthly equivalent."""
    if frequency == "daily":
        return amount * 30.416
    elif frequency == "weekly":
        return amount * (52.0 / 12.0)
    elif frequency == "biweekly":
        return amount * (26.0 / 12.0)
    elif frequency == "monthly":
        return amount
    elif frequency == "quarterly":
        return amount / 3.0
    elif frequency == "annually":
        return amount / 12.0
    return amount


class CashFlowForecaster:
    """Generates day-by-day cash balance projections over N days."""

    def __init__(
        self,
        accounts: list[Account],
        incomes: list[IncomeStream],
        expenses: list[Expense],
    ):
        self.accounts = accounts
        self.incomes = incomes
        self.expenses = expenses

    def project(
        self,
        start_date: date | None = None,
        days: int = 180,
    ) -> list[ForecastPoint]:
        """Run day-by-day simulation."""
        curr_d = start_date or datetime.now(timezone.utc).date()
        # Initial liquid starting capital
        current_balance = sum(acc.balance for acc in self.accounts if acc.is_liquid)
        points: list[ForecastPoint] = []

        for i in range(days):
            target_date = curr_d + timedelta(days=i)
            target_str = target_date.strftime("%Y-%m-%d")
            starting = current_balance
            day_inflow = 0.0
            day_outflow = 0.0
            day_events = []

            # Process Incomes
            for inc in self.incomes:
                if is_scheduled_date(target_date, inc.start_date, inc.end_date, inc.frequency):
                    net = inc.net_amount
                    day_inflow += net
                    day_events.append(f"+${net:,.2f} [{inc.name}]")

            # Process Expenses
            for exp in self.expenses:
                if is_scheduled_date(target_date, exp.start_date, exp.end_date, exp.frequency):
                    day_outflow += exp.amount
                    day_events.append(f"-${exp.amount:,.2f} [{exp.name}]")

            current_balance = starting + day_inflow - day_outflow

            points.append(
                ForecastPoint(
                    date_str=target_str,
                    starting_balance=round(starting, 2),
                    total_inflows=round(day_inflow, 2),
                    total_outflows=round(day_outflow, 2),
                    ending_balance=round(current_balance, 2),
                    events=day_events,
                )
            )

        return points


class SolvencyTester:
    """Evaluates emergency runway and stress-tests financial resilience."""

    @staticmethod
    def evaluate(
        accounts: list[Account],
        incomes: list[IncomeStream],
        expenses: list[Expense],
        income_haircut_pct: float = 0.0,
    ) -> SolvencyReport:
        liquid_capital = sum(a.balance for a in accounts if a.is_liquid)
        monthly_income = sum(normalize_to_monthly(i.net_amount, i.frequency) for i in incomes) * (
            1.0 - (income_haircut_pct / 100.0)
        )

        monthly_burn = sum(normalize_to_monthly(e.amount, e.frequency) for e in expenses)
        essential_burn = sum(
            normalize_to_monthly(e.amount, e.frequency) for e in expenses if e.is_essential
        )

        net_monthly_flow = monthly_income - monthly_burn
        savings_rate = (net_monthly_flow / monthly_income * 100.0) if monthly_income > 0 else 0.0

        # Runway calculation under total income cessation
        full_runway = (liquid_capital / monthly_burn) if monthly_burn > 0 else 999.0
        essential_runway = (liquid_capital / essential_burn) if essential_burn > 0 else 999.0

        # Solvency Rating
        if essential_runway >= 12.0:
            rating = "AAA (Fortress Runway >= 12 mos)"
        elif essential_runway >= 6.0:
            rating = "AA (Solid Emergency Buffer 6-12 mos)"
        elif essential_runway >= 3.0:
            rating = "A (Adequate Baseline 3-6 mos)"
        elif essential_runway >= 1.0:
            rating = "BBB (Vulnerable 1-3 mos)"
        else:
            rating = "C (Critical Deficit < 1 mo)"

        return SolvencyReport(
            liquid_capital=round(liquid_capital, 2),
            monthly_burn_rate=round(monthly_burn, 2),
            essential_monthly_burn=round(essential_burn, 2),
            full_runway_months=round(full_runway, 1),
            essential_runway_months=round(essential_runway, 1),
            solvency_rating=rating,
            savings_rate_pct=round(savings_rate, 1),
        )
