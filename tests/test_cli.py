"""Full end-to-end workflow tests for inboxguard CLI."""

import json
import mailbox

from inboxguard.cli import main


def test_cli_full_workflow(tmp_path, capsys):
    data_dir = str(tmp_path / "inbox_data")

    # 1. init
    rc = main(["--data-dir", data_dir, "init"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "initialized successfully" in out

    # Ingest non-existent file error
    rc = main(["--data-dir", data_dir, "ingest", str(tmp_path / "missing.json")])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "File not found" in err

    # Ingest EML file
    eml_file = tmp_path / "test.eml"
    eml_file.write_text(
        "From: Boss <boss@company.com>\nSubject: Urgent: server check\n\nCheck server immediately.", encoding="utf-8"
    )
    rc = main(["--data-dir", data_dir, "ingest", str(eml_file)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Successfully ingested EML" in out

    # Ingest MBOX file
    mbox_file = tmp_path / "test.mbox"
    mb = mailbox.mbox(str(mbox_file))
    m = mailbox.mboxMessage()
    m["From"] = "friend@domain.com"
    m["Subject"] = "Coffee sync"
    m.set_payload("Let's grab coffee.")
    mb.add(m)
    mb.flush()
    rc = main(["--data-dir", data_dir, "ingest", str(mbox_file)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Successfully ingested 1 messages from MBOX" in out

    # Ingest CSV file
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "id,subject,sender_name,sender_email,body\ncsv1,Invoice,Bill,bill@corp.com,Paid\n", encoding="utf-8"
    )
    rc = main(["--data-dir", data_dir, "ingest", str(csv_file)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Successfully ingested 1 messages from CSV" in out

    # 2. Ingest JSON
    json_path = tmp_path / "sample_inbox.json"
    emails = [
        {
            "id": "em_001",
            "subject": "CRITICAL: 2FA security alert for root login",
            "sender_name": "AWS Security",
            "sender_email": "security@aws.amazon.com",
            "date": "2026-09-14 08:00:00",
            "body": "Root login detected from unknown IP.",
            "is_read": False,
        },
        {
            "id": "em_002",
            "subject": "Pull request #12 review requested",
            "sender_name": "GitHub Notifications",
            "sender_email": "notifications@github.com",
            "date": "2026-09-14 08:30:00",
            "body": "Please review changes to auth engine.",
            "is_read": False,
        },
        {
            "id": "em_003",
            "subject": "Your Receipt for Order #88219",
            "sender_name": "Apple Store",
            "sender_email": "orders@apple.com",
            "date": "2026-09-14 09:00:00",
            "body": "Your invoice of $129.00 has been paid.",
            "is_read": True,
        },
        {
            "id": "em_004",
            "subject": "Weekly Tech Insights #99",
            "sender_name": "Tech Weekly",
            "sender_email": "news@techweekly.org",
            "date": "2026-09-14 09:30:00",
            "body": "Check out this week's news. Unsubscribe here: https://techweekly.org/unsub",
            "unsubscribe_url": "https://techweekly.org/unsub",
            "is_read": False,
        },
        {
            "id": "em_005",
            "subject": "Quick 15 min call for 50% off lead gen",
            "sender_name": "Sales SDR",
            "sender_email": "spammer@coldreach.xyz",
            "date": "2026-09-14 10:00:00",
            "body": "Limited time offer for your business.",
            "is_read": False,
        },
        {
            "id": "em_006",
            "subject": "Immediate verification required for Paypal login",
            "sender_name": "PayPal Support",
            "sender_email": "support@bank-phish-fake.xyz",
            "date": "2026-09-14 10:15:00",
            "body": "Your account will be terminated. Click http://192.168.1.50/login now.",
            "is_read": False,
        },
    ]
    json_path.write_text(json.dumps(emails), encoding="utf-8")

    rc = main(["--data-dir", data_dir, "ingest", str(json_path)])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Successfully ingested 6 messages" in out

    # 3. triage
    rc = main(["--data-dir", data_dir, "triage"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "INBOXGUARD 5-TIER TRIAGE DASHBOARD" in out

    # triage --json
    rc = main(["--data-dir", data_dir, "triage", "--json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    parsed = json.loads(out)
    assert parsed["total_emails"] >= 6

    # 4. list
    rc = main(["--data-dir", data_dir, "list", "--tier", "TIER_1_CRITICAL"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "em_001" in out

    # list with unread, risk, sender
    rc = main(["--data-dir", data_dir, "list", "--sender", "Apple", "--unread"])
    assert rc == 0
    capsys.readouterr()

    # list --json
    rc = main(["--data-dir", data_dir, "list", "--json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert len(json.loads(out)) >= 6

    # 5. newsletters
    rc = main(["--data-dir", data_dir, "newsletters", "--threshold", "0.2"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "SUBSCRIPTION HYGIENE & DECAY AUDITOR" in out
    assert "news@techweekly.org" in out

    # newsletters --json
    rc = main(["--data-dir", data_dir, "newsletters", "--threshold", "0.2", "--json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert len(json.loads(out)) >= 1

    # 6. security
    rc = main(["--data-dir", data_dir, "security"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "SECURITY & PHISHING AUDIT REPORT" in out
    assert "support@bank-phish-fake.xyz" in out

    # security --json
    rc = main(["--data-dir", data_dir, "security", "--json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert len(json.loads(out)) >= 1

    # 7. rules
    rules_xml = tmp_path / "filters.xml"
    rc = main(["--data-dir", data_dir, "rules", "--format", "gmail", "--output", str(rules_xml), "--generate-defaults"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Exported 4 filter rules" in out
    assert rules_xml.exists()
    assert "<feed xmlns=" in rules_xml.read_text(encoding="utf-8")

    # rules sieve to stdout
    rc = main(["--data-dir", data_dir, "rules", "--format", "sieve"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert 'require ["fileinto"' in out

    # rules json to stdout
    rc = main(["--data-dir", data_dir, "rules", "--format", "json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert len(json.loads(out)) >= 4

    # 8. search
    rc = main(["--data-dir", data_dir, "search", "Receipt"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Search results for: 'Receipt'" in out
    assert "em_003" in out

    # search --json
    rc = main(["--data-dir", data_dir, "search", "Receipt", "--json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert len(json.loads(out)) == 1

    # 9. ask
    rc = main(["--data-dir", data_dir, "ask", "What are my critical alerts?"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "INBOXGUARD AI TRIAGE ADVISOR" in out
    assert "CRITICAL" in out

    # ask --json
    rc = main(["--data-dir", data_dir, "ask", "Show phishing risks", "--json"])
    assert rc == 0
    out, _ = capsys.readouterr()
    resp_data = json.loads(out)
    assert len(resp_data["security_warnings"]) >= 1

    # ask newsletters and draft reply
    rc = main(["--data-dir", data_dir, "ask", "Clean my newsletters and draft a reply"])
    assert rc == 0
    out, _ = capsys.readouterr()
    assert "Subscription Prune Candidates:" in out

    # 10. no args prints help
    rc = main([])
    assert rc == 0
