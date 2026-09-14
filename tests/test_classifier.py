"""Unit tests for the 5-tier classification engine."""

from inboxguard.classifier import EmailClassifier
from inboxguard.models import EmailMessage, EmailTier


def test_classify_tier_1_critical():
    classifier = EmailClassifier()

    msg = EmailMessage(
        id="c1",
        message_id="m1",
        thread_id="t1",
        subject="URGENT: 2FA Verification Code for your account",
        sender_name="Auth Service",
        sender_email="auth@company.com",
        recipient="user@example.com",
        date="2026-09-14",
        body="Your code is 123456.",
    )
    classified = classifier.classify(msg)
    assert classified.tier == EmailTier.TIER_1_CRITICAL
    assert len(classified.tier_reasons) > 0

    # Test server outage
    msg2 = EmailMessage(
        id="c2",
        message_id="m2",
        thread_id="t2",
        subject="P0 Incident: database server outage",
        sender_name="PagerDuty",
        sender_email="alerts@pagerduty.com",
        recipient="user@example.com",
        date="2026-09-14",
        body="High severity incident open.",
    )
    classified2 = classifier.classify(msg2)
    assert classified2.tier == EmailTier.TIER_1_CRITICAL


def test_classify_tier_3_financial_travel():
    classifier = EmailClassifier()

    msg = EmailMessage(
        id="f1",
        message_id="m3",
        thread_id="t3",
        subject="Your Receipt from Airline - Flight Confirmation #NY742",
        sender_name="Delta Airlines",
        sender_email="travel@delta.com",
        recipient="user@example.com",
        date="2026-09-14",
        body="Thank you for booking with us. Your e-ticket is confirmed.",
    )
    classified = classifier.classify(msg)
    assert classified.tier == EmailTier.TIER_3_FINANCIAL_TRAVEL

    # Billing sender address
    msg2 = EmailMessage(
        id="f2",
        message_id="m4",
        thread_id="t4",
        subject="Monthly Cloud Hosting Statement",
        sender_name="Hetzner Billing",
        sender_email="billing@hetzner.com",
        recipient="user@example.com",
        date="2026-09-14",
        body="Attached is your monthly invoice.",
    )
    assert classifier.classify(msg2).tier == EmailTier.TIER_3_FINANCIAL_TRAVEL


def test_classify_tier_4_subscriptions():
    classifier = EmailClassifier()

    msg = EmailMessage(
        id="s1",
        message_id="m5",
        thread_id="t5",
        subject="Weekly Engineering Digest #42",
        sender_name="Tech Weekly",
        sender_email="news@techweekly.org",
        recipient="user@example.com",
        date="2026-09-14",
        body="Here are the top stories. To unsubscribe, click here.",
        headers={"List-Unsubscribe": "<https://techweekly.org/unsub>"},
        unsubscribe_url="https://techweekly.org/unsub",
    )
    classified = classifier.classify(msg)
    assert classified.tier == EmailTier.TIER_4_SUBSCRIPTIONS


def test_classify_tier_5_cold_promo_spam():
    classifier = EmailClassifier()

    msg = EmailMessage(
        id="p1",
        message_id="m6",
        thread_id="t6",
        subject="Quick 15 min call to boost your sales pipeline???",
        sender_name="SDR Hunter",
        sender_email="sales@leadgenpro.xyz",
        recipient="user@example.com",
        date="2026-09-14",
        body="Are you the right person to speak to about your sales funnel? Exclusive discount code inside!",
    )
    classified = classifier.classify(msg)
    assert classified.tier == EmailTier.TIER_5_COLD_PROMO_SPAM

    # ALL CAPS subject with dollar sign
    msg2 = EmailMessage(
        id="p2",
        message_id="m7",
        thread_id="t7",
        subject="EXCLUSIVE $500 DISCOUNT VOUCHER AVAILABLE NOW",
        sender_name="Deals Bot",
        sender_email="deals@offers.net",
        recipient="user@example.com",
        date="2026-09-14",
        body="Claim your bonus.",
    )
    assert classifier.classify(msg2).tier == EmailTier.TIER_5_COLD_PROMO_SPAM


def test_classify_tier_2_actionable():
    classifier = EmailClassifier()

    msg = EmailMessage(
        id="a1",
        message_id="m8",
        thread_id="t8",
        subject="Pull Request #45 review requested: Add authentication layer",
        sender_name="GitHub",
        sender_email="notifications@github.com",
        recipient="user@example.com",
        date="2026-09-14",
        body="Alice requested your review on PR #45.",
    )
    classified = classifier.classify(msg)
    assert classified.tier == EmailTier.TIER_2_ACTIONABLE

    # 1:1 human thread
    msg2 = EmailMessage(
        id="a2",
        message_id="m9",
        thread_id="t9",
        subject="Architecture sync follow-up",
        sender_name="Sarah Colleague",
        sender_email="sarah@company.com",
        recipient="user@example.com",
        date="2026-09-14",
        body="Hey, let's sync on the roadmap tomorrow morning.",
        headers={"In-Reply-To": "<prev_msg_id>"},
    )
    assert classifier.classify(msg2).tier == EmailTier.TIER_2_ACTIONABLE


def test_classify_batch():
    classifier = EmailClassifier()
    msgs = [
        EmailMessage(
            id=f"m_{i}",
            message_id=f"mid_{i}",
            thread_id=f"th_{i}",
            subject=f"Subject {i}",
            sender_name="Sender",
            sender_email="user@test.com",
            recipient="me@test.com",
            date="2026-09-14",
            body="Body content",
        )
        for i in range(5)
    ]
    batch_result = classifier.classify_batch(msgs)
    assert len(batch_result) == 5
