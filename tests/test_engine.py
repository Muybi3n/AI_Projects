"""Unit tests for ShelfWise engine calculations and analysis."""

from datetime import date
from pathlib import Path

from shelfwise.engine import (
    add_months_to_date,
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
    AssetStatus,
    MaintenanceRecord,
    MaintenanceType,
    ProofStatus,
    WarrantyTier,
)


def test_add_months_to_date():
    d1 = date(2024, 1, 15)
    assert add_months_to_date(d1, 0) == d1
    assert add_months_to_date(d1, 1) == date(2024, 2, 15)
    assert add_months_to_date(d1, 12) == date(2025, 1, 15)
    assert add_months_to_date(d1, 15) == date(2025, 4, 15)

    # End of month clamping
    d_jan31 = date(2023, 1, 31)
    assert add_months_to_date(d_jan31, 1) == date(2023, 2, 28)  # non-leap year Feb
    d_jan31_leap = date(2024, 1, 31)
    assert add_months_to_date(d_jan31_leap, 1) == date(2024, 2, 29)  # leap year Feb


def test_parse_date():
    assert parse_date("2024-05-20") == date(2024, 5, 20)
    assert parse_date("") is None
    assert parse_date("invalid-date") is None


def test_calculate_warranty_tiers():
    ref = date(2025, 1, 1)

    # 1. Lifetime warranty
    asset_life = Asset(
        id="life-01",
        name="Cable Matters Cable",
        purchase_date="2020-01-01",
        warranty_months=-1,
    )
    eval_life = calculate_warranty(asset_life, reference_date=ref)
    assert eval_life.tier == WarrantyTier.LIFETIME
    assert eval_life.days_remaining is None

    # 2. Expired warranty
    asset_exp = Asset(
        id="exp-01",
        name="Old Router",
        purchase_date="2022-01-01",
        warranty_months=12,
        purchase_price=80.0,
    )
    eval_exp = calculate_warranty(asset_exp, reference_date=ref)
    assert eval_exp.tier == WarrantyTier.EXPIRED
    assert eval_exp.days_remaining is not None and eval_exp.days_remaining < 0

    # 3. Critical warranty (expires in <= 14 days)
    # Ref is 2025-01-01. Expiration 2025-01-10 -> 9 days remaining.
    asset_crit = Asset(
        id="crit-01",
        name="Dell Server",
        purchase_date="2024-01-10",
        warranty_months=12,
        purchase_price=900.0,
    )
    eval_crit = calculate_warranty(asset_crit, reference_date=ref)
    assert eval_crit.tier == WarrantyTier.CRITICAL
    assert eval_crit.days_remaining == 9

    # 4. Warning warranty (15 to 45 days)
    # Expiration 2025-01-31 -> 30 days remaining.
    asset_warn = Asset(
        id="warn-01",
        name="NAS Synology",
        purchase_date="2024-01-31",
        warranty_months=12,
        purchase_price=650.0,
    )
    eval_warn = calculate_warranty(asset_warn, reference_date=ref)
    assert eval_warn.tier == WarrantyTier.WARNING
    assert eval_warn.days_remaining == 30

    # 5. Active warranty (> 45 days)
    asset_act = Asset(
        id="act-01",
        name="MacBook Pro",
        purchase_date="2024-08-01",
        warranty_months=12,
        purchase_price=2000.0,
    )
    eval_act = calculate_warranty(asset_act, reference_date=ref)
    assert eval_act.tier == WarrantyTier.ACTIVE
    assert eval_act.days_remaining is not None and eval_act.days_remaining > 45


def test_calculate_warranty_credit_card_extension():
    ref = date(2025, 1, 1)

    # Purchased 2023-08-01, standard 12 months expired on 2024-08-01 (153 days ago)
    # Within 365 days of mfg expiration -> CC extension eligible!
    asset = Asset(
        id="cc-01",
        name="Nikon Camera",
        purchase_date="2023-08-01",
        purchase_price=800.0,
        warranty_months=12,
    )
    eval_res = calculate_warranty(asset, reference_date=ref)
    assert eval_res.tier == WarrantyTier.EXPIRED
    assert eval_res.cc_extension_eligible is True
    assert "credit card warranty protection" in eval_res.notes


