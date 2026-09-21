"""Tests for data models in drivemesh-core."""

from drivemesh.models import (
    ClusterCategory,
    DriveAuditReport,
    DriveFile,
    DriveFolder,
    DuplicateGroup,
    DuplicateType,
    FileCluster,
    MeshMoveOperation,
    MeshPlan,
    ResolutionAction,
)


def test_drive_file_instantiation_and_dict():
    df = DriveFile(
        id="file_123",
        name="Contract.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        md5_checksum="abc123md5",
        sha256_checksum="def456sha256",
        modified_time="2024-01-01T00:00:00Z",
        created_time="2024-01-01T00:00:00Z",
        parents=["root"],
        path_hierarchy="/Legal/Contract.pdf",
        shared=True,
        starred=False,
        trashed=False,
        assigned_category=ClusterCategory.LEGAL_CONTRACTS,
        cluster_label="Legal",
        confidence=0.95,
    )
    d = df.to_dict()
    assert d["id"] == "file_123"
    assert d["name"] == "Contract.pdf"
    assert d["assigned_category"] == ClusterCategory.LEGAL_CONTRACTS.value
    assert d["shared"] is True
    assert d["confidence"] == 0.95


def test_drive_folder_model():
    folder = DriveFolder(id="fld_1", name="Finance", parents=["root"], path="/Finance")
    d = folder.to_dict()
    assert d["id"] == "fld_1"
    assert d["path"] == "/Finance"


def test_file_cluster_model():
    cluster = FileCluster(
        cluster_id="c_fin",
        category=ClusterCategory.FINANCIAL_TAX,
        label="2024 Tax",
        file_ids=["f1", "f2"],
        total_size_bytes=2048,
        suggested_target_path="/Financial_Tax/2024_Tax",
        confidence_score=0.9,
    )
    d = cluster.to_dict()
    assert d["cluster_id"] == "c_fin"
    assert d["category"] == ClusterCategory.FINANCIAL_TAX.value
    assert len(d["file_ids"]) == 2


def test_duplicate_group_model():
    group = DuplicateGroup(
        group_id="grp_1",
        canonical_file_id="f1",
        duplicate_file_ids=["f2", "f3"],
        duplicate_type=DuplicateType.EXACT_CHECKSUM,
        wasted_bytes=4096,
        resolution_suggestion=ResolutionAction.DELETE_DUPLICATES,
        explanation="Binary exact duplicate",
    )
    d = group.to_dict()
    assert d["group_id"] == "grp_1"
    assert d["duplicate_type"] == "EXACT_CHECKSUM"
    assert d["resolution_suggestion"] == "DELETE_DUPLICATES"
    assert d["wasted_bytes"] == 4096


def test_audit_report_model():
    report = DriveAuditReport(
        total_files=10,
        total_folders=2,
        total_storage_bytes=100000,
        reclaimable_bytes=20000,
        duplicate_groups_count=1,
        health_score=85,
    )
    d = report.to_dict()
    assert d["total_files"] == 10
    assert d["health_score"] == 85


def test_mesh_plan_model():
    move = MeshMoveOperation(
        file_id="f1",
        file_name="invoice.pdf",
        current_path="/invoice.pdf",
        proposed_path="/Financial_Tax/Invoices/invoice.pdf",
        reason="Tax categorization",
    )
    plan = MeshPlan(
        plan_id="plan_001",
        generated_at="2024-01-01T00:00:00Z",
        proposed_moves=[move],
        proposed_deletions=["f2"],
        total_reclaimable_bytes=5000,
    )
    d = plan.to_dict()
    assert d["plan_id"] == "plan_001"
    assert len(d["proposed_moves"]) == 1
    assert d["proposed_deletions"] == ["f2"]
