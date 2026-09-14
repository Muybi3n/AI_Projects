"""Unit tests for the rules exporter (Gmail XML, Sieve, JSON)."""

import json

from inboxguard.models import FilterRule
from inboxguard.rules_exporter import RulesExporter


def test_export_gmail_xml():
    rules = [
        FilterRule(
            name="Archive Newsletters",
            criteria_from="news@daily.com",
            criteria_subject="daily digest",
            action_apply_label="Newsletters",
            action_archive=True,
            action_mark_read=True,
        ),
        FilterRule(
            name="Star Urgent Alerts",
            criteria_subject="CRITICAL ALERT",
            action_apply_label="Critical",
            action_star=True,
        ),
    ]

    xml = RulesExporter.export_gmail_xml(rules)
    assert "<feed xmlns=" in xml
    assert "Archive Newsletters" in xml
    assert "news@daily.com" in xml
    assert "<apps:property name='shouldArchive' value='true'/>" in xml
    assert "<apps:property name='shouldStar' value='true'/>" in xml
    assert "</feed>" in xml


def test_export_sieve():
    rules = [
        FilterRule(
            name="Trash Cold Outreach",
            criteria_from="sales@spampromo.net",
            action_trash=True,
        ),
        FilterRule(
            name="File Invoices",
            criteria_subject="Your Invoice",
            action_apply_label="Invoices",
            action_archive=True,
        ),
    ]

    sieve = RulesExporter.export_sieve(rules)
    assert 'require ["fileinto", "imapflags", "regex"];' in sieve
    assert 'header :contains "from" "sales@spampromo.net"' in sieve
    assert "discard;" in sieve
    assert 'fileinto "Invoices";' in sieve


def test_export_json():
    rules = [
        FilterRule(
            name="Test Rule",
            criteria_from="test@example.com",
            action_apply_label="TestLabel",
        )
    ]

    json_str = RulesExporter.export_json(rules)
    data = json.loads(json_str)
    assert len(data) == 1
    assert data[0]["name"] == "Test Rule"
    assert data[0]["criteria_from"] == "test@example.com"
