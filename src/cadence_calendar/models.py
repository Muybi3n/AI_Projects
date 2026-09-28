"""
cadence-calendar domain data models and enums.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any


class EventType(str, Enum):
    ONE_ON_ONE = "1_ON_1"
    TEAM_SYNC = "TEAM_SYNC"
    ALL_HANDS = "ALL_HANDS"
    FOCUS_BLOCK = "FOCUS_BLOCK"
    BUFFER_BLOCK = "BUFFER_BLOCK"
    EXTERNAL_CLIENT = "EXTERNAL_CLIENT"
    INTERVIEW = "INTERVIEW"
    AD_HOC = "AD_HOC"
    LUNCH = "LUNCH"
    GENERAL = "GENERAL"


class FatigueLevel(str, Enum):
    SAFE = "SAFE"  # Score 0 - 30: Healthy cognitive balance
    MODERATE = "MODERATE"  # Score 31 - 60: Moderate meeting load, monitor buffers
    HIGH = "HIGH"  # Score 61 - 80: High fatigue, significant fragmentation
    CRITICAL = "CRITICAL"  # Score 81 - 100: Severe burnout risk, back-to-back overload


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str] = field(default_factory=list)
    event_type: EventType = EventType.GENERAL
    is_recurring: bool = False
    location_or_url: str = ""
    is_focus_protected: bool = False
    tags: list[str] = field(default_factory=list)

    @property
    def duration_minutes(self) -> int:
        delta = self.end - self.start
        return max(0, int(delta.total_seconds() / 60))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
            "attendees": self.attendees,
            "event_type": self.event_type.value,
            "is_recurring": self.is_recurring,
            "location_or_url": self.location_or_url,
            "is_focus_protected": self.is_focus_protected,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalendarEvent:
        event_type = EventType(data.get("event_type", EventType.GENERAL.value))
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            start=datetime.fromisoformat(data["start"]),
            end=datetime.fromisoformat(data["end"]),
            attendees=list(data.get("attendees", [])),
            event_type=event_type,
            is_recurring=bool(data.get("is_recurring", False)),
            location_or_url=str(data.get("location_or_url", "")),
            is_focus_protected=bool(data.get("is_focus_protected", False)),
            tags=list(data.get("tags", [])),
        )


@dataclass
class WorkHoursConfig:
    start_time: time = field(default_factory=lambda: time(9, 0))
    end_time: time = field(default_factory=lambda: time(17, 0))
    work_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Monday = 0, Friday = 4
    lunch_start: time = field(default_factory=lambda: time(12, 0))
    lunch_duration_minutes: int = 45
    target_focus_hours_per_day: float = 3.5
    max_meeting_hours_per_day: float = 4.0
    min_buffer_minutes: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "work_days": self.work_days,
            "lunch_start": self.lunch_start.strftime("%H:%M"),
            "lunch_duration_minutes": self.lunch_duration_minutes,
            "target_focus_hours_per_day": self.target_focus_hours_per_day,
            "max_meeting_hours_per_day": self.max_meeting_hours_per_day,
            "min_buffer_minutes": self.min_buffer_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkHoursConfig:
        start_parts = [int(p) for p in data.get("start_time", "09:00").split(":")]
        end_parts = [int(p) for p in data.get("end_time", "17:00").split(":")]
        lunch_parts = [int(p) for p in data.get("lunch_start", "12:00").split(":")]
        return cls(
            start_time=time(start_parts[0], start_parts[1]),
            end_time=time(end_parts[0], end_parts[1]),
            work_days=data.get("work_days", [0, 1, 2, 3, 4]),
            lunch_start=time(lunch_parts[0], lunch_parts[1]),
            lunch_duration_minutes=int(data.get("lunch_duration_minutes", 45)),
            target_focus_hours_per_day=float(data.get("target_focus_hours_per_day", 3.5)),
            max_meeting_hours_per_day=float(data.get("max_meeting_hours_per_day", 4.0)),
            min_buffer_minutes=int(data.get("min_buffer_minutes", 10)),
        )


@dataclass
class DayMetrics:
    date_str: str  # YYYY-MM-DD
    day_name: str
    total_meeting_minutes: int
    focus_time_minutes: int
    fragmented_gap_minutes: int
    context_switches_count: int
    max_consecutive_meeting_minutes: int
    back_to_back_count: int
    out_of_hours_meeting_minutes: int
    lunch_encroached_minutes: int
    fatigue_score: float  # 0 to 100
    fatigue_level: FatigueLevel
    buffer_deficit_minutes: int
    events_count: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fatigue_level"] = self.fatigue_level.value
        return data


@dataclass
class FatigueAuditResult:
    audit_date_utc: str
    total_events: int
    analyzed_days_count: int
    total_meeting_hours: float
    total_focus_hours: float
    total_fragmented_hours: float
    avg_daily_meeting_hours: float
    avg_daily_fatigue_score: float
    burnout_risk_level: FatigueLevel
    back_to_back_chains_count: int
    context_switches_total: int
    lunch_compromised_days_count: int
    out_of_hours_events_count: int
    day_breakdowns: list[DayMetrics] = field(default_factory=list)
    top_fatigue_days: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_date_utc": self.audit_date_utc,
            "total_events": self.total_events,
            "analyzed_days_count": self.analyzed_days_count,
            "total_meeting_hours": round(self.total_meeting_hours, 2),
            "total_focus_hours": round(self.total_focus_hours, 2),
            "total_fragmented_hours": round(self.total_fragmented_hours, 2),
            "avg_daily_meeting_hours": round(self.avg_daily_meeting_hours, 2),
            "avg_daily_fatigue_score": round(self.avg_daily_fatigue_score, 1),
            "burnout_risk_level": self.burnout_risk_level.value,
            "back_to_back_chains_count": self.back_to_back_chains_count,
            "context_switches_total": self.context_switches_total,
            "lunch_compromised_days_count": self.lunch_compromised_days_count,
            "out_of_hours_events_count": self.out_of_hours_events_count,
            "day_breakdowns": [d.to_dict() for d in self.day_breakdowns],
            "top_fatigue_days": self.top_fatigue_days,
            "recommendations": self.recommendations,
        }


@dataclass
class BufferRecommendation:
    date_str: str
    start: datetime
    end: datetime
    buffer_type: str  # "COGNITIVE_RESET", "DEEP_WORK_BLOCK", "LUNCH_SHIELD", "TRANSITION"
    reason: str
    duration_minutes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_str": self.date_str,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "buffer_type": self.buffer_type,
            "reason": self.reason,
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class BufferPlan:
    created_at_utc: str
    total_buffers_generated: int
    total_buffer_minutes_added: int
    total_deep_work_blocks_protected: int
    protected_focus_hours_added: float
    buffers: list[BufferRecommendation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "total_buffers_generated": self.total_buffers_generated,
            "total_buffer_minutes_added": self.total_buffer_minutes_added,
            "total_deep_work_blocks_protected": self.total_deep_work_blocks_protected,
            "protected_focus_hours_added": round(self.protected_focus_hours_added, 2),
            "buffers": [b.to_dict() for b in self.buffers],
        }


@dataclass
class CompanionResponse:
    query: str
    summary: str
    metrics_highlight: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "summary": self.summary,
            "metrics_highlight": self.metrics_highlight,
            "recommendations": self.recommendations,
            "action_items": self.action_items,
        }
