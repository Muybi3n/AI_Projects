"""Unit tests for newsletter parsing and decay tracking."""

from inboxguard.models import EmailMessage, EmailTier, UnsubscribeMechanism
from inboxguard.newsletter import NewsletterCleaner


def test_parse_unsubscribe_headers():
    cleaner = NewsletterCleaner()

    # One-click RFC 8058
    hdr = "<https://newsletter.example.com/unsub?id=123>, <mailto:unsub@example.com?subject=unsub>"
    post = "List-Unsubscribe=One-Click"
    mech, url, mailto = cleaner.parse_unsubscribe_header(hdr, post)
    assert mech == UnsubscribeMechanism.ONE_CLICK
    assert url == "https://newsletter.example.com/unsub?id=123"
    assert mailto == "mailto:unsub@example.com?subject=unsub"

    # HTTPS URL only
    hdr2 = "<https://news.corp.com/unsubscribe>"
    mech2, url2, mailto2 = cleaner.parse_unsubscribe_header(hdr2)
    assert mech2 == UnsubscribeMechanism.HTTPS_LINK
    assert url2 == "https://news.corp.com/unsubscribe"
    assert mailto2 == ""

    # Mailto only
    hdr3 = "<mailto:leave@lists.org>"
    mech3, url3, mailto3 = cleaner.parse_unsubscribe_header(hdr3)
    assert mech3 == UnsubscribeMechanism.MAILTO
    assert mailto3 == "mailto:leave@lists.org"

    # Empty
    mech4, url4, mailto4 = cleaner.parse_unsubscribe_header("")
    assert mech4 == UnsubscribeMechanism.NONE


def test_analyze_senders_and_decay():
    cleaner = NewsletterCleaner()

    # Generate 10 emails from a newsletter sender that are all unread
    messages = [
        EmailMessage(
            id=f"msg_sub_{i}",
            message_id=f"mid_sub_{i}",
            thread_id=f"th_sub_{i}",
            subject=f"Daily AI Roundup #{i}",
            sender_name="Daily AI News",
            sender_email="digest@dailyai.com",
            recipient="user@example.com",
            date=f"2026-09-0{i + 1}",
            body="Daily AI roundup content. Unsubscribe here.",
            tier=EmailTier.TIER_4_SUBSCRIPTIONS,
            unsubscribe_url="https://dailyai.com/unsub",
            is_read=False,
        )
        for i in range(8)
    ]

    # Add 2 emails from an active colleague (100% read)
    messages.extend(
        [
            EmailMessage(
                id="msg_col_1",
                message_id="mid_col_1",
                thread_id="th_col_1",
                subject="Project roadmap update",
                sender_name="Colleague Bob",
                sender_email="bob@company.com",
                recipient="user@example.com",
                date="2026-09-10",
                body="Let's sync on the roadmap.",
                tier=EmailTier.TIER_2_ACTIONABLE,
                is_read=True,
            )
        ]
    )

    profiles = cleaner.analyze_senders(messages)
    assert len(profiles) == 2

    daily_ai_profile = next(p for p in profiles if p.sender_email == "digest@dailyai.com")
    assert daily_ai_profile.total_count == 8
    assert daily_ai_profile.unread_count == 8
    assert daily_ai_profile.decay_score >= 0.7
    assert daily_ai_profile.is_subscription is True

    decayed = cleaner.extract_decayed_subscriptions(profiles, threshold=0.5)
    assert len(decayed) == 1
    assert decayed[0].sender_email == "digest@dailyai.com"
