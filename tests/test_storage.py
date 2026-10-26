"""Tests for audit storage ledger."""

from promptguard.models import ActionVerdict, AuditLogEntry, RiskTier
from promptguard.storage import AuditStorage


def test_audit_storage(tmp_path):
    storage = AuditStorage(data_dir=tmp_path)
    assert storage.load_all() == []

    entry = AuditLogEntry(
        request_id="test-1",
        timestamp="2026-10-26T12:00:00Z",
        client_ip="127.0.0.1",
        upstream_url="http://localhost:11434",
        verdict=ActionVerdict.BLOCK,
        risk_tier=RiskTier.HIGH,
        risk_score=75,
        pii_count=1,
        threat_count=1,
        reasons=["Blocked override"],
    )
    storage.append(entry)

    loaded = storage.load_all()
    assert len(loaded) == 1
    assert loaded[0].request_id == "test-1"
    assert loaded[0].verdict == ActionVerdict.BLOCK

    stats = storage.get_summary_stats()
    assert stats["total_requests"] == 1
    assert stats["blocked"] == 1
    assert stats["total_pii_redactions"] == 1

    storage.clear()
    assert storage.load_all() == []
