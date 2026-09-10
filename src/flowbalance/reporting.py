# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Reporting formatters: ASCII Sparklines, Markdown Financial Audits, and JSON exports.
"""

from .models import Account, Expense, ForecastPoint, IncomeStream, SolvencyReport


def render_ascii_sparkline(values: list[float], width: int = 40) -> str:
    """Generate mini ASCII line graph for terminal dashboards."""
    if not values:
        return ""
    min_val, max_val = min(values), max(values)
    val_range = max_val - min_val if max_val != min_val else 1.0

    # Downsample or resample to width
    step = len(values) / width
    sampled = [values[int(i * step)] for i in range(width)]

    chars = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    res = []
    for v in sampled:
        idx = int((v - min_val) / val_range * (len(chars) - 1))
        res.append(chars[max(0, min(idx, len(chars) - 1))])

    return "".join(res)


def format_forecast_markdown(
    accounts: list[Account],
    incomes: list[IncomeStream],
    expenses: list[Expense],
    solvency: SolvencyReport,
    points: list[ForecastPoint],
) -> str:
    """Generate comprehensive monthly financial health Markdown report."""
    start_bal = points[0].starting_balance if points else 0.0
    end_bal = points[-1].ending_balance if points else 0.0
    net_change = end_bal - start_bal

    balances = [p.ending_balance for p in points]
    spark = render_ascii_sparkline(balances, width=30)

    acc_rows = "\n".join(
        [
            f"| `{a.name}` | ${a.balance:,.2f} | {'Liquid' if a.is_liquid else 'Illiquid'} |"
            for a in accounts
        ]
    )
    inc_rows = "\n".join(
        [
            f"| `{i.name}` | ${i.amount:,.2f} ({i.frequency}) | Net: ${i.net_amount:,.2f} |"
            for i in incomes
        ]
    )
    exp_rows = "\n".join(
        [
            f"| `{e.name}` | ${e.amount:,.2f} ({e.frequency}) | `{e.category}` | {'Yes' if e.is_essential else 'No'} |"
            for e in expenses
        ]
    )

    return f"""# 📊 Wealth & Cash Flow Projection Audit

**Generated on:** Today  
**Solvency Rating:** `{solvency.solvency_rating}`  
**Savings Rate:** `{solvency.savings_rate_pct}%`  

---

## 🎯 Executive Balance Trajectory
* **Current Liquid Capital:** `${solvency.liquid_capital:,.2f}`
* **Projected Balance ({len(points)} Days):** `${end_bal:,.2f}` (`{"+" if net_change >= 0 else ""}${net_change:,.2f}`)
* **Monthly Burn Rate:** `${solvency.monthly_burn_rate:,.2f}/mo` (Essential: `${solvency.essential_monthly_burn:,.2f}/mo`)
* **Emergency Runway:** **`{solvency.essential_runway_months} Months`** (Zero Income Survival)

### 📈 Trajectory Sparkline
```text
Min: ${min(balances):,.2f} [{spark}] Max: ${max(balances):,.2f}
```

---

## 🏦 Accounts
| Account | Balance | Type |
| :--- | :--- | :--- |
{acc_rows if acc_rows else "| _No accounts_ | $0.00 | - |"}

---

## 💵 Income Streams
| Source | Inflow | Post-Tax Net |
| :--- | :--- | :--- |
{inc_rows if inc_rows else "| _No income streams_ | $0.00 | - |"}

---

## 💳 Recurring Expenses
| Expense | Amount | Category | Essential? |
| :--- | :--- | :--- | :--- |
{exp_rows if exp_rows else "| _No expenses recorded_ | $0.00 | - | - |"}

---

> *Generated locally by `flowbalance-core`. 100% private, deterministic financial modeling.*
"""
