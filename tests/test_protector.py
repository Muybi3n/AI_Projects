"""
Unit tests for BufferProtector and focus reservation.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from datetime import datetime, time, timezone

from cadence_calendar.models import CalendarEvent, EventType, WorkHoursConfig
from cadence_calendar.protector import BufferProtector


def test_generate_protection_plan_empty():
    protector = BufferProtector()
    plan = protector.generate_protection_plan([])
    assert plan.total_buffers_generated == 0
    assert plan.total_buffer_minutes_added == 0


def test_generate_protection_plan_buffers_and_focus():
    wh = WorkHoursConfig(
        start_time=time(9, 0),
        end_time=time(17, 0),
        lunch_start=time(12, 0),
        lunch_duration_minutes=45,
    )
    protector = BufferProtector(work_hours=wh)

    # 2 back-to-back meetings in the morning: 09:00-09:30 and 09:30-10:00
    # Then open afternoon (12:45 to 17:00 -> 4h15m deep work)
    events = [
        CalendarEvent(
            id="p-1",
            title="Standup",
            start=datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 9, 30, tzinfo=timezone.utc),
            event_type=EventType.TEAM_SYNC,
        ),
        CalendarEvent(
            id="p-2",
            title="1:1 Sync",
            start=datetime(2026, 9, 28, 9, 30, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc),
            event_type=EventType.ONE_ON_ONE,
        ),
    ]

    plan = protector.generate_protection_plan(
        events=events,
        buffer_minutes=10,
        min_focus_hours=2.0,
        protect_lunch=True,
    )

    assert plan.total_buffers_generated >= 2
    types = [b.buffer_type for b in plan.buffers]
    assert "TRANSITION" in types
    assert "LUNCH_SHIELD" in types
    assert "DEEP_WORK_BLOCK" in types

    # Apply protection
    combined = protector.apply_protection(events, plan)
    assert len(combined) == len(events) + plan.total_buffers_generated
    assert any(e.event_type == EventType.FOCUS_BLOCK for e in combined)
    assert any(e.event_type == EventType.LUNCH for e in combined)
