# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh storage: Manages the local encrypted/hashed JSON registry of active decoy tripwires and alert logs."""

from __future__ import annotations

import json
from pathlib import Path

from canarymesh.models import DecoyArtifact, TripwireAlert


class DecoyStore:
    """Local JSON registry for deployed decoy artifacts and tripwire incident alerts."""

    def __init__(self, data_dir: Path | str | None = None):
        if data_dir is None:
            self.data_dir = Path.home() / ".canarymesh"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.decoys_file = self.data_dir / "decoys.json"
        self.alerts_file = self.data_dir / "alerts.json"

        self._ensure_storage_files()

    def _ensure_storage_files(self) -> None:
        if not self.decoys_file.exists():
            self.decoys_file.write_text("[]\n", encoding="utf-8")
        if not self.alerts_file.exists():
            self.alerts_file.write_text("[]\n", encoding="utf-8")

    def list_decoys(self) -> list[DecoyArtifact]:
        try:
            content = self.decoys_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return [DecoyArtifact.from_dict(item) for item in data]
        except (json.JSONDecodeError, OSError):
            return []

    def save_decoys(self, decoys: list[DecoyArtifact]) -> None:
        data = [decoy.to_dict() for decoy in decoys]
        self.decoys_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_decoy(self, token_id_or_name: str) -> DecoyArtifact | None:
        decoys = self.list_decoys()
        for d in decoys:
            if d.token_id == token_id_or_name or d.name == token_id_or_name or d.canary_identifier == token_id_or_name:
                return d
            if d.token_id.startswith(token_id_or_name):
                return d
        return None

    def add_decoy(self, decoy: DecoyArtifact) -> None:
        decoys = self.list_decoys()
        # Avoid duplicate token_ids or paths
        updated = [d for d in decoys if d.token_id != decoy.token_id and d.file_path != decoy.file_path]
        updated.append(decoy)
        self.save_decoys(updated)

    def remove_decoy(self, token_id_or_name: str) -> bool:
        decoys = self.list_decoys()
        initial_len = len(decoys)
        updated = [
            d
            for d in decoys
            if d.token_id != token_id_or_name
            and d.name != token_id_or_name
            and not d.token_id.startswith(token_id_or_name)
        ]
        if len(updated) < initial_len:
            self.save_decoys(updated)
            return True
        return False

    def list_alerts(self) -> list[TripwireAlert]:
        try:
            content = self.alerts_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return [TripwireAlert.from_dict(item) for item in data]
        except (json.JSONDecodeError, OSError):
            return []

    def record_alerts(self, new_alerts: list[TripwireAlert]) -> None:
        if not new_alerts:
            return
        alerts = self.list_alerts()
        existing_ids = {a.alert_id for a in alerts}
        for a in new_alerts:
            if a.alert_id not in existing_ids:
                alerts.append(a)
        data = [alert.to_dict() for alert in alerts]
        self.alerts_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def clear_alerts(self) -> int:
        alerts = self.list_alerts()
        count = len(alerts)
        self.alerts_file.write_text("[]\n", encoding="utf-8")
        return count
