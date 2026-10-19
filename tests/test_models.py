from canarymesh.models import (
    AlertSeverity,
    DecoyArtifact,
    DecoyCategory,
    TripwireAlert,
    TripwireTriggerType,
    utc_now_iso,
)


def test_decoy_artifact_serialization():
    now_str = utc_now_iso()
    art = DecoyArtifact(
        token_id="CANARY-123456",
        name="test-decoy",
        category=DecoyCategory.AWS_CREDENTIALS,
        file_path="/tmp/credentials",
        expected_sha256="abc123sha",
        expected_blake2b="def456blake",
        file_size_bytes=1024,
        created_at=now_str,
        last_checked_at=now_str,
        canary_identifier="CANARY-123456",
    )
    d = art.to_dict()
    assert d["category"] == "aws_credentials"
    assert d["token_id"] == "CANARY-123456"

    restored = DecoyArtifact.from_dict(d)
    assert restored.category == DecoyCategory.AWS_CREDENTIALS
    assert restored.token_id == art.token_id


def test_tripwire_alert_serialization():
    alert = TripwireAlert(
        alert_id="ALT-123",
        token_id="CANARY-123",
        file_path="/tmp/test",
        trigger_type=TripwireTriggerType.TAMPERED,
        severity=AlertSeverity.CRITICAL,
        detected_at=utc_now_iso(),
        mitre_technique="T1565.001",
        summary="Tampering detected",
    )
    d = alert.to_dict()
    assert d["trigger_type"] == "tampered"
    assert d["severity"] == "CRITICAL"

    restored = TripwireAlert.from_dict(d)
    assert restored.trigger_type == TripwireTriggerType.TAMPERED
    assert restored.severity == AlertSeverity.CRITICAL
