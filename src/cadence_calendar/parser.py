"""
Calendar ingestion, serialization, and PII de-identification engine.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cadence_calendar.models import CalendarEvent, EventType


class CalendarParser:
    """Robust stdlib parser for iCalendar (.ics), JSON, and CSV calendar feeds."""

    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_REGEX = re.compile(r"\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b")
    ZOOM_PWD_REGEX = re.compile(r"(pwd=[a-zA-Z0-9]+|passcode=[a-zA-Z0-9]+)", re.IGNORECASE)

    @classmethod
    def classify_event_type(cls, title: str, attendee_count: int = 1) -> EventType:
        """Classify calendar event into standard EventType based on title heuristics."""
        tl = title.lower()
        if any(w in tl for w in ["focus", "deep work", "heads down", "flow time", "no meeting"]):
            return EventType.FOCUS_BLOCK
        if any(w in tl for w in ["buffer", "cognitive reset", "transition"]):
            return EventType.BUFFER_BLOCK
        if any(w in tl for w in ["lunch", "dinner", "meal break"]):
            return EventType.LUNCH
        if any(w in tl for w in ["interview", "candidate", "screen", "debrief"]):
            return EventType.INTERVIEW
        if any(w in tl for w in ["all hands", "town hall", "all-hands", "company sync"]):
            return EventType.ALL_HANDS
        if any(w in tl for w in ["1:1", "1-on-1", "1 on 1", "one on one", "catch up with", "check-in with"]):
            return EventType.ONE_ON_ONE
        if any(w in tl for w in ["client", "customer", "partner", "vendor", "demo for", "sales pitch"]):
            return EventType.EXTERNAL_CLIENT
        if any(
            w in tl for w in ["standup", "sprint", "retro", "team sync", "staff meeting", "weekly sync", "planning"]
        ):
            return EventType.TEAM_SYNC
        if attendee_count == 2:
            return EventType.ONE_ON_ONE
        if attendee_count > 10:
            return EventType.ALL_HANDS
        return EventType.GENERAL

    @classmethod
    def sanitize_pii(cls, text: str) -> str:
        """De-identify emails, phone numbers, and meeting passwords from calendar text."""
        if not text:
            return ""
        s = cls.EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
        s = cls.PHONE_REGEX.sub("[PHONE_REDACTED]", s)
        s = cls.ZOOM_PWD_REGEX.sub("pwd=[REDACTED]", s)
        return s

    @classmethod
    def parse_ics_datetime(cls, dt_str: str) -> datetime:
        """Parse iCalendar DTSTART / DTEND strings into timezone-aware or UTC datetime."""
        dt_str = dt_str.strip()
        # Strip trailing parameters e.g., TZID=America/New_York:20260928T090000
        if ":" in dt_str:
            dt_str = dt_str.split(":")[-1]
        dt_str = dt_str.strip()

        if len(dt_str) == 8 and dt_str.isdigit():
            # Date only (all-day event) e.g. 20260928
            year = int(dt_str[0:4])
            month = int(dt_str[4:6])
            day = int(dt_str[6:8])
            return datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)

        # Standard 20260928T143000 or 20260928T143000Z
        dt_clean = dt_str.rstrip("Z")
        if "T" in dt_clean:
            parts = dt_clean.split("T")
            d_part = parts[0]
            t_part = parts[1]
            year = int(d_part[0:4])
            month = int(d_part[4:6])
            day = int(d_part[6:8])
            hour = int(t_part[0:2])
            minute = int(t_part[2:4]) if len(t_part) >= 4 else 0
            second = int(t_part[4:6]) if len(t_part) >= 6 else 0
            return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

        # Fallback ISO parser
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return datetime.now(timezone.utc)

    @classmethod
    def parse_ics_text(cls, ics_content: str, sanitize: bool = True) -> list[CalendarEvent]:
        """Parse raw RFC-5545 iCalendar text into a list of CalendarEvent objects."""
        events: list[CalendarEvent] = []
        lines = ics_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # Unfold lines (RFC 5545 multi-line continuation)
        unfolded_lines: list[str] = []
        for line in lines:
            if line.startswith(" ") or line.startswith("\t"):
                if unfolded_lines:
                    unfolded_lines[-1] += line[1:]
            else:
                unfolded_lines.append(line)

        in_vevent = False
        current_data: dict[str, Any] = {}

        for line in unfolded_lines:
            line = line.strip()
            if not line:
                continue

            if line == "BEGIN:VEVENT":
                in_vevent = True
                current_data = {
                    "id": str(uuid.uuid4()),
                    "attendees": [],
                    "tags": [],
                    "is_recurring": False,
                    "location_or_url": "",
                }
                continue

            if line == "END:VEVENT":
                in_vevent = False
                if "title" in current_data and "start" in current_data and "end" in current_data:
                    title = current_data["title"]
                    if sanitize:
                        title = cls.sanitize_pii(title)
                        loc = cls.sanitize_pii(current_data.get("location_or_url", ""))
                    else:
                        loc = current_data.get("location_or_url", "")

                    ev_type = cls.classify_event_type(title, len(current_data["attendees"]))
                    is_focus = ev_type == EventType.FOCUS_BLOCK

                    event = CalendarEvent(
                        id=current_data.get("uid", current_data["id"]),
                        title=title,
                        start=current_data["start"],
                        end=current_data["end"],
                        attendees=current_data["attendees"],
                        event_type=ev_type,
                        is_recurring=current_data.get("is_recurring", False),
                        location_or_url=loc,
                        is_focus_protected=is_focus,
                        tags=current_data["tags"],
                    )
                    events.append(event)
                continue

            if in_vevent:
                if line.startswith("UID:"):
                    current_data["uid"] = line.split(":", 1)[1].strip()
                elif line.startswith("SUMMARY:"):
                    current_data["title"] = line.split(":", 1)[1].strip()
                elif line.startswith("DTSTART"):
                    current_data["start"] = cls.parse_ics_datetime(line)
                elif line.startswith("DTEND"):
                    current_data["end"] = cls.parse_ics_datetime(line)
                elif line.startswith("RRULE:"):
                    current_data["is_recurring"] = True
                elif line.startswith("LOCATION:"):
                    current_data["location_or_url"] = line.split(":", 1)[1].strip()
                elif line.startswith("ATTENDEE"):
                    att = line.split(":", 1)[1].strip().replace("mailto:", "").replace("MAILTO:", "")
                    if sanitize:
                        att = cls.sanitize_pii(att)
                    current_data["attendees"].append(att)

        return sorted(events, key=lambda e: e.start)

    @classmethod
    def parse_json_text(cls, json_content: str, sanitize: bool = True) -> list[CalendarEvent]:
        """Parse JSON list of events."""
        raw_list = json.loads(json_content)
        if isinstance(raw_list, dict) and "events" in raw_list:
            raw_list = raw_list["events"]

        events: list[CalendarEvent] = []
        for item in raw_list:
            title = item.get("title", "Untitled Event")
            if sanitize:
                title = cls.sanitize_pii(title)
            start = datetime.fromisoformat(item["start"])
            end = datetime.fromisoformat(item["end"])
            attendees = item.get("attendees", [])
            if sanitize:
                attendees = [cls.sanitize_pii(a) for a in attendees]

            ev_type_str = item.get("event_type")
            if ev_type_str:
                ev_type = EventType(ev_type_str)
            else:
                ev_type = cls.classify_event_type(title, len(attendees))

            event = CalendarEvent(
                id=str(item.get("id", uuid.uuid4())),
                title=title,
                start=start,
                end=end,
                attendees=attendees,
                event_type=ev_type,
                is_recurring=bool(item.get("is_recurring", False)),
                location_or_url=cls.sanitize_pii(str(item.get("location_or_url", "")))
                if sanitize
                else str(item.get("location_or_url", "")),
                is_focus_protected=bool(item.get("is_focus_protected", ev_type == EventType.FOCUS_BLOCK)),
                tags=list(item.get("tags", [])),
            )
            events.append(event)
        return sorted(events, key=lambda e: e.start)

    @classmethod
    def parse_csv_text(cls, csv_content: str, sanitize: bool = True) -> list[CalendarEvent]:
        """Parse CSV rows into CalendarEvent list."""
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        events: list[CalendarEvent] = []
        for row in reader:
            title = row.get("title") or row.get("summary") or "Untitled Event"
            if sanitize:
                title = cls.sanitize_pii(title)
            start_str = row.get("start") or row.get("start_time") or ""
            end_str = row.get("end") or row.get("end_time") or ""
            if not start_str or not end_str:
                continue
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
            attendees_raw = row.get("attendees", "")
            attendees = [a.strip() for a in attendees_raw.split(";") if a.strip()]
            if sanitize:
                attendees = [cls.sanitize_pii(a) for a in attendees]

            ev_type = cls.classify_event_type(title, len(attendees))
            events.append(
                CalendarEvent(
                    id=str(row.get("id", uuid.uuid4())),
                    title=title,
                    start=start,
                    end=end,
                    attendees=attendees,
                    event_type=ev_type,
                    is_recurring=row.get("is_recurring", "").lower() in ["true", "1", "yes"],
                    location_or_url=cls.sanitize_pii(row.get("location", "")) if sanitize else row.get("location", ""),
                    is_focus_protected=ev_type == EventType.FOCUS_BLOCK,
                    tags=[t.strip() for t in row.get("tags", "").split(",") if t.strip()],
                )
            )
        return sorted(events, key=lambda e: e.start)

    @classmethod
    def parse_file(cls, file_path: str | Path, sanitize: bool = True) -> list[CalendarEvent]:
        """Ingest calendar events from file path according to extension (.ics, .json, .csv)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Calendar file not found: {path}")

        content = path.read_text(encoding="utf-8", errors="replace")
        suffix = path.suffix.lower()

        if suffix in [".ics", ".ical"]:
            return cls.parse_ics_text(content, sanitize=sanitize)
        elif suffix == ".json":
            return cls.parse_json_text(content, sanitize=sanitize)
        elif suffix == ".csv":
            return cls.parse_csv_text(content, sanitize=sanitize)
        else:
            # Try ics, then json, then csv
            try:
                return cls.parse_ics_text(content, sanitize=sanitize)
            except (ValueError, KeyError, IndexError):
                try:
                    return cls.parse_json_text(content, sanitize=sanitize)
                except (json.JSONDecodeError, KeyError, ValueError):
                    return cls.parse_csv_text(content, sanitize=sanitize)

    @classmethod
    def export_to_ics(cls, events: list[CalendarEvent], cal_name: str = "Cadence Protected Calendar") -> str:
        """Export list of CalendarEvents into standard RFC-5545 iCalendar string."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Cadence Calendar Engine//EN",
            f"X-WR-CALNAME:{cal_name}",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for ev in events:
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{ev.id}")
            # Format UTC string e.g. 20260928T140000Z
            st_str = ev.start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            et_str = ev.end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            lines.append(f"DTSTART:{st_str}")
            lines.append(f"DTEND:{et_str}")
            lines.append(f"SUMMARY:{ev.title}")
            lines.append(f"CATEGORIES:{ev.event_type.value}")
            if ev.location_or_url:
                lines.append(f"LOCATION:{ev.location_or_url}")
            for att in ev.attendees:
                lines.append(f"ATTENDEE:mailto:{att}")
            lines.append("STATUS:CONFIRMED")
            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"
