"""
Unit tests for data models and enum serialization.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from datetime import datetime, time, timezone

from cadence_calendar.models import (
    BufferPlan,
    BufferRecommendation,
    CalendarEvent,
    CompanionResponse,
    DayMetrics,
    EventType,
    FatigueAuditResult,
    FatigueLevel,
    WorkHoursConfig,
)


def test_calendar_event_serialization():
    st = datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc)
    et = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
    event = CalendarEvent(
        id="evt-1",
        title="Weekly Sprint Planning",
        start=st,
        end=et,
        attendees=["alice@example.com", "bob@example.com"],
        event_type=EventType.TEAM_SYNC,
        is_recurring=True,
        location_or_url="https://meet.example.com/sprint",
        is_focus_protected=False,
        tags=["sprint", "engineering"],
    )

    assert event.duration_minutes == 60
    d = event.to_dict()
    assert d["title"] == "Weekly Sprint Planning"
    assert d["duration_minutes"] == 60
    assert d["event_type"] == "TEAM_SYNC"

    recreated = CalendarEvent.from_dict(d)
    assert recreated.id == "evt-1"
    assert recreated.title == event.title
    assert recreated.start == st
    assert recreated.end == et
    assert recreated.event_type == EventType.TEAM_SYNC
    assert recreated.is_recurring is True


def test_work_hours_config_serialization():
    wh = WorkHoursConfig(
        start_time=time(8, 30),
        end_time=time(17, 30),
        work_days=[0, 1, 2, 3, 4],
        lunch_start=time(12, 15),
        lunch_duration_minutes=45,
        target_focus_hours_per_day=4.0,
        max_meeting_hours_per_day=3.5,
        min_buffer_minutes=15,
    )
    d = wh.to_dict()
    assert d["start_time"] == "08:30"
    assert d["end_time"] == "17:30"
    assert d["min_buffer_minutes"] == 15

    recreated = WorkHoursConfig.from_dict(d)
    assert recreated.start_time == time(8, 30)
    assert recreated.end_time == time(17, 30)
    assert recreated.lunch_start == time(12, 15)
    assert recreated.lunch_duration_minutes == 45
    assert recreated.target_focus_hours_per_day == 4.0


def test_day_metrics_and_audit_result_serialization():
    dm = DayMetrics(
        date_str="2026-09-28",
        day_name="Monday",
        total_meeting_minutes=240,
        focus_time_minutes=120,
        fragmented_gap_minutes=45,
        context_switches_count=3,
        max_consecutive_meeting_minutes=120,
        back_to_back_count=2,
        out_of_hours_meeting_minutes=30,
        lunch_encroached_minutes=20,
        fatigue_score=68.5,
        fatigue_level=FatigueLevel.HIGH,
        buffer_deficit_minutes=40,
        events_count=5,
    )
    dm_dict = dm.to_dict()
    assert dm_dict["fatigue_level"] == "HIGH"
    assert dm_dict["fatigue_score"] == 68.5

    audit = FatigueAuditResult(
        audit_date_utc="2026-09-28T10:00:00Z",
        total_events=5,
        analyzed_days_count=1,
        total_meeting_hours=4.0,
        total_focus_hours=2.0,
        total_fragmented_hours=0.75,
        avg_daily_meeting_hours=4.0,
        avg_daily_fatigue_score=68.5,
        burnout_risk_level=FatigueLevel.HIGH,
        back_to_back_chains_count=2,
        context_switches_total=3,
        lunch_compromised_days_count=1,
        out_of_hours_events_count=1,
        day_breakdowns=[dm],
        top_fatigue_days=["2026-09-28 (Monday): 69/100 [HIGH] - 4h00m meetings"],
        recommendations=["Insert 10m buffers"],
    )
    a_dict = audit.to_dict()
    assert a_dict["total_meeting_hours"] == 4.0
    assert a_dict["burnout_risk_level"] == "HIGH"
    assert len(a_dict["day_breakdowns"]) == 1


def test_buffer_plan_and_companion_models():
    st = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
    et = datetime(2026, 9, 28, 10, 10, tzinfo=timezone.utc)
    rec = BufferRecommendation(
        date_str="2026-09-28",
        start=st,
        end=et,
        buffer_type="TRANSITION",
        reason="Post-meeting reset",
        duration_minutes=10,
    )
    plan = BufferPlan(
        created_at_utc="2026-09-28T10:00:00Z",
        total_buffers_generated=1,
        total_buffer_minutes_added=10,
        total_deep_work_blocks_protected=0,
        protected_focus_hours_added=0.0,
        buffers=[rec],
    )
    p_dict = plan.to_dict()
    assert p_dict["total_buffers_generated"] == 1
    assert p_dict["buffers"][0]["duration_minutes"] == 10

    resp = CompanionResponse(
        query="How is my fatigue?",
        summary="You have moderate fatigue.",
        metrics_highlight={"fatigue_score": 45.0},
        recommendations=["Protect morning focus"],
        action_items=["Block Friday"],
    )
    r_dict = resp.to_dict()
    assert r_dict["query"] == "How is my fatigue?"
    assert len(r_dict["recommendations"]) == 1
