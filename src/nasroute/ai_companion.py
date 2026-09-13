"""Pluggable AI companion and deterministic heuristic advisor for nasroute-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from nasroute.storage import NASRouteStore


@dataclass
class CompanionResponse:
    """Structured response from the NASRoute AI companion."""

    query: str
    summary: str
    recommendations: list[str] = field(default_factory=list)
    suggested_rules: list[dict[str, Any]] = field(default_factory=list)
    storage_optimization: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_sanitized_context(store: NASRouteStore) -> dict[str, Any]:
    """Extract privacy-preserving, sanitized summary context for LLM or heuristic analysis."""
    tiers_summary = {
        name: {
            "speed_class": t.speed_class,
            "max_capacity_gb": round(t.max_capacity_bytes / (1024**3), 2) if t.max_capacity_bytes else 0,
        }
        for name, t in store.tiers.items()
    }

    category_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for item in store.catalog.values():
        cat = item.get("category", "UNCATEGORIZED")
        tier = item.get("tier", "COLD_NAS")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    rules_summary = [
        {
            "rule_id": r.rule_id,
            "category": r.category,
            "target_tier": r.target_tier,
            "priority": r.priority,
            "keywords": r.name_keywords[:4],
        }
        for r in store.rules
    ]

    total_space_saved = 0
    total_duplicates = 0
    for h in store.history:
        total_space_saved += h.get("space_saved_bytes", 0)
        total_duplicates += h.get("duplicate_files_count", 0)

    return {
        "total_indexed_files": len(store.catalog),
        "total_rules": len(store.rules),
        "tiers": tiers_summary,
        "category_distribution": category_counts,
        "tier_distribution": tier_counts,
        "rules": rules_summary,
        "deduplication_summary": {
            "total_duplicates_blocked": total_duplicates,
            "total_space_saved_mb": round(total_space_saved / (1024**2), 2),
        },
    }


class NASRouteCompanion:
    """Local-first storage taxonomy and homelab architecture advisor."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str, store: NASRouteStore) -> CompanionResponse:
        """Consult AI companion with offline heuristic fallback and pluggable LLM support."""
        context = build_sanitized_context(store)

        if self.custom_llm_callable:
            raw_response = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_response)
                return CompanionResponse(
                    query=query,
                    summary=data.get("summary", raw_response),
                    recommendations=data.get("recommendations", []),
                    suggested_rules=data.get("suggested_rules", []),
                    storage_optimization=data.get("storage_optimization", {}),
                    confidence=float(data.get("confidence", 0.95)),
                )
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                return CompanionResponse(
                    query=query,
                    summary=raw_response,
                    recommendations=["LLM response provided in raw summary text."],
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> CompanionResponse:
        """Deterministic heuristic reasoning engine based on storage best practices."""
        q_lower = query.lower()
        recommendations: list[str] = []
        suggested_rules: list[dict[str, Any]] = []
        optimization: dict[str, Any] = {}

        # Domain 1: Storage Tier Allocation & Balancing
        if any(w in q_lower for w in ["tier", "nvme", "ssd", "hdd", "cold", "hot", "balance", "capacity", "space"]):
            recommendations.append(
                "Enforce Storage Tier Hierarchy: Reserve HOT_NVME for high-IOPS homelab configs and active sysadmin logs."
            )
            recommendations.append(
                "Migrate historical tax filings, medical PDFs, and legal contracts older than 90 days to COLD_NAS (ZFS RAIDZ2)."
            )
            recommendations.append(
                "Keep daily receipts and active research papers in WARM_SSD for fast indexing and zero spin-up latency."
            )
            optimization["tier_strategy"] = {
                "HOT_NVME": "Active Docker configs, WireGuard logs, Kubernetes manifests",
                "WARM_SSD": "Current fiscal year receipts, active medical records, research drafts",
                "COLD_NAS": "Historical tax archives (7+ years), immutable scanned documents, raw backups",
                "GLACIER_BACKUP": "Encrypted offsite emergency recovery bundles",
            }

        # Domain 2: Deduplication & Integrity Checksums
        if any(w in q_lower for w in ["dedup", "duplicate", "checksum", "integrity", "sha256", "blake2b", "hash"]):
            total_saved_mb = context["deduplication_summary"]["total_space_saved_mb"]
            duplicates_blocked = context["deduplication_summary"]["total_duplicates_blocked"]
            recommendations.append(
                f"Integrity & Deduplication Status: {duplicates_blocked} duplicate files detected, saving {total_saved_mb:.2f} MB of redundant storage."
            )
            recommendations.append(
                "Utilize dual cryptographic hashing (BLAKE2b for speed, SHA-256 for audit compliance) to detect bit-rot across NAS pools."
            )
            optimization["deduplication_state"] = "ACTIVE_DUAL_HASH_VERIFIED"

        # Domain 3: Taxonomy & Custom Rule Generation
        if any(
            w in q_lower
            for w in ["rule", "taxonomy", "organize", "classify", "categorize", "receipt", "tax", "log", "homelab"]
        ):
            if "tax" in q_lower or "finance" in q_lower:
                suggested_rules.append(
                    {
                        "rule_id": "rule_tax_1099_w2",
                        "name": "IRS Tax Forms & 1099/W2 Statements",
                        "category": "TAX_FINANCE",
                        "target_tier": "COLD_NAS",
                        "destination_subpath": "Finance/Taxes/{year}/IRS_Forms/{filename}",
                        "name_keywords": ["1099", "w2", "1040", "irs", "tax_return"],
                        "priority": 160,
                    }
                )
                recommendations.append("Add structured tax classification rule targeting long-term COLD_NAS retention.")

            if "log" in q_lower or "sysadmin" in q_lower or "homelab" in q_lower:
                suggested_rules.append(
                    {
                        "rule_id": "rule_pcap_syslog_active",
                        "name": "Live Sysadmin PCAP & Audit Telemetry",
                        "category": "HOMELAB_SYSADMIN",
                        "target_tier": "HOT_NVME",
                        "destination_subpath": "Homelab/Telemetry/{year}/{filename}",
                        "name_keywords": ["syslog", "pcap", "auditd", "suricata", "wazuh"],
                        "priority": 155,
                    }
                )
                recommendations.append("Route high-velocity security telemetry to HOT_NVME for real-time analysis.")

            if "receipt" in q_lower or "invoice" in q_lower:
                suggested_rules.append(
                    {
                        "rule_id": "rule_business_invoices",
                        "name": "Commercial Invoices & Hardware Receipts",
                        "category": "RECEIPTS_INVOICES",
                        "target_tier": "WARM_SSD",
                        "destination_subpath": "Finance/Receipts/{year}/{month}/{filename}",
                        "name_keywords": ["invoice", "receipt", "order_confirmation", "po_"],
                        "priority": 145,
                    }
                )
                recommendations.append("Maintain monthly date partitioning `{year}/{month}` for rapid receipt audits.")

        # Default summary & fallback advice
        if not recommendations:
            recommendations.append(
                f"Catalog currently tracking {context['total_indexed_files']} indexed files across {context['total_rules']} taxonomy rules."
            )
            recommendations.append(
                "Run `nasroute route /path/to/inbox --dry-run` to preview deterministic document placement without modifying files."
            )

        summary_text = (
            f"NASRoute Storage Advisor evaluated your query against {context['total_indexed_files']} indexed documents "
            f"and {len(context['tiers'])} configured storage tiers. "
            f"Identified {len(recommendations)} actionable recommendations."
        )

        return CompanionResponse(
            query=query,
            summary=summary_text,
            recommendations=recommendations,
            suggested_rules=suggested_rules,
            storage_optimization=optimization,
            confidence=0.98,
        )
