# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Holiday stacking optimization engine: Transforms limited PTO days into maximum consecutive days off.
"""

from datetime import date, timedelta
from typing import Any

from .models import Holiday, HolidayCalendar, PtoBreak


class PtoOptimizer:
    """Calculates high-leverage holiday bridges and optimal vacation schedules."""

    def __init__(self, year: int = 2026, custom_holidays: list[Holiday] | None = None) -> None:
        self.year = year
        self.holidays = HolidayCalendar.get_holidays_for_year(year, custom_holidays)
        self.holiday_dates: set[date] = {h.dt for h in self.holidays}

    def is_workday(self, d: date) -> bool:
        """Returns True if the date is Monday-Friday and NOT a holiday."""
        return d.weekday() < 5 and d not in self.holiday_dates

    def find_all_bridge_opportunities(self) -> list[PtoBreak]:
        """Scans the entire year to identify all high-multiplier PTO holiday stacking opportunities."""
        bridges: list[PtoBreak] = []

        for h in self.holidays:
            h_dt = h.dt
            h_dow = h_dt.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun

            # Opportunity 1: Monday Holiday (e.g., Memorial Day, Labor Day, MLK)
            # Take Tuesday - Friday (4 PTO) -> 9 consecutive days off (Sat to next Sun)
            if h_dow == 0:
                start_sat = h_dt - timedelta(days=2)
                end_sun = h_dt + timedelta(days=6)
                bridges.append(
                    PtoBreak(
                        break_name=f"{h.name} 9-Day Mega-Break",
                        start_date=start_sat.strftime("%Y-%m-%d"),
                        end_date=end_sun.strftime("%Y-%m-%d"),
                        pto_days_required=4,
                        total_consecutive_days_off=9,
                        holidays_bridged=[h.name],
                        description=f"Take Tue-Fri off ({h_dt + timedelta(days=1)} to {h_dt + timedelta(days=4)}) for 9 consecutive days off.",
                    )
                )
                # Mini 4-day weekend (Take Friday before)
                bridges.append(
                    PtoBreak(
                        break_name=f"{h.name} 4-Day Extended Weekend",
                        start_date=(h_dt - timedelta(days=3)).strftime("%Y-%m-%d"),
                        end_date=h_dt.strftime("%Y-%m-%d"),
                        pto_days_required=1,
                        total_consecutive_days_off=4,
                        holidays_bridged=[h.name],
                        description=f"Take Friday off ({h_dt - timedelta(days=3)}) before the Monday holiday for 4 days off.",
                    )
                )

            # Opportunity 2: Friday Holiday (e.g. Juneteenth, Independence Day Observed, Christmas)
            elif h_dow == 4:
                start_sat = h_dt - timedelta(days=6)
                end_sun = h_dt + timedelta(days=2)
                bridges.append(
                    PtoBreak(
                        break_name=f"{h.name} 9-Day Mega-Break",
                        start_date=start_sat.strftime("%Y-%m-%d"),
                        end_date=end_sun.strftime("%Y-%m-%d"),
                        pto_days_required=4,
                        total_consecutive_days_off=9,
                        holidays_bridged=[h.name],
                        description=f"Take Mon-Thu off ({h_dt - timedelta(days=4)} to {h_dt - timedelta(days=1)}) for 9 days off.",
                    )
                )
                # Mini 4-day weekend (Take Monday after)
                bridges.append(
                    PtoBreak(
                        break_name=f"{h.name} 4-Day Extended Weekend",
                        start_date=h_dt.strftime("%Y-%m-%d"),
                        end_date=(h_dt + timedelta(days=3)).strftime("%Y-%m-%d"),
                        pto_days_required=1,
                        total_consecutive_days_off=4,
                        holidays_bridged=[h.name],
                        description=f"Take Monday off ({h_dt + timedelta(days=3)}) after the Friday holiday for 4 days off.",
                    )
                )

            # Opportunity 3: Thursday Holiday (Thanksgiving)
            elif h_dow == 3:
                # Thanksgiving + Black Friday = 4 days off naturally.
                # Take Mon-Wed (3 PTO) -> 9 consecutive days off!
                start_sat = h_dt - timedelta(days=5)
                end_sun = h_dt + timedelta(days=3)
                bridges.append(
                    PtoBreak(
                        break_name=f"{h.name} 9-Day Fall Vacation",
                        start_date=start_sat.strftime("%Y-%m-%d"),
                        end_date=end_sun.strftime("%Y-%m-%d"),
                        pto_days_required=3,
                        total_consecutive_days_off=9,
                        holidays_bridged=[h.name, "Day After Thanksgiving"],
                        description=f"Take Mon-Wed off ({h_dt - timedelta(days=3)} to {h_dt - timedelta(days=1)}) to turn 3 PTO days into 9 days off.",
                    )
                )

            # Opportunity 4: Mid-week Wednesday Holiday (e.g. Veterans Day)
            elif h_dow == 2:
                # Take Mon-Tue or Thu-Fri (2 PTO) -> 5 consecutive days off
                bridges.append(
                    PtoBreak(
                        break_name=f"{h.name} 5-Day Mini-Break",
                        start_date=(h_dt - timedelta(days=4)).strftime("%Y-%m-%d"),
                        end_date=h_dt.strftime("%Y-%m-%d"),
                        pto_days_required=2,
                        total_consecutive_days_off=5,
                        holidays_bridged=[h.name],
                        description=f"Take Mon-Tue off ({h_dt - timedelta(days=2)} to {h_dt - timedelta(days=1)}) for 5 consecutive days off.",
                    )
                )

        # Deduplicate and sort by leverage multiplier descending
        unique_bridges = {}
        for b in bridges:
            key = (b.start_date, b.end_date)
            if (
                key not in unique_bridges
                or b.leverage_multiplier > unique_bridges[key].leverage_multiplier
            ):
                unique_bridges[key] = b

        sorted_list = sorted(
            unique_bridges.values(),
            key=lambda b: (b.leverage_multiplier, b.total_consecutive_days_off),
            reverse=True,
        )
        return sorted_list

    def optimize_plan(self, pto_budget: int = 15) -> dict[str, Any]:
        """Greedily selects the highest-leverage non-overlapping breaks within the PTO budget."""
        all_bridges = self.find_all_bridge_opportunities()
        selected_breaks: list[PtoBreak] = []
        occupied_dates: set[date] = set()
        pto_remaining = pto_budget

        for candidate in all_bridges:
            if candidate.pto_days_required <= pto_remaining:
                c_start = date.fromisoformat(candidate.start_date)
                c_end = date.fromisoformat(candidate.end_date)

                # Generate date set for candidate
                cand_dates = {
                    c_start + timedelta(days=i) for i in range((c_end - c_start).days + 1)
                }

                # Check overlap
                if not cand_dates.intersection(occupied_dates):
                    selected_breaks.append(candidate)
                    occupied_dates.update(cand_dates)
                    pto_remaining -= candidate.pto_days_required

        selected_breaks.sort(key=lambda b: b.start_date)
        total_days_off = sum(b.total_consecutive_days_off for b in selected_breaks)
        total_pto_spent = sum(b.pto_days_required for b in selected_breaks)
        overall_leverage = (
            round(total_days_off / total_pto_spent, 2) if total_pto_spent > 0 else 0.0
        )

        return {
            "year": self.year,
            "pto_budget_allocated": pto_budget,
            "pto_days_spent": total_pto_spent,
            "pto_days_remaining": pto_remaining,
            "total_consecutive_vacation_days_gained": total_days_off,
            "overall_leverage_multiplier": overall_leverage,
            "recommended_breaks": [b.to_dict() for b in selected_breaks],
        }
