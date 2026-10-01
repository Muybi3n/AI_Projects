"""
Core data models for normalized telemetry, incidents, and threat assessments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventSource(str, Enum):
    WAZUH_HIDS = "wazuh_hids"
    PIHOLE_DNS = "pihole_dns"
    LINUX_AUTH = "linux_auth"
    CLOUDFLARE_ZERO_TRUST = "cloudflare_zt"
    CUSTOM_SYSLOG = "custom_syslog"


class SeverityLevel(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MitreTactic(str, Enum):
    INITIAL_ACCESS = "Initial Access (TA0001)"
    EXECUTION = "Execution (TA0002)"
    PERSISTENCE = "Persistence (TA0003)"
    PRIVILEGE_ESCALATION = "Privilege Escalation (TA0004)"
    DEFENSE_EVASION = "Defense Evasion (TA0005)"
    CREDENTIAL_ACCESS = "Credential Access (TA0006)"
    DISCOVERY = "Discovery (TA0007)"
    LATERAL_MOVEMENT = "Lateral Movement (TA0008)"
    COMMAND_AND_CONTROL = "Command and Control (TA0011)"
    EXFILTRATION = "Exfiltration (TA0010)"
    IMPACT = "Impact (TA0040)"
    UNKNOWN = "Unknown / Informational"


@dataclass
class SecurityEvent:
    event_id: str
    source: EventSource
    timestamp: str  # ISO-8601
    source_ip: str
    destination_ip: str
    severity: SeverityLevel
    action: str  # "BLOCKED", "ALLOWED", "FAILED_LOGIN", "SUDO_ESCALATION", etc.
    event_type: str
    details: str
    user: str = "root"
    domain: str | None = None
    rule_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "severity": self.severity.value,
            "action": self.action,
            "event_type": self.event_type,
            "details": self.details,
            "user": self.user,
            "domain": self.domain,
            "rule_id": self.rule_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SecurityEvent:
        return cls(
            event_id=data["event_id"],
            source=EventSource(data["source"]),
            timestamp=data["timestamp"],
            source_ip=data.get("source_ip", "127.0.0.1"),
            destination_ip=data.get("destination_ip", "127.0.0.1"),
            severity=SeverityLevel(data.get("severity", "INFORMATIONAL")),
            action=data.get("action", "UNKNOWN"),
            event_type=data.get("event_type", "generic"),
            details=data.get("details", ""),
            user=data.get("user", "root"),
            domain=data.get("domain"),
            rule_id=data.get("rule_id"),
            tags=data.get("tags", []),
        )


@dataclass
class CorrelatedIncident:
    incident_id: str
    title: str
    primary_tactic: MitreTactic
    risk_score: int  # 0 to 100
    affected_hosts: list[str]
    source_ips: list[str]
    event_count: int
    first_seen: str
    last_seen: str
    summary: str
    events: list[SecurityEvent] = field(default_factory=list)
    remediation_guidance: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "primary_tactic": self.primary_tactic.value,
            "risk_score": self.risk_score,
            "affected_hosts": self.affected_hosts,
            "source_ips": self.source_ips,
            "event_count": self.event_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "summary": self.summary,
            "remediation_guidance": self.remediation_guidance,
        }


@dataclass
class ThreatReport:
    generated_at: str
    total_raw_events: int
    normalized_events: int
    suppressed_noise_events: int
    correlated_incidents: int
    max_risk_score: int
    incidents: list[CorrelatedIncident] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_raw_events": self.total_raw_events,
            "normalized_events": self.normalized_events,
            "suppressed_noise_events": self.suppressed_noise_events,
            "correlated_incidents": self.correlated_incidents,
            "max_risk_score": self.max_risk_score,
            "incidents": [inc.to_dict() for inc in self.incidents],
        }
