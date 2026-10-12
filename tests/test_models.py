"""Unit tests for ShelfWise data models and enums."""

from shelfwise.models import (
    AdvisorResponse,
    Asset,
    AssetCategory,
    AssetCondition,
    AssetStatus,
    AuditReport,
    DepreciationRecord,
    InsuranceClaimItem,
    InsuranceClaimPack,
    MaintenanceRecord,
    MaintenanceType,
    ProofStatus,
    WarrantyEvaluation,
    WarrantyTier,
)


def test_asset_creation_and_serialization():
    asset = Asset(
        id="test-mac-mini",
        name="Mac Mini M2",
        category=AssetCategory.HOMELAB,
        brand="Apple",
        model="A2686",
        serial_number="C02G1234567",
        purchase_date="2024-01-15",
        purchase_price=599.00,
        vendor="Apple Store",
        condition=AssetCondition.NEW,
        location="Rack 1",
        status=AssetStatus.ACTIVE,
        warranty_months=12,
        extended_warranty_months=12,
        extended_warranty_notes="AppleCare+",
        receipt_path="/receipts/apple.pdf",
        receipt_hash="abcdef123456",
        invoice_id="INV-9999",
        tags=["server", "nuc"],
        notes="Primary reverse proxy",
    )

    data = asset.to_dict()
    assert data["id"] == "test-mac-mini"
    assert data["category"] == "homelab"
    assert data["condition"] == "new"
    assert data["status"] == "active"
    assert data["purchase_price"] == 599.00

    # Roundtrip from_dict
    reconstructed = Asset.from_dict(data)
    assert reconstructed.id == asset.id
    assert reconstructed.category == AssetCategory.HOMELAB
    assert reconstructed.condition == AssetCondition.NEW
    assert reconstructed.status == AssetStatus.ACTIVE
    assert reconstructed.tags == ["server", "nuc"]


def test_asset_enum_coercion_fallbacks():
    data = {
        "id": "unknown-device",
        "name": "Custom Hardware",
        "category": "non_existent_category",
        "condition": "non_existent_condition",
        "status": "non_existent_status",
    }
    asset = Asset.from_dict(data)
    assert asset.category == AssetCategory.OTHER
    assert asset.condition == AssetCondition.NEW
    assert asset.status == AssetStatus.ACTIVE


def test_maintenance_record():
    record = MaintenanceRecord(
        id="maint-001",
        asset_id="test-mac-mini",
        date="2025-06-01",
        maintenance_type=MaintenanceType.UPGRADE,
        cost=85.50,
        description="Installed 2TB NVMe SSD",
        performed_by="Self",
        rma_ticket="TICK-123",
    )
    d = record.to_dict()
    assert d["maintenance_type"] == "upgrade"
    assert d["cost"] == 85.50

    reconstructed = MaintenanceRecord.from_dict(d)
    assert reconstructed.id == "maint-001"
    assert reconstructed.maintenance_type == MaintenanceType.UPGRADE

    # Invalid maintenance type fallback
    bad_dict = {"id": "m2", "asset_id": "a1", "date": "2025-01-01", "maintenance_type": "alien_repair"}
    bad_rec = MaintenanceRecord.from_dict(bad_dict)
    assert bad_rec.maintenance_type == MaintenanceType.OTHER


def test_warranty_evaluation_model():
    eval_obj = WarrantyEvaluation(
        asset_id="a1",
        asset_name="Server",
        purchase_date="2024-01-01",
        expiration_date="2025-01-01",
        days_remaining=10,
        tier=WarrantyTier.CRITICAL,
        cc_extension_eligible=True,
        total_warranty_months=12,
        notes="Expiring soon",
    )
    d = eval_obj.to_dict()
    assert d["tier"] == "critical"
    assert d["days_remaining"] == 10
    assert d["cc_extension_eligible"] is True


def test_depreciation_and_claim_pack_models():
    dep = DepreciationRecord(
        asset_id="a1",
        asset_name="Monitor",
        purchase_price=300.0,
        purchase_date="2023-01-01",
        age_years=2.0,
        depreciated_value=180.0,
        replacement_cost_estimate=318.0,
    )
    assert dep.to_dict()["depreciated_value"] == 180.0

    item = InsuranceClaimItem(
        asset_id="a1",
        name="Monitor",
        category="peripherals",
        brand="Dell",
        model="U2723QE",
        serial_number="SN123",
        purchase_date="2023-01-01",
        purchase_price=300.0,
        replacement_estimate=318.0,
        depreciated_value=180.0,
        receipt_status=ProofStatus.VERIFIED,
    )
    assert item.to_dict()["receipt_status"] == "verified"

    pack = InsuranceClaimPack(
        claim_id="CLAIM_THEFT_01",
        incident_type="theft_or_loss",
        incident_date="2026-10-01",
        generated_at="2026-10-12T00:00:00Z",
        total_original_cost=300.0,
        total_replacement_cost=318.0,
        total_depreciated_value=180.0,
        items=[item],
        verified_receipts_count=1,
        missing_receipts_count=0,
        checklist=["Attach police report"],
    )
    p_dict = pack.to_dict()
    assert p_dict["claim_id"] == "CLAIM_THEFT_01"
    assert len(p_dict["items"]) == 1
    assert p_dict["items"][0]["receipt_status"] == "verified"


def test_audit_report_and_advisor_response():
    audit = AuditReport(
        total_assets=5,
        total_purchase_value=2500.0,
        total_depreciated_value=1600.0,
        active_warranties_count=3,
        expiring_warranties_count=1,
        expired_warranties_count=1,
        lifetime_warranties_count=0,
        missing_receipts_count=2,
        missing_receipts_high_value_count=1,
        total_maintenance_spend=120.0,
        active_rma_count=0,
        recommendations=["Backup receipts"],
    )
    assert audit.to_dict()["total_assets"] == 5

    advisor = AdvisorResponse(
        query="Are my warranties expiring?",
        summary="1 warranty expiring soon.",
        findings=["Found 1 critical warranty."],
        recommendations=["Check Dell server."],
    )
    assert advisor.to_dict()["query"] == "Are my warranties expiring?"
