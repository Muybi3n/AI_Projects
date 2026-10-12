"""Local-first JSON persistence storage engine for ShelfWise."""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import Any

from shelfwise.models import Asset, MaintenanceRecord


class ShelfWiseStorage:
    """Manages persistent local file storage for assets and maintenance records."""

    def __init__(self, data_dir: Path | str | None = None):
        if data_dir is None:
            self.data_dir = Path.home() / ".shelfwise"
        else:
            self.data_dir = Path(data_dir).expanduser().resolve()

        self.assets_file = self.data_dir / "assets.json"
        self.maintenance_file = self.data_dir / "maintenance.json"
        self.config_file = self.data_dir / "config.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create storage directory if it does not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _safe_write_json(self, path: Path, data: Any) -> None:
        """Atomically write JSON data to disk via temporary file."""
        self._ensure_data_dir()
        temp_file = path.with_suffix(f"{path.suffix}.tmp")
        try:
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, path)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    def _read_json(self, path: Path, default: Any) -> Any:
        """Read and parse JSON file, returning default if missing or corrupted."""
        if not path.is_file():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    # --- Asset Operations ---

    def list_assets(
        self,
        category: str | None = None,
        status: str | None = None,
        location: str | None = None,
    ) -> list[Asset]:
        """List all stored assets with optional filtering."""
        raw_list = self._read_json(self.assets_file, default=[])
        assets: list[Asset] = []
        for item in raw_list:
            if isinstance(item, dict):
                assets.append(Asset.from_dict(item))

        # Filter
        filtered: list[Asset] = []
        for asset in assets:
            if category:
                cat_val = asset.category.value if hasattr(asset.category, "value") else str(asset.category)
                if cat_val.lower() != category.lower():
                    continue

            if status:
                stat_val = asset.status.value if hasattr(asset.status, "value") else str(asset.status)
                if stat_val.lower() != status.lower():
                    continue

            if location:
                if (asset.location or "").lower() != location.lower():
                    continue

            filtered.append(asset)

        return filtered

    def get_asset(self, asset_id: str) -> Asset | None:
        """Retrieve an asset by unique ID or slug."""
        assets = self.list_assets()
        for asset in assets:
            if asset.id.lower() == asset_id.lower():
                return asset
        return None

    def save_asset(self, asset: Asset) -> None:
        """Create or update an asset in the store."""
        assets = self.list_assets()
        updated = False
        new_list: list[dict[str, Any]] = []

        for existing in assets:
            if existing.id.lower() == asset.id.lower():
                new_list.append(asset.to_dict())
                updated = True
            else:
                new_list.append(existing.to_dict())

        if not updated:
            new_list.append(asset.to_dict())

        self._safe_write_json(self.assets_file, new_list)

    def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset by ID. Returns True if deleted."""
        assets = self.list_assets()
        remaining: list[dict[str, Any]] = []
        found = False

        for existing in assets:
            if existing.id.lower() == asset_id.lower():
                found = True
            else:
                remaining.append(existing.to_dict())

        if found:
            self._safe_write_json(self.assets_file, remaining)
        return found

    # --- Maintenance Operations ---

    def list_maintenance(self, asset_id: str | None = None) -> list[MaintenanceRecord]:
        """List maintenance records, optionally filtered by asset ID."""
        raw_list = self._read_json(self.maintenance_file, default=[])
        records: list[MaintenanceRecord] = []
        for item in raw_list:
            if isinstance(item, dict):
                records.append(MaintenanceRecord.from_dict(item))

        if asset_id:
            return [record for record in records if record.asset_id.lower() == asset_id.lower()]
        return records

    def save_maintenance(self, record: MaintenanceRecord) -> None:
        """Create or update a maintenance record."""
        records = self.list_maintenance()
        updated = False
        new_list: list[dict[str, Any]] = []

        for existing in records:
            if existing.id.lower() == record.id.lower():
                new_list.append(record.to_dict())
                updated = True
            else:
                new_list.append(existing.to_dict())

        if not updated:
            new_list.append(record.to_dict())

        self._safe_write_json(self.maintenance_file, new_list)

    def delete_maintenance(self, record_id: str) -> bool:
        """Delete a maintenance record by ID."""
        records = self.list_maintenance()
        remaining: list[dict[str, Any]] = []
        found = False

        for existing in records:
            if existing.id.lower() == record_id.lower():
                found = True
            else:
                remaining.append(existing.to_dict())

        if found:
            self._safe_write_json(self.maintenance_file, remaining)
        return found

    # --- Config Operations ---

    def get_config(self) -> dict[str, Any]:
        """Read configuration parameters."""
        return self._read_json(self.config_file, default={})

    def save_config(self, config: dict[str, Any]) -> None:
        """Save configuration parameters."""
        self._safe_write_json(self.config_file, config)

    # --- Export / Import ---

    def export_data(self, format_type: str = "json") -> str:
        """Export all data to JSON or CSV format."""
        assets = self.list_assets()
        maintenance = self.list_maintenance()

        if format_type.lower() == "csv":
            output = io.StringIO()
            fieldnames = [
                "id",
                "name",
                "category",
                "brand",
                "model",
                "serial_number",
                "purchase_date",
                "purchase_price",
                "vendor",
                "condition",
                "location",
                "status",
                "warranty_months",
                "receipt_path",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for asset in assets:
                data = asset.to_dict()
                row = {k: data.get(k, "") for k in fieldnames}
                writer.writerow(row)
            return output.getvalue()

        # JSON default
        full_payload = {
            "version": "0.1.0",
            "assets": [a.to_dict() for a in assets],
            "maintenance": [m.to_dict() for m in maintenance],
        }
        return json.dumps(full_payload, indent=2)

    def import_data(self, payload: dict[str, Any]) -> tuple[int, int]:
        """Import assets and maintenance records from dictionary payload."""
        assets_imported = 0
        maint_imported = 0

        if "assets" in payload and isinstance(payload["assets"], list):
            for a_dict in payload["assets"]:
                if isinstance(a_dict, dict) and "id" in a_dict and "name" in a_dict:
                    self.save_asset(Asset.from_dict(a_dict))
                    assets_imported += 1

        if "maintenance" in payload and isinstance(payload["maintenance"], list):
            for m_dict in payload["maintenance"]:
                if isinstance(m_dict, dict) and "id" in m_dict and "asset_id" in m_dict:
                    self.save_maintenance(MaintenanceRecord.from_dict(m_dict))
                    maint_imported += 1

        return assets_imported, maint_imported
