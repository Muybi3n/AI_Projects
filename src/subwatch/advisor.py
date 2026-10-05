"""Deterministic heuristic advisor and pluggable LLM interface for subwatch."""

from __future__ import annotations

import re
from collections.abc import Callable

from subwatch.engine import generate_audit_summary
from subwatch.models import AuditSummary, Category, Subscription

CATEGORY_SYNONYMS: dict[Category, tuple[str, ...]] = {
    Category.DEVELOPER_CLOUD: (
        "cloud",
        "dev",
        "developer",
        "aws",
        "hosting",
        "developer_cloud",
        "servers",
    ),
    Category.ENTERTAINMENT: ("entertainment", "streaming", "movies", "tv", "music", "video"),
    Category.AI_ML: ("ai", "ml", "llm", "chatgpt", "claude", "ai_ml", "openai", "copilot"),
    Category.SECURITY: ("security", "vpn", "password", "auth", "1password", "bitwarden"),
    Category.PRODUCTIVITY: (
        "productivity",
        "notes",
        "office",
        "workspace",
        "storage",
        "notion",
        "drive",
    ),
    Category.HEALTH_FITNESS: ("health", "fitness", "gym", "workout", "strava", "whoop"),
    Category.NEWS_MEDIA: ("news", "media", "journal", "magazine", "newspaper", "wsj", "nyt"),
    Category.UTILITIES: ("utilities", "utility", "phone", "internet", "cell"),
}


