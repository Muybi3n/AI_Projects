"""Deterministic offline AI hardware advisor with pluggable LLM interface."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from shelfwise.engine import (
    audit_inventory,
    calculate_depreciation,
    calculate_warranty,
    verify_receipt,
)
from shelfwise.models import (
    AdvisorResponse,
    Asset,
    MaintenanceRecord,
    ProofStatus,
    WarrantyTier,
)


def mask_identifier(ident: str, prefix: str = "ID") -> str:
    """Mask sensitive alphanumeric string retaining only the tail."""
    if not ident:
        return ""
    clean = ident.strip()
    if len(clean) <= 4:
        return f"{prefix}_***"
    return f"{prefix}_***{clean[-4:]}"


def sanitize_asset_context(asset: Asset, reference_date: date | None = None) -> dict[str, Any]:
    """Scrub PII, serial numbers, and filesystem paths from an asset dictionary."""
    w_eval = calculate_warranty(asset, reference_date=reference_date)
    dep_rec = calculate_depreciation(asset, reference_date=reference_date)
    proof_stat, _ = verify_receipt(asset)

    receipt_display = "[NONE]"
    if asset.receipt_path:
        receipt_display = f"[FILE: {Path(asset.receipt_path).name}]"

    cat_str = asset.category.value if hasattr(asset.category, "value") else str(asset.category)
    stat_str = asset.status.value if hasattr(asset.status, "value") else str(asset.status)

    return {
        "id": asset.id,
        "name": asset.name,
        "category": cat_str,
        "brand": asset.brand,
        "model": asset.model,
        "masked_serial": mask_identifier(asset.serial_number, "SN"),
        "purchase_year": asset.purchase_date[:4] if len(asset.purchase_date) >= 4 else "UNKNOWN",
        "purchase_price": asset.purchase_price,
        "current_depreciated_value": dep_rec.depreciated_value,
        "replacement_estimate": dep_rec.replacement_cost_estimate,
        "status": stat_str,
        "location": asset.location,
        "warranty_tier": w_eval.tier.value,
        "warranty_days_remaining": w_eval.days_remaining,
        "cc_extended_eligible": w_eval.cc_extension_eligible,
        "receipt_status": proof_stat.value,
        "receipt_file": receipt_display,
    }


def build_sanitized_context(
    assets: list[Asset],
    maintenance: list[MaintenanceRecord],
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Compile privacy-preserving structured context suitable for local/cloud LLMs."""
    audit = audit_inventory(assets, maintenance, reference_date=reference_date)
    scrubbed_assets = [sanitize_asset_context(asset, reference_date=reference_date) for asset in assets]

    scrubbed_maint = []
    for m in maintenance:
        scrubbed_maint.append(
            {
                "id": m.id,
                "asset_id": m.asset_id,
                "type": (m.maintenance_type.value if hasattr(m.maintenance_type, "value") else str(m.maintenance_type)),
                "cost": m.cost,
                "description": m.description,
                "has_rma": bool(m.rma_ticket),
            }
        )

    return {
        "fleet_summary": {
            "total_devices": audit.total_assets,
            "total_original_cost": audit.total_purchase_value,
            "total_depreciated_value": audit.total_depreciated_value,
            "active_warranties": audit.active_warranties_count,
            "expiring_warranties": audit.expiring_warranties_count,
            "expired_warranties": audit.expired_warranties_count,
            "missing_receipts": audit.missing_receipts_count,
            "high_value_missing_receipts": audit.missing_receipts_high_value_count,
            "maintenance_spend": audit.total_maintenance_spend,
        },
        "devices": scrubbed_assets,
        "maintenance_events": scrubbed_maint,
    }


