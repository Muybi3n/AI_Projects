"""Local-first storage engine for subwatch."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from subwatch.models import ChargeRecord, Subscription, SubscriptionStatus


class StorageManager:
    """Manages local JSON persistence for subscriptions and historical charge ledgers."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        if data_dir is not None:
            self.base_dir = Path(data_dir)
        elif "SUBWATCH_DATA_DIR" in os.environ:
            self.base_dir = Path(os.environ["SUBWATCH_DATA_DIR"])
        else:
            self.base_dir = Path.home() / ".subwatch"

        self.vault_file = self.base_dir / "vault.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create directory and initial empty store if not present."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.vault_file.exists():
            self._write_raw([])

    def _read_raw(self) -> list[dict[str, Any]]:
        """Read raw JSON entries from disk."""
        if not self.vault_file.exists():
            return []
        try:
            with open(self.vault_file, encoding="utf-8") as file_handle:
                content = json.load(file_handle)
                if isinstance(content, list):
                    return content
                return []
        except (json.JSONDecodeError, OSError):
            return []

    def _write_raw(self, items: list[dict[str, Any]]) -> None:
        """Atomically write raw JSON data to disk."""
        temp_file = self.vault_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as file_handle:
            json.dump(items, file_handle, indent=2)
        temp_file.replace(self.vault_file)

    def load_all(self) -> list[Subscription]:
        """Load all subscriptions from storage."""
        raw_items = self._read_raw()
        subscriptions: list[Subscription] = []
        for item in raw_items:
            try:
                subscriptions.append(Subscription.from_dict(item))
            except (KeyError, ValueError, TypeError):
                continue
        return subscriptions

    def save_all(self, subscriptions: list[Subscription]) -> None:
        """Save entire collection of subscriptions."""
        raw_items = [sub.to_dict() for sub in subscriptions]
        self._write_raw(raw_items)

    def add_subscription(self, subscription: Subscription) -> Subscription:
        """Add a new subscription to the vault."""
        subs = self.load_all()
        if not subscription.id:
            subscription.id = str(uuid.uuid4())[:8]
        subs.append(subscription)
        self.save_all(subs)
        return subscription

    def get_subscription(self, identifier: str) -> Subscription | None:
        """Find a subscription by ID or exact/case-insensitive name."""
        identifier_lower = identifier.lower().strip()
        subs = self.load_all()
        for sub in subs:
            if sub.id.lower() == identifier_lower or sub.name.lower() == identifier_lower:
                return sub
        return None

    def list_subscriptions(
        self,
        status_filter: SubscriptionStatus | None = None,
    ) -> list[Subscription]:
        """List subscriptions with optional status filtering."""
        subs = self.load_all()
        if status_filter:
            subs = [sub for sub in subs if sub.status == status_filter]
        return subs

    def update_subscription(
        self,
        identifier: str,
        updates: dict[str, Any],
    ) -> Subscription | None:
        """Update fields of an existing subscription."""
        subs = self.load_all()
        target: Subscription | None = None
        target_idx: int = -1

        identifier_lower = identifier.lower().strip()
        for idx, sub in enumerate(subs):
            if sub.id.lower() == identifier_lower or sub.name.lower() == identifier_lower:
                target = sub
                target_idx = idx
                break

        if target is None or target_idx == -1:
            return None

        # Apply updates
        sub_dict = target.to_dict()
        for key, value in updates.items():
            if value is not None:
                sub_dict[key] = value

        updated_sub = Subscription.from_dict(sub_dict)
        subs[target_idx] = updated_sub
        self.save_all(subs)
        return updated_sub

    def remove_subscription(self, identifier: str) -> bool:
        """Remove a subscription from the vault."""
        subs = self.load_all()
        identifier_lower = identifier.lower().strip()
        original_len = len(subs)
        subs = [
            sub
            for sub in subs
            if sub.id.lower() != identifier_lower and sub.name.lower() != identifier_lower
        ]
        if len(subs) < original_len:
            self.save_all(subs)
            return True
        return False

    def log_charge(
        self,
        identifier: str,
        amount: float,
        date_str: str,
        payment_method: str = "",
        notes: str = "",
    ) -> ChargeRecord | None:
        """Record an actual historical billing charge for price creep tracking."""
        subs = self.load_all()
        identifier_lower = identifier.lower().strip()
        matched: Subscription | None = None

        for sub in subs:
            if sub.id.lower() == identifier_lower or sub.name.lower() == identifier_lower:
                matched = sub
                break

        if matched is None:
            return None

        charge_id = str(uuid.uuid4())[:8]
        record = ChargeRecord(
            id=charge_id,
            subscription_id=matched.id,
            amount=amount,
            date=date_str,
            payment_method=payment_method or matched.payment_method,
            notes=notes,
        )

        matched.charge_history.append(record)
        self.save_all(subs)
        return record

    def clear(self) -> None:
        """Clear all stored data (for testing or reset)."""
        self._write_raw([])
