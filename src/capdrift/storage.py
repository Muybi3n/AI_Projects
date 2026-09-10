# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local storage manager for portfolio snapshots and historical trend audits.
"""

import json
from pathlib import Path
from typing import Any

from .models import Holding, PortfolioSnapshot

DEFAULT_DATA_DIR = Path.home() / ".capdrift"


class SnapshotStore:
    """Manages periodic snapshot JSON storage for tracking portfolio drift over time."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "snapshots_history.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.history_file.exists():
            self._save_raw([])

    def _load_raw(self) -> list[dict[str, Any]]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return []

    def _save_raw(self, data: list[dict[str, Any]]) -> None:
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        history = self._load_raw()
        # Keep latest snapshot for same ID or append
        filtered = [s for s in history if s["id"] != snapshot.id]
        filtered.append(snapshot.to_dict())
        self._save_raw(filtered)

    def list_snapshots(self) -> list[PortfolioSnapshot]:
        history = self._load_raw()
        snaps = []
        for item in history:
            holdings = [Holding(**h) for h in item.get("holdings", [])]
            snaps.append(
                PortfolioSnapshot(
                    id=item["id"],
                    timestamp=item.get("timestamp", ""),
                    broker_source=item.get("broker_source", ""),
                    cash_balance=float(item.get("cash_balance", 0.0)),
                    holdings=holdings,
                )
            )
        snaps.sort(key=lambda s: s.timestamp, reverse=True)
        return snaps

    def get_latest_snapshot(self) -> PortfolioSnapshot | None:
        snaps = self.list_snapshots()
        return snaps[0] if snaps else None
