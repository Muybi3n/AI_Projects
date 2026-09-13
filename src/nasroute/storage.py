"""Persistent storage and state management for nasroute-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nasroute.models import (
    AuditReport,
    DocumentCategory,
    StorageTier,
    StorageTierConfig,
    TaxonomyRule,
)


def get_default_tiers(base_dir: Path | None = None) -> list[StorageTierConfig]:
    """Generate default storage tier configurations for homelab environments."""
    base = base_dir or Path.home() / ".nasroute" / "storage_tiers"
    return [
        StorageTierConfig(
            tier_name=StorageTier.HOT_NVME.value,
            mount_path=str(base / "hot_nvme"),
            speed_class="NVMe_Gen4_7000MBps",
            max_capacity_bytes=1024 * 1024 * 1024 * 1024,  # 1 TB
        ),
        StorageTierConfig(
            tier_name=StorageTier.WARM_SSD.value,
            mount_path=str(base / "warm_ssd"),
            speed_class="SATA_SSD_550MBps",
            max_capacity_bytes=4 * 1024 * 1024 * 1024 * 1024,  # 4 TB
        ),
        StorageTierConfig(
            tier_name=StorageTier.COLD_NAS.value,
            mount_path=str(base / "cold_nas"),
            speed_class="HDD_ZFS_RAIDZ2_250MBps",
            max_capacity_bytes=32 * 1024 * 1024 * 1024 * 1024,  # 32 TB
        ),
        StorageTierConfig(
            tier_name=StorageTier.GLACIER_BACKUP.value,
            mount_path=str(base / "glacier_archive"),
            speed_class="Encrypted_Cold_Vault",
            max_capacity_bytes=100 * 1024 * 1024 * 1024 * 1024,  # 100 TB
        ),
    ]


def get_default_rules() -> list[TaxonomyRule]:
    """Generate deterministic taxonomy classification rules."""
    return [
        TaxonomyRule(
            rule_id="rule_taxes",
            name="Tax & Financial Filings",
            category=DocumentCategory.TAX_FINANCE.value,
            target_tier=StorageTier.COLD_NAS.value,
            destination_subpath="Finance/Taxes/{year}/{filename}",
            name_keywords=["tax", "w2", "1099", "turbotax", "irs", "return", "1040"],
            content_keywords=["internal revenue service", "form 1040", "w-2 wage", "tax return"],
            priority=150,
        ),
        TaxonomyRule(
            rule_id="rule_medical",
            name="Medical & Clinical Records",
            category=DocumentCategory.MEDICAL_HEALTH.value,
            target_tier=StorageTier.WARM_SSD.value,
            destination_subpath="Health/MedicalRecords/{year}/{filename}",
            name_keywords=["medical", "doctor", "prescription", "lab_result", "clinic", "health", "hospital"],
            content_keywords=["patient name", "physician", "diagnosis", "prescription", "clinic"],
            priority=140,
        ),
        TaxonomyRule(
            rule_id="rule_legal",
            name="Legal Deeds, Wills & Contracts",
            category=DocumentCategory.LEGAL_ESTATE.value,
            target_tier=StorageTier.COLD_NAS.value,
            destination_subpath="Legal/Contracts/{year}/{filename}",
            name_keywords=["deed", "will", "trust", "contract", "estate", "agreement", "lease", "power_of_attorney"],
            content_keywords=["agreement", "signature", "notary", "hereby", "parties"],
            priority=130,
        ),
        TaxonomyRule(
            rule_id="rule_homelab",
            name="Homelab & Sysadmin Logs/Configs",
            category=DocumentCategory.HOMELAB_SYSADMIN.value,
            target_tier=StorageTier.HOT_NVME.value,
            destination_subpath="Homelab/SysAdmin/{year}/{filename}",
            name_keywords=["syslog", "audit", "pcap", "docker-compose", "k8s", "homelab", "proxmox", "truenas"],
            content_keywords=["version:", "services:", "kernel:", "systemd", "cron"],
            priority=120,
        ),
        TaxonomyRule(
            rule_id="rule_receipts",
            name="Receipts & Purchase Invoices",
            category=DocumentCategory.RECEIPTS_INVOICES.value,
            target_tier=StorageTier.WARM_SSD.value,
            destination_subpath="Finance/Receipts/{year}/{month}/{filename}",
            name_keywords=["receipt", "invoice", "statement", "order", "purchase", "bill"],
            content_keywords=["subtotal", "total:", "invoice number", "amount paid", "billing address"],
            priority=110,
        ),
        TaxonomyRule(
            rule_id="rule_research",
            name="Research Papers & Whitepapers",
            category=DocumentCategory.RESEARCH_PAPERS.value,
            target_tier=StorageTier.WARM_SSD.value,
            destination_subpath="Knowledge/Research/{year}/{filename}",
            name_keywords=["paper", "arxiv", "whitepaper", "rfc", "ieee", "thesis", "research"],
            content_keywords=["abstract", "references", "methodology", "introduction"],
            priority=100,
        ),
        TaxonomyRule(
            rule_id="rule_scans",
            name="General Document Scans & OCR",
            category=DocumentCategory.SCANS_DOCS.value,
            target_tier=StorageTier.COLD_NAS.value,
            destination_subpath="Documents/Scans/{year}/{filename}",
            name_keywords=["scan", "docscan", "ocr", "page", "scanner", "paperless"],
            content_keywords=["scanned document"],
            priority=90,
        ),
    ]


class NASRouteStore:
    """Local-first persistent store for routing state, tier registry, and audit log."""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir).resolve() if data_dir else Path.home() / ".nasroute"
        self.config_path = self.data_dir / "config.json"
        self.catalog_path = self.data_dir / "catalog.json"
        self.history_path = self.data_dir / "history.json"

        self.tiers: dict[str, StorageTierConfig] = {}
        self.rules: list[TaxonomyRule] = []
        self.catalog: dict[str, dict[str, Any]] = {}  # sha256 -> metadata
        self.history: list[dict[str, Any]] = []

        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Create data directories and load configuration."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            # Initialize with default tiers & rules
            default_t = get_default_tiers(self.data_dir / "storage_tiers")
            self.tiers = {t.tier_name: t for t in default_t}
            self.rules = get_default_rules()
            self.save_config()
        else:
            self.load_config()

        if self.catalog_path.exists():
            try:
                with self.catalog_path.open("r", encoding="utf-8") as f:
                    self.catalog = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.catalog = {}

        if self.history_path.exists():
            try:
                with self.history_path.open("r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.history = []

    def load_config(self) -> None:
        """Load tiers and rules from config.json."""
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                tiers_data = data.get("tiers", {})
                self.tiers = {k: StorageTierConfig.from_dict(v) for k, v in tiers_data.items()}
                rules_data = data.get("rules", [])
                self.rules = [TaxonomyRule.from_dict(r) for r in rules_data]
        except (json.JSONDecodeError, OSError, KeyError):
            self.tiers = {t.tier_name: t for t in get_default_tiers()}
            self.rules = get_default_rules()

    def save_config(self) -> None:
        """Persist tiers and rules to config.json."""
        payload = {
            "tiers": {k: v.to_dict() for k, v in self.tiers.items()},
            "rules": [r.to_dict() for r in self.rules],
        }
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def save_catalog(self) -> None:
        """Persist indexed file catalog."""
        with self.catalog_path.open("w", encoding="utf-8") as f:
            json.dump(self.catalog, f, indent=2)

    def save_history(self) -> None:
        """Persist execution history."""
        with self.history_path.open("w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    def add_or_update_tier(self, tier: StorageTierConfig) -> None:
        """Register or update a storage tier."""
        self.tiers[tier.tier_name] = tier
        self.save_config()

    def add_rule(self, rule: TaxonomyRule) -> None:
        """Add or update a taxonomy rule."""
        self.rules = [r for r in self.rules if r.rule_id != rule.rule_id]
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self.save_config()

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a taxonomy rule by ID."""
        initial_len = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        if len(self.rules) != initial_len:
            self.save_config()
            return True
        return False

    def record_audit(self, report: AuditReport) -> None:
        """Record audit executions and update catalog."""
        rep_dict = report.to_dict()
        self.history.append(rep_dict)

        for exc in report.executions:
            if exc.status in ("SUCCESS", "SIMULATED"):
                self.catalog[exc.sha256] = {
                    "source_path": exc.source_path,
                    "dest_path": exc.dest_path,
                    "category": exc.category,
                    "tier": exc.tier,
                    "timestamp": exc.timestamp,
                }

        self.save_catalog()
        self.save_history()

    def get_known_hashes(self) -> set[str]:
        """Return set of all known SHA-256 hashes in catalog."""
        return set(self.catalog.keys())
