"""Domain models, Enums, and Data structures for inboxguard-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EmailTier(str, Enum):
    """5-Tier Email Priority Classification."""

    TIER_1_CRITICAL = "TIER_1_CRITICAL"  # Urgent security alerts, direct executive/boss, system outages
    TIER_2_ACTIONABLE = "TIER_2_ACTIONABLE"  # 1:1 human correspondence, PR reviews, direct deliverables
    TIER_3_FINANCIAL_TRAVEL = "TIER_3_FINANCIAL_TRAVEL"  # Invoices, receipts, booking confirms, tracking
    TIER_4_SUBSCRIPTIONS = "TIER_4_SUBSCRIPTIONS"  # Newsletters, product digests, blogs, platform updates
    TIER_5_COLD_PROMO_SPAM = "TIER_5_COLD_PROMO_SPAM"  # Cold outreach SDRs, promotional ads, suspicious bulk


class SecurityRiskLevel(str, Enum):
    """Phishing and security threat risk tiers."""

    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"
    PHISHING = "PHISHING"


class UnsubscribeMechanism(str, Enum):
    """Standard unsubscribe mechanisms detected in headers/body."""

    ONE_CLICK = "ONE_CLICK"  # RFC 8058 List-Unsubscribe=One-Click
    HTTPS_LINK = "HTTPS_LINK"  # RFC 2369 URL
    MAILTO = "MAILTO"  # RFC 2369 mailto:
    MANUAL_BODY_LINK = "MANUAL_BODY_LINK"
    NONE = "NONE"


@dataclass
class EmailMessage:
    """Canonical representation of an ingested email message."""

    id: str
    message_id: str
    thread_id: str
    subject: str
    sender_name: str
    sender_email: str
    recipient: str
    date: str
    body: str
    headers: dict[str, str] = field(default_factory=dict)
    tier: EmailTier = EmailTier.TIER_2_ACTIONABLE
    tier_reasons: list[str] = field(default_factory=list)
    security_risk: SecurityRiskLevel = SecurityRiskLevel.SAFE
    security_reasons: list[str] = field(default_factory=list)
    unsubscribe_type: UnsubscribeMechanism = UnsubscribeMechanism.NONE
    unsubscribe_url: str = ""
    unsubscribe_mailto: str = ""
    is_read: bool = False
    is_starred: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tier"] = self.tier.value if isinstance(self.tier, Enum) else self.tier
        data["security_risk"] = self.security_risk.value if isinstance(self.security_risk, Enum) else self.security_risk
        data["unsubscribe_type"] = (
            self.unsubscribe_type.value if isinstance(self.unsubscribe_type, Enum) else self.unsubscribe_type
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailMessage:
        raw = dict(data)
        if "tier" in raw and isinstance(raw["tier"], str):
            raw["tier"] = EmailTier(raw["tier"])
        if "security_risk" in raw and isinstance(raw["security_risk"], str):
            raw["security_risk"] = SecurityRiskLevel(raw["security_risk"])
        if "unsubscribe_type" in raw and isinstance(raw["unsubscribe_type"], str):
            raw["unsubscribe_type"] = UnsubscribeMechanism(raw["unsubscribe_type"])
        return cls(**raw)


@dataclass
class SenderProfile:
    """Sender statistics and decay metrics for subscription hygiene."""

    sender_email: str
    sender_name: str
    total_count: int = 0
    unread_count: int = 0
    read_rate: float = 0.0
    dominant_tier: EmailTier = EmailTier.TIER_4_SUBSCRIPTIONS
    first_seen: str = ""
    last_seen: str = ""
    unsubscribe_url: str = ""
    unsubscribe_mailto: str = ""
    is_subscription: bool = False
    decay_score: float = 0.0  # 0.0 (active/healthy) to 1.0 (deadweight/abandoned)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["dominant_tier"] = self.dominant_tier.value if isinstance(self.dominant_tier, Enum) else self.dominant_tier
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SenderProfile:
        raw = dict(data)
        if "dominant_tier" in raw and isinstance(raw["dominant_tier"], str):
            raw["dominant_tier"] = EmailTier(raw["dominant_tier"])
        return cls(**raw)


@dataclass
class SecurityAssessment:
    """Detailed security and spoofing audit for an email message."""

    message_id: str
    sender_email: str
    sender_name: str
    subject: str
    spf_pass: bool = True
    dkim_pass: bool = True
    dmarc_pass: bool = True
    display_name_spoof: bool = False
    punycode_domain: bool = False
    urgency_phishing_triggers: list[str] = field(default_factory=list)
    suspicious_links: list[str] = field(default_factory=list)
    risk_level: SecurityRiskLevel = SecurityRiskLevel.SAFE
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk_level"] = self.risk_level.value if isinstance(self.risk_level, Enum) else self.risk_level
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SecurityAssessment:
        raw = dict(data)
        if "risk_level" in raw and isinstance(raw["risk_level"], str):
            raw["risk_level"] = SecurityRiskLevel(raw["risk_level"])
        return cls(**raw)


@dataclass
class FilterRule:
    """Exportable mailbox filter rule (Gmail XML, Sieve, etc.)."""

    name: str
    criteria_from: str = ""
    criteria_subject: str = ""
    criteria_has_words: str = ""
    action_apply_label: str = ""
    action_archive: bool = False
    action_star: bool = False
    action_mark_read: bool = False
    action_trash: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterRule:
        return cls(**data)


@dataclass
class TriageReport:
    """Consolidated triage summary across the mailbox."""

    total_emails: int
    tier_counts: dict[str, int]
    security_alerts_count: int
    subscription_count: int
    decayed_subscriptions: list[SenderProfile]
    critical_emails: list[EmailMessage]
    suggested_rules: list[FilterRule]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_emails": self.total_emails,
            "tier_counts": self.tier_counts,
            "security_alerts_count": self.security_alerts_count,
            "subscription_count": self.subscription_count,
            "decayed_subscriptions": [s.to_dict() for s in self.decayed_subscriptions],
            "critical_emails": [e.to_dict() for e in self.critical_emails],
            "suggested_rules": [r.to_dict() for r in self.suggested_rules],
        }
