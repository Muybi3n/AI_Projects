"""
Unit tests for CalendarParser, format converters, and PII sanitization.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from cadence_calendar.models import CalendarEvent, EventType
from cadence_calendar.parser import CalendarParser


def test_classify_event_type():
    assert CalendarParser.classify_event_type("1:1 Sync with Alex") == EventType.ONE_ON_ONE
    assert CalendarParser.classify_event_type("Engineering Daily Standup") == EventType.TEAM_SYNC
    assert CalendarParser.classify_event_type("Company Town Hall All Hands") == EventType.ALL_HANDS
    assert CalendarParser.classify_event_type("Deep Work: Refactor Auth Engine") == EventType.FOCUS_BLOCK
    assert CalendarParser.classify_event_type("Lunch with Team") == EventType.LUNCH
    assert CalendarParser.classify_event_type("Candidate Technical Interview") == EventType.INTERVIEW
    assert CalendarParser.classify_event_type("Acme Corp Client Demo") == EventType.EXTERNAL_CLIENT
    assert CalendarParser.classify_event_type("Quarterly Review", attendee_count=2) == EventType.ONE_ON_ONE
    assert CalendarParser.classify_event_type("Quarterly Review", attendee_count=15) == EventType.ALL_HANDS
    assert CalendarParser.classify_event_type("Project Discussion", attendee_count=4) == EventType.GENERAL


def test_sanitize_pii():
    text = "Meeting with john.doe@enterprise.corp (cell: 555-123-4567) at https://zoom.us/j/12345?pwd=SecretPassword123"
    sanitized = CalendarParser.sanitize_pii(text)
    assert "[EMAIL_REDACTED]" in sanitized
    assert "john.doe@enterprise.corp" not in sanitized
    assert "[PHONE_REDACTED]" in sanitized
    assert "pwd=[REDACTED]" in sanitized
    assert "SecretPassword123" not in sanitized


def test_parse_ics_datetime():
    dt1 = CalendarParser.parse_ics_datetime("20260928T093000Z")
    assert dt1.year == 2026 and dt1.month == 9 and dt1.day == 28
    assert dt1.hour == 9 and dt1.minute == 30

    dt2 = CalendarParser.parse_ics_datetime("TZID=America/New_York:20260928T140000")
    assert dt2.year == 2026 and dt2.hour == 14 and dt2.minute == 0

    dt3 = CalendarParser.parse_ics_datetime("20260928")
    assert dt3.year == 2026 and dt3.month == 9 and dt3.day == 28 and dt3.hour == 0


def test_parse_ics_text_and_unfolding():
    ics_raw = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//Test//EN\n"
        "BEGIN:VEVENT\n"
        "UID:test-event-001\n"
        "SUMMARY:Weekly Sprint\n"
        " Planning with Team\n"
        "DTSTART:20260928T090000Z\n"
        "DTEND:20260928T100000Z\n"
        "LOCATION:https://meet.example.com/sprint?pwd=SecretMeetingKey\n"
        "ATTENDEE:mailto:lead@example.com\n"
        "ATTENDEE:mailto:dev@example.com\n"
        "RRULE:FREQ=WEEKLY;BYDAY=MO\n"
        "END:VEVENT\n"
        "BEGIN:VEVENT\n"
        "UID:test-event-002\n"
        "SUMMARY:1-on-1 with Manager\n"
        "DTSTART:20260928T100000Z\n"
        "DTEND:20260928T103000Z\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )

    events = CalendarParser.parse_ics_text(ics_raw, sanitize=True)
    assert len(events) == 2

    e1 = events[0]
    assert e1.id == "test-event-001"
    assert "Weekly Sprint" in e1.title
    assert e1.event_type == EventType.TEAM_SYNC
    assert e1.is_recurring is True
    assert "pwd=[REDACTED]" in e1.location_or_url
    assert len(e1.attendees) == 2
    assert "[EMAIL_REDACTED]" in e1.attendees[0]

    e2 = events[1]
    assert e2.id == "test-event-002"
    assert e2.event_type == EventType.ONE_ON_ONE
    assert e2.duration_minutes == 30


def test_parse_json_and_csv_text():
    json_raw = json.dumps(
        {
            "events": [
                {
                    "id": "json-1",
                    "title": "Deep Work Block",
                    "start": "2026-09-28T13:00:00+00:00",
                    "end": "2026-09-28T15:00:00+00:00",
                    "attendees": ["alice@example.com"],
                }
            ]
        }
    )
    json_events = CalendarParser.parse_json_text(json_raw, sanitize=True)
    assert len(json_events) == 1
    assert json_events[0].id == "json-1"
    assert json_events[0].event_type == EventType.FOCUS_BLOCK
    assert json_events[0].is_focus_protected is True

    csv_raw = """title,start,end,attendees,is_recurring,location
Sprint Demo,2026-09-28T15:00:00+00:00,2026-09-28T16:00:00+00:00,bob@example.com;carol@example.com,false,Room A
"""
    csv_events = CalendarParser.parse_csv_text(csv_raw, sanitize=True)
    assert len(csv_events) == 1
    assert csv_events[0].title == "Sprint Demo"
    assert len(csv_events[0].attendees) == 2


def test_parse_file_and_export_to_ics(tmp_path: Path):
    f_ics = tmp_path / "sample.ics"
    events_in = [
        CalendarEvent(
            id="exp-1",
            title="Design Review",
            start=datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 15, 0, tzinfo=timezone.utc),
            attendees=["team@example.com"],
            event_type=EventType.TEAM_SYNC,
        )
    ]
    ics_out = CalendarParser.export_to_ics(events_in, cal_name="Test Cal")
    f_ics.write_text(ics_out, encoding="utf-8")

    parsed = CalendarParser.parse_file(f_ics, sanitize=False)
    assert len(parsed) == 1
    assert parsed[0].id == "exp-1"
    assert parsed[0].title == "Design Review"
    assert parsed[0].duration_minutes == 60
