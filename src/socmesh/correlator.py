"""
Correlation and Blast-Radius Engine: MITRE ATT&CK mapping, beaconing detection, and risk scoring.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence

from .models import CorrelatedIncident, EventSource, MitreTactic, SecurityEvent, SeverityLevel


class ThreatCorrelationEngine:
    """Correlates multiple security events across Pi-hole, Wazuh, and Auth logs into unified incidents."""

    def __init__(self) -> None:
        pass

    def correlate(self, events: Sequence[SecurityEvent]) -> list[CorrelatedIncident]:
        """Correlates events into scored incidents."""
        incidents: list[CorrelatedIncident] = []

        # Group by Source IP
        ip_clusters: dict[str, list[SecurityEvent]] = defaultdict(list)
        for ev in events:
            ip_clusters[ev.source_ip].append(ev)

        for ip, cluster in ip_clusters.items():
            # Check 1: DNS Beaconing / Sinkhole Correlation
            sinkhole_events = [e for e in cluster if e.action == "GRAVITY_BLOCKED"]
            failed_auths = [e for e in cluster if e.action == "FAILED_AUTH"]
            critical_wazuh = [
                e
                for e in cluster
                if e.source == EventSource.WAZUH_HIDS
                and e.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)
            ]

            # Incident: Brute Force SSH Attack
            if len(failed_auths) >= 3:
                risk = min(100, 40 + len(failed_auths) * 10)
                inc_id = f"INC-AUTH-{hashlib.blake2b(ip.encode(), digest_size=6).hexdigest()}"
                incidents.append(
                    CorrelatedIncident(
                        incident_id=inc_id,
                        title=f"Brute Force Authentication Surge from {ip}",
                        primary_tactic=MitreTactic.CREDENTIAL_ACCESS,
                        risk_score=risk,
                        affected_hosts=["ubuntu-homelab"],
                        source_ips=[ip],
                        event_count=len(failed_auths),
                        first_seen=failed_auths[0].timestamp,
                        last_seen=failed_auths[-1].timestamp,
                        summary=f"Detected {len(failed_auths)} consecutive authentication failures targeting users from IP {ip}.",
                        events=failed_auths,
                        remediation_guidance=[
                            f"Block IP {ip} at firewall / UFW layer.",
                            "Enforce SSH key-only authentication (`PasswordAuthentication no`).",
                            "Verify Fail2ban / Wazuh active-response daemon status.",
                        ],
                    )
                )

            # Incident: Suspicious DNS Sinkhole / C2 Activity
            if sinkhole_events:
                domains = list({e.domain for e in sinkhole_events if e.domain})
                risk = min(100, 60 + len(sinkhole_events) * 8)
                inc_id = f"INC-C2-{hashlib.blake2b(ip.encode(), digest_size=6).hexdigest()}"
                incidents.append(
                    CorrelatedIncident(
                        incident_id=inc_id,
                        title=f"Sinkholed Threat Traffic / C2 Beaconing from {ip}",
                        primary_tactic=MitreTactic.COMMAND_AND_CONTROL,
                        risk_score=risk,
                        affected_hosts=[ip],
                        source_ips=[ip],
                        event_count=len(sinkhole_events),
                        first_seen=sinkhole_events[0].timestamp,
                        last_seen=sinkhole_events[-1].timestamp,
                        summary=f"Host {ip} attempted repeated DNS resolutions for blocked malicious domains: {', '.join(domains[:3])}.",
                        events=sinkhole_events,
                        remediation_guidance=[
                            f"Isolate host {ip} from local subnet.",
                            "Inspect active process tree and crontabs on affected endpoint.",
                            "Extract endpoint network socket connections via `ss -tulpn` or `netstat`.",
                        ],
                    )
                )

            # Incident: High-Severity Wazuh Detection
            if critical_wazuh:
                risk = max(75, min(100, len(critical_wazuh) * 20))
                inc_id = f"INC-WAZUH-{hashlib.blake2b(ip.encode(), digest_size=6).hexdigest()}"
                incidents.append(
                    CorrelatedIncident(
                        incident_id=inc_id,
                        title=f"Wazuh High-Severity HIDS Detection on {ip}",
                        primary_tactic=MitreTactic.DEFENSE_EVASION,
                        risk_score=risk,
                        affected_hosts=["homelab-cluster"],
                        source_ips=[ip],
                        event_count=len(critical_wazuh),
                        first_seen=critical_wazuh[0].timestamp,
                        last_seen=critical_wazuh[-1].timestamp,
                        summary=f"Wazuh HIDS generated {len(critical_wazuh)} high-priority alerts: {critical_wazuh[0].details}",
                        events=critical_wazuh,
                        remediation_guidance=[
                            "Review Wazuh agent telemetry logs in `/var/ossec/logs/alerts/alerts.json`.",
                            "Audit system binaries with `debsums -c` or `tripwire` for tampering.",
                        ],
                    )
                )

        # Sort incidents by risk score descending
        incidents.sort(key=lambda x: x.risk_score, reverse=True)
        return incidents
