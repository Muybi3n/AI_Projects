# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for careguard-core.
"""

from pathlib import Path

from careguard.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "careguard" in captured.out


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Init
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "init",
            "--name",
            "Helen Vance",
            "--relationship",
            "Mother",
            "--birth-year",
            "1946",
            "--diagnoses",
            "Heart Failure, Osteoporosis",
            "--code-status",
            "POLST",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Initialized Care Recipient" in captured.out

    # Add Doctor
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "doctor",
            "add",
            "--name",
            "Dr. Robert Klein",
            "--specialty",
            "Cardiology",
            "--clinic",
            "Heart Institute",
            "--phone",
            "555-0144",
        ]
    )
    assert code == 0

    # List Doctors
    code = main(["--data-dir", str(data_dir), "doctor", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Dr. Robert Klein" in captured.out

    # Add Visit
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "visit",
            "add",
            "--doctor",
            "Dr. Robert Klein",
            "--specialty",
            "Cardiology",
            "--findings",
            "Ejection fraction stable at 45%.",
            "--changes",
            "Increased Furosemide to 40mg.",
        ]
    )
    assert code == 0

    # List Visits
    code = main(["--data-dir", str(data_dir), "visit", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Dr. Robert Klein" in captured.out

    # Add Meds
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "med",
            "add",
            "--name",
            "Furosemide",
            "--dosage",
            "40mg",
            "--slot",
            "morning",
            "--purpose",
            "Fluid management",
            "--doctor",
            "Dr. Klein",
        ]
    )
    assert code == 0
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "med",
            "add",
            "--name",
            "Melatonin",
            "--dosage",
            "3mg",
            "--slot",
            "bedtime",
            "--purpose",
            "Sleep",
        ]
    )
    assert code == 0

    # List Meds & Pillbox Schedule
    code = main(["--data-dir", str(data_dir), "med", "list"])
    assert code == 0
    code = main(["--data-dir", str(data_dir), "med", "schedule"])
    assert code == 0
    captured = capsys.readouterr()
    assert "MORNING SLOT" in captured.out
    assert "Furosemide" in captured.out

    # Add Vitals (Normal + Anomaly)
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "vitals",
            "add",
            "--sys",
            "122",
            "--dia",
            "78",
            "--hr",
            "68",
            "--spo2",
            "97.5",
            "--weight",
            "138.0",
        ]
    )
    assert code == 0
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "vitals",
            "add",
            "--sys",
            "185",
            "--dia",
            "110",
            "--hr",
            "92",
            "--spo2",
            "90.5",
            "--weight",
            "142.5",
            "--confusion",
        ]
    )
    assert code == 0

    # List Vitals & Audit
    code = main(["--data-dir", str(data_dir), "vitals", "list"])
    assert code == 0
    code = main(["--data-dir", str(data_dir), "vitals", "audit"])
    assert code == 0
    captured = capsys.readouterr()
    assert "URGENT_ATTENTION" in captured.out
    assert "Blood Pressure" in captured.out

    # Vitals Audit JSON
    code = main(["--data-dir", str(data_dir), "vitals", "audit", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"vital_metric"' in captured.out

    # Add Caregiver Note
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "note",
            "add",
            "--author",
            "Sarah",
            "--category",
            "observation",
            "--text",
            "Mom seemed tired after lunch, took a 45 min nap.",
        ]
    )
    assert code == 0

    code = main(["--data-dir", str(data_dir), "note", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Mom seemed tired" in captured.out

    # Generate Doctor Visit Brief
    code = main(["--data-dir", str(data_dir), "brief"])
    assert code == 0
    captured = capsys.readouterr()
    assert "CLINICAL APPOINTMENT BRIEFING SHEET" in captured.out
    assert "Helen Vance" in captured.out

    # Generate Brief JSON
    code = main(["--data-dir", str(data_dir), "brief", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"patient_name"' in captured.out

    # Ask AI Caregiver Companion
    code = main(["--data-dir", str(data_dir), "ask", "Prepare questions for tomorrow's cardiologist appointment."])
    assert code == 0
    captured = capsys.readouterr()
    assert "AI CAREGIVER MEDICAL ADVOCATE" in captured.out

    # Ask JSON
    code = main(["--data-dir", str(data_dir), "ask", "What were the medication changes?", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"advocate_summary"' in captured.out
