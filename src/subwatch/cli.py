"""Command-line interface for subwatch."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date
from pathlib import Path

from subwatch.advisor import ask_advisor
from subwatch.engine import (
    analyze_price_creep,
    generate_audit_summary,
    generate_cancellation_brief,
    generate_negotiation_script,
    get_upcoming_renewals,
    parse_transaction_csv,
)
from subwatch.models import BillingCycle, Category, Subscription, SubscriptionStatus
from subwatch.storage import StorageManager


def get_storage(data_dir: str | None = None) -> StorageManager:
    return StorageManager(data_dir=data_dir)


def format_currency(amount: float, currency: str = "USD") -> str:
    sym = "$" if currency == "USD" else f"{currency} "
    return f"{sym}{amount:,.2f}"


def cmd_add(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    sub_id = args.id or str(uuid.uuid4())[:8]

    # Check if already exists
    existing = storage.get_subscription(args.name)
    if existing:
        print(f"⚠️  Subscription with name '{args.name}' already exists (ID: {existing.id}).")
        return 1

    sub = Subscription(
        id=sub_id,
        name=args.name,
        vendor=args.vendor or args.name,
        category=Category(args.category),
        status=SubscriptionStatus(args.status),
        billing_cycle=BillingCycle(args.cycle),
        current_price=float(args.price),
        currency=args.currency or "USD",
        start_date=args.start_date or date.today().isoformat(),
        next_renewal_date=args.renewal_date or "",
        cancellation_notice_days=int(args.notice_days),
        payment_method=args.payment_method or "",
        autopay=not args.no_autopay,
        usage_rating=int(args.usage),
        notes=args.notes or "",
    )

    rate_formatted = format_currency(sub.current_price, sub.currency)
    annual_formatted = format_currency(sub.annual_cost, sub.currency)

    # If an initial charge was implied or logged
    if args.initial_charge:
        charge_date = args.start_date or date.today().isoformat()
        storage.add_subscription(sub)
        storage.log_charge(
            sub.id,
            amount=float(args.initial_charge),
            date_str=charge_date,
            notes="Initial recorded billing charge",
        )
    else:
        # Automatically record current price as first charge baseline
        storage.add_subscription(sub)
        storage.log_charge(
            sub.id,
            amount=sub.current_price,
            date_str=sub.start_date or date.today().isoformat(),
            notes="Baseline charge",
        )

    print(f"✅ Added subscription '{sub.name}' [ID: {sub.id}]")
    print(f"   Rate: {rate_formatted} / {sub.billing_cycle.value}")
    print(f"   Annualized Run-Rate: {annual_formatted}/yr")
    print(f"   Category: {sub.category.value.title()} | Status: {sub.status.value.upper()}")
    if sub.next_renewal_date:
        print(f"   Next Renewal: {sub.next_renewal_date}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    status_filter = SubscriptionStatus(args.status) if args.status else None
    subs = storage.list_subscriptions(status_filter=status_filter)

    if args.category:
        subs = [s for s in subs if s.category.value == args.category]

    if args.json:
        print(json.dumps([s.to_dict() for s in subs], indent=2))
        return 0

    if not subs:
        print("ℹ️  No subscriptions found in local vault.")
        return 0

    print(f"\n📑 SubWatch Portfolio Directory ({len(subs)} entries)")
    print("=" * 80)
    print(f"{'ID':<10} {'Name':<22} {'Rate':<14} {'Annual':<12} {'Category':<16} {'Status'}")
    print("-" * 80)

    for s in subs:
        rate_str = f"${s.current_price:.2f}/{s.billing_cycle.value[:2]}"
        ann_str = f"${s.annual_cost:,.2f}"
        status_str = s.status.value.upper()
        if s.status == SubscriptionStatus.TRIAL:
            status_str = "⚠️ TRIAL"
        cat_str = s.category.value[:14]
        print(
            f"{s.id:<10} {s.name[:20]:<22} {rate_str:<14} {ann_str:<12} {cat_str:<16} {status_str}"
        )
    print("=" * 80)
    total_ann = sum(s.annual_cost for s in subs if s.status == SubscriptionStatus.ACTIVE)
    print(f"Total Active Annual Run-Rate: ${total_ann:,.2f}/yr\n")
    return 0


def cmd_log_charge(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    sub = storage.get_subscription(args.identifier)
    if not sub:
        print(f"❌ Error: Subscription '{args.identifier}' not found.")
        return 1

    charge_date = args.date or date.today().isoformat()
    record = storage.log_charge(
        sub.id,
        amount=float(args.amount),
        date_str=charge_date,
        payment_method=args.payment_method or "",
        notes=args.notes or "",
    )

    if not record:
        print("❌ Failed to log charge.")
        return 1

    # Update current_price if it differs
    if float(args.amount) != sub.current_price:
        storage.update_subscription(sub.id, {"current_price": float(args.amount)})
        print(f"ℹ️  Updated current price for '{sub.name}' to ${float(args.amount):.2f}.")

    print(f"✅ Logged charge of ${float(args.amount):.2f} on {charge_date} for '{sub.name}'.")

    # Check for price creep
    updated_sub = storage.get_subscription(sub.id)
    if updated_sub:
        creep = analyze_price_creep(updated_sub)
        if creep and creep.is_stealth_creep:
            print(
                f"⚠️  STEALTH PRICE CREEP DETECTED: Price increased +{creep.percent_increase}% "
                f"(+${creep.absolute_increase:.2f} / +${creep.annualized_dollar_impact:.2f}/yr)!"
            )
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    sub = storage.get_subscription(args.identifier)
    if not sub:
        print(f"❌ Error: Subscription '{args.identifier}' not found.")
        return 1

    updates: dict[str, object] = {}
    if args.price is not None:
        updates["current_price"] = float(args.price)
    if args.status is not None:
        updates["status"] = SubscriptionStatus(args.status)
    if args.cycle is not None:
        updates["billing_cycle"] = BillingCycle(args.cycle)
    if args.category is not None:
        updates["category"] = Category(args.category)
    if args.renewal_date is not None:
        updates["next_renewal_date"] = args.renewal_date
    if args.usage is not None:
        updates["usage_rating"] = int(args.usage)
    if args.notes is not None:
        updates["notes"] = args.notes

    updated = storage.update_subscription(sub.id, updates)
    if updated:
        print(f"✅ Updated subscription '{updated.name}' [{updated.id}].")
        return 0
    print("❌ Failed to update subscription.")
    return 1


def cmd_remove(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    sub = storage.get_subscription(args.identifier)
    if not sub:
        print(f"❌ Error: Subscription '{args.identifier}' not found.")
        return 1

    success = storage.remove_subscription(sub.id)
    if success:
        print(f"✅ Removed subscription '{sub.name}' [{sub.id}].")
        return 0
    print("❌ Failed to remove subscription.")
    return 1


def cmd_audit(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    subs = storage.load_all()

    summary = generate_audit_summary(subs)

    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
        return 0

    print("\n" + "=" * 80)
    print("  🛡️  SUBWATCH COMPREHENSIVE SUBSCRIPTION & PRICE-CREEP AUDIT")
    print("=" * 80)
    print(f"  • Active Subscriptions:    {summary.total_active_subscriptions}")
    print(f"  • Monthly Cash Outflow:    ${summary.total_monthly_spend:,.2f}/mo")
    print(f"  • Annual Run-Rate:         ${summary.total_annual_spend:,.2f}/yr")
    print(f"  • Actionable Savings Opp:  ${summary.potential_annual_savings:,.2f}/yr")
    print("-" * 80)

    # Category Breakdown
    print("\n📂 Category Spend Allocation (Annual):")
    for cat, amount in sorted(summary.category_breakdown.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / summary.total_annual_spend * 100) if summary.total_annual_spend > 0 else 0
        bar = "█" * int(pct / 5)
        print(f"  {cat.replace('_', ' ').title():<18} ${amount:>8,.2f}/yr ({pct:>5.1f}%) {bar}")

    # Price Creep Alerts
    print("\n📈 Price Creep & Stealth Inflation Alerts:")
    if not summary.creep_alerts:
        print("  ✨ Zero price increases detected across tracked history.")
    else:
        for creep in summary.creep_alerts:
            tag = " [STEALTH HIKE]" if creep.is_stealth_creep else ""
            print(
                f"  ⚠️  {creep.subscription_name:<20}: "
                f"${creep.initial_price:.2f} ➔ ${creep.current_price:.2f} "
                f"(+{creep.percent_increase:.1f}% | +${creep.annualized_dollar_impact:.2f}/yr){tag}"
            )

    # Zombie Subscriptions
    print("\n🛑 Low-Usage & Zombie Subscriptions (Usage ≤ 2/5):")
    if not summary.zombie_subscriptions:
        print("  ✨ No low-usage subscriptions detected.")
    else:
        for z in summary.zombie_subscriptions:
            print(
                f"  • {z.subscription_name:<20} Usage {z.usage_rating}/5 | "
                f"Cost: ${z.annual_cost:.2f}/yr"
            )
            print(f"    ↳ {z.recommendation}")

    # Category Redundancy
    print("\n🔄 Functional Redundancy Clusters:")
    if not summary.redundancies:
        print("  ✨ No multi-subscription category overlap detected.")
    else:
        for red in summary.redundancies:
            print(f"  • {red.category.value.title()} Cluster (${red.total_annual_cost:.2f}/yr):")
            print(f"    Services: {', '.join(red.subscription_names)}")
            print(f"    ↳ {red.recommendation}")

    # Upcoming Renewals
    print("\n📅 Upcoming Renewals (Next 30 Days):")
    if not summary.upcoming_renewals:
        print("  ✨ No renewals due in the next 30 days.")
    else:
        for r in summary.upcoming_renewals:
            tag = " [TRIAL]" if r.is_trial else ""
            print(
                f"  • {r.subscription_name:<18} in {r.days_until_renewal:>2}d ({r.renewal_date}) "
                f"${r.amount:.2f} | Cancel by: {r.cancel_by_date} [{r.urgency}]{tag}"
            )

    print("\n" + "=" * 80 + "\n")
    return 0


def cmd_renewals(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    subs = storage.load_all()
    days = int(args.days or 30)

    alerts = get_upcoming_renewals(subs, days_window=days)
    if not alerts:
        print(f"ℹ️  No subscriptions renewing within the next {days} days.")
        return 0

    print(f"\n📅 Upcoming Renewal Radar ({len(alerts)} due in {days} days)")
    print("=" * 75)
    print(
        f"{'Service':<20} {'Days':<6} {'Renewal Date':<14} {'Amount':<12} "
        f"{'Cancel By':<14} {'Urgency'}"
    )
    print("-" * 75)
    for a in alerts:
        tag = " ⚠️ TRIAL" if a.is_trial else ""
        print(
            f"{a.subscription_name[:18] + tag:<20} {a.days_until_renewal:<6} {a.renewal_date:<14} "
            f"${a.amount:<11.2f} {a.cancel_by_date:<14} {a.urgency}"
        )
    print("=" * 75 + "\n")
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    sub = storage.get_subscription(args.identifier)
    if not sub:
        print(f"❌ Error: Subscription '{args.identifier}' not found.")
        return 1

    if args.negotiate:
        print(generate_negotiation_script(sub))
    else:
        print(generate_cancellation_brief(sub))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    path = Path(args.file)
    if not path.exists():
        print(f"❌ Error: File '{args.file}' does not exist.")
        return 1

    with open(path, encoding="utf-8", errors="ignore") as file_handle:
        csv_text = file_handle.read()

    candidates = parse_transaction_csv(csv_text)
    if not candidates:
        print("ℹ️  No recurring subscription patterns detected in CSV.")
        return 0

    print(f"\n🔍 Detected {len(candidates)} Recurring Candidate Transactions in CSV:")
    print("-" * 65)
    for idx, c in enumerate(candidates, 1):
        print(f"  {idx}. {c['vendor']:<20} ${c['amount']:.2f} ({c['category']}) on {c['date']}")
    print("-" * 65)

    if args.auto_add:
        added_count = 0
        for c in candidates:
            # Check if exists
            existing = storage.get_subscription(c["vendor"])
            if existing:
                # Log charge to existing
                storage.log_charge(existing.id, c["amount"], c["date"], notes="Ingested via CSV")
            else:
                new_sub = Subscription(
                    id=str(uuid.uuid4())[:8],
                    name=c["vendor"],
                    vendor=c["vendor"],
                    category=Category(c["category"]),
                    status=SubscriptionStatus.ACTIVE,
                    billing_cycle=BillingCycle.MONTHLY,
                    current_price=c["amount"],
                    start_date=c["date"],
                    charge_history=[],
                )
                storage.add_subscription(new_sub)
                storage.log_charge(new_sub.id, c["amount"], c["date"], notes="Ingested baseline")
                added_count += 1
        print(f"✅ Automatically imported {added_count} new subscriptions and logged charges.")
    else:
        print("💡 Use `--auto-add` to automatically register detected subscriptions into vault.")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    subs = storage.load_all()
    query = " ".join(args.query) if isinstance(args.query, list) else str(args.query)
    if not query.strip():
        print("❌ Error: Query cannot be empty.")
        return 1

    response = ask_advisor(query, subs)
    print("\n" + response + "\n")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    storage = get_storage(args.data_dir)
    subs = storage.load_all()
    summary = generate_audit_summary(subs)

    export_format = args.format or "json"
    if export_format == "json":
        data = {
            "summary": summary.to_dict(),
            "subscriptions": [s.to_dict() for s in subs],
        }
        output_str = json.dumps(data, indent=2)
    else:
        # Markdown summary
        lines = [
            "# 📊 SubWatch Subscription Portfolio Export",
            f"- **Date Generated:** {date.today().isoformat()}",
            f"- **Active Subscriptions:** {summary.total_active_subscriptions}",
            f"- **Annual Run-Rate:** ${summary.total_annual_spend:.2f}/yr",
            f"- **Potential Savings:** ${summary.potential_annual_savings:.2f}/yr",
            "",
            "## 📑 Subscriptions",
            "| Service | Category | Rate | Annual Cost | Status | Renewal Date |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for s in subs:
            lines.append(
                f"| {s.name} | {s.category.value} | "
                f"${s.current_price:.2f}/{s.billing_cycle.value} | "
                f"${s.annual_cost:.2f} | {s.status.value} | {s.next_renewal_date or 'N/A'} |"
            )
        output_str = "\n".join(lines)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as file_handle:
            file_handle.write(output_str)
        print(f"✅ Exported portfolio to '{args.out}'.")
    else:
        print(output_str)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="subwatch",
        description="Local-first subscription price-creep auditor & renewal alert radar.",
    )
    parser.add_argument(
        "--data-dir", help="Path to custom data directory (defaults to ~/.subwatch)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # add
    p_add = subparsers.add_parser("add", help="Add a new subscription")
    p_add.add_argument("--name", required=True, help="Subscription or service name")
    p_add.add_argument("--price", required=True, type=float, help="Current billing price")
    p_add.add_argument("--vendor", help="Vendor or service provider name")
    p_add.add_argument(
        "--category",
        choices=[c.value for c in Category],
        default=Category.OTHER.value,
        help="Functional category",
    )
    p_add.add_argument(
        "--cycle",
        choices=[b.value for b in BillingCycle],
        default=BillingCycle.MONTHLY.value,
        help="Billing cycle",
    )
    p_add.add_argument(
        "--status",
        choices=[s.value for s in SubscriptionStatus],
        default=SubscriptionStatus.ACTIVE.value,
        help="Lifecycle status",
    )
    p_add.add_argument("--currency", default="USD", help="Currency code (USD, EUR, GBP)")
    p_add.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    p_add.add_argument("--renewal-date", help="Next auto-renewal date (YYYY-MM-DD)")
    p_add.add_argument(
        "--notice-days", default=3, type=int, help="Cancellation notice days required"
    )
    p_add.add_argument("--payment-method", help="Payment card or method descriptor")
    p_add.add_argument("--no-autopay", action="store_true", help="Disable autopay flag")
    p_add.add_argument(
        "--usage", default=3, type=int, choices=[1, 2, 3, 4, 5], help="Usage rating (1-5)"
    )
    p_add.add_argument(
        "--initial-charge", type=float, help="Initial historical charge amount if different"
    )
    p_add.add_argument("--notes", help="Arbitrary notes or tags")
    p_add.add_argument("--id", help="Explicit subscription ID")
    p_add.set_defaults(func=cmd_add)

    # list
    p_list = subparsers.add_parser("list", help="List all subscriptions")
    p_list.add_argument(
        "--status", choices=[s.value for s in SubscriptionStatus], help="Filter by status"
    )
    p_list.add_argument(
        "--category", choices=[c.value for c in Category], help="Filter by category"
    )
    p_list.add_argument("--json", action="store_true", help="Output raw JSON")
    p_list.set_defaults(func=cmd_list)

    # log-charge
    p_log = subparsers.add_parser(
        "log-charge", help="Log an actual billing charge for price-creep tracking"
    )
    p_log.add_argument("identifier", help="Subscription ID or name")
    p_log.add_argument("--amount", required=True, type=float, help="Charged amount")
    p_log.add_argument("--date", help="Charge date (YYYY-MM-DD, defaults to today)")
    p_log.add_argument("--payment-method", help="Payment method on receipt")
    p_log.add_argument("--notes", help="Optional charge notes")
    p_log.set_defaults(func=cmd_log_charge)

    # update
    p_up = subparsers.add_parser("update", help="Update subscription details")
    p_up.add_argument("identifier", help="Subscription ID or name")
    p_up.add_argument("--price", type=float, help="New current price")
    p_up.add_argument("--status", choices=[s.value for s in SubscriptionStatus], help="New status")
    p_up.add_argument("--cycle", choices=[b.value for b in BillingCycle], help="New cycle")
    p_up.add_argument("--category", choices=[c.value for c in Category], help="New category")
    p_up.add_argument("--renewal-date", help="New renewal date (YYYY-MM-DD)")
    p_up.add_argument("--usage", type=int, choices=[1, 2, 3, 4, 5], help="New usage rating")
    p_up.add_argument("--notes", help="New notes")
    p_up.set_defaults(func=cmd_update)

    # remove
    p_rm = subparsers.add_parser("remove", help="Remove a subscription")
    p_rm.add_argument("identifier", help="Subscription ID or name")
    p_rm.set_defaults(func=cmd_remove)

    # audit
    p_audit = subparsers.add_parser(
        "audit", help="Run comprehensive subscription & price-creep audit"
    )
    p_audit.add_argument("--json", action="store_true", help="Output audit as JSON")
    p_audit.set_defaults(func=cmd_audit)

    # renewals
    p_ren = subparsers.add_parser("renewals", help="Show upcoming renewal alert radar")
    p_ren.add_argument("--days", default=30, type=int, help="Days window (default: 30)")
    p_ren.set_defaults(func=cmd_renewals)

    # brief
    p_br = subparsers.add_parser(
        "brief", help="Generate cancellation playbook or negotiation script"
    )
    p_br.add_argument("identifier", help="Subscription ID or name")
    p_br.add_argument(
        "--negotiate", action="store_true", help="Generate negotiation script instead"
    )
    p_br.set_defaults(func=cmd_brief)

    # ingest
    p_ing = subparsers.add_parser(
        "ingest", help="Ingest CSV transaction export to detect subscriptions"
    )
    p_ing.add_argument("--file", required=True, help="Path to bank/credit card CSV export")
    p_ing.add_argument(
        "--auto-add", action="store_true", help="Automatically add detected candidate subscriptions"
    )
    p_ing.set_defaults(func=cmd_ingest)

    # ask
    p_ask = subparsers.add_parser("ask", help="Ask AI subscription optimization advisor")
    p_ask.add_argument("query", nargs="+", help="Natural language query")
    p_ask.set_defaults(func=cmd_ask)

    # export
    p_exp = subparsers.add_parser("export", help="Export subscriptions and audit report")
    p_exp.add_argument("--format", choices=["json", "md"], default="json", help="Export format")
    p_exp.add_argument("--out", help="Output file path")
    p_exp.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
