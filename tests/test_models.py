# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for trust models and data structures.
"""

from trustguard.models import (
    AssetCategory,
    BeneficiaryRule,
    DistributionScheme,
    ScheduleAsset,
    TrustEntity,
    TrustType,
)


def test_trust_entity_valuation():
    a1 = ScheduleAsset(name="Primary Residence", category=AssetCategory.REAL_ESTATE, estimated_value=850000.0)
    a2 = ScheduleAsset(name="Brokerage Account", category=AssetCategory.BROKERAGE_ACCOUNT, estimated_value=400000.0)

    trust = TrustEntity(
        trust_name="Test Trust",
        trust_type=TrustType.REVOCABLE_LIVING,
        assets=[a1, a2],
    )

    assert trust.total_estate_value == 1250000.0
    d = trust.to_dict()
    assert len(d["assets"]) == 2
    assert d["trust_type"] == "revocable_living"


def test_beneficiary_rule_serialization():
    b = BeneficiaryRule(
        beneficiary_name="Alice Smith",
        relationship="child",
        scheme=DistributionScheme.OUTRIGHT_PERCENTAGE,
        share_pct=50.0,
    )
    d = b.to_dict()
    assert d["scheme"] == "outright_percentage"
    assert d["share_pct"] == 50.0
