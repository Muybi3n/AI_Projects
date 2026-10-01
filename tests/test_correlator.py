from socmesh.correlator import ThreatCorrelationEngine
from socmesh.models import EventSource, MitreTactic, SecurityEvent, SeverityLevel


def test_brute_force_correlation():
    engine = ThreatCorrelationEngine()
    events = [
        SecurityEvent(
            event_id=f"auth-{i}",
            source=EventSource.LINUX_AUTH,
            timestamp="2026-09-28T10:00:00Z",
            source_ip="192.0.2.88",
            destination_ip="10.0.0.1",
            severity=SeverityLevel.MEDIUM,
            action="FAILED_AUTH",
            event_type="ssh_login_failure",
            details="Failed password",
        )
        for i in range(4)
    ]
    incidents = engine.correlate(events)
    assert len(incidents) == 1
    assert incidents[0].primary_tactic == MitreTactic.CREDENTIAL_ACCESS
    assert incidents[0].risk_score >= 70


def test_sinkhole_beaconing_correlation():
    engine = ThreatCorrelationEngine()
    events = [
        SecurityEvent(
            event_id="c2-1",
            source=EventSource.PIHOLE_DNS,
            timestamp="2026-09-28T10:00:00Z",
            source_ip="10.0.0.55",
            destination_ip="0.0.0.0",
            severity=SeverityLevel.HIGH,
            action="GRAVITY_BLOCKED",
            event_type="dns_sinkhole",
            details="Blocked c2 domain",
            domain="malware-c2.example.com",
        )
    ]
    incidents = engine.correlate(events)
    assert len(incidents) == 1
    assert incidents[0].primary_tactic == MitreTactic.COMMAND_AND_CONTROL


def test_wazuh_correlation():
    engine = ThreatCorrelationEngine()
    events = [
        SecurityEvent(
            event_id="w-1",
            source=EventSource.WAZUH_HIDS,
            timestamp="2026-09-28T10:00:00Z",
            source_ip="198.51.100.99",
            destination_ip="10.0.0.1",
            severity=SeverityLevel.CRITICAL,
            action="ALERT",
            event_type="rootcheck",
            details="Rootkit anomaly detected in /bin/ls",
        )
    ]
    incidents = engine.correlate(events)
    assert len(incidents) == 1
    assert incidents[0].primary_tactic == MitreTactic.DEFENSE_EVASION
    assert incidents[0].risk_score >= 75
