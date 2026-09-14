"""Pluggable AI Companion & Deterministic Heuristic Advisor for inboxguard-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from inboxguard.models import EmailTier, SecurityRiskLevel
from inboxguard.newsletter import NewsletterCleaner
from inboxguard.storage import StorageEngine


@dataclass
class CompanionResponse:
    """Structured response from the AI Companion."""

    query: str
    summary: str
    critical_alerts: list[str] = field(default_factory=list)
    subscription_recommendations: list[str] = field(default_factory=list)
    security_warnings: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    draft_reply: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_pii(text: str) -> str:
    """Sanitize credit cards, SSNs, and sensitive tokens from text."""
    # Mask credit card numbers (13-16 digits)
    text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CARD_NUMBER]", text)
    # Mask SSNs
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    # Mask API tokens / bearer tokens
    text = re.sub(r"\b(ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*)\b", "[REDACTED_JWT_TOKEN]", text)
    return text


def build_sanitized_context(storage: StorageEngine) -> dict[str, Any]:
    """Build a structured, PII-sanitized summary of mailbox state for AI reasoning."""
    tier_counts = storage.count_by_tier()
    all_emails = storage.list_emails(limit=200)

    cleaner = NewsletterCleaner()
    profiles = cleaner.analyze_senders(all_emails)
    decayed = cleaner.extract_decayed_subscriptions(profiles, threshold=0.4)

    critical_emails = storage.list_emails(tier=EmailTier.TIER_1_CRITICAL.value, limit=10)
    suspicious_emails = [
        e
        for e in all_emails
        if e.security_risk in [SecurityRiskLevel.SUSPICIOUS, SecurityRiskLevel.HIGH_RISK, SecurityRiskLevel.PHISHING]
    ]

    sanitized_critical = [
        {
            "id": e.id,
            "subject": sanitize_pii(e.subject),
            "sender_domain": e.sender_email.split("@")[-1] if "@" in e.sender_email else "unknown",
            "tier_reasons": e.tier_reasons,
        }
        for e in critical_emails
    ]

    sanitized_suspicious = [
        {
            "id": e.id,
            "subject": sanitize_pii(e.subject),
            "sender_email": e.sender_email,
            "risk_level": e.security_risk.value,
            "reasons": e.security_reasons,
        }
        for e in suspicious_emails
    ]

    decayed_summary = [
        {
            "sender": p.sender_email,
            "total": p.total_count,
            "unread": p.unread_count,
            "decay_score": p.decay_score,
            "unsubscribe_url": p.unsubscribe_url,
        }
        for p in decayed[:10]
    ]

    return {
        "tier_counts": tier_counts,
        "total_indexed": len(all_emails),
        "critical_count": len(critical_emails),
        "critical_emails": sanitized_critical,
        "suspicious_count": len(suspicious_emails),
        "suspicious_emails": sanitized_suspicious,
        "decayed_subscriptions": decayed_summary,
    }


class InboxCompanion:
    """Pluggable AI Companion providing deterministic heuristic advice and pluggable LLM support."""

    def __init__(
        self,
        storage: StorageEngine,
        custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None,
    ):
        self.storage = storage
        self.custom_llm_callable = custom_llm_callable

    def consult(self, query: str) -> CompanionResponse:
        """Process user query and return actionable triage recommendations."""
        context = build_sanitized_context(self.storage)

        if self.custom_llm_callable is not None:
            raw = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw)
                return CompanionResponse(
                    query=query,
                    summary=data.get("summary", ""),
                    critical_alerts=data.get("critical_alerts", []),
                    subscription_recommendations=data.get("subscription_recommendations", []),
                    security_warnings=data.get("security_warnings", []),
                    suggested_actions=data.get("suggested_actions", []),
                    draft_reply=data.get("draft_reply", ""),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return CompanionResponse(query=query, summary=raw)

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> CompanionResponse:
        q = query.lower()
        summary_lines: list[str] = []
        critical_alerts: list[str] = []
        sub_recs: list[str] = []
        sec_warnings: list[str] = []
        suggested_actions: list[str] = []
        draft_reply = ""

        # 1. Critical and Priority Inquiries
        if any(w in q for w in ["critical", "urgent", "priority", "tier 1", "tier_1", "p0"]):
            if context["critical_count"] > 0:
                summary_lines.append(
                    f"Found {context['critical_count']} critical priority message(s) requiring immediate review."
                )
                for msg in context["critical_emails"]:
                    critical_alerts.append(f"[{msg['id']}] {msg['subject']} (from {msg['sender_domain']})")
                suggested_actions.append(
                    "Review and resolve Tier 1 security alerts / 2FA resets before processing normal inbox."
                )
            else:
                summary_lines.append("No critical Tier 1 alerts detected. Inbox is clear of urgent security incidents.")

        # 2. Subscription and Newsletter Inquiries
        if any(w in q for w in ["newsletter", "subscription", "unsubscribe", "decay", "clean", "spam", "promo"]):
            decayed = context["decayed_subscriptions"]
            if decayed:
                summary_lines.append(
                    f"Identified {len(decayed)} decayed newsletter subscription(s) with high unread rates."
                )
                for sub in decayed:
                    sub_recs.append(
                        f"{sub['sender']}: {sub['unread']}/{sub['total']} unread (decay {sub['decay_score']})"
                    )
                suggested_actions.append("Execute batch unsubscribe on top decayed senders to reduce inbox noise.")
            else:
                summary_lines.append(
                    "No decayed subscriptions detected. All newsletter senders show healthy engagement."
                )

        # 3. Phishing and Security Inquiries
        if any(w in q for w in ["phish", "security", "threat", "spoof", "risk", "fake"]):
            suspicious = context["suspicious_emails"]
            if suspicious:
                summary_lines.append(f"Detected {len(suspicious)} suspicious or spoofed email(s).")
                for s in suspicious:
                    sec_warnings.append(
                        f"[{s['risk_level']}] {s['sender_email']} - {s['subject']}: {'; '.join(s['reasons'])}"
                    )
                suggested_actions.append(
                    "Quarantine or discard flagged spoofing attempts immediately. Do not click links."
                )
            else:
                summary_lines.append(
                    "All message signatures (SPF/DKIM) verified. Zero high-risk phishing attempts found."
                )

        # 4. Draft Reply Inquiries
        if any(w in q for w in ["draft", "reply", "respond", "answer"]):
            actionable = self.storage.list_emails(tier=EmailTier.TIER_2_ACTIONABLE.value, limit=1)
            if actionable:
                target = actionable[0]
                draft_reply = (
                    f"Hi {target.sender_name or 'there'},\n\n"
                    f"Thank you for your note regarding '{target.subject}'. "
                    "I am currently reviewing the details and will follow up shortly with a comprehensive update.\n\n"
                    "Best regards,\n[Your Name]"
                )
                summary_lines.append(
                    f"Synthesized standard professional reply draft for latest actionable email ({target.subject})."
                )
                suggested_actions.append(f"Review and send reply draft to {target.sender_email}.")
            else:
                summary_lines.append("No pending Tier 2 actionable messages found to draft replies for.")

        # 5. Filter Rules Inquiries
        if any(w in q for w in ["rule", "filter", "gmail", "sieve", "export"]):
            summary_lines.append(
                "Filter rules can be generated automatically to route receipts, newsletters, and promo blasts."
            )
            suggested_actions.append(
                "Run `inboxguard rules --format gmail` to export ready-to-import filters.xml for Google Workspace."
            )

        # 6. Fallback / General Overview
        if not summary_lines:
            tc = context["tier_counts"]
            summary_lines.append(
                f"Inbox Status: {context['total_indexed']} emails indexed. "
                f"T1 Critical: {tc.get(EmailTier.TIER_1_CRITICAL.value, 0)} | "
                f"T2 Actionable: {tc.get(EmailTier.TIER_2_ACTIONABLE.value, 0)} | "
                f"T3 Finance: {tc.get(EmailTier.TIER_3_FINANCIAL_TRAVEL.value, 0)} | "
                f"T4 Subs: {tc.get(EmailTier.TIER_4_SUBSCRIPTIONS.value, 0)} | "
                f"T5 Promo: {tc.get(EmailTier.TIER_5_COLD_PROMO_SPAM.value, 0)}."
            )
            suggested_actions.append(
                "Run `inboxguard triage` for full breakdown or `inboxguard newsletters` for subscription purge."
            )

        return CompanionResponse(
            query=query,
            summary="\n".join(summary_lines),
            critical_alerts=critical_alerts,
            subscription_recommendations=sub_recs,
            security_warnings=sec_warnings,
            suggested_actions=suggested_actions,
            draft_reply=draft_reply,
        )
