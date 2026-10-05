"""Tests for subwatch AI advisor and deterministic heuristic engine."""

from subwatch.advisor import ask_advisor, heuristic_subscription_advisor, sanitize_pii
from subwatch.models import (
    BillingCycle,
    Category,
    ChargeRecord,
    Subscription,
    SubscriptionStatus,
)


def test_sanitize_pii():
    text = "Payment on Visa 4111 2222 3333 4444 and CVV: 123"
    sanitized = sanitize_pii(text)
    assert "[CARD_REDACTED]" in sanitized
    assert "CVV:[REDACTED]" in sanitized


def test_advisor_price_creep_queries():
    sub_creep = Subscription(
        id="s1",
        name="Netflix",
        vendor="Netflix",
        category=Category.ENTERTAINMENT,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=22.99,
        charge_history=[
            ChargeRecord(id="c1", subscription_id="s1", amount=19.99, date="2025-01-01"),
            ChargeRecord(id="c2", subscription_id="s1", amount=22.99, date="2026-01-01"),
        ],
    )
    ans = heuristic_subscription_advisor(
        "Are any of my subscriptions creeping in price?", [sub_creep]
    )
    assert "Price Creep & Stealth Inflation Alert" in ans
    assert "Netflix" in ans
    assert "+15.01%" in ans

    sub_no_creep = Subscription(
        id="s2",
        name="Spotify",
        vendor="Spotify",
        category=Category.ENTERTAINMENT,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=10.99,
        charge_history=[
            ChargeRecord(id="c1", subscription_id="s2", amount=10.99, date="2025-01-01"),
        ],
    )
    ans2 = heuristic_subscription_advisor("Did my subscriptions increase?", [sub_no_creep])
    assert "No active price creep detected" in ans2


def test_advisor_renewal_queries():
    sub_renewal = Subscription(
        id="s1",
        name="Domain Renewal",
        vendor="Cloudflare",
        category=Category.DEVELOPER_CLOUD,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.ANNUAL,
        current_price=9.77,
        next_renewal_date="2026-10-15",
        cancellation_notice_days=3,
    )
    ans = heuristic_subscription_advisor("What renewals are due next week?", [sub_renewal])
    assert "Upcoming Renewal Radar" in ans
    assert "Domain Renewal" in ans

    ans_empty = heuristic_subscription_advisor("What renewals are due?", [])
    assert "No subscriptions due for renewal" in ans_empty


def test_advisor_savings_and_zombie_queries():
    sub_zombie = Subscription(
        id="s1",
        name="Unused Fitness App",
        vendor="Gym",
        category=Category.HEALTH_FITNESS,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=29.99,
        usage_rating=1,
    )
    sub_redundant1 = Subscription(
        id="s2",
        name="Streaming A",
        vendor="A",
        category=Category.ENTERTAINMENT,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=15.00,
    )
    sub_redundant2 = Subscription(
        id="s3",
        name="Streaming B",
        vendor="B",
        category=Category.ENTERTAINMENT,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=15.00,
    )
    sub_creep = Subscription(
        id="s4",
        name="Creeping Tool",
        vendor="Tool",
        category=Category.PRODUCTIVITY,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=25.00,
        charge_history=[
            ChargeRecord(id="c1", subscription_id="s4", amount=20.00, date="2025-01-01"),
            ChargeRecord(id="c2", subscription_id="s4", amount=25.00, date="2026-01-01"),
        ],
    )
    ans = heuristic_subscription_advisor(
        "How can I cut my budget and save money?",
        [sub_zombie, sub_redundant1, sub_redundant2, sub_creep],
    )
    assert "Subscription Cost Optimization & Savings Blueprint" in ans
    assert "Unused Fitness App" in ans
    assert "Category Redundancy Consolidation" in ans
    assert "Negotiate Grandfathered" in ans


def test_advisor_category_query():
    sub_cloud = Subscription(
        id="s1",
        name="AWS Staging",
        vendor="Amazon",
        category=Category.DEVELOPER_CLOUD,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=45.00,
    )
    ans = heuristic_subscription_advisor("How much am I spending on cloud?", [sub_cloud])
    assert "Category Deep-Dive: Developer Cloud" in ans
    assert "$540.00/yr" in ans


def test_advisor_general_overview():
    sub = Subscription(
        id="s1",
        name="1Password",
        vendor="1Password",
        category=Category.SECURITY,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.ANNUAL,
        current_price=35.88,
    )
    ans = heuristic_subscription_advisor("Give me a general overview", [sub])
    assert "SubWatch Portfolio Intelligence Summary" in ans
    assert "Active Subscriptions" in ans


def test_ask_advisor_with_custom_llm():
    sub = Subscription(
        id="s1",
        name="ChatGPT",
        vendor="OpenAI",
        category=Category.AI_ML,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=20.00,
    )

    def mock_llm(prompt: str) -> str:
        return "LLM Analysis: Consider sharing team seat."

    response = ask_advisor("Should I keep ChatGPT?", [sub], custom_llm=mock_llm)
    assert "LLM Analysis: Consider sharing team seat." in response

    # Fallback on LLM failure
    def failing_llm(prompt: str) -> str:
        raise RuntimeError("API Timeout")

    response_fallback = ask_advisor("General summary", [sub], custom_llm=failing_llm)
    assert "SubWatch Portfolio Intelligence Summary" in response_fallback
