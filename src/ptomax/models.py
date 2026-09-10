# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data models for PTO holiday calendars, optimized breaks, coverage handovers, and accrual.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Holiday:
    name: str
    date_str: str  # YYYY-MM-DD
    country: str = "US"

    @property
    def dt(self) -> date:
        return date.fromisoformat(self.date_str)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "date_str": self.date_str,
            "country": self.country,
        }


@dataclass
class WorkCoverage:
    """Project or client handover delegation assignment."""

    id: str
    project_or_domain: str  # e.g., "Wazuh SIEM & Mac Mini SOC", "Client Alpha Billing"
    primary_cover_name: str
    primary_cover_contact: str  # Email or Slack handle
    backup_cover_name: str = ""
    backup_cover_contact: str = ""
    escalation_threshold: str = "P0 production outages only"
    handover_checklist_done: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_or_domain": self.project_or_domain,
            "primary_cover_name": self.primary_cover_name,
            "primary_cover_contact": self.primary_cover_contact,
            "backup_cover_name": self.backup_cover_name,
            "backup_cover_contact": self.backup_cover_contact,
            "escalation_threshold": self.escalation_threshold,
            "handover_checklist_done": self.handover_checklist_done,
            "notes": self.notes,
        }


@dataclass
class PtoBreak:
    """A contiguous period of time off combining weekends, holidays, and PTO."""

    break_name: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    pto_days_required: int
    total_consecutive_days_off: int
    holidays_bridged: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def leverage_multiplier(self) -> float:
        """Ratio of total days off to PTO days burned (e.g. 9 days off for 4 PTO = 2.25x)."""
        if self.pto_days_required <= 0:
            return float(self.total_consecutive_days_off)
        return round(self.total_consecutive_days_off / self.pto_days_required, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "break_name": self.break_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "pto_days_required": self.pto_days_required,
            "total_consecutive_days_off": self.total_consecutive_days_off,
            "holidays_bridged": self.holidays_bridged,
            "leverage_multiplier": self.leverage_multiplier,
            "description": self.description,
        }


@dataclass
class PtoProfile:
    """User profile for PTO allowance, accruals, handover state, and family academic events."""

    total_annual_allowance_days: float = 15.0
    current_balance_days: float = 12.0
    accrual_hours_per_pay_period: float = 4.62  # e.g., 15 days = 120 hrs / 26 periods ≈ 4.62 hrs
    pay_periods_per_year: int = 26  # Bi-weekly
    max_rollover_cap_days: float = 5.0  # Max days allowed to roll over on Dec 31
    planned_breaks: list[PtoBreak] = field(default_factory=list)
    coverage_handovers: list[WorkCoverage] = field(default_factory=list)
    custom_holidays: list[Holiday] = field(default_factory=list)
    academic_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_annual_allowance_days": self.total_annual_allowance_days,
            "current_balance_days": self.current_balance_days,
            "accrual_hours_per_pay_period": self.accrual_hours_per_pay_period,
            "pay_periods_per_year": self.pay_periods_per_year,
            "max_rollover_cap_days": self.max_rollover_cap_days,
            "planned_breaks": [b.to_dict() for b in self.planned_breaks],
            "coverage_handovers": [c.to_dict() for c in self.coverage_handovers],
            "custom_holidays": [h.to_dict() for h in self.custom_holidays],
            "academic_events": self.academic_events,
        }


# Standard US Federal Holiday Calendars for 2026 and 2027
US_FEDERAL_HOLIDAYS_2026 = [
    Holiday("New Year's Day", "2026-01-01"),
    Holiday("Martin Luther King Jr. Day", "2026-01-19"),
    Holiday("Washington's Birthday (Presidents Day)", "2026-02-16"),
    Holiday("Memorial Day", "2026-05-25"),
    Holiday("Juneteenth National Independence Day", "2026-06-19"),
    Holiday("Independence Day (Observed)", "2026-07-03"),
    Holiday("Labor Day", "2026-09-07"),
    Holiday("Columbus Day / Indigenous Peoples' Day", "2026-10-12"),
    Holiday("Veterans Day", "2026-11-11"),
    Holiday("Thanksgiving Day", "2026-11-26"),
    Holiday("Day After Thanksgiving (Black Friday)", "2026-11-27"),
    Holiday("Christmas Day", "2026-12-25"),
]

US_FEDERAL_HOLIDAYS_2027 = [
    Holiday("New Year's Day", "2027-01-01"),
    Holiday("Martin Luther King Jr. Day", "2027-01-18"),
    Holiday("Presidents Day", "2027-02-15"),
    Holiday("Memorial Day", "2027-05-31"),
    Holiday("Juneteenth", "2027-06-18"),
    Holiday("Independence Day (Observed)", "2027-07-05"),
    Holiday("Labor Day", "2027-09-06"),
    Holiday("Columbus Day", "2027-10-11"),
    Holiday("Veterans Day", "2027-11-11"),
    Holiday("Thanksgiving Day", "2027-11-25"),
    Holiday("Christmas Day (Observed)", "2027-12-24"),
]


class HolidayCalendar:
    """Helper to access standard and custom holiday sets."""

    @staticmethod
    def get_holidays_for_year(year: int, custom: list[Holiday] | None = None) -> list[Holiday]:
        holidays = []
        if year == 2026:
            holidays.extend(US_FEDERAL_HOLIDAYS_2026)
        elif year == 2027:
            holidays.extend(US_FEDERAL_HOLIDAYS_2027)
        else:
            holidays.append(Holiday("New Year's Day", f"{year}-01-01"))
            holidays.append(Holiday("Independence Day", f"{year}-07-04"))
            holidays.append(Holiday("Christmas Day", f"{year}-12-25"))

        if custom:
            for ch in custom:
                if ch.date_str.startswith(str(year)):
                    holidays.append(ch)

        return sorted(holidays, key=lambda h: h.date_str)
