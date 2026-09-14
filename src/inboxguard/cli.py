"""Command Line Interface for inboxguard-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from inboxguard.ai_companion import InboxCompanion
from inboxguard.models import EmailTier, FilterRule, SecurityRiskLevel
from inboxguard.newsletter import NewsletterCleaner
from inboxguard.rules_exporter import RulesExporter
from inboxguard.security import SecurityAuditor
from inboxguard.storage import StorageEngine


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inboxguard",
        description="Local-first email triage, 5-tier classifier, newsletter cleaner, and security filter engine.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom storage directory path (defaults to ~/.inboxguard)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    subparsers.add_parser("init", help="Initialize the local SQLite database and schema.")

    # ingest
    ingest_p = subparsers.add_parser("ingest", help="Ingest emails from MBOX, EML, JSON, or CSV files.")
    ingest_p.add_argument("file_path", type=str, help="Path to MBOX, EML, JSON, or CSV file to import.")
    ingest_p.add_argument(
        "--format",
        choices=["auto", "mbox", "eml", "json", "csv"],
        default="auto",
        help="Explicit file format override (default: auto-detect)",
    )

    # triage
    triage_p = subparsers.add_parser("triage", help="Run 5-tier classification and display inbox triage summary.")
    triage_p.add_argument("--json", action="store_true", help="Output summary in JSON format.")

    # list
    list_p = subparsers.add_parser("list", help="List ingested emails with filtering.")
    list_p.add_argument("--tier", choices=[t.value for t in EmailTier], help="Filter by priority tier.")
    list_p.add_argument("--sender", type=str, help="Filter by sender email or name.")
    list_p.add_argument("--unread", action="store_true", help="Show unread messages only.")
    list_p.add_argument("--risk", choices=[r.value for r in SecurityRiskLevel], help="Filter by security risk tier.")
    list_p.add_argument("--limit", type=int, default=50, help="Max results to display (default: 50).")
    list_p.add_argument("--json", action="store_true", help="Output results in JSON format.")

    # newsletters
    news_p = subparsers.add_parser("newsletters", help="Analyze subscriptions, decay metrics, and unsubscribe links.")
    news_p.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help="Decay score threshold for pruning (0.0 to 1.0, default: 0.4)",
    )
    news_p.add_argument("--json", action="store_true", help="Output results in JSON format.")

    # security
    sec_p = subparsers.add_parser("security", help="Audit mailbox for phishing, spoofing, and signature failures.")
    sec_p.add_argument("--json", action="store_true", help="Output audit results in JSON format.")

    # rules
    rules_p = subparsers.add_parser("rules", help="Generate and export filter rules for Gmail, Sieve, or JSON.")
    rules_p.add_argument(
        "--format",
        choices=["gmail", "sieve", "json"],
        default="gmail",
        help="Target export format (default: gmail)",
    )
    rules_p.add_argument("--output", "-o", type=str, help="Output destination file path.")
    rules_p.add_argument(
        "--generate-defaults",
        action="store_true",
        help="Auto-generate standard recommended triage rules based on detected tiers.",
    )

    # search
    search_p = subparsers.add_parser("search", help="Perform full-text search across email subjects and bodies.")
    search_p.add_argument("query", type=str, help="FTS5 search term or phrase.")
    search_p.add_argument("--limit", type=int, default=25, help="Max results (default: 25).")
    search_p.add_argument("--json", action="store_true", help="Output results in JSON format.")

    # ask
    ask_p = subparsers.add_parser("ask", help="Query the AI companion / deterministic heuristic triage advisor.")
    ask_p.add_argument("query", type=str, help="Question or directive for the advisor.")
    ask_p.add_argument("--json", action="store_true", help="Output response in JSON format.")

    return parser


def get_storage(data_dir: str | None) -> StorageEngine:
    if data_dir:
        db_path = Path(data_dir) / "inboxguard.db"
        return StorageEngine(db_path=db_path)
    return StorageEngine()


def run_init(storage: StorageEngine) -> int:
    print(f"✅ inboxguard database initialized successfully at: {storage.db_path}")
    return 0


def run_ingest(storage: StorageEngine, file_path_str: str, fmt: str) -> int:
    path = Path(file_path_str)
    if not path.exists():
        print(f"❌ Error: File not found: {path}", file=sys.stderr)
        return 1

    suffix = path.suffix.lower()
    if fmt == "auto":
        if suffix in [".mbox", ".mbx"]:
            fmt = "mbox"
        elif suffix in [".eml", ".msg"]:
            fmt = "eml"
        elif suffix == ".json":
            fmt = "json"
        elif suffix == ".csv":
            fmt = "csv"
        else:
            fmt = "mbox"  # fallback

    try:
        if fmt == "mbox":
            msgs = storage.ingest_mbox(path)
            print(f"📥 Successfully ingested {len(msgs)} messages from MBOX: {path.name}")
        elif fmt == "eml":
            msg = storage.ingest_eml(path)
            print(f"📥 Successfully ingested EML message: '{msg.subject}' from {msg.sender_email}")
        elif fmt == "json":
            msgs = storage.ingest_json(path)
            print(f"📥 Successfully ingested {len(msgs)} messages from JSON: {path.name}")
        elif fmt == "csv":
            msgs = storage.ingest_csv(path)
            print(f"📥 Successfully ingested {len(msgs)} messages from CSV: {path.name}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"❌ Error ingesting file {path}: {e}", file=sys.stderr)
        return 1

    return 0


def run_triage(storage: StorageEngine, as_json: bool) -> int:
    counts = storage.count_by_tier()
    total = sum(counts.values())
    critical_msgs = storage.list_emails(tier=EmailTier.TIER_1_CRITICAL.value, limit=5)
    all_msgs = storage.list_emails(limit=200)

    cleaner = NewsletterCleaner()
    profiles = cleaner.analyze_senders(all_msgs)
    decayed = cleaner.extract_decayed_subscriptions(profiles, threshold=0.4)

    auditor = SecurityAuditor()
    security_assessments = auditor.audit_batch(all_msgs)
    high_risks = [
        a for a in security_assessments if a.risk_level in [SecurityRiskLevel.HIGH_RISK, SecurityRiskLevel.PHISHING]
    ]

    if as_json:
        data = {
            "total_emails": total,
            "tier_counts": counts,
            "critical_emails": [e.to_dict() for e in critical_msgs],
            "decayed_subscriptions_count": len(decayed),
            "high_risk_security_count": len(high_risks),
        }
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 70)
    print(" 📬 INBOXGUARD 5-TIER TRIAGE DASHBOARD ")
    print("=" * 70)
    print(f"Total Emails Indexed: {total}\n")

    tier_labels = [
        (EmailTier.TIER_1_CRITICAL.value, "🚨 Tier 1: CRITICAL (Security, 2FA, Outages, VIP)"),
        (EmailTier.TIER_2_ACTIONABLE.value, "💬 Tier 2: ACTIONABLE (Human 1:1, PR Reviews, Tasks)"),
        (EmailTier.TIER_3_FINANCIAL_TRAVEL.value, "💳 Tier 3: FINANCIAL & TRAVEL (Receipts, Flights, Bills)"),
        (EmailTier.TIER_4_SUBSCRIPTIONS.value, "📰 Tier 4: SUBSCRIPTIONS (Newsletters, Updates)"),
        (EmailTier.TIER_5_COLD_PROMO_SPAM.value, "🗑️  Tier 5: COLD PROMO & SPAM (SDR Pitches, Ads)"),
    ]

    for tier_key, label in tier_labels:
        count = counts.get(tier_key, 0)
        pct = (count / total * 100) if total > 0 else 0.0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"{label}")
        print(f"   [{bar}] {count:>4} emails ({pct:>5.1f}%)\n")

    if critical_msgs:
        print("🚨 IMMEDIATE ATTENTION REQUIRED (Tier 1 Alerts):")
        for cm in critical_msgs:
            print(f"   • [{cm.id}] {cm.subject} (From: {cm.sender_email})")
            if cm.tier_reasons:
                print(f"     Reason: {cm.tier_reasons[0]}")
        print()

    if high_risks:
        print(f"⚠️  SECURITY WARNING: {len(high_risks)} high-risk / phishing messages detected!")
        for hr in high_risks[:3]:
            print(f"   • [{hr.risk_level.value}] From: {hr.sender_email} | Subject: {hr.subject}")
        print()

    if decayed:
        print(f"🧹 SUBSCRIPTION PURGE: {len(decayed)} newsletter subscriptions show >40% decay (unread streak).")
        print("   Run `inboxguard newsletters` to view one-click unsubscribe links.")

    print("=" * 70)
    return 0


def run_list(
    storage: StorageEngine,
    tier: str | None,
    sender: str | None,
    unread: bool,
    risk: str | None,
    limit: int,
    as_json: bool,
) -> int:
    messages = storage.list_emails(tier=tier, sender=sender, unread_only=unread, security_risk=risk, limit=limit)

    if as_json:
        print(json.dumps([m.to_dict() for m in messages], indent=2))
        return 0

    print(f"\nListing {len(messages)} email(s):")
    print("-" * 80)
    for m in messages:
        read_badge = " " if m.is_read else "🔵 [UNREAD]"
        star_badge = "⭐ " if m.is_starred else ""
        print(f"{m.id:<10} | {m.tier.value:<25} | {m.date[:16]:<16} | {read_badge}{star_badge}")
        print(f"  From:    {m.sender_name} <{m.sender_email}>")
        print(f"  Subject: {m.subject}")
        if m.security_risk != SecurityRiskLevel.SAFE:
            print(f"  ⚠️ Risk:  {m.security_risk.value} ({'; '.join(m.security_reasons)})")
        print("-" * 80)
    return 0


def run_newsletters(storage: StorageEngine, threshold: float, as_json: bool) -> int:
    all_msgs = storage.list_emails(limit=500)
    cleaner = NewsletterCleaner()
    profiles = cleaner.analyze_senders(all_msgs)
    decayed = cleaner.extract_decayed_subscriptions(profiles, threshold=threshold)

    if as_json:
        print(json.dumps([p.to_dict() for p in decayed], indent=2))
        return 0

    print("\n" + "=" * 75)
    print(" 📰 SUBSCRIPTION HYGIENE & DECAY AUDITOR ")
    print("=" * 75)
    print(f"Found {len(decayed)} subscription(s) exceeding decay threshold {threshold:.2f}:\n")

    for p in decayed:
        pct_unread = (p.unread_count / p.total_count * 100) if p.total_count > 0 else 0
        print(f"• Sender: {p.sender_name} <{p.sender_email}>")
        print(
            f"  Volume: {p.total_count} total | {p.unread_count} unread ({pct_unread:.0f}% unread) | Decay Score: {p.decay_score:.3f}"
        )
        if p.unsubscribe_url:
            print(f"  🔗 Direct Unsubscribe URL: {p.unsubscribe_url}")
        if p.unsubscribe_mailto:
            print(f"  ✉️  Mailto Unsubscribe:    {p.unsubscribe_mailto}")
        if not p.unsubscribe_url and not p.unsubscribe_mailto:
            print("  ⚠️ No RFC List-Unsubscribe header found (manual unsub needed)")
        print("-" * 75)

    return 0


def run_security(storage: StorageEngine, as_json: bool) -> int:
    all_msgs = storage.list_emails(limit=500)
    auditor = SecurityAuditor()
    assessments = auditor.audit_batch(all_msgs)

    flagged = [a for a in assessments if a.risk_level != SecurityRiskLevel.SAFE]

    if as_json:
        print(json.dumps([a.to_dict() for a in flagged], indent=2))
        return 0

    print("\n" + "=" * 75)
    print(" 🛡️ SECURITY & PHISHING AUDIT REPORT ")
    print("=" * 75)
    print(f"Scanned {len(assessments)} emails. Flagged {len(flagged)} suspicious message(s).\n")

    for a in flagged:
        icon = "🚨" if a.risk_level in [SecurityRiskLevel.PHISHING, SecurityRiskLevel.HIGH_RISK] else "⚠️"
        print(f"{icon} Risk Tier: {a.risk_level.value}")
        print(f"  From:    {a.sender_name} <{a.sender_email}>")
        print(f"  Subject: {a.subject}")
        print(
            f"  SPF: {'PASS' if a.spf_pass else 'FAIL'} | DKIM: {'PASS' if a.dkim_pass else 'FAIL'} | DMARC: {'PASS' if a.dmarc_pass else 'FAIL'}"
        )
        if a.reasons:
            print("  Reasons:")
            for r in a.reasons:
                print(f"    - {r}")
        print("-" * 75)

    return 0


def run_rules(storage: StorageEngine, fmt: str, output_path: str | None, generate_defaults: bool) -> int:
    rules = storage.list_rules()

    if generate_defaults or not rules:
        # Generate standard default rule templates
        default_rules = [
            FilterRule(
                name="Security & Critical Alerts",
                criteria_subject="security alert OR 2fa OR verification code OR outage",
                action_apply_label="Priority/Critical",
                action_star=True,
            ),
            FilterRule(
                name="Receipts & Financial Invoices",
                criteria_subject="receipt OR invoice OR confirmation OR booking",
                action_apply_label="Finance/Receipts",
                action_archive=True,
            ),
            FilterRule(
                name="Newsletters & Subscriptions",
                criteria_has_words="unsubscribe OR 'view in browser'",
                action_apply_label="Subscriptions/Newsletters",
                action_archive=True,
            ),
            FilterRule(
                name="Cold Outreach & SDR Pitches",
                criteria_subject="quick 15 min OR discount OR promo OR 'limited time offer'",
                action_apply_label="Promotions",
                action_archive=True,
                action_mark_read=True,
            ),
        ]
        for r in default_rules:
            storage.save_rule(r)
        rules = storage.list_rules()

    if fmt == "gmail":
        content = RulesExporter.export_gmail_xml(rules)
    elif fmt == "sieve":
        content = RulesExporter.export_sieve(rules)
    else:
        content = RulesExporter.export_json(rules)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"✅ Exported {len(rules)} filter rules ({fmt}) to: {output_path}")
    else:
        print(content)

    return 0


def run_search(storage: StorageEngine, query: str, limit: int, as_json: bool) -> int:
    results = storage.search_fts(query, limit=limit)

    if as_json:
        print(json.dumps([m.to_dict() for m in results], indent=2))
        return 0

    print(f"\n🔍 Search results for: '{query}' ({len(results)} match(es)):")
    print("-" * 75)
    for m in results:
        print(f"[{m.id}] {m.subject} | From: {m.sender_name} <{m.sender_email}> | {m.tier.value}")
        snippet = m.body[:120].replace("\n", " ") + ("..." if len(m.body) > 120 else "")
        print(f"   Snippet: {snippet}")
        print("-" * 75)
    return 0


def run_ask(storage: StorageEngine, query: str, as_json: bool) -> int:
    companion = InboxCompanion(storage)
    resp = companion.consult(query)

    if as_json:
        print(json.dumps(resp.to_dict(), indent=2))
        return 0

    print("\n" + "=" * 70)
    print(" 🤖 INBOXGUARD AI TRIAGE ADVISOR ")
    print("=" * 70)
    print(f"Query: {resp.query}\n")
    print(f"{resp.summary}\n")

    if resp.critical_alerts:
        print("🚨 Critical Alerts:")
        for ca in resp.critical_alerts:
            print(f"  • {ca}")
        print()

    if resp.subscription_recommendations:
        print("📰 Subscription Prune Candidates:")
        for sr in resp.subscription_recommendations:
            print(f"  • {sr}")
        print()

    if resp.security_warnings:
        print("⚠️ Security Warnings:")
        for sw in resp.security_warnings:
            print(f"  • {sw}")
        print()

    if resp.draft_reply:
        print("✉️ Synthesized Reply Draft:")
        print("-" * 40)
        print(resp.draft_reply)
        print("-" * 40 + "\n")

    if resp.suggested_actions:
        print("⚡ Recommended Next Actions:")
        for sa in resp.suggested_actions:
            print(f"  ✓ {sa}")

    print("=" * 70)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    storage = get_storage(args.data_dir)

    if args.command == "init":
        return run_init(storage)
    elif args.command == "ingest":
        return run_ingest(storage, args.file_path, args.format)
    elif args.command == "triage":
        return run_triage(storage, args.json)
    elif args.command == "list":
        return run_list(storage, args.tier, args.sender, args.unread, args.risk, args.limit, args.json)
    elif args.command == "newsletters":
        return run_newsletters(storage, args.threshold, args.json)
    elif args.command == "security":
        return run_security(storage, args.json)
    elif args.command == "rules":
        return run_rules(storage, args.format, args.output, args.generate_defaults)
    elif args.command == "search":
        return run_search(storage, args.query, args.limit, args.json)
    elif args.command == "ask":
        return run_ask(storage, args.query, args.json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
