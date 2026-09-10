# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for AI Estate & Fiduciary Advisor companion.
"""

from trustguard.ai_advisor import EstateAdvisor, build_estate_context
from trustguard.models import ScheduleAsset, TitlingStatus, TrustEntity


def test_build_estate_context():
    a = ScheduleAsset(name="House", estimated_value=750000.0, titling_status=TitlingStatus.TITLED_TO_TRUST)
    trust = TrustEntity(assets=[a])

    ctx = build_estate_context(trust)
    assert ctx["total_estate_value_usd"] == 750000.0
    assert ctx["funding_metrics"]["funded_to_trust_pct"] == 100.0


def test_heuristic_advisor_probate_query():
    a = ScheduleAsset(name="Unfunded Car", estimated_value=40000.0, titling_status=TitlingStatus.UNFUNDED_PROBATE_RISK)
    trust = TrustEntity(assets=[a])

    advisor = EstateAdvisor()
    resp = advisor.consult("What assets are at risk of probate?", trust)

    assert "Unfunded Car" in resp.probate_risk_items[0]
    assert len(resp.action_items) > 0


def test_custom_llm_estate_adapter():
    trust = TrustEntity()

    def mock_llm(q: str, ctx: dict) -> str:
        return '{"executive_summary": "Estate Plan is pristine.", "action_items": ["Review annual tax returns"]}'

    advisor = EstateAdvisor(custom_llm_callable=mock_llm)
    resp = advisor.consult("Audit my fiduciary readiness", trust)

    assert resp.executive_summary == "Estate Plan is pristine."
    assert "Review annual tax returns" in resp.action_items
