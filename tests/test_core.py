# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive tests for core scanning, edge cases, symlinks, and progress callbacks.
"""

import time
from pathlib import Path

from sparsededup.core import DeduplicationScanner


def test_deduplication_scanner_basic(tmp_path: Path):
    """Test scanner finding 2 duplicate pairs and 1 unique file."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    content1 = b"Identical Video Data Chunk " * 500
    content2 = b"Another File Content" * 300
    unique_content = b"Unique content that has no duplicate"

    # Create duplicates
    (dir_a / "movie1.mkv").write_bytes(content1)
    time.sleep(0.01)
    (dir_b / "movie1_copy.mkv").write_bytes(content1)

    (dir_a / "doc.pdf").write_bytes(content2)
    time.sleep(0.01)
    (dir_b / "doc_backup.pdf").write_bytes(content2)

    (dir_a / "unique.txt").write_bytes(unique_content)

    events = []

    def progress_cb(evt, cur, tot):
        events.append((evt, cur, tot))

    scanner = DeduplicationScanner(paths=[tmp_path], progress_callback=progress_cb)
    result = scanner.scan()

    assert result.scanned_files_count == 5
    assert len(result.duplicate_clusters) == 2
    assert result.total_duplicate_files == 2
    assert result.total_reclaimable_bytes == len(content1) + len(content2)
    assert len(events) > 0


def test_scanner_with_exclusions_and_sizes(tmp_path: Path):
    """Test filtering by pattern and size bounds."""
    small = tmp_path / "small.txt"
    large = tmp_path / "large.dat"
    hidden = tmp_path / ".hidden_dup.dat"

    small.write_bytes(b"123")
    large.write_bytes(b"A" * 10000)
    hidden.write_bytes(b"A" * 10000)

    # Dup of large
    dup_large = tmp_path / "large_copy.dat"
    dup_large.write_bytes(b"A" * 10000)

    # Exclude small files and hidden files
    scanner = DeduplicationScanner(
        paths=[tmp_path],
        min_size=100,
        max_size=20000,
        include_patterns=["*.dat"],
        exclude_patterns=[".*"],
    )
    result = scanner.scan()

    assert len(result.duplicate_clusters) == 1
    assert result.duplicate_clusters[0].file_size == 10000


def test_scanner_nonexistent_path(tmp_path: Path):
    """Gracefully handle missing directories."""
    missing_dir = tmp_path / "does_not_exist"
    scanner = DeduplicationScanner(paths=[missing_dir])
    result = scanner.scan()
    assert len(result.errors) > 0


def test_scanner_single_file_target(tmp_path: Path):
    """Targeting single file directly."""
    f1 = tmp_path / "single.bin"
    f1.write_bytes(b"1234567890")
    scanner = DeduplicationScanner(paths=[f1])
    result = scanner.scan()
    assert result.scanned_files_count == 1
    assert len(result.duplicate_clusters) == 0


def test_scanner_no_duplicates(tmp_path: Path):
    """Ensure clean exit when no sizes match."""
    f1 = tmp_path / "f1.bin"
    f2 = tmp_path / "f2.bin"
    f1.write_bytes(b"A" * 10)
    f2.write_bytes(b"B" * 20)
    scanner = DeduplicationScanner(paths=[tmp_path])
    result = scanner.scan()
    assert result.scanned_files_count == 2
    assert len(result.duplicate_clusters) == 0
