"""Unit tests for SQLite storage, FTS5 search, and multi-format parsers."""

import json
import mailbox

from inboxguard.models import EmailMessage, EmailTier, FilterRule
from inboxguard.storage import StorageEngine


def test_sqlite_crud_and_fts(tmp_path):
    db_file = tmp_path / "inbox.db"
    storage = StorageEngine(db_path=db_file)

    msg1 = EmailMessage(
        id="msg_001",
        message_id="m1",
        thread_id="t1",
        subject="Quarterly Security Compliance Review",
        sender_name="Infosec Director",
        sender_email="infosec@acme.org",
        recipient="user@acme.org",
        date="2026-09-14",
        body="Please complete the SOC2 access control survey by Friday afternoon.",
        tier=EmailTier.TIER_2_ACTIONABLE,
    )

    msg2 = EmailMessage(
        id="msg_002",
        message_id="m2",
        thread_id="t2",
        subject="Your Amazon.com Order Confirmation #987-12345",
        sender_name="Amazon Orders",
        sender_email="auto-confirm@amazon.com",
        recipient="user@acme.org",
        date="2026-09-13",
        body="Your USB-C cables have shipped and will arrive tomorrow.",
        tier=EmailTier.TIER_3_FINANCIAL_TRAVEL,
    )

    storage.save_emails_batch([msg1, msg2])

    # Test list & filter
    listed = storage.list_emails()
    assert len(listed) == 2

    finance_msgs = storage.list_emails(tier=EmailTier.TIER_3_FINANCIAL_TRAVEL.value)
    assert len(finance_msgs) == 1
    assert finance_msgs[0].id == "msg_002"

    # Test get by id
    fetched = storage.get_email_by_id("msg_001")
    assert fetched is not None
    assert fetched.subject == "Quarterly Security Compliance Review"
    assert storage.get_email_by_id("non_existent") is None

    # Test FTS search
    matches = storage.search_fts("SOC2 access control")
    assert len(matches) == 1
    assert matches[0].id == "msg_001"

    # Test Rule CRUD
    rule = FilterRule(
        name="Auto-Label Receipts",
        criteria_from="amazon.com",
        action_apply_label="Receipts",
        action_archive=True,
    )
    storage.save_rule(rule)
    rules = storage.list_rules()
    assert len(rules) == 1
    assert rules[0].name == "Auto-Label Receipts"


def test_ingest_json_and_csv(tmp_path):
    db_file = tmp_path / "inbox_ingest.db"
    storage = StorageEngine(db_path=db_file)

    # 1. Test JSON
    json_path = tmp_path / "emails.json"
    data = [
        {
            "id": "j1",
            "subject": "Invoice #4021 from Vendor",
            "sender_name": "Vendor Billing",
            "sender_email": "billing@vendor.com",
            "body": "Invoice attached. Total: $500.",
            "date": "2026-09-14",
            "is_read": False,
        }
    ]
    json_path.write_text(json.dumps(data), encoding="utf-8")
    ingested_json = storage.ingest_json(json_path)
    assert len(ingested_json) == 1
    assert ingested_json[0].tier == EmailTier.TIER_3_FINANCIAL_TRAVEL

    # 2. Test CSV
    csv_path = tmp_path / "emails.csv"
    csv_content = (
        "id,message_id,thread_id,subject,sender_name,sender_email,recipient,date,body,is_read,is_starred\n"
        "c1,mid_c1,th_c1,Special Promo 50% off,Sales Bot,promo@store.com,me@test.com,2026-09-14,Huge sale!,false,false\n"
    )
    csv_path.write_text(csv_content, encoding="utf-8")
    ingested_csv = storage.ingest_csv(csv_path)
    assert len(ingested_csv) == 1
    assert ingested_csv[0].tier == EmailTier.TIER_5_COLD_PROMO_SPAM


def test_ingest_eml(tmp_path):
    db_file = tmp_path / "inbox_eml.db"
    storage = StorageEngine(db_path=db_file)

    eml_path = tmp_path / "sample.eml"
    raw_eml = (
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Architecture Review tomorrow\n"
        "Date: Mon, 14 Sep 2026 10:00:00 +0000\n"
        "Message-ID: <abc123eml@example.com>\n"
        "List-Unsubscribe: <https://example.com/unsub>\n"
        "List-Unsubscribe-Post: List-Unsubscribe=One-Click\n"
        "Content-Type: text/plain; charset=utf-8\n\n"
        "Hi Bob, looking forward to discussing the design.\n"
    )
    eml_path.write_text(raw_eml, encoding="utf-8")

    msg = storage.ingest_eml(eml_path)
    assert msg.subject == "Architecture Review tomorrow"
    assert msg.sender_email == "alice@example.com"
    assert msg.unsubscribe_url == "https://example.com/unsub"


def test_ingest_mbox(tmp_path):
    db_file = tmp_path / "inbox_mbox.db"
    storage = StorageEngine(db_path=db_file)

    mbox_path = tmp_path / "test.mbox"
    mb = mailbox.mbox(str(mbox_path))

    msg1 = mailbox.mboxMessage()
    msg1["From"] = "NOC Alerts <noc@corp.local>"
    msg1["To"] = "sysadmin@corp.local"
    msg1["Subject"] = "P0 Incident: Datacenter power failure"
    msg1["Date"] = "Mon, 14 Sep 2026 12:00:00 +0000"
    msg1.set_payload("Emergency server outage detected.")
    mb.add(msg1)

    msg2 = mailbox.mboxMessage()
    msg2["From"] = "newsletter@news.com"
    msg2["To"] = "sysadmin@corp.local"
    msg2["Subject"] = "Weekly digest"
    msg2["List-Unsubscribe"] = "<mailto:unsub@news.com>"
    msg2.set_payload("Unsubscribe from this newsletter.")
    mb.add(msg2)
    mb.flush()

    ingested = storage.ingest_mbox(mbox_path)
    assert len(ingested) == 2
    assert ingested[0].tier == EmailTier.TIER_1_CRITICAL
    assert ingested[1].tier == EmailTier.TIER_4_SUBSCRIPTIONS
