# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for funding audit, probate risk detection, and waterfall distribution engine.
"""

from trustguard.engine import EstateEngine
from trustguard.models import (
    BeneficiaryRule,
    DistributionScheme,
    ScheduleAsset,
    TitlingStatus,
    TrustEntity,
)


def test_audit_funding_probate_risk():
    a1 = ScheduleAsset(name="Home", estimated_value=500000.0, titling_status=TitlingStatus.TITLED_TO_TRUST)
    a2 = ScheduleAsset(
        name="Unassigned LLC", estimated_value=500000.0, titling_status=TitlingStatus.UNFUNDED_PROBATE_RISK
    )

    trust = TrustEntity(assets=[a1, a2])
    report = EstateEngine.audit_funding(trust)

    assert report.total_estate_value == 1000000.0
    assert report.funded_to_trust_pct == 50.0
    assert report.unfunded_probate_risk_pct == 50.0
    assert len(report.at_risk_assets) == 1
    assert "Critical" in report.probate_risk_tier


def test_waterfall_distribution_specific_and_percentages():
    a = ScheduleAsset(name="Total Assets", estimated_value=1000000.0)
    b1 = BeneficiaryRule(
        beneficiary_name="Charity Hospital",
        scheme=DistributionScheme.SPECIFIC_DOLLAR_BEQUEST,
        specific_dollar_amount=50000.0,
    )
    b2 = BeneficiaryRule(
        beneficiary_name="Child A",
        scheme=DistributionScheme.OUTRIGHT_PERCENTAGE,
        share_pct=50.0,
    )
    b3 = BeneficiaryRule(
        beneficiary_name="Child B",
        scheme=DistributionScheme.AGE_MILESTONE_TRANCHES,
        share_pct=50.0,
        milestone_schedule=[{"age": 25, "fraction": 0.5}, {"age": 30, "fraction": 0.5}],
    )

    trust = TrustEntity(assets=[a], beneficiaries=[b1, b2, b3])
    wf = EstateEngine.calculate_waterfall(trust, administrative_reserve_pct=0.0)

    assert wf.gross_estate_value == 1000000.0
    assert wf.distributable_net_estate == 1000000.0
    assert len(wf.payouts) == 3

    charity_payout = next(p for p in wf.payouts if p.beneficiary_name == "Charity Hospital")
    assert charity_payout.total_dollar_amount == 50000.0

    child_a = next(p for p in wf.payouts if p.beneficiary_name == "Child A")
    assert child_a.total_dollar_amount == 475000.0
    assert child_a.immediate_payout == 475000.0

    child_b = next(p for p in wf.payouts if p.beneficiary_name == "Child B")
    assert child_b.total_dollar_amount == 475000.0
    assert child_b.immediate_payout == 0.0
    assert len(child_b.milestone_tranches) == 2
