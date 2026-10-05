"""Tests for subwatch storage manager."""

from subwatch.models import BillingCycle, Category, Subscription, SubscriptionStatus
from subwatch.storage import StorageManager


def test_storage_crud(tmp_path):
    storage = StorageManager(data_dir=tmp_path)
    assert storage.load_all() == []

    sub = Subscription(
        id="sub123",
        name="GitHub Copilot",
        vendor="GitHub",
        category=Category.DEVELOPER_CLOUD,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=10.0,
    )
    storage.add_subscription(sub)

    loaded = storage.load_all()
    assert len(loaded) == 1
    assert loaded[0].name == "GitHub Copilot"

    # Get by ID and by Name
    assert storage.get_subscription("sub123") is not None
    assert storage.get_subscription("github copilot") is not None
    assert storage.get_subscription("nonexistent") is None

    # Update
    updated = storage.update_subscription("sub123", {"current_price": 12.0, "usage_rating": 5})
    assert updated is not None
    assert updated.current_price == 12.0
    assert updated.usage_rating == 5
    assert storage.update_subscription("invalid", {"current_price": 10.0}) is None

    # Log charge
    rec = storage.log_charge("sub123", amount=12.0, date_str="2026-10-01", notes="October renewal")
    assert rec is not None
    assert rec.amount == 12.0
    assert storage.log_charge("invalid", amount=10.0, date_str="2026-10-01") is None

    # List with filter
    active_subs = storage.list_subscriptions(status_filter=SubscriptionStatus.ACTIVE)
    assert len(active_subs) == 1
    paused_subs = storage.list_subscriptions(status_filter=SubscriptionStatus.PAUSED)
    assert len(paused_subs) == 0

    # Remove
    assert storage.remove_subscription("sub123") is True
    assert storage.remove_subscription("sub123") is False
    assert len(storage.load_all()) == 0

    # Clear
    storage.add_subscription(sub)
    assert len(storage.load_all()) == 1
    storage.clear()
    assert len(storage.load_all()) == 0


def test_storage_auto_id(tmp_path):
    storage = StorageManager(data_dir=tmp_path)
    sub = Subscription(
        id="",
        name="Auto ID Sub",
        vendor="Auto",
        category=Category.OTHER,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=5.0,
    )
    added = storage.add_subscription(sub)
    assert added.id != ""
    assert len(storage.load_all()) == 1