def sanitize_pii(text: str) -> str:
    """Sanitize payment card numbers and private financial tokens from text."""
    # Mask 13-19 digit card numbers
    sanitized = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[CARD_REDACTED]", text)
    # Mask card expiration or CVV tokens
    sanitized = re.sub(
        r"\b(?:CVV|CVC)\s*[:=]?\s*\d{3,4}\b",
        "CVV:[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def heuristic_subscription_advisor(
    query: str,
    subscriptions: list[Subscription],
    summary: AuditSummary | None = None,
) -> str:
    """Deterministic, local-first rule engine for answering subscription questions."""
    if summary is None:
        summary = generate_audit_summary(subscriptions)

    query_lower = query.lower()

    # 1. Price Creep & Inflation
    creep_keywords = ("creep", "inflation", "increase", "price hike", "more expensive", "hike")
    if any(k in query_lower for k in creep_keywords):
        if not summary.creep_alerts:
            return (
                "📈 **Price Creep Audit**: No active price creep detected across your "
                f"{summary.total_active_subscriptions} tracked subscriptions. "
                "All services remain at their initial recorded pricing."
            )
        total_impact = sum(c.annualized_dollar_impact for c in summary.creep_alerts)
        lines = [
            f"📈 **Price Creep & Stealth Inflation Alert** ({len(summary.creep_alerts)} services):",
            f"- **Cumulative Annual Impact:** +${total_impact:.2f}/yr",
            "",
        ]
        for alert in summary.creep_alerts:
            lines.append(
                f"- **{alert.subscription_name}**: Initial ${alert.initial_price:.2f} ➔ "
                f"Now ${alert.current_price:.2f} (+{alert.percent_increase}% | "
                f"+${alert.annualized_dollar_impact:.2f}/yr) "
                f"[{alert.first_charge_date} to {alert.latest_charge_date}]"
            )
        lines.append(
            "\n💡 **Action:** Run `subwatch brief <name>` to generate a negotiation script."
        )
        return "\n".join(lines)

    # 2. Upcoming Renewals & Trials
    renewal_keywords = ("renewal", "renew", "upcoming", "due", "cancel by", "trial")
    if any(k in query_lower for k in renewal_keywords):
        if not summary.upcoming_renewals:
            return "📅 **Renewal Radar**: No subscriptions due for renewal within 30 days."
        lines = [
            f"📅 **Upcoming Renewal Radar** ({len(summary.upcoming_renewals)} due soon):",
            "",
        ]
        for item in summary.upcoming_renewals:
            tag = " ⚠️ TRIAL" if item.is_trial else ""
            lines.append(
                f"- **{item.subscription_name}**{tag}: Due in **{item.days_until_renewal} days** "
                f"({item.renewal_date}) for ${item.amount:.2f} {item.currency} "
                f"[Cancel by: {item.cancel_by_date} | Urgency: {item.urgency}]"
            )
        return "\n".join(lines)

    # 3. Savings / Cutting Costs / Budget / Zombies / Redundancy
    savings_keywords = ("save", "cut", "reduce", "budget", "zombie", "redundant", "waste")
    if any(k in query_lower for k in savings_keywords):
        lines = [
            "💰 **Subscription Cost Optimization & Savings Blueprint**",
            f"- **Current Annual Run-Rate:** ${summary.total_annual_spend:.2f}/yr "
            f"(${summary.total_monthly_spend:.2f}/mo)",
            f"- **Potential Actionable Savings:** **${summary.potential_annual_savings:.2f}/yr**",
            "",
        ]

        if summary.zombie_subscriptions:
            lines.append("🛑 **1. Low-Usage / Zombie Subscriptions (Immediate Cuts):**")
            for z in summary.zombie_subscriptions:
                lines.append(
                    f"  • **{z.subscription_name}**: Usage {z.usage_rating}/5 "
                    f"— saves ${z.annual_cost:.2f}/yr"
                )
            lines.append("")

        if summary.redundancies:
            lines.append("🔄 **2. Category Redundancy Consolidation:**")
            for red in summary.redundancies:
                names = ", ".join(red.subscription_names)
                lines.append(
                    f"  • **{red.category.value.title()}** ({names}): "
                    f"${red.total_annual_cost:.2f}/yr total. {red.recommendation}"
                )
            lines.append("")

        if summary.creep_alerts:
            lines.append("📈 **3. Negotiate Grandfathered / Creeping Rates:**")
            for c in summary.creep_alerts:
                lines.append(
                    f"  • **{c.subscription_name}**: Increased by +{c.percent_increase}% "
                    f"(+${c.annualized_dollar_impact:.2f}/yr)"
                )

        return "\n".join(lines)

    # 4. Specific Category queries (Cloud, Entertainment, AI, Security, etc.)
    for category_enum, synonyms in CATEGORY_SYNONYMS.items():
        cat_val = category_enum.value
        if any(syn in query_lower for syn in synonyms):
            matched_subs = [s for s in subscriptions if s.category == category_enum]
            cat_total = summary.category_breakdown.get(cat_val, 0.0)
            lines = [
                f"🏷️ **Category Deep-Dive: {cat_val.replace('_', ' ').title()}**",
                f"- **Total Annual Spend:** ${cat_total:.2f}/yr",
                f"- **Active Services:** {len(matched_subs)}",
                "",
            ]
            for s in matched_subs:
                lines.append(
                    f"- **{s.name}**: ${s.current_price:.2f}/{s.billing_cycle.value} "
                    f"(${s.annual_cost:.2f}/yr)"
                )
            return "\n".join(lines)

    # Default: General Portfolio Diagnostic
    lines = [
        "📊 **SubWatch Portfolio Intelligence Summary**",
        f"- **Active Subscriptions:** {summary.total_active_subscriptions}",
        f"- **Total Monthly Spend:** ${summary.total_monthly_spend:.2f}/mo",
        f"- **Total Annual Run-Rate:** ${summary.total_annual_spend:.2f}/yr",
        f"- **Identified Savings Potential:** ${summary.potential_annual_savings:.2f}/yr",
        "",
        "### 🔍 Key Diagnostic Insights:",
    ]

    if summary.creep_alerts:
        creep_total = sum(c.annualized_dollar_impact for c in summary.creep_alerts)
        lines.append(
            f"• 📈 **Price Creep:** {len(summary.creep_alerts)} services increased pricing "
            f"(+${creep_total:.2f}/yr impact)."
        )
    else:
        lines.append("• 📈 **Price Creep:** No unannounced price increases detected.")

    if summary.zombie_subscriptions:
        zombie_total = sum(z.annual_cost for z in summary.zombie_subscriptions)
        lines.append(
            f"• 🛑 **Zombie Subscriptions:** {len(summary.zombie_subscriptions)} low-usage "
            f"services wasting ${zombie_total:.2f}/yr."
        )

    if summary.redundancies:
        lines.append(
            f"• 🔄 **Redundancy Clusters:** {len(summary.redundancies)} overlapping categories."
        )

    if summary.upcoming_renewals:
        lines.append(
            f"• 📅 **Upcoming Renewals:** {len(summary.upcoming_renewals)} renewals due in 30 days."
        )

    lines.append(
        "\nRun `subwatch audit` for a detailed matrix or `subwatch brief <service>` for scripts."
    )
    return "\n".join(lines)


def ask_advisor(
    query: str,
    subscriptions: list[Subscription],
    custom_llm: Callable[[str], str] | None = None,
) -> str:
    """Entry point for querying the subscription advisor with optional custom LLM fallback."""
    summary = generate_audit_summary(subscriptions)

    if custom_llm is not None:
        context_lines = [
            f"Active Subscriptions: {summary.total_active_subscriptions}",
            f"Monthly Spend: ${summary.total_monthly_spend:.2f}",
            f"Annual Spend: ${summary.total_annual_spend:.2f}",
            f"Potential Savings: ${summary.potential_annual_savings:.2f}",
            "Subscriptions:",
        ]
        for s in subscriptions:
            context_lines.append(
                f"- {s.name} ({s.category.value}): ${s.current_price}/{s.billing_cycle.value}, "
                f"usage rating {s.usage_rating}/5, status {s.status.value}"
            )

        context_prompt = (
            "You are SubWatch AI, an expert SaaS and subscription auditor. Provide a concise, "
            "actionable, and professional recommendation to optimize recurring expenses.\n\n"
            + "\n".join(context_lines)
            + f"\n\nUser Question: {sanitize_pii(query)}"
        )

        try:
            response = custom_llm(context_prompt)
            if response and response.strip():
                return response.strip()
        except (RuntimeError, ValueError, TypeError, KeyError):
            pass

    return heuristic_subscription_advisor(query, subscriptions, summary)
