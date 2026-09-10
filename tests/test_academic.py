# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for academic syllabus parser and family calendar bridge.
"""

from ptomax.academic import AcademicEventType, FamilyCalendarBridge, SyllabusParser


def test_syllabus_parser_text():
    sample_text = """
    2026-10-09: Student Holiday / School Planning Day
    October 12, 2026 - Indigenous Peoples Day (No School)
    2026-11-02 to 2026-11-03: Teacher Workday
    Nov 25 - Nov 27, 2026: Thanksgiving Holiday Break
    2027-03-29 to 2027-04-02: Spring Break
    Midterm Exam: 2026-10-20
    """
    events = SyllabusParser.parse_text(sample_text, source_label="Test District", default_year=2026)
    assert len(events) >= 5

    names = [e.name for e in events]
    assert any("Student Holiday" in n for n in names)
    assert any("Spring Break" in n for n in names)

    types = [e.event_type for e in events]
    assert (
        AcademicEventType.STUDENT_HOLIDAY in types
        or AcademicEventType.TEACHER_WORKDAY in types
        or AcademicEventType.BREAK in types
    )


def test_family_calendar_bridge():
    sample_text = """
    2026-10-09: Student Holiday / Teacher Workday
    2026-11-23 to 2026-11-27: Thanksgiving Break
    """
    events = SyllabusParser.parse_text(sample_text, default_year=2026)
    bridge = FamilyCalendarBridge(events, year=2026)

    conflicts = bridge.find_childcare_conflicts()
    # 2026-10-09 is a Friday (not federal holiday) -> should trigger childcare conflict alert!
    assert len(conflicts) >= 1
    assert any(c["date"] == "2026-10-09" for c in conflicts)

    windows = bridge.find_family_vacation_windows()
    assert len(windows) >= 1
