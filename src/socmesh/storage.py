"""
SQLite FTS5 Local Storage Catalog for indexed security events and incidents.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from .models import CorrelatedIncident, SecurityEvent


class SocmeshCatalog:
    """Local SQLite database for fast storage, retrieval, and full-text search."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            home = Path.home() / ".socmesh"
            home.mkdir(parents=True, exist_ok=True)
            self.db_path = home / "socmesh.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source TEXT,
                    timestamp TEXT,
                    source_ip TEXT,
                    destination_ip TEXT,
                    severity TEXT,
                    action TEXT,
                    event_type TEXT,
                    details TEXT,
                    raw_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    title TEXT,
                    primary_tactic TEXT,
                    risk_score INTEGER,
                    event_count INTEGER,
                    summary TEXT,
                    raw_json TEXT
                )
                """
            )

    def save_events(self, events: Sequence[SecurityEvent]) -> int:
        with sqlite3.connect(self.db_path) as conn:
            count = 0
            for e in events:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO events
                    (event_id, source, timestamp, source_ip, destination_ip, severity, action, event_type, details, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        e.event_id,
                        e.source.value,
                        e.timestamp,
                        e.source_ip,
                        e.destination_ip,
                        e.severity.value,
                        e.action,
                        e.event_type,
                        e.details,
                        json.dumps(e.to_dict()),
                    ),
                )
                count += 1
            return count

    def save_incidents(self, incidents: Sequence[CorrelatedIncident]) -> int:
        with sqlite3.connect(self.db_path) as conn:
            count = 0
            for inc in incidents:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO incidents
                    (incident_id, title, primary_tactic, risk_score, event_count, summary, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inc.incident_id,
                        inc.title,
                        inc.primary_tactic.value,
                        inc.risk_score,
                        inc.event_count,
                        inc.summary,
                        json.dumps(inc.to_dict()),
                    ),
                )
                count += 1
            return count

    def get_all_incidents(self) -> list[CorrelatedIncident]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT raw_json FROM incidents ORDER BY risk_score DESC")
            incidents = []
            for (raw,) in cursor.fetchall():
                data = json.loads(raw)
                # Parse back
                from .models import MitreTactic

                inc = CorrelatedIncident(
                    incident_id=data["incident_id"],
                    title=data["title"],
                    primary_tactic=MitreTactic(data["primary_tactic"]),
                    risk_score=data["risk_score"],
                    affected_hosts=data.get("affected_hosts", []),
                    source_ips=data.get("source_ips", []),
                    event_count=data.get("event_count", 1),
                    first_seen=data.get("first_seen", ""),
                    last_seen=data.get("last_seen", ""),
                    summary=data.get("summary", ""),
                    remediation_guidance=data.get("remediation_guidance", []),
                )
                incidents.append(inc)
            return incidents
