# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh models: Decoy files, integrity baselines, tripwire alerts, and audit events."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DecoyCategory(str, Enum):
    AWS_CREDENTIALS = "aws_credentials"
    SSH_KEY = "ssh_key"
    ENV_SECRETS = "env_secrets"
    DATABASE_CONFIG = "database_config"
    API_TOKEN = "api_token"
    SENSITIVE_DOCUMENT = "sensitive_document"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TripwireTriggerType(str, Enum):
    TAMPERED = "tampered"
    ACCESSED_ATIME = "accessed_atime"
    DELETED = "deleted"
    MISSING = "missing"
    PERMISSION_CHANGED = "permission_changed"
    TOKEN_PING = "token_ping"


@dataclass
class DecoyArtifact:
    token_id: str
    name: str
    category: DecoyCategory
    file_path: str
    expected_sha256: str
    expected_blake2b: str
    file_size_bytes: int
    created_at: str
    last_checked_at: str
    canary_identifier: str
    description: str = ""
    mitre_technique: str = "T1078 - Valid Accounts"
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecoyArtifact:
        data_copy = dict(data)
        if "category" in data_copy and isinstance(data_copy["category"], str):
            data_copy["category"] = DecoyCategory(data_copy["category"])
        return cls(**data_copy)


@dataclass
class TripwireAlert:
    alert_id: str
    token_id: str
    file_path: str
    trigger_type: TripwireTriggerType
    severity: AlertSeverity
    detected_at: str
    mitre_technique: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["trigger_type"] = self.trigger_type.value
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TripwireAlert:
        data_copy = dict(data)
        if "trigger_type" in data_copy and isinstance(data_copy["trigger_type"], str):
            data_copy["trigger_type"] = TripwireTriggerType(data_copy["trigger_type"])
        if "severity" in data_copy and isinstance(data_copy["severity"], str):
            data_copy["severity"] = AlertSeverity(data_copy["severity"])
        return cls(**data_copy)


@dataclass
class DecoyAuditSummary:
    timestamp: str
    total_decoys: int
    active_decoys: int
    intact_decoys: int
    tampered_decoys: int
    missing_decoys: int
    alerts_generated: int
    overall_health: str
    alerts: list[TripwireAlert] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_decoys": self.total_decoys,
            "active_decoys": self.active_decoys,
            "intact_decoys": self.intact_decoys,
            "tampered_decoys": self.tampered_decoys,
            "missing_decoys": self.missing_decoys,
            "alerts_generated": self.alerts_generated,
            "overall_health": self.overall_health,
            "alerts": [alert.to_dict() for alert in self.alerts],
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
