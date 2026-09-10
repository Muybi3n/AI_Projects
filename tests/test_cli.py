# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for trustguard-core.
"""

from pathlib import Path

from trustguard.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "trustguard" in captured.out


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Init
    code = main(
        ["--data-dir", str(data_dir), "init", "--name", "Test Family Trust", "--grantor", "Alice", "--trustee", "Bob"]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Initialized Trust" in captured.out

    # Add Asset (Titled)
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "asset",
            "add",
            "--name",
            "Residence",
            "--category",
            "real_estate",
            "--value",
            "800000",
            "--titling",
            "titled_to_trust",
        ]
    )
    assert code == 0

    # Add Asset (Unfunded Risk)
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "asset",
            "add",
            "--name",
            "Startup Equity",
            "--category",
            "business_equity_llc",
            "--value",
            "200000",
            "--titling",
            "unfunded_probate_risk",
        ]
    )
    assert code == 0

    # List Assets
    code = main(["--data-dir", str(data_dir), "asset", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Residence" in captured.out
    assert "$1,000,000.00" in captured.out

    # Audit Assets
    code = main(["--data-dir", str(data_dir), "asset", "audit"])
    assert code == 0
    captured = capsys.readouterr()
    assert "TRUST FUNDING & PROBATE AUDIT" in captured.out
    assert "Startup Equity" in captured.out

    # Audit Assets JSON
    code = main(["--data-dir", str(data_dir), "asset", "audit", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"unfunded_probate_risk_pct"' in captured.out

    # Add Beneficiary
    code = main(["--data-dir", str(data_dir), "beneficiary", "add", "--name", "Charlie", "--pct", "100.0"])
    assert code == 0

    # List Beneficiaries
    code = main(["--data-dir", str(data_dir), "beneficiary", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Charlie" in captured.out

    # Waterfall
    code = main(["--data-dir", str(data_dir), "waterfall"])
    assert code == 0
    captured = capsys.readouterr()
    assert "BENEFICIARY DISTRIBUTION WATERFALL" in captured.out

    # Waterfall JSON
    code = main(["--data-dir", str(data_dir), "waterfall", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"distributable_net_estate"' in captured.out

    # Fiduciary Log
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "fiduciary",
            "log",
            "--category",
            "appraisal",
            "--desc",
            "Annual real estate appraisal",
            "--amount",
            "1200",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Logged Fiduciary Action" in captured.out

    # Fiduciary List
    code = main(["--data-dir", str(data_dir), "fiduciary", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Annual real estate appraisal" in captured.out

    # Ask
    code = main(["--data-dir", str(data_dir), "ask", "What assets are at risk of probate?"])
    assert code == 0
    captured = capsys.readouterr()
    assert "AI ESTATE & FIDUCIARY COMPANION" in captured.out

    # Ask JSON
    code = main(["--data-dir", str(data_dir), "ask", "What are the trustee duties?", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"executive_summary"' in captured.out
