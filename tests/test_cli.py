# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for capdrift-engine.
"""

from pathlib import Path

from capdrift.cli import main, parse_target_str, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "capdrift" in captured.out


def test_parse_target_str():
    res = parse_target_str("us_equities:60,intl_equities:20,fixed_income:20")
    assert res["us_equities"] == 60.0
    assert res["intl_equities"] == 20.0


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"
    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text("Symbol,Shares,Price,Average Cost,Name\nVOO,10,500,450,S&P 500\nBND,20,75,75,Total Bond\n", encoding="utf-8")

    # Ingest
    exit_code = main(["--data-dir", str(data_dir), "ingest", str(csv_file)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Ingested Snapshot" in captured.out

    # Audit
    exit_code = main(["--data-dir", str(data_dir), "audit"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "PORTFOLIO HEALTH AUDIT" in captured.out

    # Audit JSON
    exit_code = main(["--data-dir", str(data_dir), "audit", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"snapshot"' in captured.out

    # Rebalance
    exit_code = main(["--data-dir", str(data_dir), "rebalance", "--target", "us_equities:70,fixed_income:30"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "REBALANCING TRADE DELTAS" in captured.out

    # Stress-test
    exit_code = main(["--data-dir", str(data_dir), "stress-test"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "HISTORICAL MACRO CRASH STRESS-TESTS" in captured.out

    # Dividends
    exit_code = main(["--data-dir", str(data_dir), "dividends", "--years", "3"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "DIVIDEND COMPOUNDING SNOWBALL" in captured.out

    # Ask
    exit_code = main(["--data-dir", str(data_dir), "ask", "What is my biggest concentration risk?"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "AI PORTFOLIO COMPANION" in captured.out

    # Ask JSON
    exit_code = main(["--data-dir", str(data_dir), "ask", "What are my dividends?", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"executive_thesis"' in captured.out

    # History
    exit_code = main(["--data-dir", str(data_dir), "history"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Portfolio History" in captured.out
