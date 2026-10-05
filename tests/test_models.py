"""Tests for subwatch domain models."""

from subwatch.models import (
    AuditSummary,
    BillingCycle,
    Category,
    ChargeRecord,
    CreepReport,
    RedundancyCluster,
    RenewalAlert,
    Subscription,
    SubscriptionStatus,
    ZombieSubscription,
)


def test_billing_cycle_multipliers():
    assert BillingCycle.MONTHLY.multiplier_to_annual == 12.0
    assert BillingCycle.MONTHLY.multiplier_to_monthly == 1.0
    assert BillingCycle.ANNUAL.multiplier_to_annual == 1.0
    assert round(BillingCycle.ANNUAL.multiplier_to_monthly, 4) == round(1.0 / 12.0, 4)
    assert BillingCycle.QUARTERLY.multiplier_to_annual == 4.0
    assert BillingCycle.SEMI_ANNUAL.multiplier_to_annual == 2.0
    assert BillingCycle.WEEKLY.multiplier_to_annual == 52.0
    assert BillingCycle.BI_WEEKLY.multiplier_to_annual == 26.0


def test_charge_record_serialization():
    rec = ChargeRecord(
        id="ch1",
        subscription_id="sub1",
        amount=19.99,
        date="2026-01-15",
        payment_method="Visa 4242",
        notes="Monthly charge",
    )
    d = rec.to_dict()
    assert d["id"] == "ch1"
    assert d["amount"] == 19.99

    rec2 = ChargeRecord.from_dict(d)
    assert rec2.id == "ch1"
    assert rec2.amount == 19.99
    assert rec2.payment_method == "Visa 4242"


def test_subscription_annual_and_monthly_cost():
    sub = Subscription(
        id="sub1",
        name="GitHub Copilot",
        vendor="GitHub",
        category=Category.DEVELOPER_CLOUD,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=10.0,
    )
    assert sub.annual_cost == 120.0
    assert sub.monthly_cost == 10.0

    sub_annual = Subscription(
        id="sub2",
        name="1Password Family",
        vendor="1Password",
        category=Category.SECURITY,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.ANNUAL,
        current_price=59.88,
    )
    assert sub_annual.annual_cost == 59.88
    assert sub_annual.monthly_cost == 4.99


def test_subscription_serialization():
    sub = Subscription(
        id="sub1",
        name="Netflix",
        vendor="Netflix",
        category=Category.ENTERTAINMENT,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=22.99,
        charge_history=[
            ChargeRecord(id="c1", subscription_id="sub1", amount=19.99, date="2025-01-01"),
            ChargeRecord(id="c2", subscription_id="sub1", amount=22.99, date="2026-01-01"),
        ],
    )
    d = sub.to_dict()
    assert d["category"] == "entertainment"
    assert d["status"] == "active"
    assert len(d["charge_history"]) == 2

    restored = Subscription.from_dict(d)
    assert restored.id == "sub1"
    assert restored.name == "Netflix"
    assert restored.category == Category.ENTERTAINMENT
    assert len(restored.charge_history) == 2
    assert restored.charge_history[0].amount == 19.99


def test_reports_serialization():
    creep = CreepReport(
        subscription_id="sub1",
        subscription_name="Netflix",
        initial_price=19.99,
        current_price=22.99,
        absolute_increase=3.00,
        percent_increase=15.01,
        annualized_dollar_impact=36.00,
        first_charge_date="2025-01-01",
        latest_charge_date="2026-01-01",
        is_stealth_creep=True,
    )
    assert creep.to_dict()["is_stealth_creep"] is True

    alert = RenewalAlert(
        subscription_id="sub1",
        subscription_name="Netflix",
        renewal_date="2026-10-15",
        days_until_renewal=10,
        cancel_by_date="2026-10-12",
        amount=22.99,
        currency="USD",
        urgency="UPCOMING",
        is_trial=False,
    )
    assert alert.to_dict()["days_until_renewal"] == 10

    cluster = RedundancyCluster(
        category=Category.ENTERTAINMENT,
        subscription_ids=["sub1", "sub2"],
        subscription_names=["Netflix", "Max"],
        total_annual_cost=400.0,
        recommendation="Rotate monthly",
    )
    assert cluster.to_dict()["category"] == "entertainment"

    zombie = ZombieSubscription(
        subscription_id="sub3",
        subscription_name="Dormant Gym",
        usage_rating=1,
        annual_cost=600.0,
        recommendation="Cancel immediately",
    )
    assert zombie.to_dict()["usage_rating"] == 1

    summary = AuditSummary(
        total_active_subscriptions=1,
        total_monthly_spend=22.99,
        total_annual_spend=275.88,
        category_breakdown={"entertainment": 275.88},
        creep_alerts=[creep],
        upcoming_renewals=[alert],
        redundancies=[cluster],
        zombie_subscriptions=[zombie],
        potential_annual_savings=636.0,
    )
    sum_dict = summary.to_dict()
    assert sum_dict["total_active_subscriptions"] == 1
    assert len(sum_dict["creep_alerts"]) == 1
