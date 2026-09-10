# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for CSV and JSON portfolio ingestion and PII stripping.
"""

from pathlib import Path

from capdrift.ingest import PortfolioIngester


def test_ingest_generic_csv(tmp_path: Path):
    csv_content = """Symbol,Shares,Price,Average Cost,Name
VOO,10,500.00,450.00,Vanguard S&P 500
VXUS,20,60.00,55.00,Vanguard Total Intl
BND,15,75.00,75.00,Vanguard Total Bond
"""
    csv_file = tmp_path / "portfolio.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    ingester = PortfolioIngester()
    snap = ingester.ingest_file(csv_file)

    assert len(snap.holdings) == 3
    assert snap.holdings[0].symbol == "VOO"
    assert snap.holdings[0].market_value == 5000.0
    assert snap.holdings[1].symbol == "VXUS"


def test_ingest_json(tmp_path: Path):
    json_content = """{
  "cash_balance": 2500.0,
  "holdings": [
    {
      "symbol": "QQQ",
      "name": "Invesco QQQ",
      "shares": 5.0,
      "current_price": 450.0,
      "average_cost": 400.0,
      "asset_class": "us_equities",
      "dividend_yield_pct": 0.6
    }
  ]
}"""
    json_file = tmp_path / "portfolio.json"
    json_file.write_text(json_content, encoding="utf-8")

    ingester = PortfolioIngester()
    snap = ingester.ingest_file(json_file)

    assert snap.cash_balance == 2500.0
    assert len(snap.holdings) == 1
    assert snap.holdings[0].symbol == "QQQ"


def test_ingest_missing_file(tmp_path: Path):
    ingester = PortfolioIngester()
    try:
        ingester.ingest_file(tmp_path / "does_not_exist.csv")
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass
