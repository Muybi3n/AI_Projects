"""Metadata ingestion and parsing for Google Drive exports and local directories."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from drivemesh.models import DriveFile, DriveFolder


def _calculate_file_hashes(filepath: Path) -> tuple[str, str]:
    """Calculate MD5 and SHA-256 for a local file."""
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    try:
        with filepath.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                md5.update(chunk)
                sha256.update(chunk)
        return md5.hexdigest(), sha256.hexdigest()
    except (OSError, PermissionError):
        return "", ""


class DriveImporter:
    """Imports Drive metadata from various file formats and local directories."""

    @staticmethod
    def load_from_json(json_path_or_content: str | Path | dict[str, Any] | list[dict[str, Any]]) -> list[DriveFile]:
        """Load Drive files from Google Drive API export or rclone JSON format."""
        raw_data: Any
        if isinstance(json_path_or_content, (str, Path)):
            path = Path(json_path_or_content)
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            else:
                raw_data = json.loads(str(json_path_or_content))
        else:
            raw_data = json_path_or_content

        entries: list[dict[str, Any]] = []
        if isinstance(raw_data, dict):
            if "files" in raw_data and isinstance(raw_data["files"], list):
                entries = raw_data["files"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                entries = raw_data["items"]
            else:
                entries = [raw_data]
        elif isinstance(raw_data, list):
            entries = raw_data

        files: list[DriveFile] = []
        for item in entries:
            # Handle rclone format or standard Google Drive API schema
            is_dir = item.get("IsDir", False) or item.get("mimeType") == "application/vnd.google-apps.folder"
            if is_dir:
                continue

            file_id = str(item.get("id") or item.get("ID") or item.get("Path") or item.get("name", ""))
            name = str(item.get("name") or item.get("Name") or Path(file_id).name)
            mime = str(
                item.get("mimeType") or item.get("mime_type") or item.get("MimeType") or "application/octet-stream"
            )
            size = int(item.get("size") or item.get("size_bytes") or item.get("Size") or 0)
            md5 = str(
                item.get("md5Checksum")
                or item.get("md5_checksum")
                or item.get("md5")
                or (item.get("Hashes", {}).get("MD5", "") if isinstance(item.get("Hashes"), dict) else "")
            ).lower()
            sha256 = str(
                item.get("sha256Checksum")
                or item.get("sha256_checksum")
                or item.get("sha256")
                or (item.get("Hashes", {}).get("SHA256", "") if isinstance(item.get("Hashes"), dict) else "")
            ).lower()
            mtime = str(item.get("modifiedTime") or item.get("modified_time") or item.get("ModTime") or "")
            ctime = str(item.get("createdTime") or item.get("created_time") or "")
            parents = item.get("parents") or []
            if isinstance(parents, str):
                parents = [parents]
            path_hier = str(item.get("path") or item.get("path_hierarchy") or item.get("Path") or "/")

            files.append(
                DriveFile(
                    id=file_id,
                    name=name,
                    mime_type=mime,
                    size_bytes=size,
                    md5_checksum=md5,
                    sha256_checksum=sha256,
                    modified_time=mtime,
                    created_time=ctime,
                    parents=parents,
                    path_hierarchy=path_hier,
                    shared=bool(item.get("shared", False)),
                    starred=bool(item.get("starred", False)),
                    trashed=bool(item.get("trashed", False)),
                    web_view_link=str(item.get("webViewLink", "")),
                )
            )
        return files

    @staticmethod
    def load_from_csv(csv_path: str | Path) -> list[DriveFile]:
        """Load Drive metadata from a CSV export."""
        path = Path(csv_path)
        files: list[DriveFile] = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                file_id = row.get("id") or row.get("ID") or row.get("name") or ""
                name = row.get("name") or row.get("Name") or "unnamed_file"
                mime = row.get("mime_type") or row.get("mimeType") or "application/octet-stream"
                size = int(row.get("size_bytes") or row.get("size") or row.get("Size") or 0)
                md5 = (row.get("md5_checksum") or row.get("md5") or "").lower()
                sha256 = (row.get("sha256_checksum") or row.get("sha256") or "").lower()
                mtime = row.get("modified_time") or row.get("modifiedTime") or ""
                path_hier = row.get("path") or row.get("path_hierarchy") or "/"

                files.append(
                    DriveFile(
                        id=file_id,
                        name=name,
                        mime_type=mime,
                        size_bytes=size,
                        md5_checksum=md5,
                        sha256_checksum=sha256,
                        modified_time=mtime,
                        path_hierarchy=path_hier,
                    )
                )
        return files

    @staticmethod
    def scan_directory(dir_path: str | Path, compute_hashes: bool = True) -> tuple[list[DriveFile], list[DriveFolder]]:
        """Scan a local directory mirror or export tree."""
        root = Path(dir_path).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Directory path does not exist: {dir_path}")

        files: list[DriveFile] = []
        folders: list[DriveFolder] = []

        for p in root.rglob("*"):
            rel_path = "/" + str(p.relative_to(root)).replace("\\", "/")
            if p.is_dir():
                folders.append(
                    DriveFolder(
                        id=f"dir_{p.name}_{hash(rel_path) & 0xFFFFFFFF:08x}",
                        name=p.name,
                        parents=[str(p.parent.name)] if p.parent != root else ["root"],
                        path=rel_path,
                    )
                )
            elif p.is_file():
                md5, sha256 = _calculate_file_hashes(p) if compute_hashes else ("", "")
                stat = p.stat()
                files.append(
                    DriveFile(
                        id=f"file_{p.name}_{hash(rel_path) & 0xFFFFFFFF:08x}",
                        name=p.name,
                        size_bytes=stat.st_size,
                        md5_checksum=md5,
                        sha256_checksum=sha256,
                        modified_time=str(stat.st_mtime),
                        parents=[str(p.parent.name)] if p.parent != root else ["root"],
                        path_hierarchy=rel_path,
                    )
                )
        return files, folders

    @staticmethod
    def generate_demo_dataset() -> list[DriveFile]:
        """Generate realistic synthetic Google Drive dataset with duplicates and messy folders."""
        demo_files = [
            # Financial & Tax
            DriveFile(
                id="doc_tax_2024_w2",
                name="2024_W2_Form_Final.pdf",
                mime_type="application/pdf",
                size_bytes=420500,
                md5_checksum="a1b2c3d4e5f601020304050607080910",
                sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                modified_time="2024-02-15T14:22:00Z",
                path_hierarchy="/Tax Documents/2024_W2_Form_Final.pdf",
            ),
            DriveFile(
                id="doc_tax_2024_w2_copy",
                name="Copy of 2024_W2_Form_Final.pdf",
                mime_type="application/pdf",
                size_bytes=420500,
                md5_checksum="a1b2c3d4e5f601020304050607080910",
                sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                modified_time="2024-02-16T09:10:00Z",
                path_hierarchy="/2024_W2_Form_Final (1).pdf",
            ),
            DriveFile(
                id="doc_tax_1099_misc",
                name="1099_Consolidated_Tax_Statement_2024.pdf",
                mime_type="application/pdf",
                size_bytes=1048576,
                md5_checksum="fa01b02c03d04e05f060708090a0b0c0",
                sha256_checksum="11223344556677889900aabbccddeeff00112233445566778899aabbccddeeff",
                modified_time="2024-03-01T10:00:00Z",
                path_hierarchy="/Unsorted/1099_Consolidated_Tax_Statement_2024.pdf",
            ),
            DriveFile(
                id="doc_q4_budget_v1",
                name="Q4_Financial_Forecast_v1.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                size_bytes=845000,
                md5_checksum="b1b2b3b4b5b6b7b8b9b0c1c2c3c4c5c6",
                modified_time="2024-10-01T11:00:00Z",
                path_hierarchy="/Finance/Q4_Financial_Forecast_v1.xlsx",
            ),
            DriveFile(
                id="doc_q4_budget_v2_final",
                name="Q4_Financial_Forecast_v2_FINAL.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                size_bytes=890000,
                md5_checksum="c1c2c3c4c5c6c7c8c9c0d1d2d3d4d5d6",
                modified_time="2024-10-15T16:30:00Z",
                path_hierarchy="/My Drive/Q4_Financial_Forecast_v2_FINAL.xlsx",
            ),
            # Legal & Contracts
            DriveFile(
                id="doc_consulting_nda",
                name="Mutual_Non_Disclosure_Agreement_Signed.pdf",
                mime_type="application/pdf",
                size_bytes=350000,
                md5_checksum="d1d2d3d4d5d6d7d8d9d0e1e2e3e4e5e6",
                modified_time="2023-11-20T12:00:00Z",
                path_hierarchy="/Legal/Mutual_Non_Disclosure_Agreement_Signed.pdf",
            ),
            DriveFile(
                id="doc_consulting_nda_dup",
                name="Mutual_Non_Disclosure_Agreement_Signed (1).pdf",
                mime_type="application/pdf",
                size_bytes=350000,
                md5_checksum="d1d2d3d4d5d6d7d8d9d0e1e2e3e4e5e6",
                modified_time="2023-11-20T12:05:00Z",
                path_hierarchy="/Downloads_Backup/Mutual_Non_Disclosure_Agreement_Signed (1).pdf",
            ),
            # Health & Medical
            DriveFile(
                id="doc_health_blood_panel",
                name="Annual_Lab_Panel_Bloodwork_Results.pdf",
                mime_type="application/pdf",
                size_bytes=2100000,
                md5_checksum="e1e2e3e4e5e6e7e8e9e0f1f2f3f4f5f6",
                modified_time="2024-05-12T08:00:00Z",
                path_hierarchy="/Health/Annual_Lab_Panel_Bloodwork_Results.pdf",
            ),
            DriveFile(
                id="doc_health_immunization",
                name="Vaccine_Immunization_Card_Record.pdf",
                mime_type="application/pdf",
                size_bytes=512000,
                md5_checksum="f1f2f3f4f5f6f7f8f9f0a1a2a3a4a5a6",
                modified_time="2023-08-01T15:00:00Z",
                path_hierarchy="/Medical Records/Vaccine_Immunization_Card_Record.pdf",
            ),
            # Engineering & Code
            DriveFile(
                id="doc_k8s_manifests",
                name="kubernetes_cluster_manifests.tar.gz",
                mime_type="application/gzip",
                size_bytes=15400000,
                md5_checksum="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
                modified_time="2024-06-10T18:00:00Z",
                path_hierarchy="/Homelab/kubernetes_cluster_manifests.tar.gz",
            ),
            DriveFile(
                id="doc_docker_compose_backup",
                name="docker-compose.yml",
                mime_type="text/yaml",
                size_bytes=4096,
                md5_checksum="2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d",
                modified_time="2024-07-01T10:00:00Z",
                path_hierarchy="/docker-compose.yml",
            ),
            DriveFile(
                id="doc_docker_compose_backup_copy",
                name="docker-compose_backup.yml",
                mime_type="text/yaml",
                size_bytes=4096,
                md5_checksum="2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d",
                modified_time="2024-07-02T10:00:00Z",
                path_hierarchy="/Backups/docker-compose_backup.yml",
            ),
            # Media & Big Assets
            DriveFile(
                id="doc_large_video_screen",
                name="Architecture_Walkthrough_Demo_4K.mp4",
                mime_type="video/mp4",
                size_bytes=1073741824,  # 1 GB
                md5_checksum="3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d",
                modified_time="2024-04-20T20:00:00Z",
                path_hierarchy="/Videos/Architecture_Walkthrough_Demo_4K.mp4",
            ),
            # Ghost zero-byte file
            DriveFile(
                id="doc_ghost_empty",
                name="Untitled_document_corrupted.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                size_bytes=0,
                md5_checksum="",
                modified_time="2023-01-01T00:00:00Z",
                path_hierarchy="/Untitled_document_corrupted.docx",
            ),
        ]
        return demo_files
