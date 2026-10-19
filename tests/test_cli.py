import json
from pathlib import Path

from canarymesh.cli import main


def test_cli_full_workflow(tmp_path, capsys):
    data_dir = str(tmp_path / "canary_data")

    # 1. demo command
    rc = main(["--data-dir", data_dir, "demo"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CanaryMesh demo environment seeded" in out

    # 2. list command
    rc = main(["--data-dir", data_dir, "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "aws-prod-admin-bait" in out

    # list json
    rc = main(["--data-dir", data_dir, "list", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    items = json.loads(out)
    assert len(items) == 4

    # 3. audit command (clean)
    rc = main(["--data-dir", data_dir, "audit"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "All decoy tripwires intact" in out

    # audit json
    rc = main(["--data-dir", data_dir, "audit", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    audit_data = json.loads(out)
    assert audit_data["overall_health"] == "ALL_DECOYS_INTACT"

    # 4. ask command
    rc = main(["--data-dir", data_dir, "ask", "What is our deception posture?"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CanaryMesh AI Deception Advisor" in out

    # ask json
    rc = main(["--data-dir", data_dir, "ask", "What is our deception posture?", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    adv_data = json.loads(out)
    assert "threat_assessment" in adv_data

    # 5. Tamper with a file and re-audit
    demo_creds = Path(data_dir) / "demo_environment" / ".aws" / "credentials"
    demo_creds.write_text("TAMPERED BY ATTACKER", encoding="utf-8")

    rc = main(["--data-dir", data_dir, "audit"])
    assert rc == 2
    out = capsys.readouterr().out
    assert "CRITICAL BREACH ALERT" in out

    # 6. alerts command
    rc = main(["--data-dir", data_dir, "alerts"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CRITICAL" in out

    # alerts --clear
    rc = main(["--data-dir", data_dir, "alerts", "--clear"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Cleared" in out


def test_cli_deploy_and_register(tmp_path, capsys):
    data_dir = str(tmp_path / "canary_data_2")
    decoy_file = tmp_path / "test_api_key.json"

    # deploy
    rc = main(
        [
            "--data-dir",
            data_dir,
            "deploy",
            "--category",
            "api_token",
            "--path",
            str(decoy_file),
            "--name",
            "custom-stripe-bait",
        ]
    )
    assert rc == 0
    assert decoy_file.exists()

    # register custom file
    another_file = tmp_path / "manual_honeypot.txt"
    another_file.write_text("SECRET_KEY=12345", encoding="utf-8")

    rc = main(
        [
            "--data-dir",
            data_dir,
            "register",
            "--path",
            str(another_file),
            "--name",
            "manual-honey",
        ]
    )
    assert rc == 0
