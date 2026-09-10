# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Academic calendar & syllabus ingestion engine: Universal parser for K-12 school calendars and university syllabi.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, ClassVar

from .models import HolidayCalendar


class AcademicEventType(str, Enum):
    STUDENT_HOLIDAY = "student_holiday"
    TEACHER_WORKDAY = "teacher_workday"
    BREAK = "extended_break"
    EARLY_RELEASE = "early_release"
    EXAM_PERIOD = "exam_period"
    NO_CLASS = "no_class"


@dataclass
class AcademicEvent:
    id: str
    name: str
    event_type: AcademicEventType
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    source_label: str = "General School / Syllabus"
    affected_students: list[str] = field(default_factory=list)
    notes: str = ""

    def get_all_dates(self) -> list[date]:
        s = date.fromisoformat(self.start_date)
        e = date.fromisoformat(self.end_date)
        return [s + timedelta(days=i) for i in range((e - s).days + 1)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "event_type": self.event_type.value,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "source_label": self.source_label,
            "affected_students": self.affected_students,
            "notes": self.notes,
        }


class SyllabusParser:
    """Universal parser for academic syllabi, district schedules, and K-12 calendars."""

    MONTH_MAP: ClassVar[dict[str, int]] = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }

    @classmethod
    def parse_text(
        cls,
        text: str,
        source_label: str = "School Calendar",
        default_year: int = 2026,
        students: list[str] | None = None,
    ) -> list[AcademicEvent]:
        """Parses multi-line text, syllabi, or raw school schedule listings."""
        events: list[AcademicEvent] = []
        lines = text.strip().splitlines()
        student_list = students or []

        for line_idx, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            # Detect event type
            line_lower = line.lower()
            if any(
                w in line_lower
                for w in [
                    "teacher workday",
                    "staff development",
                    "planning day",
                    "professional development",
                ]
            ):
                etype = AcademicEventType.TEACHER_WORKDAY
            elif any(
                w in line_lower
                for w in [
                    "spring break",
                    "winter break",
                    "thanksgiving break",
                    "holiday break",
                    "fall break",
                    "recess",
                ]
            ):
                etype = AcademicEventType.BREAK
            elif any(w in line_lower for w in ["early release", "half day", "2-hour early"]):
                etype = AcademicEventType.EARLY_RELEASE
            elif any(w in line_lower for w in ["exam", "final", "midterm"]):
                etype = AcademicEventType.EXAM_PERIOD
            elif any(
                w in line_lower for w in ["student holiday", "no school", "no classes", "holiday"]
            ):
                etype = AcademicEventType.STUDENT_HOLIDAY
            else:
                etype = AcademicEventType.NO_CLASS

            # Try date patterns
            # Pattern A: ISO YYYY-MM-DD or range YYYY-MM-DD to YYYY-MM-DD
            iso_match = re.search(
                r"(\d{4}-\d{2}-\d{2})(?:\s*(?:to|-|through)\s*(\d{4}-\d{2}-\d{2}))?", line
            )
            if iso_match:
                start_str = iso_match.group(1)
                end_str = iso_match.group(2) or start_str
                # Remove date from description
                desc = re.sub(
                    r"(\d{4}-\d{2}-\d{2})(?:\s*(?:to|-|through)\s*(\d{4}-\d{2}-\d{2}))?[:\s-]*",
                    "",
                    line,
                ).strip()
                event_name = desc or "Academic Milestone"
                events.append(
                    AcademicEvent(
                        id=f"acad-{line_idx:03d}",
                        name=event_name,
                        event_type=etype,
                        start_date=start_str,
                        end_date=end_str,
                        source_label=source_label,
                        affected_students=student_list,
                    )
                )
                continue

            # Pattern B: Month Day, Year (e.g. October 12, 2026 or Oct 12-16, 2026)
            month_range_match = re.search(
                r"([A-Za-z]+)\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?(?:,?\s*(\d{4}))?", line
            )
            if month_range_match:
                month_str = month_range_match.group(1).lower()
                if month_str in cls.MONTH_MAP:
                    month_num = cls.MONTH_MAP[month_str]
                    day1 = int(month_range_match.group(2))
                    day2 = int(month_range_match.group(3)) if month_range_match.group(3) else day1
                    year = (
                        int(month_range_match.group(4))
                        if month_range_match.group(4)
                        else default_year
                    )

                    try:
                        d1 = date(year, month_num, day1)
                        d2 = date(year, month_num, day2)
                        desc = re.sub(
                            r"([A-Za-z]+)\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?(?:,?\s*(\d{4}))?[:\s-]*",
                            "",
                            line,
                        ).strip()
                        event_name = desc or "School Scheduled Day Off"
                        events.append(
                            AcademicEvent(
                                id=f"acad-{line_idx:03d}",
                                name=event_name,
                                event_type=etype,
                                start_date=d1.strftime("%Y-%m-%d"),
                                end_date=d2.strftime("%Y-%m-%d"),
                                source_label=source_label,
                                affected_students=student_list,
                            )
                        )
                    except ValueError:
                        pass

        return events


