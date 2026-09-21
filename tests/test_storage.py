"""Tests for SQLite storage and FTS5 search."""

from pathlib import Path

from drivemesh.cluster import SubjectClusterer
from drivemesh.duplicates import DuplicateDetector
from drivemesh.importer import DriveImporter
from drivemesh.models import DriveFolder
from drivemesh.storage import DriveStorage


def test_storage_lifecycle(tmp_path: Path):
    db_path = tmp_path / "test_drive.db"
    storage = DriveStorage(db_path)

    demo_files = DriveImporter.generate_demo_dataset()
    storage.save_files(demo_files)

    folders = [DriveFolder(id="fld_1", name="Finance", path="/Finance")]
    storage.save_folders(folders)

    loaded = storage.load_files()
    assert len(loaded) == len(demo_files)

    # Search FTS
    results = storage.search_fts("Tax")
    assert len(results) > 0

    # Test audit summary
    clusterer = SubjectClusterer(demo_files)
    clusters = clusterer.cluster_all()
    storage.save_clusters(clusters)

    detector = DuplicateDetector(demo_files)
    dups = detector.run_all()
    storage.save_duplicates(dups)

    report = storage.get_audit_summary()
    assert report.total_files == len(demo_files)
    assert report.duplicate_groups_count > 0
    assert report.health_score > 0
    assert len(report.recommendations) > 0
