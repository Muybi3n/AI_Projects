# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for deduplication actions (hardlink, symlink, delete, manifest).
"""

import json
from pathlib import Path

from sparsededup.actions import (
    apply_deletion,
    apply_hardlinks,
    apply_symlinks,
    export_json_manifest,
    format_bytes,
)
from sparsededup.core import DeduplicationScanner


def test_format_bytes():
    assert format_bytes(500) == "500.00 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024**2 * 5) == "5.00 MB"
    assert format_bytes(1024**3 * 2.5) == "2.50 GB"


def test_apply_hardlinks(tmp_path: Path):
    f1 = tmp_path / "orig.bin"
    f2 = tmp_path / "copy.bin"
    data = b"Testing hardlink deduplication" * 100
    f1.write_bytes(data)
    f2.write_bytes(data)

    scanner = DeduplicationScanner(paths=[tmp_path])
    res = scanner.scan()
    assert len(res.duplicate_clusters) == 1

    action_res = apply_hardlinks(res)
    assert action_res.processed_files == 1
    assert action_res.reclaimed_bytes == len(data)

    # Inodes should now match
    stat1 = f1.stat()
    stat2 = f2.stat()
    assert stat1.st_ino == stat2.st_ino
    assert f2.read_bytes() == data


def test_apply_symlinks(tmp_path: Path):
    f1 = tmp_path / "orig_sym.bin"
    f2 = tmp_path / "copy_sym.bin"
    data = b"Testing symlink deduplication" * 100
    f1.write_bytes(data)
    f2.write_bytes(data)

    scanner = DeduplicationScanner(paths=[tmp_path])
    res = scanner.scan()

    action_res = apply_symlinks(res)
    assert action_res.processed_files == 1
    assert f2.is_symlink()
    assert f2.resolve() == f1.resolve()


def test_apply_deletion(tmp_path: Path):
    f1 = tmp_path / "keep.bin"
    f2 = tmp_path / "delete_me.bin"
    data = b"Testing deletion" * 50
    f1.write_bytes(data)
    f2.write_bytes(data)

    scanner = DeduplicationScanner(paths=[tmp_path])
    res = scanner.scan()

    action_res = apply_deletion(res)
    assert action_res.processed_files == 1
    assert f1.exists()
    assert not f2.exists()


def test_export_json_manifest(tmp_path: Path):
    f1 = tmp_path / "file1.bin"
    f2 = tmp_path / "file2.bin"
    data = b"JSON manifest data" * 20
    f1.write_bytes(data)
    f2.write_bytes(data)

    manifest_path = tmp_path / "manifest.json"
    scanner = DeduplicationScanner(paths=[tmp_path])
    res = scanner.scan()

    export_json_manifest(res, manifest_path)
    assert manifest_path.exists()

    with open(manifest_path, "r") as f:
        loaded = json.load(f)

    assert loaded["summary"]["duplicate_files"] == 1
    assert len(loaded["clusters"]) == 1
