"""Unit tests for nasroute engine, hashing, classification, and routing."""

import os
from pathlib import Path

import pytest

from nasroute.engine import (
    NASRouter,
    TaxonomyClassifier,
    compute_hashes,
    extract_date_hint,
    extract_metadata,
)
from nasroute.models import (
    DocumentCategory,
    DocumentMetadata,
    RouteAction,
    StorageTier,
    StorageTierConfig,
    TaxonomyRule,
)


def test_compute_hashes_and_date_extraction(tmp_path: Path):
    test_file = tmp_path / "2024-03-15_medical_report.txt"
    test_file.write_text("Patient bloodwork records and metabolic health results", encoding="utf-8")

    sha256, blake2b = compute_hashes(test_file)
    assert len(sha256) == 64
    assert len(blake2b) == 128

    meta = extract_metadata(test_file)
    assert meta.file_name == "2024-03-15_medical_report.txt"
    assert meta.extracted_date == "2024-03-15"
    assert meta.size_bytes > 0


def test_date_hint_patterns():
    assert extract_date_hint("invoice_2023-11-20.pdf") == "2023-11-20"
    assert extract_date_hint("tax_return_20240415.pdf") == "2024-04-15"
    assert extract_date_hint("statement_2022_08.pdf") == "2022-08-01"
    assert extract_date_hint("doc_2021.txt") == "2021-01-01"
    assert extract_date_hint("random_file_no_date.doc") is None


def test_taxonomy_classifier_rules_and_content_matching():
    rules = [
        TaxonomyRule(
            rule_id="r_tax",
            name="Taxes",
            category=DocumentCategory.TAX_FINANCE.value,
            target_tier=StorageTier.COLD_NAS.value,
            destination_subpath="Finance/Taxes/{year}/{filename}",
            name_keywords=["tax", "w2", "1099"],
            priority=150,
        ),
        TaxonomyRule(
            rule_id="r_content_invoice",
            name="Invoices Content",
            category=DocumentCategory.RECEIPTS_INVOICES.value,
            target_tier=StorageTier.WARM_SSD.value,
            destination_subpath="Finance/Invoices/{year}/{month}/{filename}",
            content_keywords=["invoice number", "amount due"],
            priority=140,
        ),
        TaxonomyRule(
            rule_id="r_regex",
            name="Regex Syslogs",
            category=DocumentCategory.HOMELAB_SYSADMIN.value,
            target_tier=StorageTier.HOT_NVME.value,
            destination_subpath="Homelab/Logs/{year}/{filename}",
            path_pattern=r"syslog_.*\.log",
            priority=100,
        ),
    ]

    classifier = TaxonomyClassifier(rules)

    tax_meta = DocumentMetadata(
        file_path="/tmp/2024_w2_statement.pdf",
        file_name="2024_w2_statement.pdf",
        size_bytes=500,
        sha256="aaa",
        blake2b="bbb",
        extracted_date="2024-01-15",
    )
    rule, cat, tier, subpath = classifier.classify(tax_meta)
    assert rule is not None
    assert rule.rule_id == "r_tax"
    assert cat == DocumentCategory.TAX_FINANCE.value
    assert tier == StorageTier.COLD_NAS.value
    assert subpath == "Finance/Taxes/2024/2024_w2_statement.pdf"

    # Content keyword test
    inv_meta = DocumentMetadata(
        file_path="/tmp/billing_statement.txt",
        file_name="billing_statement.txt",
        size_bytes=500,
        sha256="aaa2",
        blake2b="bbb2",
        extracted_date="2024-05-10",
    )
    i_rule, i_cat, i_tier, i_subpath = classifier.classify(
        inv_meta, content_snippet="Here is your invoice number #12345 with amount due $50."
    )
    assert i_rule is not None
    assert i_rule.rule_id == "r_content_invoice"
    assert i_cat == DocumentCategory.RECEIPTS_INVOICES.value
    assert i_subpath == "Finance/Invoices/2024/05/billing_statement.txt"

    # Regex path test
    regex_meta = DocumentMetadata(
        file_path="/tmp/syslog_auditd.log",
        file_name="syslog_auditd.log",
        size_bytes=500,
        sha256="aaa3",
        blake2b="bbb3",
        extracted_date="2024-01-01",
    )
    r_rule, r_cat, r_tier, r_subpath = classifier.classify(regex_meta)
    assert r_rule is not None
    assert r_rule.rule_id == "r_regex"
    assert r_cat == DocumentCategory.HOMELAB_SYSADMIN.value

    # Fallback uncategorized
    unknown_meta = DocumentMetadata(
        file_path="/tmp/vacation_photo.jpg",
        file_name="vacation_photo.jpg",
        size_bytes=5000,
        sha256="ccc",
        blake2b="ddd",
    )
    u_rule, u_cat, u_tier, u_subpath = classifier.classify(unknown_meta)
    assert u_rule is None
    assert u_cat == DocumentCategory.UNCATEGORIZED.value
    assert u_subpath == "Uncategorized/vacation_photo.jpg"


