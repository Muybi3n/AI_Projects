"""Unit tests for inboxguard domain models and serialization."""

from inboxguard.models import (
    EmailMessage,
    EmailTier,
    FilterRule,
    SecurityAssessment,
    SecurityRiskLevel,
    SenderProfile,
    TriageReport,
    UnsubscribeMechanism,
)


def test_email_message_serialization():
    msg = EmailMessage(
        id="msg_001",
        message_id="mid_123",
        thread_id="th_123",
        subject="Important Server Alert",
        sender_name="NOC Alerts",
        sender_email="noc@infra.local",
        recipient="admin@company.com",
        date="2026-09-14T09:00:00Z",
        body="Server node 4 is experiencing high load.",
        tier=EmailTier.TIER_1_CRITICAL,
        tier_reasons=["Server outage trigger"],
        security_risk=SecurityRiskLevel.SAFE,
        unsubscribe_type=UnsubscribeMechanism.NONE,
        is_read=False,
        is_starred=True,
    )

    data = msg.to_dict()
    assert data["id"] == "msg_001"
    assert data["tier"] == "TIER_1_CRITICAL"
    assert data["security_risk"] == "SAFE"
    assert data["unsubscribe_type"] == "NONE"

    restored = EmailMessage.from_dict(data)
    assert restored.id == msg.id
    assert restored.tier == EmailTier.TIER_1_CRITICAL
    assert restored.security_risk == SecurityRiskLevel.SAFE
    assert restored.is_starred is True


def test_sender_profile_serialization():
    profile = SenderProfile(
        sender_email="newsletter@techdaily.io",
        sender_name="Tech Daily",
        total_count=15,
        unread_count=12,
        read_rate=0.2,
        dominant_tier=EmailTier.TIER_4_SUBSCRIPTIONS,
        first_seen="2026-08-01",
        last_seen="2026-09-14",
        unsubscribe_url="https://techdaily.io/unsub",
        is_subscription=True,
        decay_score=0.74,
    )

    data = profile.to_dict()
    assert data["sender_email"] == "newsletter@techdaily.io"
    assert data["dominant_tier"] == "TIER_4_SUBSCRIPTIONS"
    assert data["decay_score"] == 0.74

    restored = SenderProfile.from_dict(data)
    assert restored.sender_name == "Tech Daily"
    assert restored.dominant_tier == EmailTier.TIER_4_SUBSCRIPTIONS


def test_security_assessment_and_filter_rule():
    sec = SecurityAssessment(
        message_id="sec_01",
        sender_email="fake@phish-login.xyz",
        sender_name="Security Team",
        subject="Update your password immediately",
        spf_pass=False,
        dkim_pass=False,
        dmarc_pass=False,
        display_name_spoof=True,
        risk_level=SecurityRiskLevel.PHISHING,
        reasons=["Spoofed display name", "SPF/DKIM fail"],
    )
    s_dict = sec.to_dict()
    assert s_dict["risk_level"] == "PHISHING"
    restored_sec = SecurityAssessment.from_dict(s_dict)
    assert restored_sec.risk_level == SecurityRiskLevel.PHISHING

    rule = FilterRule(
        name="Auto-Archive Newsletters",
        criteria_from="marketing@corp.com",
        action_apply_label="Marketing",
        action_archive=True,
    )
    r_dict = rule.to_dict()
    assert r_dict["name"] == "Auto-Archive Newsletters"
    restored_rule = FilterRule.from_dict(r_dict)
    assert restored_rule.action_archive is True


def test_triage_report():
    report = TriageReport(
        total_emails=10,
        tier_counts={"TIER_1_CRITICAL": 1, "TIER_2_ACTIONABLE": 9},
        security_alerts_count=0,
        subscription_count=2,
        decayed_subscriptions=[],
        critical_emails=[],
        suggested_rules=[],
    )
    d = report.to_dict()
    assert d["total_emails"] == 10
    assert d["tier_counts"]["TIER_1_CRITICAL"] == 1
