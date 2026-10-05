"""Core subscription analysis and audit engine."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any

from subwatch.models import (
    AuditSummary,
    Category,
    CreepReport,
    RedundancyCluster,
    RenewalAlert,
    Subscription,
    SubscriptionStatus,
    ZombieSubscription,
)

# Known recurring vendors and category heuristics
KNOWN_VENDORS: dict[str, tuple[str, Category]] = {
    "netflix": ("Netflix", Category.ENTERTAINMENT),
    "spotify": ("Spotify", Category.ENTERTAINMENT),
    "disney+": ("Disney+", Category.ENTERTAINMENT),
    "disneyplus": ("Disney+", Category.ENTERTAINMENT),
    "hulu": ("Hulu", Category.ENTERTAINMENT),
    "hbo max": ("Max", Category.ENTERTAINMENT),
    "prime video": ("Amazon Prime Video", Category.ENTERTAINMENT),
    "youtube premium": ("YouTube Premium", Category.ENTERTAINMENT),
    "apple tv": ("Apple TV+", Category.ENTERTAINMENT),
    "github": ("GitHub", Category.DEVELOPER_CLOUD),
    "openai": ("OpenAI ChatGPT", Category.AI_ML),
    "chatgpt": ("OpenAI ChatGPT", Category.AI_ML),
    "anthropic": ("Anthropic Claude", Category.AI_ML),
    "claude.ai": ("Anthropic Claude", Category.AI_ML),
    "aws": ("Amazon Web Services", Category.DEVELOPER_CLOUD),
    "digitalocean": ("DigitalOcean", Category.DEVELOPER_CLOUD),
    "cloudflare": ("Cloudflare", Category.SECURITY),
    "vercel": ("Vercel", Category.DEVELOPER_CLOUD),
    "notion": ("Notion", Category.PRODUCTIVITY),
    "slack": ("Slack", Category.PRODUCTIVITY),
    "1password": ("1Password", Category.SECURITY),
    "bitwarden": ("Bitwarden", Category.SECURITY),
    "adobe": ("Adobe Creative Cloud", Category.PRODUCTIVITY),
    "figma": ("Figma", Category.PRODUCTIVITY),
    "jetbrains": ("JetBrains", Category.DEVELOPER_CLOUD),
    "linear": ("Linear", Category.PRODUCTIVITY),
    "dropbox": ("Dropbox", Category.PRODUCTIVITY),
    "google one": ("Google One Storage", Category.PRODUCTIVITY),
    "icloud": ("Apple iCloud", Category.PRODUCTIVITY),
    "zoom": ("Zoom Video", Category.PRODUCTIVITY),
    "wsj": ("Wall Street Journal", Category.NEWS_MEDIA),
    "nyt": ("New York Times", Category.NEWS_MEDIA),
    "strava": ("Strava", Category.HEALTH_FITNESS),
    "whoop": ("Whoop", Category.HEALTH_FITNESS),
}


def analyze_price_creep(subscription: Subscription) -> CreepReport | None:
    """Analyze historical price creep for a given subscription."""
    if not subscription.charge_history:
        return None

    # Sort charges chronologically
    sorted_charges = sorted(
        subscription.charge_history,
        key=lambda item: item.date if item.date else "1970-01-01",
    )

    earliest = sorted_charges[0]
    latest = sorted_charges[-1]

    initial_price = earliest.amount
    current_price = subscription.current_price

    # Fallback to latest charge amount if subscription price was not updated
    if current_price <= 0 and latest.amount > 0:
        current_price = latest.amount

    if initial_price <= 0:
        return None

    absolute_increase = round(current_price - initial_price, 2)
    percent_increase = round(((current_price - initial_price) / initial_price) * 100.0, 2)
    annualized_impact = round(
        absolute_increase * subscription.billing_cycle.multiplier_to_annual, 2
    )

    return CreepReport(
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        initial_price=initial_price,
        current_price=current_price,
        absolute_increase=absolute_increase,
        percent_increase=percent_increase,
        annualized_dollar_impact=annualized_impact,
        first_charge_date=earliest.date,
        latest_charge_date=latest.date,
        is_stealth_creep=(percent_increase >= 5.0 and absolute_increase > 0),
    )


def get_upcoming_renewals(
    subscriptions: list[Subscription],
    days_window: int = 30,
    today: date | None = None,
) -> list[RenewalAlert]:
    """Identify subscriptions renewing within the given day window."""
    if today is None:
        today = date.today()

    alerts: list[RenewalAlert] = []

    for subscription in subscriptions:
        if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
            continue

        if not subscription.next_renewal_date:
            continue

        try:
            renewal_dt = datetime.strptime(subscription.next_renewal_date, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_until = (renewal_dt - today).days

        # Include renewals within the window, or overdue renewals
        if days_until <= days_window:
            cancel_by_dt = renewal_dt - timedelta(days=subscription.cancellation_notice_days)

            if days_until < 0:
                urgency = "PAST_DUE"
            elif days_until <= 3:
                urgency = "CRITICAL"
            elif days_until <= 7:
                urgency = "WARNING"
            else:
                urgency = "UPCOMING"

            alerts.append(
                RenewalAlert(
                    subscription_id=subscription.id,
                    subscription_name=subscription.name,
                    renewal_date=subscription.next_renewal_date,
                    days_until_renewal=days_until,
                    cancel_by_date=cancel_by_dt.isoformat(),
                    amount=subscription.current_price,
                    currency=subscription.currency,
                    urgency=urgency,
                    is_trial=(subscription.status == SubscriptionStatus.TRIAL),
                )
            )

    alerts.sort(key=lambda alert: alert.days_until_renewal)
    return alerts


def detect_redundancies(subscriptions: list[Subscription]) -> list[RedundancyCluster]:
    """Detect overlapping subscriptions in the same functional category."""
    active_subs = [
        s
        for s in subscriptions
        if s.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL)
    ]

    by_category: dict[Category, list[Subscription]] = {}
    for sub in active_subs:
        by_category.setdefault(sub.category, []).append(sub)

    clusters: list[RedundancyCluster] = []

    category_recommendations: dict[Category, str] = {
        Category.ENTERTAINMENT: (
            "Rotate streaming platforms monthly rather than keeping multiple active simultaneously."
        ),
        Category.AI_ML: (
            "Evaluate multi-model consolidation. Benchmark single API vs multiple chat tiers."
        ),
        Category.DEVELOPER_CLOUD: (
            "Audit unused developer instances, staging environments, or duplicate hosting tiers."
        ),
        Category.PRODUCTIVITY: (
            "Check for duplicate note-taking, project management, or cloud storage tiers."
        ),
        Category.SECURITY: (
            "Verify whether duplicate password managers or VPNs are active across multiple tiers."
        ),
        Category.NEWS_MEDIA: (
            "Consolidate news publications or look into digital aggregator passes."
        ),
    }

    for category, subs in by_category.items():
        if len(subs) >= 2:
            total_annual = round(sum(s.annual_cost for s in subs), 2)
            names = [s.name for s in subs]
            sub_ids = [s.id for s in subs]
            rec = category_recommendations.get(
                category,
                f"Consolidate multiple {category.value} subscriptions to reduce annual overhead.",
            )
            clusters.append(
                RedundancyCluster(
                    category=category,
                    subscription_ids=sub_ids,
                    subscription_names=names,
                    total_annual_cost=total_annual,
                    recommendation=rec,
                )
            )

    clusters.sort(key=lambda cluster: cluster.total_annual_cost, reverse=True)
    return clusters


def detect_zombies(subscriptions: list[Subscription]) -> list[ZombieSubscription]:
    """Detect low-usage or dormant subscriptions draining cash flow."""
    zombies: list[ZombieSubscription] = []

    for sub in subscriptions:
        if sub.status == SubscriptionStatus.ACTIVE and sub.usage_rating <= 2:
            rec = (
                f"Usage rating is {sub.usage_rating}/5. "
                f"Cancel or pause to recover ${sub.annual_cost:.2f}/yr."
            )
            zombies.append(
                ZombieSubscription(
                    subscription_id=sub.id,
                    subscription_name=sub.name,
                    usage_rating=sub.usage_rating,
                    annual_cost=sub.annual_cost,
                    recommendation=rec,
                )
            )

    zombies.sort(key=lambda zombie: zombie.annual_cost, reverse=True)
    return zombies


def generate_audit_summary(
    subscriptions: list[Subscription],
    today: date | None = None,
) -> AuditSummary:
    """Generate a comprehensive audit of all subscriptions."""
    if today is None:
        today = date.today()

    active_subs = [
        s
        for s in subscriptions
        if s.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL)
    ]

    total_monthly = sum(sub.monthly_cost for sub in active_subs)
    total_annual = sum(sub.annual_cost for sub in active_subs)

    # Category breakdown
    breakdown: dict[str, float] = {}
    for sub in active_subs:
        cat_name = sub.category.value
        breakdown[cat_name] = round(breakdown.get(cat_name, 0.0) + sub.annual_cost, 2)

    # Price creep alerts
    creep_alerts: list[CreepReport] = []
    for sub in active_subs:
        report = analyze_price_creep(sub)
        if report and report.absolute_increase > 0:
            creep_alerts.append(report)

    creep_alerts.sort(key=lambda report: report.annualized_dollar_impact, reverse=True)

    # Renewals
    upcoming_renewals = get_upcoming_renewals(subscriptions, days_window=30, today=today)

    # Redundancies
    redundancies = detect_redundancies(subscriptions)

    # Zombies
    zombies = detect_zombies(subscriptions)

    # Estimated potential annual savings
    zombie_savings = sum(z.annual_cost for z in zombies)
    redundancy_savings = 0.0
    for cluster in redundancies:
        if len(cluster.subscription_names) > 1:
            redundancy_savings += cluster.total_annual_cost * 0.40

    creep_savings = sum(c.annualized_dollar_impact for c in creep_alerts)
    potential_savings = zombie_savings + (redundancy_savings * 0.5) + creep_savings

    return AuditSummary(
        total_active_subscriptions=len(active_subs),
        total_monthly_spend=round(total_monthly, 2),
        total_annual_spend=round(total_annual, 2),
        category_breakdown=breakdown,
        creep_alerts=creep_alerts,
        upcoming_renewals=upcoming_renewals,
        redundancies=redundancies,
        zombie_subscriptions=zombies,
        potential_annual_savings=round(potential_savings, 2),
    )


def generate_cancellation_brief(subscription: Subscription) -> str:
    """Generate an actionable cancellation playbook for a subscription."""
    rate_str = f"${subscription.current_price:.2f} / {subscription.billing_cycle.value}"
    buf_days = subscription.cancellation_notice_days
    lines = [
        f"# 🛑 Cancellation Playbook: {subscription.name}",
        f"- **Vendor / Service:** {subscription.vendor}",
        f"- **Category:** {subscription.category.value.title()}",
        f"- **Current Rate:** {rate_str}",
        f"- **Annual Run-Rate:** ${subscription.annual_cost:.2f}/yr",
        f"- **Next Auto-Renewal:** {subscription.next_renewal_date or 'Not Set'}",
        f"- **Required Cancellation Buffer:** {buf_days} days before billing",
        f"- **Payment Method On File:** {subscription.payment_method or 'Unknown'}",
        "",
        "## 📋 Recommended Action Steps:",
        "1. **Log in to Account Portal:** Go to Account Settings → Subscriptions.",
        "2. **Check for Proration:** Inquire if unspent balance is refundable.",
        "3. **Decline Retention Offers:** Note if discounts or pause options appear.",
        "4. **Export Your Data:** Download invoices and data backups first.",
        "5. **Revoke Payment Authorization:** Lock virtual card token if desired.",
        f"6. **Mark as Cancelled:** `subwatch update {subscription.id} --status cancelled`",
    ]
    return "\n".join(lines)


def generate_negotiation_script(subscription: Subscription) -> str:
    """Generate a proven SaaS retention negotiation script."""
    creep = analyze_price_creep(subscription)
    price_context = f"${subscription.current_price:.2f}/{subscription.billing_cycle.value}"
    if creep and creep.absolute_increase > 0:
        price_context += f" (increased from initial ${creep.initial_price:.2f})"

    start = subscription.start_date or "several cycles"
    lines = [
        f"# 💬 Retention Negotiation Script: {subscription.name}",
        f"**Target Service:** {subscription.vendor} ({price_context})",
        f"**Current Annual Cost:** ${subscription.annual_cost:.2f}/yr",
        "",
        "### 📞 Chat / Support Phone Script:",
        "---",
        f'"Hi there, I have been a customer of {subscription.vendor} since {start}. '
        "I am conducting a quarterly audit of my recurring software and service expenses.",
        "",
        f"I noticed my rate is currently {price_context}. Given budget adjustments, "
        "I am considering pausing or cancelling my account unless there are promotional rates, "
        "loyalty credits, or retention discounts available to match my target budget.",
        "",
        "Could you please review my account to see what grandfathered pricing or renewal "
        'promotions can be applied to keep my subscription active?"',
        "---",
        "",
        "### 🎯 Negotiation Playbook Tips:",
        "- **Best Timing:** Contact support 5–10 days before your `next_renewal_date`.",
        "- **Target Discount:** Aim for 20%–40% off annual rate, or 2–3 months free credits.",
        "- **Acceptable Fallback:** Request a downgrade to a cheaper tier or a 3-month pause.",
    ]
    return "\n".join(lines)


def parse_transaction_csv(csv_text: str) -> list[dict[str, Any]]:
    """Parse CSV export from standard bank statements and detect candidate subscriptions."""
    reader = csv.reader(io.StringIO(csv_text.strip()))
    header = None
    candidates: list[dict[str, Any]] = []

    for row in reader:
        if not row or not any(row):
            continue

        if header is None:
            header = [col.lower().strip() for col in row]
            continue

        row_dict = dict(zip(header, row, strict=False))

        desc = ""
        for key in ("description", "merchant", "payee", "name", "transaction", "memo"):
            if key in row_dict and row_dict[key]:
                desc = row_dict[key]
                break

        amount_val = 0.0
        for key in ("amount", "debit", "total", "charge"):
            if key in row_dict and row_dict[key]:
                raw_amt = row_dict[key].replace("$", "").replace(",", "").replace("-", "").strip()
                try:
                    amount_val = float(raw_amt)
                    break
                except ValueError:
                    continue

        date_str = ""
        for key in ("date", "transaction date", "post date", "posting date"):
            if key in row_dict and row_dict[key]:
                date_str = row_dict[key].strip()
                break

        if not desc or amount_val <= 0:
            continue

        desc_lower = desc.lower()
        matched_vendor = None
        matched_category = Category.OTHER

        for keyword, (vendor_name, category) in KNOWN_VENDORS.items():
            if keyword in desc_lower:
                matched_vendor = vendor_name
                matched_category = category
                break

        if matched_vendor:
            candidates.append(
                {
                    "vendor": matched_vendor,
                    "raw_description": desc,
                    "amount": round(amount_val, 2),
                    "date": date_str,
                    "category": matched_category.value,
                    "inferred_cycle": "monthly",
                }
            )

    return candidates
