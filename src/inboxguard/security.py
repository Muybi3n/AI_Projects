"""Security and Phishing Telemetry Scanner for Email Messages.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import re

from inboxguard.models import EmailMessage, SecurityAssessment, SecurityRiskLevel


class SecurityAuditor:
    """Audits email headers, sender reputation, display name spoofing, and phishing indicators."""

    BRAND_KEYWORDS = {
        "google": ["google.com", "accounts.google.com"],
        "microsoft": ["microsoft.com", "office365.com", "live.com"],
        "apple": ["apple.com", "icloud.com"],
        "paypal": ["paypal.com"],
        "chase": ["chase.com"],
        "amazon": ["amazon.com"],
        "netflix": ["netflix.com"],
        "bank of america": ["bankofamerica.com"],
        "wells fargo": ["wellsfargo.com"],
    }

    SUSPICIOUS_TLDS = [
        ".xyz",
        ".top",
        ".work",
        ".click",
        ".club",
        ".gq",
        ".cf",
        ".tk",
        ".ml",
        ".ga",
        ".buzz",
        ".icu",
        ".cam",
    ]

    URGENT_PHISHING_PHRASES = [
        "account will be terminated",
        "suspended within 24 hours",
        "immediate verification required",
        "verify your credentials",
        "confirm your identity immediately",
        "update your billing info immediately",
        "unauthorized transaction reported",
        "password expiration warning",
        "action required: security compromise",
    ]

    def audit(self, message: EmailMessage) -> SecurityAssessment:
        """Perform security audit on a single email message."""
        headers_lower = {k.lower(): v.lower() for k, v in message.headers.items()}
        sender_email = message.sender_email.lower()
        sender_name = message.sender_name.lower()
        subject_lower = message.subject.lower()
        body_lower = message.body.lower()

        reasons: list[str] = []
        urgency_triggers: list[str] = []
        suspicious_links: list[str] = []

        # 1. SPF / DKIM / DMARC verification
        spf_pass = True
        dkim_pass = True
        dmarc_pass = True

        auth_results = headers_lower.get("authentication-results", "")
        received_spf = headers_lower.get("received-spf", "")

        if auth_results:
            if "spf=fail" in auth_results or "spf=softfail" in auth_results:
                spf_pass = False
                reasons.append("SPF check failed or softfailed in Authentication-Results header")
            if "dkim=fail" in auth_results:
                dkim_pass = False
                reasons.append("DKIM cryptographic signature verification failed")
            if "dmarc=fail" in auth_results:
                dmarc_pass = False
                reasons.append("DMARC domain policy evaluation failed")
        elif received_spf and ("fail" in received_spf or "softfail" in received_spf):
            spf_pass = False
            reasons.append("SPF failed in Received-SPF header")

        # 2. Display Name Spoofing
        display_name_spoof = False
        for brand, legitimate_domains in self.BRAND_KEYWORDS.items():
            if brand in sender_name:
                # Check if sender email ends with any legitimate domain
                is_legit = any(
                    sender_email.endswith(f"@{dom}") or sender_email.endswith(f".{dom}") for dom in legitimate_domains
                )
                if not is_legit:
                    display_name_spoof = True
                    reasons.append(
                        f"Display name '{message.sender_name}' impersonates brand '{brand}' from untrusted domain '{sender_email}'"
                    )

        # 3. Punycode & Typosquatting
        punycode_domain = False
        if "xn--" in sender_email or "xn--" in message.body:
            punycode_domain = True
            reasons.append("Punycode (xn--) internationalized domain encoding detected (possible homoglyph attack)")

        # 4. Suspicious TLD on sender
        sender_domain = sender_email.split("@")[-1] if "@" in sender_email else ""
        if any(sender_domain.endswith(tld) for tld in self.SUSPICIOUS_TLDS):
            reasons.append(f"Sender domain '{sender_domain}' uses high-risk suspicious TLD")

        # 5. Phishing Urgency Triggers
        for phrase in self.URGENT_PHISHING_PHRASES:
            if phrase in subject_lower or phrase in body_lower:
                urgency_triggers.append(phrase)
                reasons.append(f"Contains high-urgency phishing trigger: '{phrase}'")

        # 6. Suspicious Link Scan
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', message.body)
        for url in urls:
            url_lower = url.lower()
            # IP address in URL
            if re.search(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", url_lower):
                suspicious_links.append(url)
                reasons.append(f"Raw IP address URL detected: {url}")
            # Suspicious TLD in link
            elif any(f"{tld}/" in url_lower or url_lower.endswith(tld) for tld in self.SUSPICIOUS_TLDS):
                suspicious_links.append(url)
                reasons.append(f"Link pointing to high-risk TLD: {url}")

        # 7. Calculate overall risk level
        risk_level = SecurityRiskLevel.SAFE
        if display_name_spoof and (not spf_pass or urgency_triggers or suspicious_links):
            risk_level = SecurityRiskLevel.PHISHING
        elif display_name_spoof or punycode_domain or len(suspicious_links) > 0:
            risk_level = SecurityRiskLevel.HIGH_RISK
        elif not spf_pass or not dkim_pass or not dmarc_pass or len(urgency_triggers) > 0:
            risk_level = SecurityRiskLevel.SUSPICIOUS

        assessment = SecurityAssessment(
            message_id=message.message_id or message.id,
            sender_email=message.sender_email,
            sender_name=message.sender_name,
            subject=message.subject,
            spf_pass=spf_pass,
            dkim_pass=dkim_pass,
            dmarc_pass=dmarc_pass,
            display_name_spoof=display_name_spoof,
            punycode_domain=punycode_domain,
            urgency_phishing_triggers=urgency_triggers,
            suspicious_links=suspicious_links,
            risk_level=risk_level,
            reasons=reasons,
        )

        message.security_risk = risk_level
        message.security_reasons = reasons
        return assessment

    def audit_batch(self, messages: list[EmailMessage]) -> list[SecurityAssessment]:
        """Audit a batch of messages."""
        return [self.audit(msg) for msg in messages]
