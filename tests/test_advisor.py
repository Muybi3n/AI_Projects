"""Unit tests for ShelfWise hardware advisor and PII scrubbed LLM adapter."""

import json
from datetime import date

from shelfwise.advisor import (
    HardwareAdvisor,
    build_sanitized_context,
    mask_identifier,
)
from shelfwise.models import (
    Asset,
    AssetCategory,
    MaintenanceRecord,
    MaintenanceType,
)


def test_mask_identifier():
    assert mask_identifier("") == ""
    assert mask_identifier("123", "ID") == "ID_***"
    assert mask_identifier("ABC12345", "SN") == "SN_***2345"
    assert mask_identifier("SECRET_SERIAL_XYZ9", "DEV") == "DEV_***XYZ9"


def test_sanitized_context_pii_scrubbing():
    asset = Asset(
        id="dev-01",
        name="Primary Workstation",
        serial_number="SECRET_SN_9999",
        purchase_date="2024-01-01",
        purchase_price=2500.0,
        receipt_path="/home/user/documents/receipts/workstation_invoice.pdf",
    )
    maint = [
        MaintenanceRecord(
            id="m-01",
            asset_id="dev-01",
            date="2024-06-01",
            maintenance_type=MaintenanceType.UPGRADE,
            cost=200.0,
            description="Upgraded RAM",
        )
    ]

    context = build_sanitized_context([asset], maint, reference_date=date(2025, 1, 1))
    device = context["devices"][0]

    # Serial number masked
    assert device["masked_serial"] == "SN_***9999"
    assert "SECRET_SN" not in device["masked_serial"]

    # File path stripped to basename only
    assert "/home/user" not in device["receipt_file"]
    assert "workstation_invoice.pdf" in device["receipt_file"]


def test_advisor_empty_fleet():
    advisor = HardwareAdvisor()
    res = advisor.consult("What is expiring?", assets=[], maintenance=[], reference_date=date(2025, 1, 1))
    assert "No hardware assets" in res.summary
    assert len(res.recommendations) > 0


def test_advisor_warranty_intent():
    advisor = HardwareAdvisor()
    ref = date(2025, 1, 1)
    assets = [
        Asset(
            id="a1",
            name="Expiring Server",
            purchase_date="2024-01-10",
            warranty_months=12,  # Expires 2025-01-10 (9 days left -> CRITICAL)
        )
    ]
    res = advisor.consult("Check upcoming warranty expirations", assets=assets, maintenance=[], reference_date=ref)
    assert any("Expiring Server" in f for f in res.findings)
    assert any("stress-tests" in r for r in res.recommendations)


def test_advisor_insurance_and_missing_receipts():
    advisor = HardwareAdvisor()
    ref = date(2025, 1, 1)
    assets = [
        Asset(
            id="a1",
            name="Unreceipted GPU",
            purchase_date="2024-01-01",
            purchase_price=999.00,
            receipt_path=None,  # Missing receipt on > $250 item
        )
    ]
    res = advisor.consult("Do I have receipts for insurance claims?", assets=assets, maintenance=[], reference_date=ref)
    assert any("Unverified Receipts" in f for f in res.findings)
    assert any("shelfwise update" in r for r in res.recommendations)


def test_advisor_maintenance_lemon_detection():
    advisor = HardwareAdvisor()
    ref = date(2025, 1, 1)
    assets = [
        Asset(
            id="a1",
            name="Troublesome Laptop",
            purchase_date="2023-01-01",
            purchase_price=500.0,
        )
    ]
    maint = [
        MaintenanceRecord(
            id="m1",
            asset_id="a1",
            date="2023-06-01",
            cost=150.0,
            maintenance_type=MaintenanceType.REPAIR,
        ),
        MaintenanceRecord(
            id="m2",
            asset_id="a1",
            date="2024-01-01",
            cost=150.0,
            maintenance_type=MaintenanceType.REPAIR,
        ),
    ]  # Total $300 > 50% of $500
    res = advisor.consult("Review maintenance and repairs", assets=assets, maintenance=maint, reference_date=ref)
    assert any("High Repair Burden" in f for f in res.findings)
    assert any("retiring or replacing" in r for r in res.recommendations)


def test_advisor_homelab_intent():
    advisor = HardwareAdvisor()
    ref = date(2025, 1, 1)
    assets = [
        Asset(
            id="a1",
            name="Unifi Dream Machine",
            category=AssetCategory.NETWORKING,
            purchase_price=379.0,
        ),
        Asset(
            id="a2",
            name="TrueNAS Mini",
            category=AssetCategory.HOMELAB,
            purchase_price=1200.0,
        ),
    ]
    res = advisor.consult("Homelab status and network storage", assets=assets, maintenance=[], reference_date=ref)
    assert any("Homelab & Network" in f for f in res.findings)
    assert any("cold-spare" in r for r in res.recommendations)


def test_advisor_custom_llm_callable():
    def mock_llm_json(prompt: str, context: dict) -> str:
        return json.dumps(
            {
                "summary": "Mock LLM analyzed your devices.",
                "findings": ["Custom finding from mock model."],
                "recommendations": ["Custom recommendation."],
            }
        )

    advisor = HardwareAdvisor(custom_llm_callable=mock_llm_json)
    res = advisor.consult("Analyze my setup", assets=[], maintenance=[])
    assert res.summary == "Mock LLM analyzed your devices."
    assert "Custom finding from mock model." in res.findings

    # Fallback when model returns raw non-JSON text
    def mock_llm_raw(prompt: str, context: dict) -> str:
        return "Here is a prose summary from an external LLM."

    advisor_raw = HardwareAdvisor(custom_llm_callable=mock_llm_raw)
    res_raw = advisor_raw.consult("Analyze", assets=[], maintenance=[])
    assert res_raw.summary == "Here is a prose summary from an external LLM."