def test_calculate_depreciation_curves():
    ref = date(2025, 1, 1)
    asset = Asset(
        id="dep-01",
        name="Gaming GPU",
        purchase_date="2023-01-01",  # exactly ~2 years old
        purchase_price=1000.0,
    )

    tech_dep = calculate_depreciation(asset, reference_date=ref, method="tech_curve")
    assert tech_dep.age_years >= 1.9
    assert tech_dep.depreciated_value < 1000.0
    assert tech_dep.depreciated_value >= 120.0  # above salvage floor
    assert tech_dep.replacement_cost_estimate >= 1000.0

    line_dep = calculate_depreciation(asset, reference_date=ref, method="straight_line")
    assert line_dep.depreciated_value < 1000.0
    assert line_dep.depreciated_value >= 100.0


def test_verify_receipt(tmp_path: Path):
    receipt_file = tmp_path / "invoice_bestbuy.pdf"
    receipt_file.write_text("DUMMY INVOICE CONTENT 12345")
    expected_hash = compute_file_sha256(receipt_file)

    # 1. Missing receipt path
    a_none = Asset(id="a1", name="Mouse", receipt_path=None)
    st, h = verify_receipt(a_none, base_dir=tmp_path)
    assert st == ProofStatus.MISSING
    assert h is None

    # 2. File doesn't exist
    a_missing = Asset(id="a2", name="Keyboard", receipt_path=str(tmp_path / "non_existent.pdf"))
    st, h = verify_receipt(a_missing, base_dir=tmp_path)
    assert st == ProofStatus.MISSING
    assert h is None

    # 3. File exists and hash matches
    a_valid = Asset(
        id="a3",
        name="Monitor",
        receipt_path=str(receipt_file),
        receipt_hash=expected_hash,
    )
    st, h = verify_receipt(a_valid, base_dir=tmp_path)
    assert st == ProofStatus.VERIFIED
    assert h == expected_hash

    # 4. Hash mismatch (pending/modified)
    a_tampered = Asset(
        id="a4",
        name="Laptop",
        receipt_path=str(receipt_file),
        receipt_hash="mismatched_hash_9999",
    )
    st, h = verify_receipt(a_tampered, base_dir=tmp_path)
    assert st == ProofStatus.PENDING


def test_build_insurance_claim_pack(tmp_path: Path):
    rec_file = tmp_path / "receipt.pdf"
    rec_file.write_text("RECEIPT CONTENT")
    rec_hash = compute_file_sha256(rec_file)

    assets = [
        Asset(
            id="a1",
            name="MacBook Pro 16",
            brand="Apple",
            model="M3 Max",
            serial_number="C02ABC123",
            purchase_date="2024-01-01",
            purchase_price=3499.00,
            receipt_path=str(rec_file),
            receipt_hash=rec_hash,
        ),
        Asset(
            id="a2",
            name="Sony Headphones",
            brand="Sony",
            model="WH-1000XM5",
            serial_number="",
            purchase_date="2024-02-01",
            purchase_price=399.00,
            receipt_path=None,
        ),
    ]

    ref = date(2025, 1, 1)
    pack = build_insurance_claim_pack(
        assets=assets,
        incident_type="theft_or_loss",
        incident_date="2025-01-01",
        reference_date=ref,
        base_dir=tmp_path,
    )

    assert pack.total_original_cost == 3898.00
    assert pack.total_replacement_cost > 3898.00
    assert pack.verified_receipts_count == 1
    assert pack.missing_receipts_count == 1
    assert len(pack.items) == 2
    assert len(pack.checklist) >= 5


def test_audit_inventory():
    assets = [
        Asset(
            id="a1",
            name="Server",
            category=AssetCategory.HOMELAB,
            purchase_date="2024-12-25",
            purchase_price=1200.0,
            warranty_months=1,  # Expiring in Jan 2025 (critical / warning)
        ),
        Asset(
            id="a2",
            name="GPU",
            category=AssetCategory.COMPUTING,
            purchase_date="2022-01-01",
            purchase_price=800.0,
            warranty_months=12,  # Expired
            status=AssetStatus.RMA,
        ),
    ]
    maintenance = [
        MaintenanceRecord(
            id="m1",
            asset_id="a2",
            date="2024-05-01",
            maintenance_type=MaintenanceType.RMA,
            cost=150.0,
            description="Fan replacement RMA",
            rma_ticket="RMA-999",
        )
    ]

    ref = date(2025, 1, 1)
    report = audit_inventory(assets, maintenance, reference_date=ref)

    assert report.total_assets == 2
    assert report.total_purchase_value == 2000.0
    assert report.total_maintenance_spend == 150.0
    assert report.active_rma_count == 1
    assert report.expiring_warranties_count == 1
    assert report.expired_warranties_count == 1
    assert len(report.recommendations) >= 1