def test_nas_router_symlink_and_hardlink(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    hot_tier = tmp_path / "storage_tiers" / "hot_nvme"
    hot_tier.mkdir(parents=True)

    tier_configs = {
        StorageTier.HOT_NVME.value: StorageTierConfig(
            tier_name=StorageTier.HOT_NVME.value,
            mount_path=str(hot_tier),
        ),
    }

    rules = [
        TaxonomyRule(
            rule_id="r_docker",
            name="Docker",
            category=DocumentCategory.HOMELAB_SYSADMIN.value,
            target_tier=StorageTier.HOT_NVME.value,
            destination_subpath="Docker/{year}/{filename}",
            name_keywords=["docker"],
            priority=100,
        ),
    ]

    classifier = TaxonomyClassifier(rules)
    router = NASRouter(classifier=classifier, tier_configs=tier_configs)

    doc = inbox / "docker-compose.yml"
    doc.write_text("services: test\n", encoding="utf-8")

    # Symlink
    _, sym_res = router.route_document(doc, action=RouteAction.SYMLINK)
    assert sym_res.status == "SUCCESS"
    assert Path(sym_res.dest_path).is_symlink()

    # Hardlink
    doc2 = inbox / "docker-entrypoint.sh"
    doc2.write_text("#!/bin/sh\n", encoding="utf-8")
    _, hard_res = router.route_document(doc2, action=RouteAction.HARDLINK)
    assert hard_res.status == "SUCCESS"
    assert os.stat(doc2).st_ino == os.stat(hard_res.dest_path).st_ino


def test_collision_name_resolution(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    cold_tier = tmp_path / "cold_nas"
    cold_tier.mkdir()

    tier_configs = {
        StorageTier.COLD_NAS.value: StorageTierConfig(
            tier_name=StorageTier.COLD_NAS.value,
            mount_path=str(cold_tier),
        ),
    }

    rules = [
        TaxonomyRule(
            rule_id="r_general",
            name="General",
            category=DocumentCategory.SCANS_DOCS.value,
            target_tier=StorageTier.COLD_NAS.value,
            destination_subpath="Scans/{year}/{filename}",
            name_keywords=["scan"],
            priority=100,
        )
    ]

    classifier = TaxonomyClassifier(rules)
    router = NASRouter(classifier=classifier, tier_configs=tier_configs)

    f1 = inbox / "scan_doc.txt"
    f1.write_text("First file content", encoding="utf-8")
    _, res1 = router.route_document(f1, action=RouteAction.COPY)

    # Different content, same filename
    f2 = tmp_path / "other_inbox" / "scan_doc.txt"
    f2.parent.mkdir()
    f2.write_text("Second file DIFFERENT content", encoding="utf-8")
    _, res2 = router.route_document(f2, action=RouteAction.COPY)

    # Verify both exist with differentiated name
    assert Path(res1.dest_path).exists()
    assert Path(res2.dest_path).exists()
    assert res1.dest_path != res2.dest_path
    assert "scan_doc_1.txt" in res2.dest_path


def test_nas_router_copy_and_deduplication(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    hot_tier = tmp_path / "storage_tiers" / "hot_nvme"
    cold_tier = tmp_path / "storage_tiers" / "cold_nas"
    hot_tier.mkdir(parents=True)
    cold_tier.mkdir(parents=True)

    tier_configs = {
        StorageTier.HOT_NVME.value: StorageTierConfig(
            tier_name=StorageTier.HOT_NVME.value,
            mount_path=str(hot_tier),
        ),
        StorageTier.COLD_NAS.value: StorageTierConfig(
            tier_name=StorageTier.COLD_NAS.value,
            mount_path=str(cold_tier),
        ),
    }

    rules = [
        TaxonomyRule(
            rule_id="r_tax",
            name="Taxes",
            category=DocumentCategory.TAX_FINANCE.value,
            target_tier=StorageTier.COLD_NAS.value,
            destination_subpath="Taxes/{year}/{filename}",
            name_keywords=["tax", "w2"],
            priority=150,
        ),
    ]

    classifier = TaxonomyClassifier(rules)
    router = NASRouter(classifier=classifier, tier_configs=tier_configs)

    f1 = inbox / "2024_w2_tax.pdf"
    f1.write_text("W2 Tax Form 2024 Content Data", encoding="utf-8")

    meta, res = router.route_document(f1, action=RouteAction.COPY, verify_checksum=True)
    assert res.status == "SUCCESS"
    assert res.category == DocumentCategory.TAX_FINANCE.value
    assert res.tier == StorageTier.COLD_NAS.value
    assert Path(res.dest_path).exists()
    assert Path(res.dest_path).read_text(encoding="utf-8") == "W2 Tax Form 2024 Content Data"

    # Routing duplicate should be skipped
    meta2, res2 = router.route_document(f1, action=RouteAction.COPY)
    assert res2.status == "SKIPPED_DUPLICATE"


def test_nas_router_move_and_dry_run(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    cold_tier = tmp_path / "cold_nas"
    cold_tier.mkdir()

    tier_configs = {
        StorageTier.COLD_NAS.value: StorageTierConfig(
            tier_name=StorageTier.COLD_NAS.value,
            mount_path=str(cold_tier),
        ),
    }

    classifier = TaxonomyClassifier([])
    router = NASRouter(classifier=classifier, tier_configs=tier_configs)

    doc = inbox / "document.txt"
    doc.write_text("Hello Homelab Storage", encoding="utf-8")

    # Dry run
    _, dry_res = router.route_document(doc, action=RouteAction.DRY_RUN)
    assert dry_res.status == "SIMULATED"
    assert doc.exists()

    # Real move
    _, move_res = router.route_document(doc, action=RouteAction.MOVE)
    assert move_res.status == "SUCCESS"
    assert not doc.exists()
    assert Path(move_res.dest_path).exists()


def test_scan_and_route_directory_report(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "receipt_2024_05.txt").write_text("Home Depot hardware receipt", encoding="utf-8")
    (inbox / "syslog_audit_2024.log").write_text("systemd service started", encoding="utf-8")

    tier_configs = {
        StorageTier.COLD_NAS.value: StorageTierConfig(
            tier_name=StorageTier.COLD_NAS.value,
            mount_path=str(tmp_path / "cold_tier"),
        ),
    }

    router = NASRouter(classifier=TaxonomyClassifier([]), tier_configs=tier_configs)
    report = router.scan_and_route_directory(inbox, action=RouteAction.DRY_RUN)

    assert report.total_files_scanned == 2
    assert report.routed_files_count == 2
    assert len(report.executions) == 2


def test_extract_metadata_nonexistent(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        extract_metadata(tmp_path / "nonexistent.file")
