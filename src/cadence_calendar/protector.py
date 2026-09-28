"""
Calendar buffer injection, lunch shield, and deep-work focus block protector engine.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from cadence_calendar.models import (
    BufferPlan,
    BufferRecommendation,
    CalendarEvent,
    EventType,
    WorkHoursConfig,
)


class BufferProtector:
    """Calculates and inserts transition buffers, lunch shields, and deep work focus blocks."""

    def __init__(self, work_hours: WorkHoursConfig | None = None):
        self.work_hours = work_hours or WorkHoursConfig()

    def generate_protection_plan(
        self,
        events: list[CalendarEvent],
        buffer_minutes: int = 10,
        min_focus_hours: float = 2.0,
        protect_lunch: bool = True,
    ) -> BufferPlan:
        """Generate a complete protection plan inserting buffers and focus blocks."""
        if not events:
            return BufferPlan(
                created_at_utc=datetime.now(timezone.utc).isoformat(),
                total_buffers_generated=0,
                total_buffer_minutes_added=0,
                total_deep_work_blocks_protected=0,
                protected_focus_hours_added=0.0,
                buffers=[],
            )

        grouped: dict[date, list[CalendarEvent]] = defaultdict(list)
        for ev in events:
            grouped[ev.start.date()].append(ev)

        recommendations: list[BufferRecommendation] = []
        deep_work_count = 0
        total_focus_minutes = 0

        for day_dt in sorted(grouped.keys()):
            day_events = sorted(grouped[day_dt], key=lambda e: e.start)
            ref_tz = day_events[0].start.tzinfo if day_events else timezone.utc

            work_start = datetime.combine(day_dt, self.work_hours.start_time, tzinfo=ref_tz)
            work_end = datetime.combine(day_dt, self.work_hours.end_time, tzinfo=ref_tz)
            lunch_start = datetime.combine(day_dt, self.work_hours.lunch_start, tzinfo=ref_tz)
            lunch_end = lunch_start + timedelta(minutes=self.work_hours.lunch_duration_minutes)

            meetings = [e for e in day_events if e.event_type not in (EventType.FOCUS_BLOCK, EventType.BUFFER_BLOCK)]

            # 1. Back-to-Back Transition Buffers
            for i, m in enumerate(meetings):
                if i < len(meetings) - 1:
                    next_m = meetings[i + 1]
                    gap_mins = int((next_m.start - m.end).total_seconds() / 60)
                    if 0 <= gap_mins <= buffer_minutes:
                        if gap_mins == 0:
                            buf_start = m.end
                            buf_end = m.end + timedelta(minutes=buffer_minutes)
                            dur = buffer_minutes
                        else:
                            buf_start = m.end
                            buf_end = next_m.start
                            dur = gap_mins

                        recommendations.append(
                            BufferRecommendation(
                                date_str=day_dt.isoformat(),
                                start=buf_start,
                                end=buf_end,
                                buffer_type="TRANSITION",
                                reason=f"Post-meeting reset between '{m.title}' and '{next_m.title}'",
                                duration_minutes=dur,
                            )
                        )

            # 2. Lunch Shield
            if protect_lunch:
                lunch_blocked = any(m.start < lunch_end and m.end > lunch_start for m in meetings)
                if not lunch_blocked:
                    recommendations.append(
                        BufferRecommendation(
                            date_str=day_dt.isoformat(),
                            start=lunch_start,
                            end=lunch_end,
                            buffer_type="LUNCH_SHIELD",
                            reason="Protected nutrition and mental recharge window (12:00 - 12:45)",
                            duration_minutes=self.work_hours.lunch_duration_minutes,
                        )
                    )

            # 3. Deep Work Focus Block Reservation
            # Find contiguous gaps >= min_focus_hours between work_start and work_end
            existing_busy = sorted(
                [e for e in day_events if e.end > work_start and e.start < work_end],
                key=lambda e: e.start,
            )

            # Also add lunch if protected
            if protect_lunch:
                busy_intervals = [(max(e.start, work_start), min(e.end, work_end)) for e in existing_busy]
                busy_intervals.append((lunch_start, lunch_end))
                busy_intervals.sort(key=lambda x: x[0])
            else:
                busy_intervals = [(max(e.start, work_start), min(e.end, work_end)) for e in existing_busy]

            # Merge overlapping intervals
            merged_busy: list[tuple[datetime, datetime]] = []
            for b_st, b_et in busy_intervals:
                if not merged_busy:
                    merged_busy.append((b_st, b_et))
                else:
                    last_st, last_et = merged_busy[-1]
                    if b_st <= last_et:
                        merged_busy[-1] = (last_st, max(last_et, b_et))
                    else:
                        merged_busy.append((b_st, b_et))

            # Scan gaps
            cursor = work_start
            for b_st, b_et in merged_busy:
                if b_st > cursor:
                    gap_mins = int((b_st - cursor).total_seconds() / 60)
                    if gap_mins >= int(min_focus_hours * 60):
                        recommendations.append(
                            BufferRecommendation(
                                date_str=day_dt.isoformat(),
                                start=cursor,
                                end=b_st,
                                buffer_type="DEEP_WORK_BLOCK",
                                reason=f"Protected {gap_mins // 60}h{gap_mins % 60:02d}m uninterrupted focus block",
                                duration_minutes=gap_mins,
                            )
                        )
                        deep_work_count += 1
                        total_focus_minutes += gap_mins
                cursor = max(cursor, b_et)

            if work_end > cursor:
                gap_mins = int((work_end - cursor).total_seconds() / 60)
                if gap_mins >= int(min_focus_hours * 60):
                    recommendations.append(
                        BufferRecommendation(
                            date_str=day_dt.isoformat(),
                            start=cursor,
                            end=work_end,
                            buffer_type="DEEP_WORK_BLOCK",
                            reason=f"Protected {gap_mins // 60}h{gap_mins % 60:02d}m uninterrupted focus block",
                            duration_minutes=gap_mins,
                        )
                    )
                    deep_work_count += 1
                    total_focus_minutes += gap_mins

        total_buf_mins = sum(r.duration_minutes for r in recommendations if r.buffer_type != "DEEP_WORK_BLOCK")

        return BufferPlan(
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            total_buffers_generated=len(recommendations),
            total_buffer_minutes_added=total_buf_mins,
            total_deep_work_blocks_protected=deep_work_count,
            protected_focus_hours_added=total_focus_minutes / 60.0,
            buffers=recommendations,
        )

    def apply_protection(
        self,
        events: list[CalendarEvent],
        plan: BufferPlan,
    ) -> list[CalendarEvent]:
        """Convert BufferPlan recommendations into CalendarEvents and combine with existing events."""
        protected_events = list(events)

        for b in plan.buffers:
            if b.buffer_type == "LUNCH_SHIELD":
                ev_type = EventType.LUNCH
                title = "🥗 Protected Lunch Break"
            elif b.buffer_type == "DEEP_WORK_BLOCK":
                ev_type = EventType.FOCUS_BLOCK
                title = "🚀 Deep Work (Do Not Book)"
            else:
                ev_type = EventType.BUFFER_BLOCK
                title = "🛡️ Cognitive Transition Buffer"

            new_ev = CalendarEvent(
                id=f"cadence-buf-{uuid.uuid4().hex[:8]}",
                title=title,
                start=b.start,
                end=b.end,
                attendees=[],
                event_type=ev_type,
                is_recurring=False,
                location_or_url="",
                is_focus_protected=(ev_type == EventType.FOCUS_BLOCK),
                tags=["cadence-managed", b.buffer_type.lower()],
            )
            protected_events.append(new_ev)

        return sorted(protected_events, key=lambda e: e.start)
