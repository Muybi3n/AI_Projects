"""
Unit tests for CalendarAuditor and cognitive fatigue scoring.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from datetime import date, datetime, time, timezone

from cadence_calendar.auditor import CalendarAuditor
from cadence_calendar.models import CalendarEvent, EventType, FatigueLevel, WorkHoursConfig


def test_audit_empty_events():
    auditor = CalendarAuditor()
    res = auditor.audit_events([])
    assert res.total_events == 0
    assert res.analyzed_days_count == 0
    assert res.burnout_risk_level == FatigueLevel.SAFE
    assert len(res.recommendations) > 0


def test_audit_healthy_calendar():
    wh = WorkHoursConfig(
        start_time=time(9, 0),
        end_time=time(17, 0),
        lunch_start=time(12, 0),
        lunch_duration_minutes=45,
    )
    auditor = CalendarAuditor(work_hours=wh)

    # 1 light meeting (10:00 - 10:30) and 1 focus block (13:00 - 15:00)
    events = [
        CalendarEvent(
            id="h-1",
            title="1:1 Sync with Sarah",
            start=datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 10, 30, tzinfo=timezone.utc),
            event_type=EventType.ONE_ON_ONE,
        ),
        CalendarEvent(
            id="h-2",
            title="Deep Work Coding",
            start=datetime(2026, 9, 28, 13, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 15, 0, tzinfo=timezone.utc),
            event_type=EventType.FOCUS_BLOCK,
        ),
    ]

    res = auditor.audit_events(events)
    assert res.total_events == 2
    assert res.analyzed_days_count == 1
    assert res.total_meeting_hours == 0.5
    assert res.burnout_risk_level == FatigueLevel.SAFE
    assert res.avg_daily_fatigue_score < 30.0
    assert res.back_to_back_chains_count == 0


def test_audit_overloaded_and_fragmented_calendar():
    wh = WorkHoursConfig(
        start_time=time(9, 0),
        end_time=time(17, 0),
        lunch_start=time(12, 0),
        lunch_duration_minutes=45,
        max_meeting_hours_per_day=4.0,
    )
    auditor = CalendarAuditor(work_hours=wh)

    # Overloaded day:
    # 08:30-09:00 (Early out of hours)
    # 09:00-10:30 (90m meeting)
    # 10:30-11:30 (Back-to-back 60m meeting, total stretch 150m)
    # 11:45-12:30 (15m Swiss cheese gap before, encroaches on lunch)
    # 13:00-14:30 (90m afternoon sync)
    # 17:00-17:45 (Late out of hours)
    events = [
        CalendarEvent(
            id="ov-1",
            title="Early Bird Triage",
            start=datetime(2026, 9, 29, 8, 30, tzinfo=timezone.utc),
            end=datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc),
            event_type=EventType.AD_HOC,
        ),
        CalendarEvent(
            id="ov-2",
            title="Architecture Review",
            start=datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 29, 10, 30, tzinfo=timezone.utc),
            event_type=EventType.TEAM_SYNC,
        ),
        CalendarEvent(
            id="ov-3",
            title="1:1 Sync with Director",
            start=datetime(2026, 9, 29, 10, 30, tzinfo=timezone.utc),
            end=datetime(2026, 9, 29, 11, 30, tzinfo=timezone.utc),
            event_type=EventType.ONE_ON_ONE,
        ),
        CalendarEvent(
            id="ov-4",
            title="Lunch & Learn / Client Call",
            start=datetime(2026, 9, 29, 11, 45, tzinfo=timezone.utc),
            end=datetime(2026, 9, 29, 12, 30, tzinfo=timezone.utc),
            event_type=EventType.EXTERNAL_CLIENT,
        ),
        CalendarEvent(
            id="ov-5",
            title="Product Roadmap Session",
            start=datetime(2026, 9, 29, 13, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 29, 14, 30, tzinfo=timezone.utc),
            event_type=EventType.TEAM_SYNC,
        ),
        CalendarEvent(
            id="ov-6",
            title="Late Incident Post-Mortem",
            start=datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 29, 17, 45, tzinfo=timezone.utc),
            event_type=EventType.AD_HOC,
        ),
    ]

    res = auditor.audit_events(events)
    assert res.total_events == 6
    assert res.total_meeting_hours >= 5.0
    assert res.burnout_risk_level in (FatigueLevel.HIGH, FatigueLevel.CRITICAL)
    assert res.back_to_back_chains_count >= 1
    assert res.lunch_compromised_days_count >= 1
    assert res.out_of_hours_events_count >= 1
    assert len(res.recommendations) >= 3


def test_audit_date_filtering():
    auditor = CalendarAuditor()
    events = [
        CalendarEvent(
            id="d-1",
            title="September Event",
            start=datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc),
        ),
        CalendarEvent(
            id="d-2",
            title="October Event",
            start=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc),
        ),
    ]
    res = auditor.audit_events(events, start_date=date(2026, 10, 1), end_date=date(2026, 10, 31))
    assert res.total_events == 1
    assert res.day_breakdowns[0].date_str == "2026-10-05"
