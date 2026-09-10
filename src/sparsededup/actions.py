# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Action handlers for deduplication results: Hardlinking, Symlinking, Deletion, and Manifests.
"""

import json
import os
from pathlib import Path

from .core import ScanResult


class ActionResult:
    """Outcome of deduplication execution actions."""
    def __init__(self):
        self.processed_files: int = 0
        self.reclaimed_bytes: int = 0
        self.errors: list[str] = []
        self.details: list[str] = []

    def to_dict(self) -> dict:
        return {
            "processed_files": self.processed_files,
            "reclaimed_bytes": self.reclaimed_bytes,
            "errors": self.errors,
            "details": self.details,
        }


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    val = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(val) < 1024.0:
            return f"{val:3.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} EB"


def apply_hardlinks(scan_result: ScanResult) -> ActionResult:
    """
    Replace duplicate files with atomic hardlinks to the canonical file.
    Preserves filesystem structure while instantly freeing storage blocks.
    """
    action_res = ActionResult()

    for cluster in scan_result.duplicate_clusters:
        canonical = cluster.canonical_file.path

        for dup in cluster.duplicates:
            dup_path = dup.path
            try:
                # Check if they are on the same filesystem/device
                if cluster.canonical_file.device != dup.device:
                    action_res.errors.append(
                        f"Cannot hardlink across different filesystems: {dup_path} -> {canonical}"
                    )
                    continue

                # Create atomic link via temp file in same directory
                dir_name = dup_path.parent
                temp_link = dir_name / f".tmp_hardlink_{os.getpid()}_{dup_path.name}"

                os.link(canonical, temp_link)
                os.replace(temp_link, dup_path)

                action_res.processed_files += 1
                action_res.reclaimed_bytes += cluster.file_size
                action_res.details.append(f"Hardlinked: {dup_path} -> {canonical}")
            except OSError as e:
                action_res.errors.append(f"Failed to hardlink {dup_path}: {e}")

    return action_res


def apply_symlinks(scan_result: ScanResult) -> ActionResult:
    """
    Replace duplicate files with relative or absolute symbolic links.
    """
    action_res = ActionResult()

    for cluster in scan_result.duplicate_clusters:
        canonical = cluster.canonical_file.path

        for dup in cluster.duplicates:
            dup_path = dup.path
            try:
                # Remove duplicate and create symlink
                dup_path.unlink()
                dup_path.symlink_to(canonical)

                action_res.processed_files += 1
                action_res.reclaimed_bytes += cluster.file_size
                action_res.details.append(f"Symlinked: {dup_path} -> {canonical}")
            except OSError as e:
                action_res.errors.append(f"Failed to symlink {dup_path}: {e}")

    return action_res


def apply_deletion(scan_result: ScanResult) -> ActionResult:
    """
    Safely delete redundant duplicate files.
    """
    action_res = ActionResult()

    for cluster in scan_result.duplicate_clusters:
        for dup in cluster.duplicates:
            dup_path = dup.path
            try:
                dup_path.unlink()
                action_res.processed_files += 1
                action_res.reclaimed_bytes += cluster.file_size
                action_res.details.append(f"Deleted: {dup_path}")
            except OSError as e:
                action_res.errors.append(f"Failed to delete {dup_path}: {e}")

    return action_res


def export_json_manifest(scan_result: ScanResult, output_path: Path) -> None:
    """Export scan results as a structured JSON manifest."""
    data = {
        "summary": {
            "scanned_files": scan_result.scanned_files_count,
            "scanned_bytes": scan_result.scanned_total_bytes,
            "scanned_bytes_human": format_bytes(scan_result.scanned_total_bytes),
            "duplicate_files": scan_result.total_duplicate_files,
            "reclaimable_bytes": scan_result.total_reclaimable_bytes,
            "reclaimable_bytes_human": format_bytes(scan_result.total_reclaimable_bytes),
            "duplicate_clusters": len(scan_result.duplicate_clusters),
        },
        "clusters": [
            {
                "full_hash": cluster.full_hash,
                "file_size": cluster.file_size,
                "file_size_human": format_bytes(cluster.file_size),
                "reclaimable_bytes": cluster.total_reclaimable_bytes,
                "reclaimable_bytes_human": format_bytes(cluster.total_reclaimable_bytes),
                "canonical_file": str(cluster.canonical_file.path),
                "duplicates": [str(d.path) for d in cluster.duplicates],
            }
            for cluster in scan_result.duplicate_clusters
        ],
        "errors": scan_result.errors,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
