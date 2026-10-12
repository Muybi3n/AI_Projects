"""Command-line interface for ShelfWise hardware asset management."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from shelfwise.advisor import HardwareAdvisor
from shelfwise.engine import (
    audit_inventory,
    build_insurance_claim_pack,
    calculate_depreciation,
    calculate_warranty,
    compute_file_sha256,
    parse_date,
    verify_receipt,
)
from shelfwise.models import (
    Asset,
    AssetCategory,
    AssetCondition,
    AssetStatus,
    MaintenanceRecord,
    MaintenanceType,
    ProofStatus,
    WarrantyTier,
)
from shelfwise.storage import ShelfWiseStorage


def slugify(text: str) -> str:
    """Convert string to a clean identifier slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", text).strip("-")


def get_reference_date(date_str: str | None) -> date:
    """Parse reference date override or default to current UTC date."""
    if date_str:
        parsed = parse_date(date_str)
        if parsed:
            return parsed
    return datetime.now(timezone.utc).date()


def create_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="shelfwise",
        description="ShelfWise: Local-first hardware asset inventory, warranty radar & insurance claim packager.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom storage directory path (defaults to ~/.shelfwise)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--ref-date",
        type=str,
        default=None,
        help="Override current evaluation date (YYYY-MM-DD)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    subparsers.add_parser("init", help="Initialize or verify local ShelfWise environment")

    # add
    add_p = subparsers.add_parser("add", help="Add a new hardware asset to inventory")
    add_p.add_argument("--name", type=str, required=True, help="Asset name / description")
    add_p.add_argument("--id", type=str, default=None, help="Custom asset ID slug")
    add_p.add_argument(
        "--category",
        type=str,
        default="computing",
        choices=[c.value for c in AssetCategory],
        help="Asset category",
    )
    add_p.add_argument("--brand", type=str, default="", help="Manufacturer / brand")
    add_p.add_argument("--model", type=str, default="", help="Model number / name")
    add_p.add_argument("--serial", type=str, default="", help="Serial number")
    add_p.add_argument("--price", type=float, default=0.0, help="Purchase price in USD")
    add_p.add_argument(
        "--purchase-date",
        type=str,
        default="",
        help="Purchase date (YYYY-MM-DD)",
    )
    add_p.add_argument("--vendor", type=str, default="", help="Vendor / retailer")
    add_p.add_argument(
        "--condition",
        type=str,
        default="new",
        choices=[c.value for c in AssetCondition],
        help="Acquisition condition",
    )
    add_p.add_argument("--location", type=str, default="Default", help="Deployment location")
    add_p.add_argument(
        "--status",
        type=str,
        default="active",
        choices=[s.value for s in AssetStatus],
        help="Operational status",
    )
    add_p.add_argument(
        "--warranty-months",
        type=int,
        default=12,
        help="Manufacturer warranty months (-1=lifetime, 0=none)",
    )
    add_p.add_argument(
        "--ext-warranty-months",
        type=int,
        default=0,
        help="Extended warranty months",
    )
    add_p.add_argument(
        "--ext-warranty-notes",
        type=str,
        default="",
        help="Extended warranty terms / provider",
    )
    add_p.add_argument(
        "--receipt",
        type=str,
        default=None,
        help="Path to receipt / invoice file",
    )
    add_p.add_argument("--invoice", type=str, default=None, help="Invoice / Order number")
    add_p.add_argument("--tags", type=str, default="", help="Comma-separated tags")
    add_p.add_argument("--notes", type=str, default="", help="Additional notes")

    # list
    list_p = subparsers.add_parser("list", help="List registered hardware assets")
    list_p.add_argument("--category", type=str, default=None, help="Filter by category")
    list_p.add_argument("--status", type=str, default=None, help="Filter by status")
    list_p.add_argument("--location", type=str, default=None, help="Filter by location")

    # show
    show_p = subparsers.add_parser("show", help="Display detailed specifications for an asset")
    show_p.add_argument("asset_id", type=str, help="Asset ID slug")

    # update
    up_p = subparsers.add_parser("update", help="Update attributes of an existing asset")
    up_p.add_argument("asset_id", type=str, help="Asset ID slug")
    up_p.add_argument("--name", type=str, default=None, help="New name")
    up_p.add_argument("--category", type=str, default=None, choices=[c.value for c in AssetCategory])
    up_p.add_argument("--brand", type=str, default=None)
    up_p.add_argument("--model", type=str, default=None)
    up_p.add_argument("--serial", type=str, default=None)
    up_p.add_argument("--price", type=float, default=None)
    up_p.add_argument("--purchase-date", type=str, default=None)
    up_p.add_argument("--vendor", type=str, default=None)
    up_p.add_argument("--condition", type=str, default=None, choices=[c.value for c in AssetCondition])
    up_p.add_argument("--location", type=str, default=None)
    up_p.add_argument("--status", type=str, default=None, choices=[s.value for s in AssetStatus])
    up_p.add_argument("--warranty-months", type=int, default=None)
    up_p.add_argument("--ext-warranty-months", type=int, default=None)
    up_p.add_argument("--ext-warranty-notes", type=str, default=None)
    up_p.add_argument("--receipt", type=str, default=None)
    up_p.add_argument("--invoice", type=str, default=None)
    up_p.add_argument("--tags", type=str, default=None)
    up_p.add_argument("--notes", type=str, default=None)

    # delete
    del_p = subparsers.add_parser("delete", help="Remove an asset from inventory")
    del_p.add_argument("asset_id", type=str, help="Asset ID slug")
    del_p.add_argument("--yes", action="store_true", help="Bypass confirmation prompt")

    # warranty
    w_p = subparsers.add_parser("warranty", help="Warranty radar and expiration tracking")
    w_p.add_argument("--days", type=int, default=None, help="Filter warranties expiring within N days")
    w_p.add_argument(
        "--tier",
        type=str,
        default=None,
        choices=[t.value for t in WarrantyTier],
        help="Filter by warranty urgency tier",
    )

    # audit
    subparsers.add_parser("audit", help="Run full fleet inventory audit and risk analysis")

    # receipts
    rec_p = subparsers.add_parser("receipts", help="Inspect proof-of-purchase coverage and verify integrity")
    rec_p.add_argument("--missing-only", action="store_true", help="Show only assets lacking receipt proofs")
    rec_p.add_argument("--verify-files", action="store_true", help="Check physical disk presence & sha256")

    # log-maintenance
    m_p = subparsers.add_parser("log-maintenance", help="Record a maintenance, repair, or RMA event")
    m_p.add_argument("--asset-id", type=str, required=True, help="Target asset ID")
    m_p.add_argument(
        "--type",
        type=str,
        default="inspection",
        choices=[t.value for t in MaintenanceType],
        help="Maintenance action type",
    )
    m_p.add_argument("--date", type=str, default="", help="Event date (YYYY-MM-DD)")
    m_p.add_argument("--cost", type=float, default=0.0, help="Maintenance cost in USD")
    m_p.add_argument("--desc", type=str, default="", help="Description of work done")
    m_p.add_argument("--performed-by", type=str, default="Self", help="Service provider or technician")
    m_p.add_argument("--rma-ticket", type=str, default=None, help="RMA or support ticket number")

    # maintenance-history
    mh_p = subparsers.add_parser("maintenance-history", help="List maintenance and repair history")
    mh_p.add_argument("--asset-id", type=str, default=None, help="Filter by asset ID")

    # claim-pack
    cp_p = subparsers.add_parser("claim-pack", help="Generate an insurance or warranty loss/damage claim bundle")
    cp_p.add_argument("--asset-id", type=str, default=None, help="Single asset ID (or all active if omitted)")
    cp_p.add_argument(
        "--incident",
        type=str,
        default="theft_or_loss",
        choices=["theft_or_loss", "power_surge", "water_damage", "transit_damage", "accidental_damage", "fire"],
        help="Incident classification",
    )
    cp_p.add_argument("--incident-date", type=str, default="", help="Incident date (YYYY-MM-DD)")
    cp_p.add_argument("--output", type=str, default=None, help="File path to save Markdown or JSON dossier")

    # ask
    ask_p = subparsers.add_parser("ask", help="Query the hardware advisor using natural language")
    ask_p.add_argument("query", type=str, help="Natural language inquiry")

    # export
    exp_p = subparsers.add_parser("export", help="Export inventory database to JSON or CSV")
    exp_p.add_argument("--format", type=str, default="json", choices=["json", "csv"], help="Export format")
    exp_p.add_argument("--output", type=str, default=None, help="Output destination file path")

    return parser


