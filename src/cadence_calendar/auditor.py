"""
Calendar fatigue scoring, cognitive load analytics, and Swiss-cheese fragmentation auditor.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from cadence_calendar.models import (
    CalendarEvent,
    DayMetrics,
    EventType,
    FatigueAuditResult,
    FatigueLevel,
    WorkHoursConfig,
)


class CalendarAuditor:
    """Audits calendar events for fatigue, back-to-back overload, fragmented time loss, and burnout risk."""

    def __init__(self, work_hours: WorkHoursConfig | None = None):
        self.work_hours = work_hours or WorkHoursConfig()

    def audit_events(
        self,
        events: list[CalendarEvent],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> FatigueAuditResult:
        """Run a comprehensive calendar fatigue audit across the given events."""
        if not events:
            now_iso = datetime.now(timezone.utc).isoformat()
            return FatigueAuditResult(
                audit_date_utc=now_iso,
                total_events=0,
                analyzed_days_count=0,
                total_meeting_hours=0.0,
                total_focus_hours=0.0,
                total_fragmented_hours=0.0,
                avg_daily_meeting_hours=0.0,
                avg_daily_fatigue_score=0.0,
                burnout_risk_level=FatigueLevel.SAFE,
                back_to_back_chains_count=0,
                context_switches_total=0,
                lunch_compromised_days_count=0,
                out_of_hours_events_count=0,
                day_breakdowns=[],
                top_fatigue_days=[],
                recommendations=["No calendar events found to audit. Ingest your calendar with 'cadence ingest'."],
            )

        # Filter by date if specified
        filtered_events = []
        for ev in events:
            ev_date = ev.start.date()
            if start_date and ev_date < start_date:
                continue
            if end_date and ev_date > end_date:
                continue
            filtered_events.append(ev)

        # Group events by date
        grouped: dict[date, list[CalendarEvent]] = defaultdict(list)
        for ev in filtered_events:
            grouped[ev.start.date()].append(ev)

        # Audit each day
        day_metrics_list: list[DayMetrics] = []
        for day_dt in sorted(grouped.keys()):
            day_events = sorted(grouped[day_dt], key=lambda e: e.start)
            metrics = self._audit_single_day(day_dt, day_events)
            day_metrics_list.append(metrics)

        # Aggregate summary statistics
        analyzed_days = len(day_metrics_list)
        total_meeting_mins = sum(d.total_meeting_minutes for d in day_metrics_list)
        total_focus_mins = sum(d.focus_time_minutes for d in day_metrics_list)
        total_frag_mins = sum(d.fragmented_gap_minutes for d in day_metrics_list)
        total_b2b_chains = sum(d.back_to_back_count for d in day_metrics_list)
        total_switches = sum(d.context_switches_count for d in day_metrics_list)
        lunch_compromised = sum(1 for d in day_metrics_list if d.lunch_encroached_minutes > 15)
        out_of_hours_count = sum(1 for d in day_metrics_list if d.out_of_hours_meeting_minutes > 0)

        total_meeting_hours = total_meeting_mins / 60.0
        total_focus_hours = total_focus_mins / 60.0
        total_fragmented_hours = total_frag_mins / 60.0

        avg_meeting_hours = total_meeting_hours / analyzed_days if analyzed_days > 0 else 0.0
        avg_fatigue = sum(d.fatigue_score for d in day_metrics_list) / analyzed_days if analyzed_days > 0 else 0.0

        burnout_risk = self._classify_fatigue_level(avg_fatigue)

        # Top fatigue days
        top_days = [
            f"{d.date_str} ({d.day_name}): {d.fatigue_score:.0f}/100 [{d.fatigue_level.value}] - {d.total_meeting_minutes // 60}h{d.total_meeting_minutes % 60:02d}m meetings"
            for d in sorted(day_metrics_list, key=lambda d: d.fatigue_score, reverse=True)[:3]
        ]

        # Generate rule-based recommendations
        recommendations = self._generate_recommendations(
            day_metrics_list,
            total_meeting_hours,
            total_fragmented_hours,
            total_b2b_chains,
            lunch_compromised,
            out_of_hours_count,
        )

        return FatigueAuditResult(
            audit_date_utc=datetime.now(timezone.utc).isoformat(),
            total_events=len(filtered_events),
            analyzed_days_count=analyzed_days,
            total_meeting_hours=total_meeting_hours,
            total_focus_hours=total_focus_hours,
            total_fragmented_hours=total_fragmented_hours,
            avg_daily_meeting_hours=avg_meeting_hours,
            avg_daily_fatigue_score=avg_fatigue,
            burnout_risk_level=burnout_risk,
            back_to_back_chains_count=total_b2b_chains,
            context_switches_total=total_switches,
            lunch_compromised_days_count=lunch_compromised,
            out_of_hours_events_count=out_of_hours_count,
            day_breakdowns=day_metrics_list,
            top_fatigue_days=top_days,
            recommendations=recommendations,
        )

    def _audit_single_day(self, day_dt: date, events: list[CalendarEvent]) -> DayMetrics:
        """Analyze meeting load, gaps, and fatigue for a single day."""
        day_name = day_dt.strftime("%A")
        # Define work window for this day in tz of events or UTC
        ref_tz = events[0].start.tzinfo if events else timezone.utc

        work_start = datetime.combine(day_dt, self.work_hours.start_time, tzinfo=ref_tz)
        work_end = datetime.combine(day_dt, self.work_hours.end_time, tzinfo=ref_tz)
        lunch_start = datetime.combine(day_dt, self.work_hours.lunch_start, tzinfo=ref_tz)
        lunch_end = lunch_start + timedelta(minutes=self.work_hours.lunch_duration_minutes)

        meetings = [e for e in events if e.event_type not in (EventType.FOCUS_BLOCK, EventType.BUFFER_BLOCK)]
        focus_events = [e for e in events if e.event_type == EventType.FOCUS_BLOCK]

        total_meeting_mins = sum(m.duration_minutes for m in meetings)
        out_of_hours_mins = 0
        lunch_encroached_mins = 0

        # Check out of hours and lunch collisions
        for m in meetings:
            # Out of hours before
            if m.start < work_start:
                ooh_before = min(m.end, work_start) - m.start
                out_of_hours_mins += max(0, int(ooh_before.total_seconds() / 60))
            # Out of hours after
            if m.end > work_end:
                ooh_after = m.end - max(m.start, work_end)
                out_of_hours_mins += max(0, int(ooh_after.total_seconds() / 60))

            # Lunch collision
            overlap_start = max(m.start, lunch_start)
            overlap_end = min(m.end, lunch_end)
            if overlap_end > overlap_start:
                lunch_encroached_mins += int((overlap_end - overlap_start).total_seconds() / 60)

        # Back to back analysis & consecutive stretches
        back_to_back_count = 0
        max_consecutive_mins = 0
        current_stretch_mins = 0
        fragmented_gap_mins = 0
        context_switches = 0

        sorted_meetings = sorted(meetings, key=lambda e: e.start)

        for i, m in enumerate(sorted_meetings):
            if i == 0:
                current_stretch_mins = m.duration_minutes
            else:
                prev_m = sorted_meetings[i - 1]
                gap_delta = m.start - prev_m.end
                gap_minutes = int(gap_delta.total_seconds() / 60)

                if gap_minutes <= 5:
                    # Back to back meeting
                    back_to_back_count += 1
                    current_stretch_mins += m.duration_minutes
                else:
                    max_consecutive_mins = max(max_consecutive_mins, current_stretch_mins)
                    current_stretch_mins = m.duration_minutes
                    # "Swiss cheese" fragmented gap (short dead zone: 6m to 29m)
                    if 5 < gap_minutes < 30:
                        fragmented_gap_mins += gap_minutes

                # Context switch detection (different topic / event_type / attendees)
                if m.event_type != prev_m.event_type or set(m.attendees) != set(prev_m.attendees):
                    context_switches += 1

        max_consecutive_mins = max(max_consecutive_mins, current_stretch_mins)

        # Available deep focus time calculation (slots >= 60 min during work hours + explicit focus blocks)
        focus_mins = sum(f.duration_minutes for f in focus_events)

        # Calculate open slots between work_start and work_end
        timeline_events = sorted(
            [e for e in events if e.event_type != EventType.BUFFER_BLOCK and e.end > work_start and e.start < work_end],
            key=lambda e: e.start,
        )

        cursor = work_start
        for ev in timeline_events:
            ev_clamped_start = max(ev.start, work_start)
            if ev_clamped_start > cursor:
                slot_mins = int((ev_clamped_start - cursor).total_seconds() / 60)
                # If slot is uninterrupted and >= 60m (excluding lunch)
                if slot_mins >= 60:
                    focus_mins += slot_mins
            cursor = max(cursor, ev.end)

        if work_end > cursor:
            remaining_mins = int((work_end - cursor).total_seconds() / 60)
            if remaining_mins >= 60:
                focus_mins += remaining_mins

        # Buffer deficit: ideally 10 min per meeting transition
        ideal_buffers_mins = len(meetings) * self.work_hours.min_buffer_minutes
        buffer_deficit = max(0, ideal_buffers_mins - (len(events) - len(meetings)) * 10)

        # Calculate Fatigue Score (0 to 100)
        fatigue_score = self._compute_daily_fatigue_score(
            total_meeting_mins=total_meeting_mins,
            max_consecutive_mins=max_consecutive_mins,
            back_to_back_count=back_to_back_count,
            fragmented_gap_mins=fragmented_gap_mins,
            out_of_hours_mins=out_of_hours_mins,
            lunch_encroached_mins=lunch_encroached_mins,
            context_switches=context_switches,
        )

        fatigue_level = self._classify_fatigue_level(fatigue_score)

        return DayMetrics(
            date_str=day_dt.isoformat(),
            day_name=day_name,
            total_meeting_minutes=total_meeting_mins,
            focus_time_minutes=focus_mins,
            fragmented_gap_minutes=fragmented_gap_mins,
            context_switches_count=context_switches,
            max_consecutive_meeting_minutes=max_consecutive_mins,
            back_to_back_count=back_to_back_count,
            out_of_hours_meeting_minutes=out_of_hours_mins,
            lunch_encroached_minutes=lunch_encroached_mins,
            fatigue_score=fatigue_score,
            fatigue_level=fatigue_level,
            buffer_deficit_minutes=buffer_deficit,
            events_count=len(events),
        )

    def _compute_daily_fatigue_score(
        self,
        total_meeting_mins: int,
        max_consecutive_mins: int,
        back_to_back_count: int,
        fragmented_gap_mins: int,
        out_of_hours_mins: int,
        lunch_encroached_mins: int,
        context_switches: int,
    ) -> float:
        """Compute holistic cognitive fatigue score (0.0 to 100.0)."""
        score = 0.0

        # Meeting Volume (Max 45 pts)
        max_mins = self.work_hours.max_meeting_hours_per_day * 60
        meeting_ratio = min(1.5, total_meeting_mins / max_mins) if max_mins > 0 else 0
        score += meeting_ratio * 40.0

        # Back-to-Back & Consecutive Strain (Max 25 pts)
        if max_consecutive_mins >= 180:
            score += 25.0
        elif max_consecutive_mins >= 120:
            score += 18.0
        elif max_consecutive_mins >= 90:
            score += 10.0
        elif back_to_back_count >= 2:
            score += 6.0

        # Swiss Cheese Fragmentation (Max 15 pts)
        frag_hours = fragmented_gap_mins / 60.0
        score += min(15.0, frag_hours * 10.0)

        # Context Switching Strain (Max 10 pts)
        if context_switches >= 5:
            score += 10.0
        elif context_switches >= 3:
            score += 6.0
        elif context_switches >= 1:
            score += 3.0

        # Lunch Boundary Violation (Max 5 pts)
        if lunch_encroached_mins >= 30:
            score += 5.0
        elif lunch_encroached_mins > 0:
            score += 2.5

        # Out of Hours Extension (Max 10 pts)
        if out_of_hours_mins >= 60:
            score += 10.0
        elif out_of_hours_mins > 0:
            score += 5.0

        return min(100.0, max(0.0, score))

    def _classify_fatigue_level(self, score: float) -> FatigueLevel:
        if score <= 30.0:
            return FatigueLevel.SAFE
        elif score <= 60.0:
            return FatigueLevel.MODERATE
        elif score <= 80.0:
            return FatigueLevel.HIGH
        else:
            return FatigueLevel.CRITICAL

    def _generate_recommendations(
        self,
        day_metrics: list[DayMetrics],
        total_meeting_hours: float,
        total_fragmented_hours: float,
        total_b2b_chains: int,
        lunch_compromised_days: int,
        out_of_hours_count: int,
    ) -> list[str]:
        """Generate high-yield, actionable calendar optimization advice."""
        recs: list[str] = []

        if total_b2b_chains > 0:
            recs.append(
                f"🛡️ **Insert 10-Minute Cognitive Buffers:** Found {total_b2b_chains} back-to-back meeting sequences. Use 'cadence protect --apply' to automatically reserve transition buffers."
            )

        if total_fragmented_hours >= 1.5:
            recs.append(
                f"🧀 **Eliminate Swiss-Cheese Calendar Gaps:** Identified {total_fragmented_hours:.1f} hours lost in unworkable 15-25m fragmented gaps. Batch 1:1 syncs and team standups into dedicated morning or afternoon clusters."
            )

        if lunch_compromised_days > 0:
            recs.append(
                f"🥗 **Protect Lunch Hour (12:00-12:45):** Meeting conflicts encroached on lunch across {lunch_compromised_days} day(s). Enable 'LUNCH_SHIELD' to prevent noon scheduling creep."
            )

        if out_of_hours_count > 0:
            recs.append(
                f"⏰ **Enforce Boundary Guardrails:** Detected {out_of_hours_count} meeting(s) scheduled outside core work hours (09:00 - 17:00). Proactively negotiate async updates or reschedule within standard hours."
            )

        # Friday or High fatigue check
        friday_metrics = [d for d in day_metrics if d.day_name == "Friday"]
        if friday_metrics and any(f.fatigue_score > 40 for f in friday_metrics):
            recs.append(
                "🚀 **Institute 'Focus Friday':** Block Friday afternoons (13:00-17:00) for deep coding, documentation, and backlog triage with zero external syncs."
            )

        if not recs:
            recs.append(
                "✨ **Healthy Calendar Cadence:** Meeting load and focus reserves are within optimal parameters. Maintain 10m transition buffers."
            )

        return recs
