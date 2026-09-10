# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Universal portfolio ingestion engine with PII scrubbing and broker header auto-detection.
"""

import csv
import io
import json
import uuid
from pathlib import Path

from .models import Holding, PortfolioSnapshot

# Default sector & asset class mapping heuristics
KNOWN_ETF_MAPPINGS: dict[str, tuple[str, str, float]] = {
    "VOO": ("us_equities", "Large Cap Blend (S&P 500)", 1.5),
    "VTI": ("us_equities", "Total US Stock Market", 1.5),
    "SPY": ("us_equities", "Large Cap Blend (S&P 500)", 1.5),
    "QQQ": ("us_equities", "Technology / Growth (Nasdaq 100)", 0.6),
    "VXUS": ("intl_equities", "Total International", 3.2),
    "BND": ("fixed_income", "Total US Bond Market", 3.8),
    "AGG": ("fixed_income", "Total US Aggregate Bond", 3.7),
    "VNQ": ("real_estate", "Real Estate (REIT)", 4.1),
    "SCHD": ("us_equities", "Dividend Appreciation", 3.4),
    "BTC": ("crypto", "Digital Assets", 0.0),
    "ETH": ("crypto", "Digital Assets", 0.0),
}


class PortfolioIngester:
    """Parses exported broker CSV / JSON files and scrubs PII."""

    def ingest_file(self, file_path: Path | str, broker_hint: str | None = None) -> PortfolioSnapshot:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Portfolio file not found: {path}")

        content = path.read_text(encoding="utf-8", errors="replace")
        snap_id = str(uuid.uuid4())[:8]

        if path.suffix.lower() == ".json":
            return self._parse_json(content, snap_id)

        return self._parse_csv(content, snap_id, broker_hint)

    def _parse_json(self, content: str, snap_id: str) -> PortfolioSnapshot:
        data = json.loads(content)
        cash = float(data.get("cash_balance", 0.0))
        holdings = []
        for h in data.get("holdings", []):
            holdings.append(
                Holding(
                    symbol=str(h["symbol"]).upper().strip(),
                    name=str(h.get("name", h["symbol"])),
                    shares=float(h["shares"]),
                    current_price=float(h["current_price"]),
                    average_cost=float(h.get("average_cost", 0.0)),
                    asset_class=h.get("asset_class", "us_equities"),
                    sector=h.get("sector", "Broad Market"),
                    dividend_yield_pct=float(h.get("dividend_yield_pct", 0.0)),
                )
            )
        return PortfolioSnapshot(
            id=snap_id,
            broker_source="JSON Import",
            cash_balance=cash,
            holdings=holdings,
        )

    def _parse_csv(self, content: str, snap_id: str, broker_hint: str | None) -> PortfolioSnapshot:
        # PII scrub: drop potential account number headers
        reader = csv.reader(io.StringIO(content))
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
        if not rows:
            return PortfolioSnapshot(id=snap_id, broker_source="Empty CSV")

        # Detect header row
        header_idx = -1
        for idx, r in enumerate(rows):
            r_lower = [c.lower().strip() for c in r]
            if any(k in r_lower for k in ["symbol", "ticker", "instrument", "asset"]):
                header_idx = idx
                break

        if header_idx == -1:
            # Fallback: assume first row
            header_idx = 0

        headers = [c.lower().strip().replace(" ", "_") for c in rows[header_idx]]
        data_rows = rows[header_idx + 1 :]

        # Identify column indices
        col_map = self._map_columns(headers)
        holdings: list[Holding] = []
        cash_balance = 0.0

        for r in data_rows:
            if len(r) <= max(col_map.values(), default=0):
                continue

            symbol_raw = r[col_map["symbol"]].strip().upper() if "symbol" in col_map else ""
            if not symbol_raw or symbol_raw in ["TOTAL", "CASH", "USD", "ACCOUNT VALUE"]:
                if symbol_raw in ["CASH", "USD"] and "value" in col_map:
                    try:
                        cash_balance += float(r[col_map["value"]].replace("$", "").replace(",", ""))
                    except ValueError:
                        pass
                continue

            try:
                shares = float(r[col_map["shares"]].replace(",", "")) if "shares" in col_map else 1.0
                price = float(r[col_map["price"]].replace("$", "").replace(",", "")) if "price" in col_map else 0.0
                cost = float(r[col_map["cost"]].replace("$", "").replace(",", "")) if "cost" in col_map else price
                name = r[col_map["name"]].strip() if "name" in col_map else symbol_raw
            except (ValueError, IndexError):
                continue

            # Look up known asset class / sector / yield if standard ETF
            known = KNOWN_ETF_MAPPINGS.get(symbol_raw)
            if known:
                asset_class, sector, div_yield = known
            else:
                asset_class = "crypto" if symbol_raw in ["BTC", "ETH", "SOL"] else "us_equities"
                sector = "General Equities"
                div_yield = 1.0

            holdings.append(
                Holding(
                    symbol=symbol_raw,
                    name=name,
                    shares=shares,
                    current_price=price,
                    average_cost=cost,
                    asset_class=asset_class,
                    sector=sector,
                    dividend_yield_pct=div_yield,
                )
            )

        return PortfolioSnapshot(
            id=snap_id,
            broker_source=broker_hint or "CSV Auto-Detect",
            cash_balance=cash_balance,
            holdings=holdings,
        )

    def _map_columns(self, headers: list[str]) -> dict[str, int]:
        mapping = {}
        for idx, h in enumerate(headers):
            if h in ["symbol", "ticker", "instrument", "asset_symbol"]:
                mapping["symbol"] = idx
            elif h in ["quantity", "shares", "units", "qty", "number_of_shares"]:
                mapping["shares"] = idx
            elif h in ["price", "current_price", "last_price", "market_price"]:
                mapping["price"] = idx
            elif h in ["average_cost", "avg_cost", "cost_basis_per_share", "unit_cost"]:
                mapping["cost"] = idx
            elif h in ["name", "description", "security_name", "company"]:
                mapping["name"] = idx
            elif h in ["total_value", "market_value", "equity", "current_value", "value"]:
                mapping["value"] = idx
        return mapping
