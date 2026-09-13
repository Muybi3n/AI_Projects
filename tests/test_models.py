"""Unit tests for nasroute models and data structures."""

from nasroute.models import (
    AuditReport,
    DocumentCategory,
    DocumentMetadata,
    RouteAction,
    RouteExecution,
    StorageTier,
    StorageTierConfig,
    TaxonomyRule,
)


def test_storage_tier_and_action_enums():
    assert StorageTier.HOT_NVME.value == "HOT_NVME"
    assert StorageTier.WARM_SSD.value == "WARM_SSD"
    assert StorageTier.COLD_NAS.value == "COLD_NAS"
    assert StorageTier.GLACIER_BACKUP.value == "GLACIER_BACKUP"

    assert RouteAction.MOVE.value == "MOVE"
    assert RouteAction.COPY.value == "COPY"
    assert RouteAction.SYMLINK.value == "SYMLINK"
    assert RouteAction.HARDLINK.value == "HARDLINK"
    assert RouteAction.DRY_RUN.value == "DRY_RUN"

    assert DocumentCategory.TAX_FINANCE.value == "TAX_FINANCE"
    assert DocumentCategory.MEDICAL_HEALTH.value == "MEDICAL_HEALTH"


def test_document_metadata_serialization():
    meta = DocumentMetadata(
        file_path="/data/inbox/2024_tax_w2.pdf",
        file_name="2024_tax_w2.pdf",
        size_bytes=1024,
        sha256="abc123sha",
        blake2b="def456blake",
        mime_type="application/pdf",
        created_at="2024-01-01T00:00:00Z",
        modified_at="2024-01-01T00:00:00Z",
        tags=["tax", "w2"],
        extracted_date="2024-01-01",
        suggested_category=DocumentCategory.TAX_FINANCE.value,
        suggested_tier=StorageTier.COLD_NAS.value,
    )
    d = meta.to_dict()
    assert d["file_name"] == "2024_tax_w2.pdf"
    assert d["size_bytes"] == 1024
    assert d["sha256"] == "abc123sha"

    restored = DocumentMetadata.from_dict(d)
    assert restored.file_name == meta.file_name
    assert restored.suggested_category == meta.suggested_category


def test_taxonomy_rule_serialization():
    rule = TaxonomyRule(
        rule_id="tax_rule",
        name="Tax Ingestion",
        category=DocumentCategory.TAX_FINANCE.value,
        target_tier=StorageTier.COLD_NAS.value,
        destination_subpath="Taxes/{year}/{filename}",
        name_keywords=["tax", "w2"],
        priority=150,
    )
    d = rule.to_dict()
    assert d["rule_id"] == "tax_rule"
    assert d["priority"] == 150

    restored = TaxonomyRule.from_dict(d)
    assert restored.name == rule.name
    assert restored.name_keywords == ["tax", "w2"]


def test_route_execution_and_tier_config():
    tier = StorageTierConfig(
        tier_name="HOT_NVME",
        mount_path="/mnt/nvme",
        speed_class="NVMe_Gen4",
        max_capacity_bytes=1000000,
        current_used_bytes=5000,
    )
    t_dict = tier.to_dict()
    assert t_dict["tier_name"] == "HOT_NVME"
    assert StorageTierConfig.from_dict(t_dict).mount_path == "/mnt/nvme"

    exc = RouteExecution(
        source_path="/inbox/doc.txt",
        dest_path="/dest/doc.txt",
        action="COPY",
        category="HOMELAB_SYSADMIN",
        tier="HOT_NVME",
        sha256="hash123",
        status="SUCCESS",
        message="OK",
        timestamp="2026-09-13T00:00:00Z",
    )
    e_dict = exc.to_dict()
    assert e_dict["status"] == "SUCCESS"
    assert RouteExecution.from_dict(e_dict).category == "HOMELAB_SYSADMIN"


def test_audit_report_serialization():
    exc = RouteExecution(
        source_path="/inbox/doc.txt",
        dest_path="/dest/doc.txt",
        action="COPY",
        category="TAX_FINANCE",
        tier="COLD_NAS",
        sha256="hash123",
        status="SUCCESS",
        message="OK",
        timestamp="2026-09-13T00:00:00Z",
    )
    report = AuditReport(
        total_files_scanned=10,
        total_bytes_scanned=100000,
        routed_files_count=8,
        duplicate_files_count=2,
        space_saved_bytes=20000,
        tier_breakdown={"COLD_NAS": 8},
        category_breakdown={"TAX_FINANCE": 8},
        executions=[exc],
    )
    rep_dict = report.to_dict()
    assert rep_dict["total_files_scanned"] == 10
    assert rep_dict["duplicate_files_count"] == 2
    assert len(rep_dict["executions"]) == 1

    restored = AuditReport.from_dict(rep_dict)
    assert restored.space_saved_bytes == 20000
    assert restored.executions[0].sha256 == "hash123"
