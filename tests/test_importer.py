"""Tests for importer module."""

import json
from pathlib import Path

from drivemesh.importer import DriveImporter


def test_load_from_json_dict_and_list(tmp_path: Path):
    sample_data = {
        "files": [
            {
                "id": "file1",
                "name": "Tax_2024.pdf",
                "mimeType": "application/pdf",
                "size": "5000",
                "md5Checksum": "abc12345",
                "modifiedTime": "2024-04-15T00:00:00Z",
                "parents": ["folder1"],
            },
            {
                "id": "folder1",
                "name": "Tax Folder",
                "mimeType": "application/vnd.google-apps.folder",
            },
        ]
    }
    json_file = tmp_path / "drive_export.json"
    json_file.write_text(json.dumps(sample_data), encoding="utf-8")

    files = DriveImporter.load_from_json(json_file)
    assert len(files) == 1
    assert files[0].id == "file1"
    assert files[0].name == "Tax_2024.pdf"
    assert files[0].size_bytes == 5000
    assert files[0].md5_checksum == "abc12345"


def test_load_from_rclone_json(tmp_path: Path):
    rclone_data = [
        {
            "Path": "Documents/Contract.pdf",
            "Name": "Contract.pdf",
            "Size": 12000,
            "MimeType": "application/pdf",
            "ModTime": "2024-01-10T12:00:00Z",
            "IsDir": False,
            "Hashes": {"MD5": "hash_md5", "SHA256": "hash_sha256"},
        },
        {
            "Path": "Documents",
            "Name": "Documents",
            "Size": -1,
            "IsDir": True,
        },
    ]
    files = DriveImporter.load_from_json(rclone_data)
    assert len(files) == 1
    assert files[0].name == "Contract.pdf"
    assert files[0].md5_checksum == "hash_md5"
    assert files[0].sha256_checksum == "hash_sha256"


def test_load_from_csv(tmp_path: Path):
    csv_file = tmp_path / "drive_export.csv"
    csv_content = (
        "id,name,mime_type,size_bytes,md5_checksum,path\n"
        "f1,Invoice.pdf,application/pdf,2048,fa123,/Finance/Invoice.pdf\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    files = DriveImporter.load_from_csv(csv_file)
    assert len(files) == 1
    assert files[0].id == "f1"
    assert files[0].name == "Invoice.pdf"
    assert files[0].size_bytes == 2048


def test_scan_directory(tmp_path: Path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    f1 = sub / "test.txt"
    f1.write_text("hello world", encoding="utf-8")

    files, folders = DriveImporter.scan_directory(tmp_path, compute_hashes=True)
    assert len(files) == 1
    assert len(folders) == 1
    assert files[0].name == "test.txt"
    assert files[0].size_bytes == 11
    assert len(files[0].md5_checksum) > 0
    assert len(files[0].sha256_checksum) > 0


def test_generate_demo_dataset():
    files = DriveImporter.generate_demo_dataset()
    assert len(files) >= 10
    assert any(f.name.endswith(".pdf") for f in files)
    assert any(f.size_bytes == 0 for f in files)
