"""Targeted edge-case coverage tests for subwatch."""

import os
from datetime import date
from unittest.mock import patch

from subwatch.advisor import heuristic_subscription_advisor
from subwatch.engine import (
    analyze_price_creep,
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
from subwatch.storage import StorageManager


def test_advisor_overview_with_all_flags():
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
            name="Disney+",
            vendor="Disney",
            category=Category.ENTERTAINMENT,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_price=13.99,
            next_renewal_date="2026-10-15",
            usage_rating=1,
        ),
    ]
    ans = heuristic_subscription_advisor("What is the state of my accounts?", subs)
    assert "Price Creep:" in ans
    assert "Zombie Subscriptions:" in ans
    assert "Redundancy Clusters:" in ans
    assert "Upcoming Renewals:" in ans


def test_storage_env_var_and_error_handling(tmp_path):
    env_dir = tmp_path / "env_subwatch"
    with patch.dict(os.environ, {"SUBWATCH_DATA_DIR": str(env_dir)}):
        sm = StorageManager()
        assert sm.base_dir == env_dir

    # Corrupt / invalid json in vault file
    vault_file = env_dir / "vault.json"
    vault_file.write_text("{not valid json}", encoding="utf-8")
    sm2 = StorageManager(data_dir=env_dir)
    assert sm2.load_all() == []

    # Non-list JSON in vault
    vault_file.write_text('{"key": "value"}', encoding="utf-8")
    assert sm2.load_all() == []

    # List with malformed item
    vault_file.write_text('[{"invalid_key": 123}]', encoding="utf-8")
    assert sm2.load_all() == []


def test_engine_date_parsing_edge_cases():
    sub_bad_date = Subscription(
        id="s1",
        name="Bad Date Sub",
        vendor="Vendor",
        category=Category.OTHER,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=10.0,
        next_renewal_date="invalid-date-format",
    )
    alerts = get_upcoming_renewals([sub_bad_date], today=date(2026, 10, 5))
    assert alerts == []

    # Price creep with initial_price = 0 or empty charges
    sub_zero = Subscription(
        id="s2",
        name="Zero Price",
        vendor="Vendor",
        category=Category.OTHER,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_price=0.0,
        charge_history=[ChargeRecord(id="c1", subscription_id="s2", amount=0.0, date="2025-01-01")],
    )
    assert analyze_price_creep(sub_zero) is None


def test_csv_parser_edge_cases():
    csv_text = """Date,Payee,Charge
2026-01-01,Unknown Coffee Shop,$5.50
,Empty Merchant,$0.00
2026-01-02,,$10.00
"""
    candidates = parse_transaction_csv(csv_text)
    assert candidates == []