class FamilyCalendarBridge:
    """Synchronizes academic schedules across multiple children, schools, and syllabi with parent PTO & Federal holidays."""

    def __init__(self, academic_events: list[AcademicEvent], year: int = 2026) -> None:
        self.events = academic_events
        self.year = year
        self.holidays = HolidayCalendar.get_holidays_for_year(year)
        self.holiday_dates: set[date] = {h.dt for h in self.holidays}

    def get_all_student_days_off(self) -> set[date]:
        """Returns all dates where students are off (Student Holiday, Teacher Workday, Breaks)."""
        off_dates: set[date] = set()
        for e in self.events:
            if e.event_type in (
                AcademicEventType.STUDENT_HOLIDAY,
                AcademicEventType.TEACHER_WORKDAY,
                AcademicEventType.BREAK,
                AcademicEventType.NO_CLASS,
            ):
                off_dates.update(e.get_all_dates())
        return off_dates

    def find_childcare_conflicts(self) -> list[dict[str, Any]]:
        """Identifies days where kids are off school, but parents have a normal work day (no Federal holiday)."""
        conflicts = []
        off_dates = sorted(self.get_all_student_days_off())

        for d in off_dates:
            # Check if workday for parent (Mon-Fri and not a federal holiday)
            if d.weekday() < 5 and d not in self.holiday_dates:
                # Find matching events
                matched_events = [e for e in self.events if d in e.get_all_dates()]
                names = [e.name for e in matched_events]
                sources = list({e.source_label for e in matched_events})
                conflicts.append(
                    {
                        "date": d.strftime("%Y-%m-%d"),
                        "day_of_week": d.strftime("%A"),
                        "event_names": names,
                        "sources": sources,
                        "risk_tier": "COVERAGE_NEEDED",
                        "guidance": f"School is closed on {d.strftime('%A, %b %d')} ({', '.join(names)}), but it is a normal work day for parents. Plan PTO or childcare.",
                    }
                )

        return conflicts

    def find_family_vacation_windows(self, min_consecutive_days: int = 4) -> list[dict[str, Any]]:
        """Finds contiguous clusters where students are off and can be stacked with parent PTO/Holidays."""
        student_off = self.get_all_student_days_off()
        # Union with weekends and federal holidays
        full_off_pool: set[date] = set(student_off)
        full_off_pool.update(self.holiday_dates)

        # Add weekends adjacent to days off
        start_year = date(self.year, 1, 1)
        end_year = date(self.year, 12, 31)
        curr = start_year
        while curr <= end_year:
            if curr.weekday() in (5, 6):  # Sat or Sun
                full_off_pool.add(curr)
            curr += timedelta(days=1)

        # Find contiguous spans
        sorted_dates = sorted(full_off_pool)
        if not sorted_dates:
            return []

        clusters: list[list[date]] = []
        current_cluster = [sorted_dates[0]]

        for d in sorted_dates[1:]:
            if d == current_cluster[-1] + timedelta(days=1):
                current_cluster.append(d)
            else:
                if len(current_cluster) >= min_consecutive_days and any(
                    cd in student_off for cd in current_cluster
                ):
                    clusters.append(current_cluster)
                current_cluster = [d]

        if len(current_cluster) >= min_consecutive_days and any(
            cd in student_off for cd in current_cluster
        ):
            clusters.append(current_cluster)

        vacation_windows = []
        for cluster in clusters:
            start_d = cluster[0]
            end_d = cluster[-1]
            total_days = len(cluster)
            # Count how many workdays in this cluster parent needs PTO for
            pto_needed = sum(1 for d in cluster if d.weekday() < 5 and d not in self.holiday_dates)
            matched_events = [
                e for e in self.events if any(d in e.get_all_dates() for d in cluster)
            ]
            event_names = list({e.name for e in matched_events})

            vacation_windows.append(
                {
                    "window_name": f"{event_names[0] if event_names else 'Family Break'} ({total_days} Days Off)",
                    "start_date": start_d.strftime("%Y-%m-%d"),
                    "end_date": end_d.strftime("%Y-%m-%d"),
                    "total_consecutive_days_off": total_days,
                    "pto_days_required": pto_needed,
                    "school_events_included": event_names,
                    "leverage_multiplier": round(total_days / pto_needed, 2)
                    if pto_needed > 0
                    else float(total_days),
                }
            )

        return vacation_windows
