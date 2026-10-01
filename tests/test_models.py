from socmesh.models import (
    CorrelatedIncident,
    EventSource,
    MitreTactic,
    SecurityEvent,
    SeverityLevel,
)


def test_security_event_serialization():
    ev = SecurityEvent(
        event_id="test-1",
        source=EventSource.PIHOLE_DNS,
        timestamp="2026-09-28T10:00:00Z",
        source_ip="192.168.1.50",
        destination_ip="1.1.1.1",
        severity=SeverityLevel.LOW,
        action="DNS_QUERY",
        event_type="dns_query",
        details="Query for example.com",
        domain="example.com",
    )
    d = ev.to_dict()
    assert d["event_id"] == "test-1"
    assert d["source"] == "pihole_dns"

    rebuilt = SecurityEvent.from_dict(d)
    assert rebuilt.domain == "example.com"
    assert rebuilt.severity == SeverityLevel.LOW


def test_incident_serialization():
    inc = CorrelatedIncident(
        incident_id="INC-100",
        title="Test Incident",
        primary_tactic=MitreTactic.CREDENTIAL_ACCESS,
        risk_score=85,
        affected_hosts=["host1"],
        source_ips=["192.0.2.1"],
        event_count=5,
        first_seen="2026-09-28T10:00:00Z",
        last_seen="2026-09-28T10:05:00Z",
        summary="Test summary",
        remediation_guidance=["Step 1", "Step 2"],
    )
    d = inc.to_dict()
    assert d["risk_score"] == 85
    assert len(d["remediation_guidance"]) == 2
