# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local storage manager for trust entities, schedule assets, beneficiaries, and fiduciary logs.
"""

import json
from pathlib import Path
from typing import Any

from .models import (
    AssetCategory,
    BeneficiaryRule,
    DistributionScheme,
    FiduciaryLogEntry,
    ScheduleAsset,
    TitlingStatus,
    TrustEntity,
    TrustType,
)

DEFAULT_DATA_DIR = Path.home() / ".trustguard"


class TrustStore:
    """Manages persistent JSON storage for trusts and fiduciary ledgers."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trust_file = self.data_dir / "trust_entity.json"
        self._init_store()

    def _init_store(self) -> None:
        if not self.trust_file.exists():
            default_trust = TrustEntity(
                trust_name="Primary Family Revocable Living Trust",
                trust_type=TrustType.REVOCABLE_LIVING,
                jurisdiction_state="Delaware",
                grantor_settlor="Settlor",
                current_trustee="Settlor",
                successor_trustee="Successor Trustee",
            )
            self.save_trust(default_trust)

    def load_trust(self) -> TrustEntity:
        try:
            with open(self.trust_file, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (OSError, json.JSONDecodeError, KeyError):
            return TrustEntity()

    def save_trust(self, trust: TrustEntity) -> None:
        with open(self.trust_file, "w", encoding="utf-8") as f:
            json.dump(trust.to_dict(), f, indent=2)

    def _deserialize(self, d: dict[str, Any]) -> TrustEntity:
        assets = [
            ScheduleAsset(
                id=a["id"],
                name=a["name"],
                category=AssetCategory(a.get("category", AssetCategory.REAL_ESTATE.value)),
                estimated_value=float(a.get("estimated_value", 0.0)),
                titling_status=TitlingStatus(a.get("titling_status", TitlingStatus.TITLED_TO_TRUST.value)),
                institution_or_parcel=a.get("institution_or_parcel", ""),
                notes=a.get("notes", ""),
            )
            for a in d.get("assets", [])
        ]

        beneficiaries = [
            BeneficiaryRule(
                id=b["id"],
                beneficiary_name=b["beneficiary_name"],
                relationship=b.get("relationship", "child"),
                scheme=DistributionScheme(b.get("scheme", DistributionScheme.OUTRIGHT_PERCENTAGE.value)),
                share_pct=float(b.get("share_pct", 0.0)),
                specific_dollar_amount=float(b.get("specific_dollar_amount", 0.0)),
                milestone_schedule=b.get("milestone_schedule", []),
                contingent_beneficiary=b.get("contingent_beneficiary", ""),
                is_primary=bool(b.get("is_primary", True)),
            )
            for b in d.get("beneficiaries", [])
        ]

        fiduciary_logs = [
            FiduciaryLogEntry(
                id=log["id"],
                timestamp=log.get("timestamp", ""),
                trustee_name=log.get("trustee_name", ""),
                action_category=log.get("action_category", "accounting"),
                description=log.get("description", ""),
                dollar_impact=float(log.get("dollar_impact", 0.0)),
                supporting_doc_ref=log.get("supporting_doc_ref", ""),
            )
            for log in d.get("fiduciary_logs", [])
        ]

        return TrustEntity(
            id=d.get("id", ""),
            trust_name=d.get("trust_name", "Revocable Living Trust"),
            trust_type=TrustType(d.get("trust_type", TrustType.REVOCABLE_LIVING.value)),
            jurisdiction_state=d.get("jurisdiction_state", "Delaware"),
            grantor_settlor=d.get("grantor_settlor", "Settlor"),
            current_trustee=d.get("current_trustee", "Trustee"),
            successor_trustee=d.get("successor_trustee", "Successor Trustee"),
            created_date=d.get("created_date", ""),
            assets=assets,
            beneficiaries=beneficiaries,
            fiduciary_logs=fiduciary_logs,
        )
