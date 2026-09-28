"""
Local-first JSON state storage and configuration management.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cadence_calendar.models import CalendarEvent, FatigueAuditResult, WorkHoursConfig


class CadenceStorage:
    """Manages local JSON persistence for calendar profiles, events, and audit histories."""

    def __init__(self, data_dir: str | Path | None = None):
        if data_dir:
            self.root = Path(data_dir).expanduser().resolve()
        else:
            self.root = Path("~/.cadence").expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.root / "profile.json"
        self.events_path = self.root / "events.json"
        self.audits_path = self.root / "audits.json"

    def save_profile(self, name: str, work_hours: WorkHoursConfig, metadata: dict[str, Any] | None = None) -> None:
        """Save user calendar profile."""
        payload = {
            "name": name,
            "work_hours": work_hours.to_dict(),
            "metadata": metadata or {},
        }
        self.profile_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_profile(self) -> tuple[str, WorkHoursConfig, dict[str, Any]]:
        """Load user calendar profile or return defaults."""
        if not self.profile_path.exists():
            return "Default Profile", WorkHoursConfig(), {}
        try:
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            name = data.get("name", "Default Profile")
            wh = WorkHoursConfig.from_dict(data.get("work_hours", {}))
            meta = data.get("metadata", {})
            return name, wh, meta
        except (json.JSONDecodeError, KeyError, ValueError):
            return "Default Profile", WorkHoursConfig(), {}

    def save_events(self, events: list[CalendarEvent]) -> None:
        """Save full list of CalendarEvents."""
        payload = [e.to_dict() for e in events]
        self.events_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_events(self) -> list[CalendarEvent]:
        """Load list of CalendarEvents."""
        if not self.events_path.exists():
            return []
        try:
            raw = json.loads(self.events_path.read_text(encoding="utf-8"))
            return [CalendarEvent.from_dict(item) for item in raw]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def append_events(self, new_events: list[CalendarEvent]) -> int:
        """Merge new events with existing events (deduplicating by id and start/title)."""
        existing = self.load_events()
        seen_keys = {(e.id, e.title, e.start.isoformat()) for e in existing}

        added_count = 0
        for ev in new_events:
            key = (ev.id, ev.title, ev.start.isoformat())
            if key not in seen_keys:
                existing.append(ev)
                seen_keys.add(key)
                added_count += 1

        existing.sort(key=lambda e: e.start)
        self.save_events(existing)
        return added_count

    def clear_events(self) -> None:
        """Clear all stored calendar events."""
        if self.events_path.exists():
            self.events_path.unlink()

    def save_audit(self, audit: FatigueAuditResult) -> None:
        """Append audit result to audits log."""
        history = self.load_audit_history()
        history.append(audit.to_dict())
        self.audits_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def load_audit_history(self) -> list[dict[str, Any]]:
        """Load history of past audits."""
        if not self.audits_path.exists():
            return []
        try:
            return json.loads(self.audits_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return []