class HardwareAdvisor:
    """Hardware fleet intelligence engine combining deterministic rules with optional LLM."""

    def __init__(
        self,
        custom_llm_callable: (Callable[[str, dict[str, Any]], str] | None) = None,
    ):
        self.custom_llm_callable = custom_llm_callable

    def consult(
        self,
        query: str,
        assets: list[Asset],
        maintenance: list[MaintenanceRecord],
        reference_date: date | None = None,
    ) -> AdvisorResponse:
        """Run advisory reasoning against the hardware fleet."""
        if reference_date is None:
            reference_date = datetime.now(timezone.utc).date()

        context = build_sanitized_context(assets, maintenance, reference_date=reference_date)

        if self.custom_llm_callable:
            raw_output = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw_output)
                return AdvisorResponse(
                    query=query,
                    summary=data.get("summary", "Advisor evaluation completed."),
                    findings=data.get("findings", []),
                    recommendations=data.get("recommendations", []),
                    pii_scrubbed_context=context,
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                # Fallback on raw string response if model didn't provide strict JSON
                return AdvisorResponse(
                    query=query,
                    summary=str(raw_output).strip(),
                    findings=[],
                    recommendations=[],
                    pii_scrubbed_context=context,
                )

        return self._heuristic_consult(query, assets, maintenance, reference_date, context)

    def _heuristic_consult(
        self,
        query: str,
        assets: list[Asset],
        maintenance: list[MaintenanceRecord],
        reference_date: date,
        context: dict[str, Any],
    ) -> AdvisorResponse:
        """Deterministic, rule-based offline advisory logic."""
        q_lower = query.lower()
        findings: list[str] = []
        recommendations: list[str] = []

        # Domain intent checks (scored independently, not if/elif)
        wants_warranty = any(
            w in q_lower
            for w in [
                "warranty",
                "warranties",
                "expire",
                "expiration",
                "guarantee",
                "deadline",
                "coverage",
            ]
        )
        wants_insurance = any(
            w in q_lower
            for w in [
                "insurance",
                "claim",
                "receipt",
                "receipts",
                "proof",
                "theft",
                "loss",
                "damage",
                "missing",
            ]
        )
        wants_maintenance = any(
            w in q_lower
            for w in [
                "maintenance",
                "repair",
                "service",
                "rma",
                "fix",
                "battery",
                "firmware",
                "lemon",
            ]
        )
        wants_homelab = any(
            w in q_lower
            for w in [
                "homelab",
                "server",
                "network",
                "networking",
                "switch",
                "nas",
                "cluster",
                "router",
            ]
        )
        wants_value = any(
            w in q_lower
            for w in [
                "worth",
                "depreciation",
                "value",
                "valuation",
                "resale",
                "cost",
                "budget",
                "portfolio",
            ]
        )

        # General inquiry if no specific domain matched
        is_general = not (wants_warranty or wants_insurance or wants_maintenance or wants_homelab or wants_value)

        total_assets = len(assets)
        if total_assets == 0:
            return AdvisorResponse(
                query=query,
                summary="No hardware assets currently tracked in ShelfWise.",
                findings=["Fleet inventory is empty."],
                recommendations=[
                    "Run `shelfwise add --name '<device>' --price <cost>` to register your first hardware device."
                ],
                pii_scrubbed_context=context,
            )

        # 1. Warranty Domain
        if wants_warranty or is_general:
            expiring_assets = []
            expired_assets = []
            cc_eligible_assets = []
            for asset in assets:
                w_eval = calculate_warranty(asset, reference_date=reference_date)
                if w_eval.tier in (WarrantyTier.CRITICAL, WarrantyTier.WARNING):
                    expiring_assets.append((asset.name, w_eval.days_remaining))
                elif w_eval.tier == WarrantyTier.EXPIRED:
                    expired_assets.append(asset.name)
                if w_eval.cc_extension_eligible:
                    cc_eligible_assets.append(asset.name)

            if expiring_assets:
                details = ", ".join(f"{name} ({days}d left)" for name, days in expiring_assets)
                findings.append(
                    f"Warranty Expiration Imminent: {len(expiring_assets)} asset(s) expiring within 45 days: {details}."
                )
                recommendations.append(
                    "Conduct physical stress-tests and inspect hardware health before warranty window closes."
                )

            if cc_eligible_assets:
                findings.append(
                    f"Credit Card Extended Warranty Opportunity: {len(cc_eligible_assets)} device(s) eligible for +1yr secondary protection."
                )

            if expired_assets and not expiring_assets:
                findings.append(
                    f"Standard Coverage Lapsed: {len(expired_assets)} asset(s) are out of manufacturer warranty."
                )

        # 2. Insurance & Receipt Domain
        if wants_insurance or is_general:
            missing_high_val = []
            for asset in assets:
                proof_stat, _ = verify_receipt(asset)
                if proof_stat == ProofStatus.MISSING and asset.purchase_price >= 250.0:
                    missing_high_val.append((asset.name, asset.purchase_price))

            if missing_high_val:
                details = ", ".join(f"{name} (${cost:,.2f})" for name, cost in missing_high_val)
                findings.append(
                    f"High-Value Unverified Receipts: {len(missing_high_val)} asset(s) lack proof-of-purchase: {details}."
                )
                recommendations.append(
                    "Locate digital PDFs or store invoices and link via `shelfwise update <id> --receipt <path>` to protect insurance claims."
                )
            else:
                findings.append("Proof-of-Purchase Integrity: All high-value items have recorded receipt proofs.")

        # 3. Maintenance & RMA Domain
        if wants_maintenance or is_general:
            active_rmas = [a.name for a in assets if str(a.status).lower().endswith("rma")]
            total_maint = sum(m.cost for m in maintenance)
            if active_rmas:
                findings.append(
                    f"Active RMAs: {len(active_rmas)} device(s) awaiting manufacturer repair/replacement: {', '.join(active_rmas)}."
                )
                recommendations.append("Follow up with vendor support tickets to ensure turnaround within SLA.")

            # Identify lemon assets (> 40% of original price in repairs)
            for asset in assets:
                asset_maint = sum(m.cost for m in maintenance if m.asset_id.lower() == asset.id.lower())
                if asset.purchase_price > 0 and asset_maint > (asset.purchase_price * 0.40):
                    findings.append(
                        f"High Repair Burden: {asset.name} has incurred ${asset_maint:,.2f} in maintenance ({asset_maint / asset.purchase_price * 100:.1f}% of original price)."
                    )
                    recommendations.append(
                        f"Evaluate retiring or replacing {asset.name} instead of investing further repair capital."
                    )

            if total_maint > 0:
                findings.append(
                    f"Total Fleet Maintenance: ${total_maint:,.2f} across {len(maintenance)} service events."
                )

        # 4. Homelab & Infrastructure Domain
        if wants_homelab:
            homelab_assets = [
                a for a in assets if a.category in ("homelab", "networking") or "homelab" in str(a.location).lower()
            ]
            homelab_cost = sum(a.purchase_price for a in homelab_assets)
            findings.append(
                f"Homelab & Network Infrastructure: {len(homelab_assets)} assets valued at ${homelab_cost:,.2f}."
            )
            recommendations.append("Maintain cold-spare replacement drives and verify offline configuration backups.")

        # 5. Value & Depreciation Domain
        if wants_value or is_general:
            total_orig = sum(a.purchase_price for a in assets)
            total_dep = sum(calculate_depreciation(a, reference_date=reference_date).depreciated_value for a in assets)
            total_repl = sum(
                calculate_depreciation(a, reference_date=reference_date).replacement_cost_estimate for a in assets
            )
            findings.append(
                f"Fleet Financial Valuation: ${total_orig:,.2f} original acquisition cost | ${total_dep:,.2f} current depreciated market value | ${total_repl:,.2f} estimated replacement cost."
            )

        summary_parts = []
        if findings:
            summary_parts.append(findings[0])
        if len(findings) > 1:
            summary_parts.append(findings[1])
        summary = " ".join(summary_parts) if summary_parts else "Hardware portfolio audit complete."

        return AdvisorResponse(
            query=query,
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            pii_scrubbed_context=context,
        )