def handle_init(storage: ShelfWiseStorage, as_json: bool) -> int:
    """Initialize local environment."""
    assets = storage.list_assets()
    maintenance = storage.list_maintenance()
    res = {
        "status": "ready",
        "data_dir": str(storage.data_dir),
        "assets_count": len(assets),
        "maintenance_count": len(maintenance),
    }
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print(f"📦 ShelfWise initialized at: {storage.data_dir}")
        print(f"   Assets recorded: {len(assets)} | Maintenance events: {len(maintenance)}")
    return 0


def handle_add(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Add a new hardware asset."""
    # Generate ID if missing
    asset_id = args.id
    if not asset_id:
        slug_base = slugify(f"{args.brand}-{args.name}" if args.brand else args.name)
        existing = storage.get_asset(slug_base)
        if existing is None:
            asset_id = slug_base
        else:
            ts = datetime.now(timezone.utc).strftime("%H%M%S")
            asset_id = f"{slug_base}-{ts}"

    p_date = args.purchase_date or ref_date.isoformat()

    # Hash receipt file if provided and exists
    receipt_hash = None
    if args.receipt:
        rec_path = Path(args.receipt)
        if rec_path.is_file():
            try:
                receipt_hash = compute_file_sha256(rec_path)
            except OSError:
                pass

    tags_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    asset = Asset(
        id=asset_id,
        name=args.name,
        category=AssetCategory(args.category),
        brand=args.brand,
        model=args.model,
        serial_number=args.serial,
        purchase_date=p_date,
        purchase_price=args.price,
        vendor=args.vendor,
        condition=AssetCondition(args.condition),
        location=args.location,
        status=AssetStatus(args.status),
        warranty_months=args.warranty_months,
        extended_warranty_months=args.ext_warranty_months,
        extended_warranty_notes=args.ext_warranty_notes,
        receipt_path=args.receipt,
        receipt_hash=receipt_hash,
        invoice_id=args.invoice,
        tags=tags_list,
        notes=args.notes,
    )

    storage.save_asset(asset)

    if args.json:
        print(json.dumps(asset.to_dict(), indent=2))
    else:
        w_eval = calculate_warranty(asset, reference_date=ref_date)
        print(f"✅ Added asset '{asset.name}' (ID: {asset.id})")
        print(
            f"   Category: {asset.category.value} | Price: ${asset.purchase_price:,.2f} | Status: {asset.status.value}"
        )
        print(
            f"   Warranty: {w_eval.tier.value.upper()} (Expires: {w_eval.expiration_date or 'N/A'}, Days: {w_eval.days_remaining})"
        )
        if asset.receipt_path:
            status_str = "Verified" if receipt_hash else "Path recorded (file missing)"
            print(f"   Receipt: {asset.receipt_path} [{status_str}]")
    return 0


def handle_list(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """List assets."""
    assets = storage.list_assets(
        category=args.category,
        status=args.status,
        location=args.location,
    )

    if args.json:
        print(json.dumps([a.to_dict() for a in assets], indent=2))
        return 0

    if not assets:
        print("No assets found matching the specified filters.")
        return 0

    print(f"\n📋 Registered Hardware Assets ({len(assets)} total):")
    header = f"{'ID':<20} {'NAME':<28} {'CATEGORY':<14} {'PRICE':<10} {'STATUS':<10} {'WARRANTY':<12} {'LOCATION':<14}"
    print(header)
    print("-" * len(header))

    for asset in assets:
        w_eval = calculate_warranty(asset, reference_date=ref_date)
        tier_display = w_eval.tier.value.upper()
        cat_display = asset.category.value if hasattr(asset.category, "value") else str(asset.category)
        stat_display = asset.status.value if hasattr(asset.status, "value") else str(asset.status)
        print(
            f"{asset.id:<20} {asset.name[:26]:<28} {cat_display:<14} "
            f"${asset.purchase_price:<9.2f} {stat_display:<10} {tier_display:<12} {asset.location[:12]:<14}"
        )
    print()
    return 0


def handle_show(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Show details of a single asset."""
    asset = storage.get_asset(args.asset_id)
    if not asset:
        print(f"❌ Error: Asset '{args.asset_id}' not found.", file=sys.stderr)
        return 1

    w_eval = calculate_warranty(asset, reference_date=ref_date)
    dep_rec = calculate_depreciation(asset, reference_date=ref_date)
    proof_stat, computed_hash = verify_receipt(asset)
    maint_records = storage.list_maintenance(asset_id=asset.id)

    if args.json:
        payload = {
            "asset": asset.to_dict(),
            "warranty": w_eval.to_dict(),
            "depreciation": dep_rec.to_dict(),
            "receipt_verification": {
                "status": proof_stat.value,
                "verified_hash": computed_hash,
            },
            "maintenance_records": [m.to_dict() for m in maint_records],
        }
        print(json.dumps(payload, indent=2))
        return 0

    cat_val = asset.category.value if hasattr(asset.category, "value") else str(asset.category)
    cond_val = asset.condition.value if hasattr(asset.condition, "value") else str(asset.condition)
    stat_val = asset.status.value if hasattr(asset.status, "value") else str(asset.status)

    print(f"\n🔍 Asset Details: {asset.name} (ID: {asset.id})")
    print(f"   Brand / Model:      {asset.brand or 'N/A'} {asset.model or ''}")
    print(f"   Serial Number:      {asset.serial_number or 'NOT_RECORDED'}")
    print(f"   Category:           {cat_val} | Condition: {cond_val} | Status: {stat_val}")
    print(f"   Location:           {asset.location} | Vendor: {asset.vendor or 'N/A'}")
    print(f"   Purchase Date:      {asset.purchase_date or 'N/A'} | Price: ${asset.purchase_price:,.2f}")
    print(
        f"   Current Est. Value: ${dep_rec.depreciated_value:,.2f} (Age: {dep_rec.age_years:.1f} yrs, Repl: ${dep_rec.replacement_cost_estimate:,.2f})"
    )
    print("-" * 65)
    print("🛡️ Warranty Radar:")
    print(f"   Status Tier:        {w_eval.tier.value.upper()}")
    print(f"   Expiration Date:    {w_eval.expiration_date or 'N/A'}")
    print(f"   Days Remaining:     {w_eval.days_remaining if w_eval.days_remaining is not None else 'N/A'}")
    print(f"   CC Extension Perk:  {'Eligible (+1 yr)' if w_eval.cc_extension_eligible else 'None'}")
    if w_eval.notes:
        print(f"   Notes:              {w_eval.notes}")
    print("-" * 65)
    print("🧾 Proof of Purchase:")
    print(f"   Receipt File:       {asset.receipt_path or 'None'}")
    print(f"   Verification:       {proof_stat.value.upper()}")
    if computed_hash:
        print(f"   SHA-256 Hash:       {computed_hash}")
    if asset.invoice_id:
        print(f"   Invoice / Order ID: {asset.invoice_id}")
    if asset.tags:
        print(f"   Tags:               {', '.join(asset.tags)}")
    print("-" * 65)
    print(f"🔧 Maintenance History ({len(maint_records)} events):")
    if maint_records:
        for m in maint_records:
            m_type = m.maintenance_type.value if hasattr(m.maintenance_type, "value") else str(m.maintenance_type)
            rma_info = f" [RMA: {m.rma_ticket}]" if m.rma_ticket else ""
            print(f"   - {m.date} | {m_type.upper()} | ${m.cost:,.2f}{rma_info} | {m.description}")
    else:
        print("   No maintenance events logged.")
    print()
    return 0


def handle_update(args: argparse.Namespace, storage: ShelfWiseStorage) -> int:
    """Update asset fields."""
    asset = storage.get_asset(args.asset_id)
    if not asset:
        print(f"❌ Error: Asset '{args.asset_id}' not found.", file=sys.stderr)
        return 1

    if args.name is not None:
        asset.name = args.name
    if args.category is not None:
        asset.category = AssetCategory(args.category)
    if args.brand is not None:
        asset.brand = args.brand
    if args.model is not None:
        asset.model = args.model
    if args.serial is not None:
        asset.serial_number = args.serial
    if args.price is not None:
        asset.purchase_price = args.price
    if args.purchase_date is not None:
        asset.purchase_date = args.purchase_date
    if args.vendor is not None:
        asset.vendor = args.vendor
    if args.condition is not None:
        asset.condition = AssetCondition(args.condition)
    if args.location is not None:
        asset.location = args.location
    if args.status is not None:
        asset.status = AssetStatus(args.status)
    if args.warranty_months is not None:
        asset.warranty_months = args.warranty_months
    if args.ext_warranty_months is not None:
        asset.extended_warranty_months = args.ext_warranty_months
    if args.ext_warranty_notes is not None:
        asset.extended_warranty_notes = args.ext_warranty_notes
    if args.receipt is not None:
        asset.receipt_path = args.receipt
        rec_path = Path(args.receipt)
        if rec_path.is_file():
            try:
                asset.receipt_hash = compute_file_sha256(rec_path)
            except OSError:
                pass
    if args.invoice is not None:
        asset.invoice_id = args.invoice
    if args.tags is not None:
        asset.tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.notes is not None:
        asset.notes = args.notes

    asset.updated_at = datetime.now(timezone.utc).isoformat()
    storage.save_asset(asset)

    if args.json:
        print(json.dumps(asset.to_dict(), indent=2))
    else:
        print(f"✅ Updated asset '{asset.name}' ({asset.id})")
    return 0


def handle_delete(args: argparse.Namespace, storage: ShelfWiseStorage) -> int:
    """Delete asset."""
    asset = storage.get_asset(args.asset_id)
    if not asset:
        print(f"❌ Error: Asset '{args.asset_id}' not found.", file=sys.stderr)
        return 1

    if not args.yes:
        # Require confirmation in interactive shell
        confirm = input(f"Are you sure you want to delete asset '{asset.name}' ({asset.id})? [y/N]: ")
        if confirm.lower() != "y":
            print("Deletion cancelled.")
            return 0

    storage.delete_asset(asset.id)
    if args.json:
        print(json.dumps({"deleted": True, "asset_id": asset.id}))
    else:
        print(f"🗑️ Deleted asset '{asset.name}' ({asset.id})")
    return 0


def handle_warranty(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Run warranty radar."""
    assets = storage.list_assets()
    results: list[dict] = []

    for asset in assets:
        w_eval = calculate_warranty(asset, reference_date=ref_date)
        if args.tier and w_eval.tier.value.lower() != args.tier.lower():
            continue
        if args.days is not None:
            if w_eval.days_remaining is None or w_eval.days_remaining > args.days:
                continue
        results.append(
            {
                "asset": asset,
                "evaluation": w_eval,
            }
        )

    if args.json:
        payload = [
            {
                "asset_id": r["asset"].id,
                "asset_name": r["asset"].name,
                "evaluation": r["evaluation"].to_dict(),
            }
            for r in results
        ]
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\n🛡️ Warranty Radar (Reference: {ref_date.isoformat()} | {len(results)} items):")
    header = f"{'TIER':<10} {'DAYS':<8} {'EXPIRATION':<12} {'ASSET ID':<20} {'ASSET NAME':<26} {'CC EXTENSION'}"
    print(header)
    print("-" * len(header))

    # Sort: CRITICAL, WARNING, ACTIVE, LIFETIME, EXPIRED
    order = {
        WarrantyTier.CRITICAL: 1,
        WarrantyTier.WARNING: 2,
        WarrantyTier.ACTIVE: 3,
        WarrantyTier.LIFETIME: 4,
        WarrantyTier.EXPIRED: 5,
    }
    results.sort(key=lambda r: (order.get(r["evaluation"].tier, 99), r["evaluation"].days_remaining or 9999))

    for r in results:
        w_eval = r["evaluation"]
        asset = r["asset"]
        days_str = str(w_eval.days_remaining) if w_eval.days_remaining is not None else "N/A"
        cc_str = "Eligible (+1y)" if w_eval.cc_extension_eligible else "-"
        print(
            f"{w_eval.tier.value.upper():<10} {days_str:<8} {w_eval.expiration_date or 'N/A':<12} "
            f"{asset.id:<20} {asset.name[:24]:<26} {cc_str}"
        )
    print()
    return 0


def handle_audit(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Run fleet audit."""
    assets = storage.list_assets()
    maintenance = storage.list_maintenance()
    report = audit_inventory(assets, maintenance, reference_date=ref_date)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print("\n📊 ShelfWise Fleet Inventory Audit & Risk Summary:")
    print(f"   Total Assets Tracked:         {report.total_assets}")
    print(f"   Total Acquisition Cost:       ${report.total_purchase_value:,.2f}")
    print(f"   Current Depreciated Value:    ${report.total_depreciated_value:,.2f}")
    print(f"   Total Maintenance Spend:      ${report.total_maintenance_spend:,.2f}")
    print("-" * 60)
    print("🛡️ Warranty Coverage Breakdown:")
    print(f"   Active Warranties:            {report.active_warranties_count}")
    print(f"   Expiring Soon (<= 45d):       {report.expiring_warranties_count}")
    print(f"   Expired Warranties:           {report.expired_warranties_count}")
    print(f"   Lifetime Warranties:          {report.lifetime_warranties_count}")
    print("-" * 60)
    print("🧾 Proof of Purchase & Insurance Risk:")
    print(f"   Missing Receipts (Total):     {report.missing_receipts_count}")
    print(f"   Missing Receipts (>= $250):   {report.missing_receipts_high_value_count} [RISK]")
    print(f"   Active RMA Devices:           {report.active_rma_count}")
    print("-" * 60)
    print("💡 Strategic Action Items:")
    for rec in report.recommendations:
        print(f"   * {rec}")
    print()
    return 0


def handle_receipts(args: argparse.Namespace, storage: ShelfWiseStorage) -> int:
    """Inspect receipt files."""
    assets = storage.list_assets()
    items = []

    for asset in assets:
        status, verified_hash = verify_receipt(asset)
        if args.missing_only and status != ProofStatus.MISSING:
            continue
        items.append(
            {
                "asset_id": asset.id,
                "name": asset.name,
                "price": asset.purchase_price,
                "status": status.value,
                "path": asset.receipt_path or "",
                "hash": verified_hash or asset.receipt_hash or "",
            }
        )

    if args.json:
        print(json.dumps(items, indent=2))
        return 0

    print(f"\n🧾 Receipt & Proof-of-Purchase Registry ({len(items)} items):")
    header = f"{'STATUS':<10} {'PRICE':<10} {'ASSET ID':<20} {'RECEIPT PATH'}"
    print(header)
    print("-" * 75)

    for itm in items:
        status_disp = itm["status"].upper()
        print(f"{status_disp:<10} ${itm['price']:<9.2f} {itm['asset_id']:<20} {itm['path'] or '[MISSING]'}")
    print()
    return 0


def handle_log_maintenance(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Log maintenance event."""
    asset = storage.get_asset(args.asset_id)
    if not asset:
        print(f"❌ Error: Asset '{args.asset_id}' not found.", file=sys.stderr)
        return 1

    m_id = f"maint-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    ev_date = args.date or ref_date.isoformat()

    record = MaintenanceRecord(
        id=m_id,
        asset_id=asset.id,
        date=ev_date,
        maintenance_type=MaintenanceType(args.type),
        cost=args.cost,
        description=args.desc,
        performed_by=args.performed_by,
        rma_ticket=args.rma_ticket,
    )
    storage.save_maintenance(record)

    if args.json:
        print(json.dumps(record.to_dict(), indent=2))
    else:
        print(f"✅ Logged maintenance event for '{asset.name}' ({record.id}):")
        print(f"   Date: {record.date} | Type: {record.maintenance_type.value} | Cost: ${record.cost:,.2f}")
        if record.rma_ticket:
            print(f"   RMA Ticket: {record.rma_ticket}")
        if record.description:
            print(f"   Notes: {record.description}")
    return 0


def handle_maintenance_history(args: argparse.Namespace, storage: ShelfWiseStorage) -> int:
    """View maintenance records."""
    records = storage.list_maintenance(asset_id=args.asset_id)

    if args.json:
        print(json.dumps([m.to_dict() for m in records], indent=2))
        return 0

    if not records:
        print("No maintenance records found.")
        return 0

    print(f"\n🔧 Maintenance History ({len(records)} events):")
    header = f"{'DATE':<12} {'TYPE':<12} {'COST':<10} {'ASSET ID':<20} {'RMA TICKET':<14} {'DESCRIPTION'}"
    print(header)
    print("-" * len(header))

    for m in records:
        m_type = m.maintenance_type.value if hasattr(m.maintenance_type, "value") else str(m.maintenance_type)
        print(
            f"{m.date:<12} {m_type:<12} ${m.cost:<9.2f} {m.asset_id:<20} {m.rma_ticket or '-':<14} {m.description[:30]}"
        )
    print()
    return 0


def handle_claim_pack(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Build insurance claim dossier."""
    if args.asset_id:
        target_asset = storage.get_asset(args.asset_id)
        if not target_asset:
            print(f"❌ Error: Asset '{args.asset_id}' not found.", file=sys.stderr)
            return 1
        assets = [target_asset]
    else:
        assets = storage.list_assets()

    claim_pack = build_insurance_claim_pack(
        assets=assets,
        incident_type=args.incident,
        incident_date=args.incident_date or ref_date.isoformat(),
        reference_date=ref_date,
    )

    if args.json:
        json_output = json.dumps(claim_pack.to_dict(), indent=2)
        if args.output:
            Path(args.output).write_text(json_output, encoding="utf-8")
            print(f"Saved claim pack JSON to {args.output}")
        else:
            print(json_output)
        return 0

    # Format Markdown claim dossier
    lines = [
        f"# 🛡️ INSURANCE & WARRANTY CLAIM PACK: {claim_pack.claim_id}",
        "",
        f"**Incident Type:** {claim_pack.incident_type.upper()}  ",
        f"**Incident Date:** {claim_pack.incident_date}  ",
        f"**Dossier Generated:** {claim_pack.generated_at}  ",
        "",
        "## 💰 Financial Valuation Summary",
        f"- **Total Original Cost:** ${claim_pack.total_original_cost:,.2f}",
        f"- **Estimated Replacement Cost:** ${claim_pack.total_replacement_cost:,.2f}",
        f"- **Current Depreciated Value:** ${claim_pack.total_depreciated_value:,.2f}",
        f"- **Verified Receipts:** {claim_pack.verified_receipts_count} of {len(claim_pack.items)} items",
        "",
        "## 📦 Asset Loss Inventory Schedule",
        "| Asset Name | Serial Number | Purchase Date | Original Cost | Repl. Value | Proof Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for itm in claim_pack.items:
        lines.append(
            f"| {itm.name} | `{itm.serial_number}` | {itm.purchase_date} | "
            f"${itm.purchase_price:,.2f} | ${itm.replacement_estimate:,.2f} | {itm.receipt_status.value.upper()} |"
        )

    lines.extend(
        [
            "",
            "## 📋 Claims Action Checklist",
        ]
    )
    for step in claim_pack.checklist:
        lines.append(f"- [ ] {step}")

    lines.extend(
        [
            "",
            "---",
            "*Affidavit: The undersigned affirms that the hardware items cataloged above were lawfully acquired and deployed as described.*",
        ]
    )

    report_text = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(report_text, encoding="utf-8")
        print(f"📄 Generated claim pack saved to: {args.output}")
    else:
        print(report_text)

    return 0


def handle_ask(args: argparse.Namespace, storage: ShelfWiseStorage, ref_date: date) -> int:
    """Consult hardware advisor."""
    assets = storage.list_assets()
    maintenance = storage.list_maintenance()
    advisor = HardwareAdvisor()

    response = advisor.consult(
        query=args.query,
        assets=assets,
        maintenance=maintenance,
        reference_date=ref_date,
    )

    if args.json:
        print(json.dumps(response.to_dict(), indent=2))
        return 0

    print("\n🤖 ShelfWise Hardware Advisor:")
    print(f'   Query: "{response.query}"')
    print(f"\n📌 Summary:\n   {response.summary}")

    if response.findings:
        print("\n🔍 Key Findings:")
        for f in response.findings:
            print(f"   • {f}")

    if response.recommendations:
        print("\n💡 Strategic Recommendations:")
        for r in response.recommendations:
            print(f"   • {r}")
    print()
    return 0


def handle_export(args: argparse.Namespace, storage: ShelfWiseStorage) -> int:
    """Export inventory database."""
    content = storage.export_data(format_type=args.format)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"✅ Exported database to {args.output} ({args.format.upper()})")
    else:
        print(content)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    storage = ShelfWiseStorage(data_dir=args.data_dir)
    ref_date = get_reference_date(args.ref_date)

    if args.command == "init":
        return handle_init(storage, args.json)
    elif args.command == "add":
        return handle_add(args, storage, ref_date)
    elif args.command == "list":
        return handle_list(args, storage, ref_date)
    elif args.command == "show":
        return handle_show(args, storage, ref_date)
    elif args.command == "update":
        return handle_update(args, storage)
    elif args.command == "delete":
        return handle_delete(args, storage)
    elif args.command == "warranty":
        return handle_warranty(args, storage, ref_date)
    elif args.command == "audit":
        return handle_audit(args, storage, ref_date)
    elif args.command == "receipts":
        return handle_receipts(args, storage)
    elif args.command == "log-maintenance":
        return handle_log_maintenance(args, storage, ref_date)
    elif args.command == "maintenance-history":
        return handle_maintenance_history(args, storage)
    elif args.command == "claim-pack":
        return handle_claim_pack(args, storage, ref_date)
    elif args.command == "ask":
        return handle_ask(args, storage, ref_date)
    elif args.command == "export":
        return handle_export(args, storage)

    return 0


if __name__ == "__main__":
    sys.exit(main())
