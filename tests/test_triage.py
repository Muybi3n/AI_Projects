from socmesh.models import EventSource, SecurityEvent, SeverityLevel
from socmesh.triage import AlertTriageGovernor


def test_triage_noise_filtering():
    triage = AlertTriageGovernor()
    ntp_event = SecurityEvent(
        event_id="e1",
        source=EventSource.PIHOLE_DNS,
        timestamp="2026-09-28T10:00:00Z",
        source_ip="10.0.0.2",
        destination_ip="127.0.0.1",
        severity=SeverityLevel.INFORMATIONAL,
        action="DNS_QUERY",
        event_type="dns_query",
        details="query ntp",
        domain="pool.ntp.org",
    )
    bad_event = SecurityEvent(
        event_id="e2",
        source=EventSource.PIHOLE_DNS,
        timestamp="2026-09-28T10:00:00Z",
        source_ip="10.0.0.2",
        destination_ip="0.0.0.0",
        severity=SeverityLevel.HIGH,
        action="GRAVITY_BLOCKED",
        event_type="dns_sinkhole",
        details="query malware",
        domain="evil-c2.example.com",
    )
    actionable, noise = triage.filter_noise([ntp_event, bad_event])
    assert len(actionable) == 1
    assert len(noise) == 1
    assert actionable[0].event_id == "e2"
