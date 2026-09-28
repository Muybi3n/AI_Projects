"""
Unit tests for CadenceCompanion offline heuristic reasoner and pluggable LLM adapter.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import json
from datetime import datetime, timezone

from cadence_calendar.ai_companion import CadenceCompanion
from cadence_calendar.models import (
    DayMetrics,
    FatigueAuditResult,
    FatigueLevel,
)


def _mock_audit_result() -> FatigueAuditResult:
    dm = DayMetrics(
        date_str="2026-09-28",
        day_name="Monday",
        total_meeting_minutes=270,
        focus_time_minutes=90,
        fragmented_gap_minutes=60,
        context_switches_count=4,
        max_consecutive_meeting_minutes=150,
        back_to_back_count=2,
        out_of_hours_meeting_minutes=30,
        lunch_encroached_minutes=20,
        fatigue_score=75.0,
        fatigue_level=FatigueLevel.HIGH,
        buffer_deficit_minutes=40,
        events_count=6,
    )
    return FatigueAuditResult(
        audit_date_utc=datetime.now(timezone.utc).isoformat(),
        total_events=6,
        analyzed_days_count=1,
        total_meeting_hours=4.5,
        total_focus_hours=1.5,
        total_fragmented_hours=1.0,
        avg_daily_meeting_hours=4.5,
        avg_daily_fatigue_score=75.0,
        burnout_risk_level=FatigueLevel.HIGH,
        back_to_back_chains_count=2,
        context_switches_total=4,
        lunch_compromised_days_count=1,
        out_of_hours_events_count=1,
        day_breakdowns=[dm],
        top_fatigue_days=["2026-09-28 (Monday): 75/100 [HIGH] - 4h30m meetings"],
        recommendations=["Insert 10m buffers", "Protect lunch"],
    )


def test_companion_offline_heuristic_queries():
    audit = _mock_audit_result()
    companion = CadenceCompanion()

    # Query 1: Fatigue / Burnout
    r1 = companion.consult("How high is my burnout risk this week?", audit)
    assert "HIGH" in r1.summary or "75.0" in r1.summary
    assert len(r1.recommendations) > 0

    # Query 2: Buffers
    r2 = companion.consult("Can we insert transition buffers between back to back meetings?", audit)
    assert "back-to-back" in r2.summary.lower()
    assert any("buffer" in a.lower() for a in r2.action_items)

    # Query 3: Focus / Deep Work
    r3 = companion.consult("How do I protect deep work coding blocks?", audit)
    assert "focus" in r3.summary.lower()

    # Query 4: Swiss cheese
    r4 = companion.consult("How do I fix my Swiss cheese calendar gaps?", audit)
    assert "fragmented" in r4.summary.lower() or "swiss" in r4.recommendations[0].lower()

    # Query 5: Decline script
    r5 = companion.consult("Give me a script to decline an unnecessary meeting", audit)
    assert "script" in r5.summary.lower() or any("async" in r.lower() for r in r5.recommendations)

    # Query 6: Friday
    r6 = companion.consult("Should we institute focus Friday?", audit)
    assert "friday" in r6.summary.lower() or any("friday" in r.lower() for r in r6.recommendations)

    # Query 7: General
    r7 = companion.consult("General overview", audit)
    assert "Calendar Health Overview" in r7.summary


def test_companion_pluggable_llm_json_and_fallback():
    audit = _mock_audit_result()

    # 1. Valid JSON callable
    def mock_llm_json(query: str, context: dict) -> str:
        return json.dumps(
            {
                "summary": "Custom LLM Summary: Meeting load is elevated.",
                "metrics_highlight": {"strain": "high"},
                "recommendations": ["Delegate standup"],
                "action_items": ["Block 2 hours"],
            }
        )

    c_llm = CadenceCompanion(custom_llm_callable=mock_llm_json)
    res = c_llm.consult("What should I do?", audit)
    assert "Custom LLM Summary" in res.summary
    assert res.recommendations == ["Delegate standup"]

    # 2. Raw text / malformed JSON fallback
    def mock_llm_raw(query: str, context: dict) -> str:
        return "I recommend declining non-critical meetings and taking a walk."

    c_raw = CadenceCompanion(custom_llm_callable=mock_llm_raw)
    res_raw = c_raw.consult("Advice please", audit)
    assert "I recommend declining non-critical meetings" in res_raw.summary
    assert len(res_raw.recommendations) > 0
