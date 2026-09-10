# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for flowbalance-core.
"""

from pathlib import Path

from flowbalance.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "flowbalance" in captured.out


def test_cli_account_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Add account
    exit_code = main(
        [
            "--data-dir",
            str(data_dir),
            "account",
            "add",
            "--name",
            "Main Checking",
            "--balance",
            "5000",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Added Account" in captured.out
    acc_id = captured.out.split("[ID: ")[1].split("]")[0]

    # List accounts
    exit_code = main(["--data-dir", str(data_dir), "account", "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Main Checking" in captured.out

    # Remove account
    exit_code = main(["--data-dir", str(data_dir), "account", "rm", acc_id])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Removed account" in captured.out

    # Remove invalid account
    exit_code = main(["--data-dir", str(data_dir), "account", "rm", "missing_id"])
    assert exit_code == 1


def test_cli_income_and_expense_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Add Income
    exit_code = main(
        [
            "--data-dir",
            str(data_dir),
            "income",
            "add",
            "--name",
            "Salary",
            "--amount",
            "6000",
            "--frequency",
            "monthly",
            "--tax-pct",
            "15",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    inc_id = captured.out.split("[ID: ")[1].split("]")[0]

    # List Incomes
    exit_code = main(["--data-dir", str(data_dir), "income", "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Salary" in captured.out

    # Add Expense
    exit_code = main(
        [
            "--data-dir",
            str(data_dir),
            "expense",
            "add",
            "--name",
            "Rent",
            "--amount",
            "2000",
            "--frequency",
            "monthly",
            "--category",
            "needs",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    exp_id = captured.out.split("[ID: ")[1].split("]")[0]

    # List Expenses
    exit_code = main(["--data-dir", str(data_dir), "expense", "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Rent" in captured.out

    # Remove
    assert main(["--data-dir", str(data_dir), "income", "rm", inc_id]) == 0
    assert main(["--data-dir", str(data_dir), "income", "rm", "invalid_id"]) == 1

    assert main(["--data-dir", str(data_dir), "expense", "rm", exp_id]) == 0
    assert main(["--data-dir", str(data_dir), "expense", "rm", "invalid_id"]) == 1


def test_cli_forecast_and_stress_test(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"
    main(["--data-dir", str(data_dir), "account", "add", "--name", "Savings", "--balance", "20000"])
    main(
        [
            "--data-dir",
            str(data_dir),
            "income",
            "add",
            "--name",
            "Base Pay",
            "--amount",
            "5000",
            "--frequency",
            "monthly",
        ]
    )
    main(
        [
            "--data-dir",
            str(data_dir),
            "expense",
            "add",
            "--name",
            "Living Cost",
            "--amount",
            "2500",
            "--frequency",
            "monthly",
        ]
    )
    capsys.readouterr()

    # Forecast terminal
    exit_code = main(["--data-dir", str(data_dir), "forecast", "--days", "90"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "CASH FLOW FORECAST" in captured.out

    # Forecast JSON
    exit_code = main(["--data-dir", str(data_dir), "forecast", "--days", "30", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"solvency"' in captured.out

    # Forecast Markdown output file
    out_md = tmp_path / "forecast.md"
    exit_code = main(
        ["--data-dir", str(data_dir), "forecast", "--days", "30", "--out", str(out_md)]
    )
    assert exit_code == 0
    assert out_md.exists()

    # Stress-test
    exit_code = main(["--data-dir", str(data_dir), "stress-test", "--haircut", "50"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "SOLVENCY STRESS TEST" in captured.out
