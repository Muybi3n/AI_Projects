"""Tests for subwatch core engine."""

from datetime import date

from subwatch.engine import (
    analyze_price_creep,
    detect_redundancies,
    detect_zombies,
    generate_audit_summary,
    generate_cancellation_brief,
    generate_negotiation_script,
    get_upcoming_renewals,
    parse_transaction_csv,
)
from subwatch.models import (
    BillingCycle,
    Category,
    ChargeRecord,
    Subscription,
    SubscriptionStatus,
)


def test_analyze_price_creep():
    sub = Subscription(
        id="s1",
        name="ChatGPT Plus",
        vendor="OpenAI",
        category=Category.AI_ML,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=24.00,
        charge_history=[
            ChargeRecord(id="c1", subscription_id="s1", amount=20.00, date="2024-01-01"),
            ChargeRecord(id="c2", subscription_id="s1", amount=20.00, date="2024-06-01"),
            ChargeRecord(id="c3", subscription_id="s1", amount=24.00, date="2025-01-01"),
        ],
    )
    report = analyze_price_creep(sub)
    assert report is not None
    assert report.initial_price == 20.00
    assert report.current_price == 24.00
    assert report.absolute_increase == 4.00
    assert report.percent_increase == 20.0
    assert report.annualized_dollar_impact == 48.00
    assert report.is_stealth_creep is True


def test_analyze_price_creep_no_history():
    sub = Subscription(
        id="s2",
        name="Zero History",
        vendor="Vendor",
        category=Category.OTHER,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=15.00,
    )
    assert analyze_price_creep(sub) is None


def test_get_upcoming_renewals():
    ref_date = date(2026, 10, 5)
    subs = [
        Subscription(
            id="s1",
            name="Critical Sub",
            vendor="V1",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=10.0,
            next_renewal_date="2026-10-07",
            cancellation_notice_days=2,
        ),
        Subscription(
            id="s2",
            name="Warning Sub",
            vendor="V2",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.TRIAL,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=15.0,
            next_renewal_date="2026-10-11",
            cancellation_notice_days=3,
        ),
        Subscription(
            id="s3",
            name="Upcoming Sub",
            vendor="V3",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=5.0,
            next_renewal_date="2026-10-25",
            cancellation_notice_days=3,
        ),
        Subscription(
            id="s4",
            name="Past Due Sub",
            vendor="V4",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=8.0,
            next_renewal_date="2026-10-01",
            cancellation_notice_days=1,
        ),
        Subscription(
            id="s5",
            name="Far Future Sub",
            vendor="V5",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.ANNUAL,
            current_price=100.0,
            next_renewal_date="2027-01-01",
        ),
        Subscription(
            id="s6",
            name="Cancelled Sub",
            vendor="V6",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.CANCELLED,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=10.0,
            next_renewal_date="2026-10-08",
        ),
    ]

    alerts = get_upcoming_renewals(subs, days_window=30, today=ref_date)
    assert len(alerts) == 4
    assert alerts[0].urgency == "PAST_DUE"
    assert alerts[1].urgency == "CRITICAL"
    assert alerts[2].urgency == "WARNING"
    assert alerts[2].is_trial is True
    assert alerts[3].urgency == "UPCOMING"


def test_detect_redundancies():
    subs = [
        Subscription(
            id="s1",
            name="Netflix",
            vendor="Netflix",
            category=Category.ENTERTAINMENT,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=22.99,
        ),
        Subscription(
            id="s2",
            name="Disney+",
            vendor="Disney",
            category=Category.ENTERTAINMENT,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=13.99,
        ),
        Subscription(
            id="s3",
            name="1Password",
            vendor="1Password",
            category=Category.SECURITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.ANNUAL,
            current_price=36.00,
        ),
    ]
    clusters = detect_redundancies(subs)
    assert len(clusters) == 1
    assert clusters[0].category == Category.ENTERTAINMENT
    assert len(clusters[0].subscription_names) == 2


def test_detect_zombies():
    subs = [
        Subscription(
            id="s1",
            name="Rarely Used App",
            vendor="App",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=15.00,
            usage_rating=1,
        ),
        Subscription(
            id="s2",
            name="Core Daily Tool",
            vendor="Core",
            category=Category.PRODUCTIVITY,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=20.00,
            usage_rating=5,
        ),
    ]
    zombies = detect_zombies(subs)
    assert len(zombies) == 1
    assert zombies[0].subscription_id == "s1"
    assert zombies[0].annual_cost == 180.00


def test_generate_audit_summary():
    ref_date = date(2026, 10, 5)
    subs = [
        Subscription(
            id="s1",
            name="Netflix",
            vendor="Netflix",
            category=Category.ENTERTAINMENT,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=22.99,
            next_renewal_date="2026-10-10",
            charge_history=[
                ChargeRecord(id="c1", subscription_id="s1", amount=19.99, date="2025-01-01"),
                ChargeRecord(id="c2", subscription_id="s1", amount=22.99, date="2026-01-01"),
            ],
            usage_rating=4,
        ),
        Subscription(
            id="s2",
            name="Dormant Magazine",
            vendor="Mag",
            category=Category.NEWS_MEDIA,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=10.00,
            usage_rating=1,
        ),
    ]
    summary = generate_audit_summary(subs, today=ref_date)
    assert summary.total_active_subscriptions == 2
    assert summary.total_monthly_spend == 32.99
    assert len(summary.creep_alerts) == 1
    assert len(summary.zombie_subscriptions) == 1
    assert summary.potential_annual_savings > 0


def test_cancellation_and_negotiation_briefs():
    sub = Subscription(
        id="s1",
        name="Cloudflare Pro",
        vendor="Cloudflare",
        category=Category.SECURITY,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=25.00,
        start_date="2024-01-01",
        next_renewal_date="2026-11-01",
        charge_history=[
            ChargeRecord(id="c1", subscription_id="s1", amount=20.00, date="2024-01-01"),
            ChargeRecord(id="c2", subscription_id="s1", amount=25.00, date="2025-01-01"),
        ],
    )
    cancel_brief = generate_cancellation_brief(sub)
    assert "Cancellation Playbook: Cloudflare Pro" in cancel_brief
    assert "$25.00 / monthly" in cancel_brief

    neg_script = generate_negotiation_script(sub)
    assert "Retention Negotiation Script: Cloudflare Pro" in neg_script
    assert "Cloudflare" in neg_script
    assert "increased from initial $20.00" in neg_script


def test_parse_transaction_csv():
    csv_sample = """Date,Description,Amount,Category
2026-09-01,NETFLIX.COM PAYMENT,$22.99,Entertainment
2026-09-02,GITHUB SPONSORS,$10.00,Software
2026-09-03,OPENAI *CHATGPT SUBSCR,$20.00,Online Services
2026-09-04,LOCAL GROCERY STORE,$145.20,Food & Dining
"""
    candidates = parse_transaction_csv(csv_sample)
    assert len(candidates) == 3
    vendors = [c["vendor"] for c in candidates]
    assert "Netflix" in vendors
    assert "GitHub" in vendors
    assert "OpenAI ChatGPT" in vendors
