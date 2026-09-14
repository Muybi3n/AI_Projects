"""Unit tests for the security, spoofing, and phishing detector."""

from inboxguard.models import EmailMessage, SecurityRiskLevel
from inboxguard.security import SecurityAuditor


def test_detect_display_name_spoofing():
    auditor = SecurityAuditor()

    msg = EmailMessage(
        id="phish_01",
        message_id="mid_p1",
        thread_id="th_p1",
        subject="Action Required: Security compromise on Google Account",
        sender_name="Google Security Team",
        sender_email="admin@google-security-verify.xyz",
        recipient="victim@example.com",
        date="2026-09-14",
        body="Your account will be terminated within 24 hours. Click http://192.168.1.100/verify to update your billing info immediately.",
        headers={
            "Authentication-Results": "spf=fail (sender IP is 1.2.3.4) smtp.mailfrom=google-security-verify.xyz; dkim=fail; dmarc=fail"
        },
    )

    assessment = auditor.audit(msg)
    assert assessment.display_name_spoof is True
    assert assessment.spf_pass is False
    assert assessment.dkim_pass is False
    assert assessment.dmarc_pass is False
    assert assessment.risk_level == SecurityRiskLevel.PHISHING
    assert msg.security_risk == SecurityRiskLevel.PHISHING
    assert len(assessment.suspicious_links) > 0


def test_detect_punycode_and_suspicious_tld():
    auditor = SecurityAuditor()

    msg = EmailMessage(
        id="phish_02",
        message_id="mid_p2",
        thread_id="th_p2",
        subject="Immediate verification required for Paypal login",
        sender_name="PayPal Support",
        sender_email="support@xn--pypal-4ve.com",
        recipient="victim@example.com",
        date="2026-09-14",
        body="Verify your credentials now at http://malicious.top/login",
    )

    assessment = auditor.audit(msg)
    assert assessment.punycode_domain is True
    assert assessment.display_name_spoof is True
    assert assessment.risk_level in [SecurityRiskLevel.HIGH_RISK, SecurityRiskLevel.PHISHING]


def test_legitimate_email_audit():
    auditor = SecurityAuditor()

    msg = EmailMessage(
        id="legit_01",
        message_id="mid_l1",
        thread_id="th_l1",
        subject="Team Meeting Notes & Sprint Roadmap",
        sender_name="Alice Smith",
        sender_email="alice@company.com",
        recipient="bob@company.com",
        date="2026-09-14",
        body="Here is the link to the design doc: https://docs.google.com/document/d/123",
        headers={
            "Authentication-Results": "spf=pass smtp.mailfrom=company.com; dkim=pass header.d=company.com; dmarc=pass"
        },
    )

    assessment = auditor.audit(msg)
    assert assessment.spf_pass is True
    assert assessment.dkim_pass is True
    assert assessment.dmarc_pass is True
    assert assessment.display_name_spoof is False
    assert assessment.punycode_domain is False
    assert assessment.risk_level == SecurityRiskLevel.SAFE
    assert msg.security_risk == SecurityRiskLevel.SAFE
