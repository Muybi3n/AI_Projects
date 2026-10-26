"""Tests for PromptGuard data models."""

from promptguard.models import (
    ActionVerdict,
    AuditLogEntry,
    InjectionThreat,
    PIIMatch,
    PromptScanResult,
    ProxyConfig,
    RiskTier,
)


def test_models_to_dict():
    pii = PIIMatch(
        entity_type="EMAIL",
        original_value="alice@example.com",
        redacted_token="[EMAIL_REDACTED]",
        start=0,
        end=17,
    )
    assert pii.to_dict()["entity_type"] == "EMAIL"

    threat = InjectionThreat(
        category="DIRECT_OVERRIDE",
        matched_pattern="ignore all instructions",
        confidence=0.95,
        description="Override test",
        mitre_technique="AML.T0051.000",
    )
    assert threat.to_dict()["category"] == "DIRECT_OVERRIDE"

    scan_res = PromptScanResult(
        original_text="test",
        sanitized_text="test",
        verdict=ActionVerdict.ALLOW,
        risk_tier=RiskTier.SAFE,
        risk_score=0,
        pii_matches=[pii],
        threats=[threat],
        reasons=["Sample reason"],
    )
    d = scan_res.to_dict()
    assert d["verdict"] == "ALLOW"
    assert len(d["pii_matches"]) == 1
    assert len(d["threats"]) == 1

    entry = AuditLogEntry(
        request_id="req-1",
        timestamp="2026-10-26T12:00:00Z",
        client_ip="127.0.0.1",
        upstream_url="http://localhost:11434",
        verdict=ActionVerdict.BLOCK,
        risk_tier=RiskTier.CRITICAL,
        risk_score=95,
        pii_count=0,
        threat_count=1,
    )
    assert entry.to_dict()["request_id"] == "req-1"

    config = ProxyConfig()
    assert config.to_dict()["listen_port"] == 8088
