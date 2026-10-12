"""Core analytics, warranty radar, depreciation, and claim generation engine."""

from __future__ import annotations

import calendar
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path

from shelfwise.models import (
    Asset,
    AuditReport,
    DepreciationRecord,
    InsuranceClaimItem,
    InsuranceClaimPack,
    MaintenanceRecord,
    ProofStatus,
    WarrantyEvaluation,
    WarrantyTier,
)


def add_months_to_date(d: date, months: int) -> date:
    """Accurately add calendar months to a date, clamping end-of-month days."""
    if months == 0:
        return d
    new_month = d.month + months
    year_offset = (new_month - 1) // 12
    final_month = (new_month - 1) % 12 + 1
    final_year = d.year + year_offset

    # Clamp day for months with fewer days (e.g. Feb 29 -> Feb 28 on non-leap years)
    max_days = calendar.monthrange(final_year, final_month)[1]
    final_day = min(d.day, max_days)
    return date(final_year, final_month, final_day)


def parse_date(date_str: str) -> date | None:
    """Safely parse ISO YYYY-MM-DD date."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        return None


def calculate_warranty(asset: Asset, reference_date: date | None = None) -> WarrantyEvaluation:
    """Evaluate warranty status, tier, and days remaining for an asset."""
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    if not asset.purchase_date:
        return WarrantyEvaluation(
            asset_id=asset.id,
            asset_name=asset.name,
            purchase_date="",
            expiration_date=None,
            days_remaining=None,
            tier=WarrantyTier.EXPIRED,
            cc_extension_eligible=False,
            total_warranty_months=0,
            notes="No purchase date recorded; treated as expired.",
        )

    purchase_d = parse_date(asset.purchase_date)
    if purchase_d is None:
        return WarrantyEvaluation(
            asset_id=asset.id,
            asset_name=asset.name,
            purchase_date=asset.purchase_date,
            expiration_date=None,
            days_remaining=None,
            tier=WarrantyTier.EXPIRED,
            cc_extension_eligible=False,
            total_warranty_months=0,
            notes="Invalid purchase date format; expected YYYY-MM-DD.",
        )

    # Lifetime warranty
    if asset.warranty_months == -1:
        return WarrantyEvaluation(
            asset_id=asset.id,
            asset_name=asset.name,
            purchase_date=asset.purchase_date,
            expiration_date=None,
            days_remaining=None,
            tier=WarrantyTier.LIFETIME,
            cc_extension_eligible=False,
            total_warranty_months=-1,
            notes="Manufacturer lifetime warranty active.",
        )

    total_months = max(0, asset.warranty_months) + max(0, asset.extended_warranty_months)
    if total_months == 0:
        days_past = (reference_date - purchase_d).days
        return WarrantyEvaluation(
            asset_id=asset.id,
            asset_name=asset.name,
            purchase_date=asset.purchase_date,
            expiration_date=purchase_d.isoformat(),
            days_remaining=-days_past if days_past > 0 else 0,
            tier=WarrantyTier.EXPIRED,
            cc_extension_eligible=False,
            total_warranty_months=0,
            notes="No standard or extended warranty specified.",
        )

    expiration_d = add_months_to_date(purchase_d, total_months)
    days_remaining = (expiration_d - reference_date).days

    # Determine warranty tier
    if days_remaining < 0:
        tier = WarrantyTier.EXPIRED
    elif days_remaining <= 14:
        tier = WarrantyTier.CRITICAL
    elif days_remaining <= 45:
        tier = WarrantyTier.WARNING
    else:
        tier = WarrantyTier.ACTIVE

    # Check credit card extended warranty protection eligibility:
    # Most major cards grant +1 additional year on eligible items with manufacturer warranties <= 36 months.
    cc_eligible = False
    cc_notes = []
    if asset.extended_warranty_months == 0 and 0 < asset.warranty_months <= 36 and asset.purchase_price >= 50.0:
        # Eligible if expired within the last 365 days, or currently active
        mfg_exp = add_months_to_date(purchase_d, asset.warranty_months)
        days_since_mfg_exp = (reference_date - mfg_exp).days
        if 0 <= days_since_mfg_exp <= 365:
            cc_eligible = True
            cc_notes.append(
                f"Manufacturer warranty expired {days_since_mfg_exp}d ago, but secondary credit card warranty protection (+1 yr) may still be claimable."
            )
        elif days_since_mfg_exp < 0:
            cc_eligible = True
            cc_notes.append("Eligible for credit card extended warranty protection (+1 yr beyond manufacturer expiry).")

    note_text = (
        " ".join(cc_notes)
        if cc_notes
        else (
            f"Extended warranty: {asset.extended_warranty_notes}"
            if asset.extended_warranty_notes
            else "Standard warranty."
        )
    )

    return WarrantyEvaluation(
        asset_id=asset.id,
        asset_name=asset.name,
        purchase_date=asset.purchase_date,
        expiration_date=expiration_d.isoformat(),
        days_remaining=days_remaining,
        tier=tier,
        cc_extension_eligible=cc_eligible,
        total_warranty_months=total_months,
        notes=note_text,
    )


def calculate_depreciation(
    asset: Asset,
    reference_date: date | None = None,
    method: str = "tech_curve",
) -> DepreciationRecord:
    """Calculate current depreciated fair-market value and replacement cost."""
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    purchase_d = parse_date(asset.purchase_date) or reference_date
    age_days = max(0, (reference_date - purchase_d).days)
    age_years = age_days / 365.25

    price = max(0.0, float(asset.purchase_price))

    if method == "straight_line":
        # 5-year linear depreciation down to 10% salvage floor
        salvage = price * 0.10
        annual_dep = (price - salvage) / 5.0
        depreciated = max(salvage, price - annual_dep * min(5.0, age_years))
    else:
        # Tech curve: rapid initial depreciation with 12% salvage floor
        if age_years <= 1.0:
            depreciated = price * (1.0 - 0.25 * age_years)
        elif age_years <= 2.0:
            depreciated = price * (0.75 - 0.15 * (age_years - 1.0))
        elif age_years <= 3.0:
            depreciated = price * (0.60 - 0.12 * (age_years - 2.0))
        else:
            depreciated = max(price * 0.12, price * (0.48 - 0.08 * (age_years - 3.0)))

    # Replacement cost adjusted for inflation / replacement index (3.0% annual inflation, capped at 5 yrs)
    inflation_factor = (1.03) ** min(5.0, age_years)
    replacement_cost = round(price * inflation_factor, 2)

    return DepreciationRecord(
        asset_id=asset.id,
        asset_name=asset.name,
        purchase_price=round(price, 2),
        purchase_date=asset.purchase_date,
        age_years=round(age_years, 2),
        depreciated_value=round(depreciated, 2),
        replacement_cost_estimate=replacement_cost,
        depreciation_method=method,
    )


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_receipt(asset: Asset, base_dir: Path | None = None) -> tuple[ProofStatus, str | None]:
    """Verify presence and cryptographic hash integrity of the receipt file."""
    if not asset.receipt_path:
        return ProofStatus.MISSING, None

    path = Path(asset.receipt_path)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path

    if not path.is_file():
        return ProofStatus.MISSING, None

    try:
        current_hash = compute_file_sha256(path)
    except (OSError, PermissionError):
        return ProofStatus.PENDING, None

    if asset.receipt_hash:
        if current_hash.lower() == asset.receipt_hash.lower():
            return ProofStatus.VERIFIED, current_hash
        return ProofStatus.PENDING, current_hash

    return ProofStatus.VERIFIED, current_hash


def build_insurance_claim_pack(
    assets: list[Asset],
    incident_type: str = "theft_or_loss",
    incident_date: str | None = None,
    reference_date: date | None = None,
    base_dir: Path | None = None,
) -> InsuranceClaimPack:
    """Package selected assets into an insurance or warranty claim dossier."""
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    if not incident_date:
        incident_date = reference_date.isoformat()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    claim_id = f"CLAIM_{incident_type.upper()}_{timestamp}"

    total_orig = 0.0
    total_repl = 0.0
    total_depr = 0.0
    claim_items: list[InsuranceClaimItem] = []
    verified_count = 0
    missing_count = 0

    for asset in assets:
        dep_rec = calculate_depreciation(asset, reference_date=reference_date)
        status, verified_hash = verify_receipt(asset, base_dir=base_dir)

        if status == ProofStatus.VERIFIED:
            verified_count += 1
        elif status == ProofStatus.MISSING:
            missing_count += 1

        total_orig += asset.purchase_price
        total_repl += dep_rec.replacement_cost_estimate
        total_depr += dep_rec.depreciated_value

        category_val = asset.category.value if hasattr(asset.category, "value") else str(asset.category)

        claim_items.append(
            InsuranceClaimItem(
                asset_id=asset.id,
                name=asset.name,
                category=category_val,
                brand=asset.brand,
                model=asset.model,
                serial_number=asset.serial_number or "NOT_RECORDED",
                purchase_date=asset.purchase_date,
                purchase_price=round(asset.purchase_price, 2),
                replacement_estimate=dep_rec.replacement_cost_estimate,
                depreciated_value=dep_rec.depreciated_value,
                receipt_status=status,
                receipt_hash=verified_hash or asset.receipt_hash,
                receipt_path=asset.receipt_path,
            )
        )

    checklist = [
        "1. Attach digital receipt files and SHA-256 integrity proofs for verified assets.",
        "2. For missing receipts, attach vendor order confirmations, bank statement excerpts, or serial lookup screenshots.",
        "3. File a local police report and obtain a formal case number if incident involves theft or burglary.",
        "4. Verify that physical serial numbers match the exact entries registered on carrier/vendor accounts.",
        "5. Submit secondary claims to credit card purchase protection if items were acquired within 90-120 days.",
    ]

    return InsuranceClaimPack(
        claim_id=claim_id,
        incident_type=incident_type,
        incident_date=incident_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_original_cost=round(total_orig, 2),
        total_replacement_cost=round(total_repl, 2),
        total_depreciated_value=round(total_depr, 2),
        items=claim_items,
        verified_receipts_count=verified_count,
        missing_receipts_count=missing_count,
        checklist=checklist,
    )


def audit_inventory(
    assets: list[Asset],
    maintenance_records: list[MaintenanceRecord],
    reference_date: date | None = None,
    base_dir: Path | None = None,
) -> AuditReport:
    """Run comprehensive fleet inventory audit and risk assessment."""
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    total_purchase = 0.0
    total_depreciated = 0.0
    active_warranties = 0
    expiring_warranties = 0
    expired_warranties = 0
    lifetime_warranties = 0
    missing_receipts = 0
    missing_receipts_high_value = 0
    active_rma = 0

    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_location: dict[str, int] = {}

    for asset in assets:
        total_purchase += asset.purchase_price
        dep_rec = calculate_depreciation(asset, reference_date=reference_date)
        total_depreciated += dep_rec.depreciated_value

        w_eval = calculate_warranty(asset, reference_date=reference_date)
        if w_eval.tier == WarrantyTier.ACTIVE:
            active_warranties += 1
        elif w_eval.tier in (WarrantyTier.CRITICAL, WarrantyTier.WARNING):
            expiring_warranties += 1
        elif w_eval.tier == WarrantyTier.EXPIRED:
            expired_warranties += 1
        elif w_eval.tier == WarrantyTier.LIFETIME:
            lifetime_warranties += 1

        proof_status, _ = verify_receipt(asset, base_dir=base_dir)
        if proof_status == ProofStatus.MISSING:
            missing_receipts += 1
            if asset.purchase_price >= 250.0:
                missing_receipts_high_value += 1

        cat_str = asset.category.value if hasattr(asset.category, "value") else str(asset.category)
        stat_str = asset.status.value if hasattr(asset.status, "value") else str(asset.status)
        loc_str = asset.location or "Unassigned"

        by_category[cat_str] = by_category.get(cat_str, 0) + 1
        by_status[stat_str] = by_status.get(stat_str, 0) + 1
        by_location[loc_str] = by_location.get(loc_str, 0) + 1

        if stat_str.lower() == "rma":
            active_rma += 1

    total_maint_spend = sum(record.cost for record in maintenance_records)

    recommendations: list[str] = []
    if expiring_warranties > 0:
        recommendations.append(
            f"Prompt Action: {expiring_warranties} asset(s) have warranties expiring within 45 days. Run `shelfwise warranty` to inspect upcoming deadlines."
        )
    if missing_receipts_high_value > 0:
        recommendations.append(
            f"Insurance Risk: {missing_receipts_high_value} high-value asset(s) (>= $250.00) lack proof-of-purchase receipts. Run `shelfwise receipts --missing-only` to attach invoice records."
        )
    if active_rma > 0:
        recommendations.append(
            f"RMA Tracking: {active_rma} device(s) currently in RMA status. Monitor vendor return deadlines."
        )
    if total_maint_spend > (total_purchase * 0.25) and total_purchase > 0:
        recommendations.append(
            f"High Maintenance Cost: Cumulative repair expenses (${total_maint_spend:,.2f}) exceed 25% of fleet purchase value. Consider retiring lemon hardware."
        )
    if not recommendations:
        recommendations.append(
            "Hardware Fleet Optimal: All assets are accounted for with active warranty and receipt protections."
        )

    return AuditReport(
        total_assets=len(assets),
        total_purchase_value=round(total_purchase, 2),
        total_depreciated_value=round(total_depreciated, 2),
        active_warranties_count=active_warranties,
        expiring_warranties_count=expiring_warranties,
        expired_warranties_count=expired_warranties,
        lifetime_warranties_count=lifetime_warranties,
        missing_receipts_count=missing_receipts,
        missing_receipts_high_value_count=missing_receipts_high_value,
        total_maintenance_spend=round(total_maint_spend, 2),
        active_rma_count=active_rma,
        by_category=by_category,
        by_status=by_status,
        by_location=by_location,
        recommendations=recommendations,
    )
