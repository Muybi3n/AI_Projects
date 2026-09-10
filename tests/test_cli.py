# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
CLI tests for cardroute-engine.
"""

from pathlib import Path

from cardroute.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "CARDROUTE" in captured.out


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # List
    code = main(["--data-dir", str(data_dir), "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Wallet Portfolio" in captured.out

    # Add card
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "add",
            "--id",
            "usbank-ar",
            "--name",
            "US Bank Altitude Reserve",
            "--fee",
            "400",
            "--points",
            "US Bank Points",
            "--cpp",
            "1.5",
        ]
    )
    assert code == 0

    # Route
    code = main(["--data-dir", str(data_dir), "route", "--category", "dining", "--amount", "150"])
    assert code == 0
    captured = capsys.readouterr()
    assert "RECOMMENDED CARD" in captured.out

    # 524
    code = main(["--data-dir", str(data_dir), "524"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Chase 5/24 Status" in captured.out

    # SUB List
    code = main(["--data-dir", str(data_dir), "sub", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Sign-Up Bonus" in captured.out

    # SUB Log
    code = main(["--data-dir", str(data_dir), "sub", "log", "--id", "amex-gold", "--amount", "500"])
    assert code == 0

    # Audit
    code = main(["--data-dir", str(data_dir), "audit"])
    assert code == 0
    captured = capsys.readouterr()
    assert "WALLET ANNUAL NET VALUE AUDIT" in captured.out

    # Ask
    code = main(["--data-dir", str(data_dir), "ask", "What should I do about my 5/24 status?"])
    assert code == 0
    captured = capsys.readouterr()
    assert "CARDROUTE ADVISOR" in captured.out
