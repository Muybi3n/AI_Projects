# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for ptomax data models.
"""

from ptomax.models import HolidayCalendar, PtoBreak


def test_pto_break_leverage():
    b = PtoBreak(
        break_name="Memorial Day Mega-Break",
        start_date="2026-05-23",
        end_date="2026-05-31",
        pto_days_required=4,
        total_consecutive_days_off=9,
    )
    assert b.leverage_multiplier == 2.25


def test_holiday_calendar_2026():
    holidays = HolidayCalendar.get_holidays_for_year(2026)
    assert len(holidays) >= 10
    names = [h.name for h in holidays]
    assert "Memorial Day" in names
    assert "Thanksgiving Day" in names
