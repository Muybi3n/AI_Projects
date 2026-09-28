"""
Unit tests for CadenceStorage local JSON database.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from datetime import datetime, time, timezone
from pathlib import Path

from cadence_calendar.models import CalendarEvent, FatigueAuditResult, FatigueLevel, WorkHoursConfig
from cadence_calendar.storage import CadenceStorage


def test_storage_profile_lifecycle(tmp_path: Path):
    storage = CadenceStorage(data_dir=tmp_path)
    name, wh, meta = storage.load_profile()
    assert name == "Default Profile"
    assert wh.start_time == time(9, 0)

    custom_wh = WorkHoursConfig(
        start_time=time(8, 0),
        end_time=time(16, 0),
        lunch_start=time(12, 0),
        lunch_duration_minutes=30,
        target_focus_hours_per_day=4.5,
    )
    storage.save_profile("Engineering Lead Schedule", custom_wh, {"timezone": "UTC"})

    name_loaded, wh_loaded, meta_loaded = storage.load_profile()
    assert name_loaded == "Engineering Lead Schedule"
    assert wh_loaded.start_time == time(8, 0)
    assert wh_loaded.end_time == time(16, 0)
    assert meta_loaded.get("timezone") == "UTC"


def test_storage_events_and_deduplication(tmp_path: Path):
    storage = CadenceStorage(data_dir=tmp_path)
    assert storage.load_events() == []

    st = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
    et = datetime(2026, 9, 28, 11, 0, tzinfo=timezone.utc)
    ev1 = CalendarEvent(id="e-1", title="Sprint Planning", start=st, end=et)
    ev2 = CalendarEvent(id="e-2", title="1:1 Sync", start=st, end=et)

    added1 = storage.append_events([ev1, ev2])
    assert added1 == 2
    assert len(storage.load_events()) == 2

    # Appending duplicates
    added2 = storage.append_events([ev1])
    assert added2 == 0
    assert len(storage.load_events()) == 2

    # Clear
    storage.clear_events()
    assert storage.load_events() == []


def test_storage_audits_history(tmp_path: Path):
    storage = CadenceStorage(data_dir=tmp_path)
    assert storage.load_audit_history() == []

    audit = FatigueAuditResult(
        audit_date_utc=datetime.now(timezone.utc).isoformat(),
        total_events=3,
        analyzed_days_count=1,
        total_meeting_hours=2.0,
        total_focus_hours=4.0,
        total_fragmented_hours=0.5,
        avg_daily_meeting_hours=2.0,
        avg_daily_fatigue_score=35.0,
        burnout_risk_level=FatigueLevel.MODERATE,
        back_to_back_chains_count=1,
        context_switches_total=2,
        lunch_compromised_days_count=0,
        out_of_hours_events_count=0,
        day_breakdowns=[],
        top_fatigue_days=[],
        recommendations=["Keep buffers"],
    )
    storage.save_audit(audit)
    history = storage.load_audit_history()
    assert len(history) == 1
    assert history[0]["burnout_risk_level"] == "MODERATE"
