"""Data models and enums for PromptGuard Proxy.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RiskTier(str, Enum):
    """Categorized threat risk tier."""

    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionVerdict(str, Enum):
    """Final routing decision for the inspected request."""

    ALLOW = "ALLOW"
    SANITIZE_AND_FORWARD = "SANITIZE_AND_FORWARD"
    BLOCK = "BLOCK"


@dataclass
class PIIMatch:
    """Detected Personally Identifiable Information token."""

    entity_type: str
    original_value: str
    redacted_token: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InjectionThreat:
    """Detected adversarial prompt injection pattern."""

    category: str
    matched_pattern: str
    confidence: float
    description: str
    mitre_technique: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PromptScanResult:
    """Combined security analysis result for prompt content."""

    original_text: str
    sanitized_text: str
    verdict: ActionVerdict
    risk_tier: RiskTier
    risk_score: int  # 0 to 100
    pii_matches: list[PIIMatch] = field(default_factory=list)
    threats: list[InjectionThreat] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "sanitized_text": self.sanitized_text,
            "verdict": self.verdict.value,
            "risk_tier": self.risk_tier.value,
            "risk_score": self.risk_score,
            "pii_matches": [m.to_dict() for m in self.pii_matches],
            "threats": [t.to_dict() for t in self.threats],
            "reasons": self.reasons,
        }


@dataclass
class AuditLogEntry:
    """Persistent audit trail entry for audited transactions."""

    request_id: str
    timestamp: str
    client_ip: str
    upstream_url: str
    verdict: ActionVerdict
    risk_tier: RiskTier
    risk_score: int
    pii_count: int
    threat_count: int
    reasons: list[str] = field(default_factory=list)
    sanitized_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "client_ip": self.client_ip,
            "upstream_url": self.upstream_url,
            "verdict": self.verdict.value,
            "risk_tier": self.risk_tier.value,
            "risk_score": self.risk_score,
            "pii_count": self.pii_count,
            "threat_count": self.threat_count,
            "reasons": self.reasons,
            "sanitized_preview": self.sanitized_preview,
        }


@dataclass
class ProxyConfig:
    """Configuration options for PromptGuard reverse-proxy server."""

    listen_host: str = "127.0.0.1"
    listen_port: int = 8088
    upstream_url: str = "http://127.0.0.1:11434"
    block_threshold: int = 70
    enable_pii_redaction: bool = True
    enable_injection_shield: bool = True
    mask_reversibility: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
