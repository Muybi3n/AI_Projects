"""
Extended unit tests for CalendarAuditor edge cases.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from datetime import datetime, time, timezone

from cadence_calendar.auditor import CalendarAuditor
from cadence_calendar.models import CalendarEvent, EventType, WorkHoursConfig


def test_audit_friday_focus_and_context_switches():
    wh = WorkHoursConfig(
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    auditor = CalendarAuditor(work_hours=wh)

    # Friday with 4 consecutive meetings and context switches
    # 2026-10-02 is a Friday
    events = [
        CalendarEvent(
            id="f-1",
            title="Sprint Retro",
            start=datetime(2026, 10, 2, 13, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc),
            event_type=EventType.TEAM_SYNC,
            attendees=["team@example.com"],
        ),
        CalendarEvent(
            id="f-2",
            title="External Vendor Demo",
            start=datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 2, 15, 0, tzinfo=timezone.utc),
            event_type=EventType.EXTERNAL_CLIENT,
            attendees=["vendor@example.com"],
        ),
        CalendarEvent(
            id="f-3",
            title="Candidate Interview",
            start=datetime(2026, 10, 2, 15, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc),
            event_type=EventType.INTERVIEW,
            attendees=["recruiter@example.com"],
        ),
        CalendarEvent(
            id="f-4",
            title="1:1 Wrap Up",
            start=datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 2, 16, 30, tzinfo=timezone.utc),
            event_type=EventType.ONE_ON_ONE,
            attendees=["peer@example.com"],
        ),
    ]

    res = auditor.audit_events(events)
    assert res.total_events == 4
    assert res.context_switches_total >= 3
    assert any("Focus Friday" in r for r in res.recommendations)
