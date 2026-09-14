"""Deterministic 5-Tier Email Classifier Engine.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

from inboxguard.models import EmailMessage, EmailTier, UnsubscribeMechanism


class EmailClassifier:
    """Classifies emails into 5 tiers using deterministic header, sender, and content analysis."""

    CRITICAL_KEYWORDS = [
        "critical",
        "security alert",
        "unauthorized access",
        "2fa code",
        "verification code",
        "password reset",
        "account suspended",
        "account compromised",
        "server outage",
        "database outage",
        "replication failed",
        "system failure",
        "p0 incident",
        "p1 outage",
        "immediate action required",
        "urgent: server",
        "fraud alert",
        "wire transfer confirmation",
        "critical vulnerability",
        "emergency notice",
        "court summons",
        "legal notice",
    ]

    FINANCIAL_TRAVEL_KEYWORDS = [
        "order confirmation",
        "your receipt",
        "invoice #",
        "invoice attached",
        "payment received",
        "payment receipt",
        "flight confirmation",
        "boarding pass",
        "e-ticket",
        "hotel reservation",
        "booking confirmation",
        "tracking number",
        "package delivered",
        "shipped with tracking",
        "bank statement",
        "tax document",
        "1099-",
        "w-2 form",
        "subscription billed",
        "auto-renewal confirmation",
    ]

    PROMO_SPAM_KEYWORDS = [
        "limited time offer",
        "exclusive discount",
        "% off your next",
        "flash sale",
        "special promo",
        "quick 15 min call",
        "quick 15-minute call",
        "are you the right person",
        "grow your pipeline",
        "schedule a demo",
        "free consultation call",
        "partner with us",
        "claim your prize",
        "act now before it's gone",
        "boost your revenue",
    ]

    GITHUB_ACTION_KEYWORDS = [
        "pull request #",
        "review requested",
        "assigned to you",
        "mentioned you on",
        "requested your review",
        "ci build failed",
        "action required on pr",
    ]

    def classify(self, message: EmailMessage) -> EmailMessage:
        """Analyze message metadata, headers, and body to assign an EmailTier with reasons."""
        subject_lower = message.subject.lower()
        body_lower = message.body.lower()
        sender_lower = message.sender_email.lower()
        headers_lower = {k.lower(): v.lower() for k, v in message.headers.items()}

        reasons: list[str] = []
        assigned_tier: EmailTier = EmailTier.TIER_2_ACTIONABLE

        # 1. Check for TIER_1_CRITICAL
        for kw in self.CRITICAL_KEYWORDS:
            if kw in subject_lower:
                assigned_tier = EmailTier.TIER_1_CRITICAL
                reasons.append(f"Subject contains critical keyword: '{kw}'")
                break

        if assigned_tier != EmailTier.TIER_1_CRITICAL:
            if any(
                prefix in sender_lower
                for prefix in ["security@", "noc@", "incident@", "fraud@", "alerts@", "alert@", "soc@", "dba@", "ops@"]
            ):
                if any(
                    kw in subject_lower or kw in body_lower
                    for kw in ["alert", "code", "warning", "reset", "fail", "incident", "down", "outage"]
                ):
                    assigned_tier = EmailTier.TIER_1_CRITICAL
                    reasons.append(f"High-priority security/infra sender '{sender_lower}' with alert content")

        if assigned_tier == EmailTier.TIER_1_CRITICAL:
            message.tier = assigned_tier
            message.tier_reasons = reasons
            return message

        # 2. Check for TIER_3_FINANCIAL_TRAVEL
        for kw in self.FINANCIAL_TRAVEL_KEYWORDS:
            if kw in subject_lower or (kw in body_lower and len(body_lower) < 3000):
                assigned_tier = EmailTier.TIER_3_FINANCIAL_TRAVEL
                reasons.append(f"Matched financial/travel keyword: '{kw}'")
                break

        if assigned_tier != EmailTier.TIER_3_FINANCIAL_TRAVEL:
            if any(
                prefix in sender_lower
                for prefix in ["billing@", "receipts@", "invoices@", "payments@", "orders@", "travel@"]
            ):
                assigned_tier = EmailTier.TIER_3_FINANCIAL_TRAVEL
                reasons.append(f"Financial/transactional sender address: '{sender_lower}'")

        if assigned_tier == EmailTier.TIER_3_FINANCIAL_TRAVEL:
            message.tier = assigned_tier
            message.tier_reasons = reasons
            return message

        # 3. Check for TIER_5_COLD_PROMO_SPAM
        for kw in self.PROMO_SPAM_KEYWORDS:
            if kw in subject_lower or kw in body_lower[:500]:
                assigned_tier = EmailTier.TIER_5_COLD_PROMO_SPAM
                reasons.append(f"Promotional/cold outreach pattern: '{kw}'")
                break

        if assigned_tier != EmailTier.TIER_5_COLD_PROMO_SPAM:
            # Check for excessive exclamation or uppercase in subject
            if message.subject.count("!") >= 3 or (
                len(message.subject) > 12 and message.subject.isupper() and "$" in message.subject
            ):
                assigned_tier = EmailTier.TIER_5_COLD_PROMO_SPAM
                reasons.append("Subject contains aggressive capitalization/exclamation marks")

        if assigned_tier == EmailTier.TIER_5_COLD_PROMO_SPAM:
            message.tier = assigned_tier
            message.tier_reasons = reasons
            return message

        # 4. Check for TIER_4_SUBSCRIPTIONS (Newsletters, Bulk lists)
        has_list_unsubscribe = (
            "list-unsubscribe" in headers_lower
            or message.unsubscribe_url != ""
            or message.unsubscribe_type != UnsubscribeMechanism.NONE
        )
        has_precedence_bulk = headers_lower.get("precedence") in ["bulk", "list"] or "list-id" in headers_lower
        has_sub_keywords = any(
            kw in body_lower
            for kw in [
                "unsubscribe",
                "manage your subscription",
                "email preferences",
                "view in browser",
                "newsletter",
            ]
        )

        if has_list_unsubscribe or has_precedence_bulk or (has_sub_keywords and "github" not in sender_lower):
            assigned_tier = EmailTier.TIER_4_SUBSCRIPTIONS
            if has_list_unsubscribe:
                reasons.append("Detected RFC List-Unsubscribe header or unsubscribe URL")
            if has_precedence_bulk:
                reasons.append("Header Precedence: bulk or List-Id detected")
            if has_sub_keywords:
                reasons.append("Contains standard newsletter footer keywords")

            message.tier = assigned_tier
            message.tier_reasons = reasons
            return message

        # 5. Default to TIER_2_ACTIONABLE (Human 1:1, PR reviews, Direct correspondence)
        assigned_tier = EmailTier.TIER_2_ACTIONABLE
        if any(kw in subject_lower for kw in self.GITHUB_ACTION_KEYWORDS) or "notifications@github.com" in sender_lower:
            reasons.append("Direct GitHub review, issue, or pull request assignment")
        elif "in-reply-to" in headers_lower or "references" in headers_lower:
            reasons.append("Active human conversation thread (In-Reply-To/References header)")
        else:
            reasons.append("Direct interpersonal or operational correspondence")

        message.tier = assigned_tier
        message.tier_reasons = reasons
        return message

    def classify_batch(self, messages: list[EmailMessage]) -> list[EmailMessage]:
        """Classify a list of messages in place."""
        return [self.classify(msg) for msg in messages]
