"""
Full-workflow CLI integration tests covering every subcommand.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from pathlib import Path

from cadence_calendar.cli import main


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = str(tmp_path / "cadence_data")
    ics_sample = tmp_path / "sample.ics"
    ics_sample.write_text(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:cli-ev-001
SUMMARY:Weekly Engineering Sync
DTSTART:20260928T090000Z
DTEND:20260928T100000Z
ATTENDEE:mailto:eng@example.com
END:VEVENT
BEGIN:VEVENT
UID:cli-ev-002
SUMMARY:1:1 with Alex
DTSTART:20260928T100000Z
DTEND:20260928T103000Z
ATTENDEE:mailto:alex@example.com
END:VEVENT
END:VCALENDAR""",
        encoding="utf-8",
    )

    # 1. init
    rc = main(
        [
            "--data-dir",
            data_dir,
            "init",
            "--name",
            "Test Engineer Profile",
            "--work-hours",
            "09:00-17:00",
            "--lunch",
            "12:00-12:45",
            "--target-focus",
            "4.0",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "Initialized profile" in out

    # 1b. init error handling
    rc_err = main(["--data-dir", data_dir, "init", "--work-hours", "invalid-format"])
    assert rc_err == 1

    # 2. ingest
    rc = main(
        [
            "--data-dir",
            data_dir,
            "ingest",
            str(ics_sample),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "Successfully ingested 2 events" in out

    # 2b. ingest missing file
    rc = main(["--data-dir", data_dir, "ingest", str(tmp_path / "missing.ics")])
    assert rc == 1

    # 3. stats (text & json)
    rc = main(["--data-dir", data_dir, "stats"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Stored Events: 2" in out

    rc = main(["--data-dir", data_dir, "stats", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"total_events": 2' in out

    # 4. audit (text & json)
    rc = main(["--data-dir", data_dir, "audit"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CADENCE CALENDAR: FATIGUE & COGNITIVE LOAD AUDIT REPORT" in out

    rc = main(["--data-dir", data_dir, "audit", "--json", "--from-date", "2026-09-01", "--to-date", "2026-09-30"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"burnout_risk_level"' in out

    # 5. protect (plan, apply, export)
    protected_ics = tmp_path / "protected.ics"
    rc = main(
        [
            "--data-dir",
            data_dir,
            "protect",
            "--buffer-minutes",
            "10",
            "--apply",
            "--export",
            str(protected_ics),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "DEEP WORK & BUFFER PROTECTION PLAN" in out
    assert protected_ics.exists()

    rc = main(["--data-dir", data_dir, "protect", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"total_buffers_generated"' in out

    # 6. ask (text & json)
    rc = main(["--data-dir", data_dir, "ask", "How can I avoid meeting fatigue?"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CADENCE AI ADVISOR" in out

    rc = main(["--data-dir", data_dir, "ask", "Can you give me a decline script?", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"query"' in out

    # 7. export
    export_json = tmp_path / "exported.json"
    rc = main(["--data-dir", data_dir, "export", "-o", str(export_json)])
    assert rc == 0
    assert export_json.exists()

    # 8. clean (missing --all vs with --all)
    rc = main(["--data-dir", data_dir, "clean"])
    assert rc == 1

    rc = main(["--data-dir", data_dir, "clean", "--all"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Successfully cleared" in out
