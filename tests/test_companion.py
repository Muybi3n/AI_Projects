import json

from canarymesh.advisor import CanaryMeshAdvisor
from canarymesh.models import (
    AlertSeverity,
    DecoyArtifact,
    DecoyCategory,
    TripwireAlert,
    TripwireTriggerType,
    utc_now_iso,
)


def test_advisor_heuristic_clean():
    advisor = CanaryMeshAdvisor()
    art = DecoyArtifact(
        token_id="CANARY-1",
        name="art1",
        category=DecoyCategory.AWS_CREDENTIALS,
        file_path="/tmp/f1",
        expected_sha256="s1",
        expected_blake2b="b1",
        file_size_bytes=10,
        created_at=utc_now_iso(),
        last_checked_at=utc_now_iso(),
        canary_identifier="CANARY-1",
    )
    art2 = DecoyArtifact(
        token_id="CANARY-2",
        name="art2",
        category=DecoyCategory.SSH_KEY,
        file_path="/tmp/f2",
        expected_sha256="s2",
        expected_blake2b="b2",
        file_size_bytes=10,
        created_at=utc_now_iso(),
        last_checked_at=utc_now_iso(),
        canary_identifier="CANARY-2",
    )
    art3 = DecoyArtifact(
        token_id="CANARY-3",
        name="art3",
        category=DecoyCategory.ENV_SECRETS,
        file_path="/tmp/f3",
        expected_sha256="s3",
        expected_blake2b="b3",
        file_size_bytes=10,
        created_at=utc_now_iso(),
        last_checked_at=utc_now_iso(),
        canary_identifier="CANARY-3",
    )
    resp = advisor.consult("What is our security posture?", [art, art2, art3], [])
    assert "HEALTHY DECEPTION POSTURE" in resp.threat_assessment
    assert len(resp.recommendations) > 0


def test_advisor_heuristic_alert():
    advisor = CanaryMeshAdvisor()
    alert = TripwireAlert(
        alert_id="ALT-1",
        token_id="CANARY-1",
        file_path="/tmp/creds",
        trigger_type=TripwireTriggerType.TAMPERED,
        severity=AlertSeverity.CRITICAL,
        detected_at=utc_now_iso(),
        mitre_technique="T1565.001",
        summary="Tampering detected",
    )
    resp = advisor.consult("What happened?", [], [alert])
    assert "HIGH ALERT" in resp.threat_assessment
    assert any("containment" in a.lower() for a in resp.suggested_actions)


def test_advisor_pluggable_llm():
    def mock_llm(query: str, context: dict) -> str:
        return json.dumps(
            {
                "threat_assessment": "Custom LLM Deception Assessment",
                "recommendations": ["Recommendation A", "Recommendation B"],
                "suggested_actions": ["Action 1"],
                "mitre_references": ["T1078"],
            }
        )

    advisor = CanaryMeshAdvisor(custom_llm_callable=mock_llm)
    resp = advisor.consult("Advise me", [], [])
    assert resp.threat_assessment == "Custom LLM Deception Assessment"
    assert "Recommendation A" in resp.recommendations
