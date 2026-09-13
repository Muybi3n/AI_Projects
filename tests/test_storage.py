"""Unit tests for nasroute storage management."""

from pathlib import Path

from nasroute.models import (
    AuditReport,
    DocumentCategory,
    RouteExecution,
    StorageTier,
    StorageTierConfig,
    TaxonomyRule,
)
from nasroute.storage import NASRouteStore


def test_storage_initialization_and_persistence(tmp_path: Path):
    data_dir = tmp_path / "nas_store"
    store = NASRouteStore(data_dir=data_dir)

    assert len(store.tiers) >= 4
    assert len(store.rules) >= 7
    assert (data_dir / "config.json").exists()

    # Add custom tier
    custom_tier = StorageTierConfig(
        tier_name="TEST_TIER",
        mount_path=str(tmp_path / "test_mount"),
        speed_class="RAM_DISK",
        max_capacity_bytes=5000000,
    )
    store.add_or_update_tier(custom_tier)
    assert "TEST_TIER" in store.tiers

    # Add custom rule
    custom_rule = TaxonomyRule(
        rule_id="custom_rule_1",
        name="Custom Rule",
        category=DocumentCategory.HOMELAB_SYSADMIN.value,
        target_tier=StorageTier.HOT_NVME.value,
        destination_subpath="Custom/{year}/{filename}",
        priority=200,
    )
    store.add_rule(custom_rule)
    assert any(r.rule_id == "custom_rule_1" for r in store.rules)

    # Re-instantiate to test persistence from disk
    store_reloaded = NASRouteStore(data_dir=data_dir)
    assert "TEST_TIER" in store_reloaded.tiers
    assert any(r.rule_id == "custom_rule_1" for r in store_reloaded.rules)

    # Remove rule
    assert store_reloaded.remove_rule("custom_rule_1") is True
    assert store_reloaded.remove_rule("nonexistent_rule") is False


def test_storage_record_audit_and_hashes(tmp_path: Path):
    data_dir = tmp_path / "nas_store"
    store = NASRouteStore(data_dir=data_dir)

    exc = RouteExecution(
        source_path="/inbox/doc.txt",
        dest_path="/storage/doc.txt",
        action="COPY",
        category="TAX_FINANCE",
        tier="COLD_NAS",
        sha256="abc123456789",
        status="SUCCESS",
        message="OK",
        timestamp="2026-09-13T00:00:00Z",
    )
    report = AuditReport(
        total_files_scanned=1,
        total_bytes_scanned=500,
        routed_files_count=1,
        duplicate_files_count=0,
        space_saved_bytes=0,
        executions=[exc],
    )

    store.record_audit(report)
    hashes = store.get_known_hashes()
    assert "abc123456789" in hashes
    assert (data_dir / "catalog.json").exists()
    assert (data_dir / "history.json").exists()
