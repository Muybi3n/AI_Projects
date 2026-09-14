"""Unit tests for the AI Companion and heuristic advisor."""

import json

from inboxguard.ai_companion import InboxCompanion, sanitize_pii
from inboxguard.models import EmailMessage, EmailTier, SecurityRiskLevel
from inboxguard.storage import StorageEngine


def test_sanitize_pii():
    text = "User credit card is 4532-1234-5678-9012 and SSN is 123-45-6789."
    sanitized = sanitize_pii(text)
    assert "[REDACTED_CARD_NUMBER]" in sanitized
    assert "[REDACTED_SSN]" in sanitized
    assert "4532-1234-5678-9012" not in sanitized
    assert "123-45-6789" not in sanitized


def test_companion_heuristic_queries(tmp_path):
    db_path = tmp_path / "test_inbox.db"
    storage = StorageEngine(db_path=db_path)

    # Ingest mock messages
    storage.save_email(
        EmailMessage(
            id="msg_c1",
            message_id="mid_c1",
            thread_id="th_c1",
            subject="CRITICAL: 2FA verification code 998877",
            sender_name="Security Bot",
            sender_email="security@corp.local",
            recipient="me@corp.local",
            date="2026-09-14",
            body="Your verification code is 998877.",
            tier=EmailTier.TIER_1_CRITICAL,
        )
    )

    storage.save_email(
        EmailMessage(
            id="msg_a1",
            message_id="mid_a1",
            thread_id="th_a1",
            subject="Sprint planning agenda",
            sender_name="Alice Product",
            sender_email="alice@company.com",
            recipient="me@company.com",
            date="2026-09-14",
            body="Hey, can you review the sprint backlog before our 2pm call?",
            tier=EmailTier.TIER_2_ACTIONABLE,
            is_read=False,
        )
    )

    storage.save_email(
        EmailMessage(
            id="msg_p1",
            message_id="mid_p1",
            thread_id="th_p1",
            subject="Immediate verification needed",
            sender_name="Bank Spoof",
            sender_email="admin@bank-phish.xyz",
            recipient="me@company.com",
            date="2026-09-14",
            body="Click here to verify.",
            security_risk=SecurityRiskLevel.PHISHING,
            security_reasons=["Untrusted TLD and display name spoof"],
        )
    )

    companion = InboxCompanion(storage)

    # 1. Critical question
    resp_crit = companion.consult("What are my critical priority alerts?")
    assert len(resp_crit.critical_alerts) >= 1
    assert "CRITICAL" in resp_crit.critical_alerts[0]

    # 2. Phishing question
    resp_sec = companion.consult("Are there any phishing threats in my inbox?")
    assert len(resp_sec.security_warnings) >= 1
    assert "PHISHING" in resp_sec.security_warnings[0]

    # 3. Draft reply
    resp_draft = companion.consult("Draft a reply to Alice")
    assert "Alice" in resp_draft.draft_reply
    assert "Sprint planning agenda" in resp_draft.draft_reply

    # 4. Fallback status
    resp_status = companion.consult("What is the general inbox status?")
    assert "Inbox Status:" in resp_status.summary


def test_companion_custom_llm(tmp_path):
    db_path = tmp_path / "test_inbox.db"
    storage = StorageEngine(db_path=db_path)

    def mock_llm_callable(query: str, context: dict) -> str:
        return json.dumps(
            {
                "summary": f"Custom LLM answered: {query}",
                "critical_alerts": ["Custom Alert 1"],
                "suggested_actions": ["Action 1"],
            }
        )

    companion = InboxCompanion(storage, custom_llm_callable=mock_llm_callable)
    resp = companion.consult("How is my day looking?")
    assert "Custom LLM answered: How is my day looking?" in resp.summary
    assert resp.critical_alerts == ["Custom Alert 1"]
