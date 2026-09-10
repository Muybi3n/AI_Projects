# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
PTO accrual projector, rollover cliff calculator & forfeiture warning engine.
"""

from datetime import date, datetime, timezone
from typing import Any

from .models import PtoProfile


class AccrualEngine:
    """Computes pay-period accruals, year-end balances, and use-it-or-lose-it risk."""

    def __init__(self, profile: PtoProfile) -> None:
        self.profile = profile

    def project_year_end_balance(self, as_of_date: date | None = None) -> dict[str, Any]:
        """Calculates expected PTO balance at year-end based on accrual rate and planned breaks."""
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc).date()

        current_year = as_of_date.year
        dec_31 = date(current_year, 12, 31)

        # Estimate remaining pay periods in current year
        days_left_in_year = max(0, (dec_31 - as_of_date).days)
        fraction_of_year = days_left_in_year / 365.25
        remaining_pay_periods = fraction_of_year * self.profile.pay_periods_per_year

        hours_to_accrue = remaining_pay_periods * self.profile.accrual_hours_per_pay_period
        days_to_accrue = hours_to_accrue / 8.0  # 8 hours = 1 PTO day

        # Planned PTO days in remainder of year
        planned_pto_days = sum(b.pto_days_required for b in self.profile.planned_breaks)

        projected_gross = self.profile.current_balance_days + days_to_accrue - planned_pto_days
        rollover_cap = self.profile.max_rollover_cap_days

        days_at_risk_of_forfeiture = max(0.0, projected_gross - rollover_cap)

        status = "HEALTHY"
        advisory = "Your planned PTO matches your annual accrual."
        if days_at_risk_of_forfeiture > 0.5:
            status = "USE_IT_OR_LOSE_IT_ALERT"
            advisory = (
                f"🚨 WARNING: You are projected to lose {days_at_risk_of_forfeiture:.1f} days of PTO "
                f"at year-end due to the {rollover_cap:.0f}-day rollover cap. Schedule time off before Dec 31!"
            )

        return {
            "current_balance_days": round(self.profile.current_balance_days, 1),
            "projected_accrual_days": round(days_to_accrue, 1),
            "planned_pto_spent": round(planned_pto_days, 1),
            "projected_year_end_balance": round(projected_gross, 1),
            "max_rollover_cap": rollover_cap,
            "days_at_risk_of_forfeiture": round(days_at_risk_of_forfeiture, 1),
            "status": status,
            "advisory": advisory,
        }
