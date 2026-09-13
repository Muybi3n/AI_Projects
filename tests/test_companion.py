"""Unit tests for nasroute AI companion and heuristic reasoner."""

import json
from pathlib import Path

from nasroute.ai_companion import NASRouteCompanion, build_sanitized_context
from nasroute.storage import NASRouteStore


def test_companion_heuristic_consult(tmp_path: Path):
    store = NASRouteStore(data_dir=tmp_path / "nas_data")
    companion = NASRouteCompanion()

    # Query storage tier strategy
    resp_tier = companion.consult("How should I optimize my NVMe and HDD cold storage tiers?", store)
    assert resp_tier.confidence >= 0.9
    assert len(resp_tier.recommendations) > 0
    assert "HOT_NVME" in resp_tier.storage_optimization.get("tier_strategy", {})

    # Query tax and sysadmin rule generation
    resp_rules = companion.consult("Suggest taxonomy rules for IRS tax returns and homelab syslog telemetry", store)
    assert len(resp_rules.suggested_rules) >= 2
    rule_ids = [r["rule_id"] for r in resp_rules.suggested_rules]
    assert "rule_tax_1099_w2" in rule_ids
    assert "rule_pcap_syslog_active" in rule_ids

    # Query deduplication
    resp_dedup = companion.consult("What is the deduplication status and checksum integrity?", store)
    assert any("Integrity & Deduplication" in rec for rec in resp_dedup.recommendations)


def test_companion_custom_llm_adapter(tmp_path: Path):
    store = NASRouteStore(data_dir=tmp_path / "nas_data")

    # Mock custom LLM returning valid JSON
    def mock_llm_json(prompt: str, context: dict) -> str:
        return json.dumps(
            {
                "summary": "Custom LLM homelab storage assessment.",
                "recommendations": ["Rebalance ZFS pool", "Enable compression on cold tier"],
                "suggested_rules": [],
                "storage_optimization": {"pool_health": "OPTIMAL"},
                "confidence": 0.99,
            }
        )

    companion_custom = NASRouteCompanion(custom_llm_callable=mock_llm_json)
    resp = companion_custom.consult("Audit storage pool", store)
    assert resp.summary == "Custom LLM homelab storage assessment."
    assert "Rebalance ZFS pool" in resp.recommendations
    assert resp.confidence == 0.99

    # Mock custom LLM returning plain text
    def mock_llm_raw(prompt: str, context: dict) -> str:
        return "Raw textual advice for NAS routing."

    companion_raw = NASRouteCompanion(custom_llm_callable=mock_llm_raw)
    resp_raw = companion_raw.consult("Raw prompt", store)
    assert resp_raw.summary == "Raw textual advice for NAS routing."


def test_build_sanitized_context(tmp_path: Path):
    store = NASRouteStore(data_dir=tmp_path / "nas_data")
    ctx = build_sanitized_context(store)
    assert "tiers" in ctx
    assert "rules" in ctx
    assert "total_indexed_files" in ctx
    assert "deduplication_summary" in ctx
