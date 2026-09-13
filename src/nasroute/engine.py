"""Core deterministic routing, taxonomy classification, and hashing engine for nasroute-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

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


def compute_hashes(file_path: str | Path, chunk_size: int = 65536) -> tuple[str, str]:
    """Compute SHA-256 and BLAKE2b checksums in chunked stream for memory efficiency."""
    p = Path(file_path)
    sha256_hash = hashlib.sha256()
    blake2b_hash = hashlib.blake2b()

    with p.open("rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)
            blake2b_hash.update(chunk)

    return sha256_hash.hexdigest(), blake2b_hash.hexdigest()


def extract_date_hint(text: str) -> str | None:
    """Extract standard ISO date or year hint from filename or text."""
    # Matches YYYY-MM-DD or YYYY_MM_DD
    iso_match = re.search(r"(?<!\d)(20\d{2})[-_](0[1-9]|1[0-2])[-_](0[1-9]|[12]\d|3[01])(?!\d)", text)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"

    # Matches YYYYMMDD
    compact_match = re.search(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)", text)
    if compact_match:
        return f"{compact_match.group(1)}-{compact_match.group(2)}-{compact_match.group(3)}"

    # Matches YYYY-MM or YYYY_MM
    month_match = re.search(r"(?<!\d)(20\d{2})[-_](0[1-9]|1[0-2])(?!\d)", text)
    if month_match:
        return f"{month_match.group(1)}-{month_match.group(2)}-01"

    # Matches standalone 4-digit year (2000-2099)
    year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", text)
    if year_match:
        return f"{year_match.group(1)}-01-01"

    return None


def extract_metadata(file_path: str | Path) -> DocumentMetadata:
    """Extract file system metadata, cryptographic hashes, and date hints."""
    p = Path(file_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    stat = p.stat()
    size_bytes = stat.st_size
    sha256, blake2b = compute_hashes(p)

    mime, _ = mimetypes.guess_type(str(p))
    mime_type = mime or "application/octet-stream"

    # Datetimes in UTC ISO format
    created_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
    modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    date_hint = extract_date_hint(p.name)

    return DocumentMetadata(
        file_path=str(p),
        file_name=p.name,
        size_bytes=size_bytes,
        sha256=sha256,
        blake2b=blake2b,
        mime_type=mime_type,
        created_at=created_dt,
        modified_at=modified_dt,
        extracted_date=date_hint,
    )


class TaxonomyClassifier:
    """Deterministic rule-based classification engine."""

    def __init__(self, rules: list[TaxonomyRule] | None = None):
        self.rules = sorted(rules or [], key=lambda r: r.priority, reverse=True)

    def resolve_destination(self, subpath_template: str, metadata: DocumentMetadata, category: str) -> str:
        """Render destination subpath template with extracted variables."""
        date_val = metadata.extracted_date
        year = "archive"
        month = "01"
        day = "01"

        if date_val:
            parts = date_val.split("-")
            if len(parts) >= 1:
                year = parts[0]
            if len(parts) >= 2:
                month = parts[1]
            if len(parts) >= 3:
                day = parts[2]
        else:
            # Fallback to file modified date
            try:
                mod_date = datetime.fromisoformat(metadata.modified_at)
                year = str(mod_date.year)
                month = f"{mod_date.month:02d}"
                day = f"{mod_date.day:02d}"
            except (ValueError, TypeError):
                year = "archive"

        ext = Path(metadata.file_name).suffix.lstrip(".").lower() or "bin"
        stem = Path(metadata.file_name).stem

        rendered = subpath_template.format(
            year=year,
            month=month,
            day=day,
            category=category.lower(),
            ext=ext,
            stem=stem,
            filename=metadata.file_name,
        )
        return rendered

    def classify(
        self,
        metadata: DocumentMetadata,
        content_snippet: str = "",
        default_tier: str = StorageTier.COLD_NAS.value,
    ) -> tuple[TaxonomyRule | None, str, str, str]:
        """Classify a document against configured rules.

        Returns: (matched_rule, category, target_tier, destination_subpath)
        """
        name_lower = metadata.file_name.lower()
        path_lower = metadata.file_path.lower()
        content_lower = content_snippet.lower()

        for rule in self.rules:
            # Check path pattern regex if provided
            if rule.path_pattern:
                try:
                    if re.search(rule.path_pattern, path_lower):
                        resolved = self.resolve_destination(rule.destination_subpath, metadata, rule.category)
                        return rule, rule.category, rule.target_tier, resolved
                except re.error:
                    pass

            # Check filename keywords
            if rule.name_keywords:
                if any(kw.lower() in name_lower for kw in rule.name_keywords):
                    resolved = self.resolve_destination(rule.destination_subpath, metadata, rule.category)
                    return rule, rule.category, rule.target_tier, resolved

            # Check content keywords
            if rule.content_keywords and content_lower:
                if any(kw.lower() in content_lower for kw in rule.content_keywords):
                    resolved = self.resolve_destination(rule.destination_subpath, metadata, rule.category)
                    return rule, rule.category, rule.target_tier, resolved

        # Default fallback
        fallback_subpath = f"Uncategorized/{metadata.file_name}"
        return None, DocumentCategory.UNCATEGORIZED.value, default_tier, fallback_subpath


class NASRouter:
    """Execution engine for file routing, verification, deduplication, and tier storage."""

    def __init__(
        self,
        classifier: TaxonomyClassifier,
        tier_configs: dict[str, StorageTierConfig],
        existing_hashes: set[str] | None = None,
    ):
        self.classifier = classifier
        self.tier_configs = tier_configs
        self.known_hashes = existing_hashes if existing_hashes is not None else set()

    def get_tier_root(self, tier_name: str) -> Path:
        """Resolve mount path for a given storage tier name."""
        if tier_name in self.tier_configs:
            return Path(self.tier_configs[tier_name].mount_path).resolve()
        # Fallback to local tier directory under current working dir
        return Path(f"./storage_tiers/{tier_name.lower()}").resolve()

    def _resolve_collision_name(self, dest_dir: Path, file_name: str, src_hash: str) -> Path:
        """Resolve filename collisions: if identical hash, return existing; else generate unique suffix."""
        dest_candidate = dest_dir / file_name
        if not dest_candidate.exists():
            return dest_candidate

        # Check existing destination hash
        try:
            existing_sha256, _ = compute_hashes(dest_candidate)
            if existing_sha256 == src_hash:
                return dest_candidate
        except (OSError, ValueError):
            pass

        # Hash differs: append numeric suffix
        stem = Path(file_name).stem
        suffix = Path(file_name).suffix
        counter = 1
        while True:
            candidate = dest_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            try:
                cand_sha256, _ = compute_hashes(candidate)
                if cand_sha256 == src_hash:
                    return candidate
            except (OSError, ValueError):
                pass
            counter += 1

    def route_document(
        self,
        file_path: str | Path,
        action: RouteAction = RouteAction.MOVE,
        content_snippet: str = "",
        verify_checksum: bool = True,
    ) -> tuple[DocumentMetadata, RouteExecution]:
        """Classify and route an individual document with integrity checks."""
        metadata = extract_metadata(file_path)
        rule, category, tier, subpath = self.classifier.classify(metadata, content_snippet=content_snippet)
        metadata.suggested_category = category
        metadata.suggested_tier = tier

        tier_root = self.get_tier_root(tier)
        dest_full = tier_root / subpath
        dest_dir = dest_full.parent

        timestamp = datetime.now(timezone.utc).isoformat()
        src_path = Path(metadata.file_path)

        # Check if already present in global known hash database
        is_duplicate = metadata.sha256 in self.known_hashes

        if is_duplicate and action != RouteAction.DRY_RUN:
            # Duplicate found
            exec_record = RouteExecution(
                source_path=str(src_path),
                dest_path=str(dest_full),
                action=action.value,
                category=category,
                tier=tier,
                sha256=metadata.sha256,
                status="SKIPPED_DUPLICATE",
                message=f"Duplicate content detected (SHA-256: {metadata.sha256[:12]}...). Storage preserved.",
                timestamp=timestamp,
            )
            return metadata, exec_record

        if action == RouteAction.DRY_RUN:
            exec_record = RouteExecution(
                source_path=str(src_path),
                dest_path=str(dest_full),
                action=action.value,
                category=category,
                tier=tier,
                sha256=metadata.sha256,
                status="SIMULATED",
                message=f"[DRY RUN] Would route to {dest_full} via {category} ({tier})",
                timestamp=timestamp,
            )
            return metadata, exec_record

        # Prepare destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_dest = self._resolve_collision_name(dest_dir, dest_full.name, metadata.sha256)

        try:
            if final_dest.exists() and compute_hashes(final_dest)[0] == metadata.sha256:
                # Same file already at destination
                if action == RouteAction.MOVE and src_path != final_dest:
                    src_path.unlink()
                exec_record = RouteExecution(
                    source_path=str(src_path),
                    dest_path=str(final_dest),
                    action=action.value,
                    category=category,
                    tier=tier,
                    sha256=metadata.sha256,
                    status="SUCCESS",
                    message=f"Identical file already in target tier. Source cleaned up: {final_dest}",
                    timestamp=timestamp,
                )
                self.known_hashes.add(metadata.sha256)
                return metadata, exec_record

            if action == RouteAction.COPY:
                shutil.copy2(src_path, final_dest)
            elif action == RouteAction.MOVE:
                shutil.move(src_path, final_dest)
            elif action == RouteAction.SYMLINK:
                if final_dest.exists() or final_dest.is_symlink():
                    final_dest.unlink()
                os.symlink(src_path.resolve(), final_dest)
            elif action == RouteAction.HARDLINK:
                if final_dest.exists():
                    final_dest.unlink()
                os.link(src_path.resolve(), final_dest)

            # Integrity verification
            if verify_checksum and action in (RouteAction.COPY, RouteAction.MOVE):
                dest_sha, _ = compute_hashes(final_dest)
                if dest_sha != metadata.sha256:
                    raise ValueError(f"Checksum mismatch: source {metadata.sha256} != dest {dest_sha}")

            self.known_hashes.add(metadata.sha256)
            exec_record = RouteExecution(
                source_path=str(src_path),
                dest_path=str(final_dest),
                action=action.value,
                category=category,
                tier=tier,
                sha256=metadata.sha256,
                status="SUCCESS",
                message=f"Successfully routed to {final_dest}",
                timestamp=timestamp,
            )
        except (OSError, ValueError, shutil.Error) as err:
            exec_record = RouteExecution(
                source_path=str(src_path),
                dest_path=str(final_dest),
                action=action.value,
                category=category,
                tier=tier,
                sha256=metadata.sha256,
                status="FAILED",
                message=f"Routing failed: {err}",
                timestamp=timestamp,
            )

        return metadata, exec_record

    def scan_and_route_directory(
        self,
        source_dir: str | Path,
        action: RouteAction = RouteAction.DRY_RUN,
        recursive: bool = True,
        verify_checksum: bool = True,
    ) -> AuditReport:
        """Scan a directory, classify and route all discovered documents, generating an audit report."""
        src_path = Path(source_dir).resolve()
        if not src_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {src_path}")

        files_to_process: list[Path] = []
        if recursive:
            for root, _, files in os.walk(src_path):
                for f in files:
                    files_to_process.append(Path(root) / f)
        else:
            files_to_process = [p for p in src_path.iterdir() if p.is_file()]

        # Sort for deterministic processing
        files_to_process.sort()

        total_files = len(files_to_process)
        total_bytes = 0
        routed_count = 0
        duplicate_count = 0
        space_saved = 0
        tier_counts: dict[str, int] = {}
        cat_counts: dict[str, int] = {}
        executions: list[RouteExecution] = []

        for file_item in files_to_process:
            try:
                # Read short text snippet if plain text or log
                snippet = ""
                if file_item.suffix.lower() in (".txt", ".log", ".json", ".csv", ".md", ".yaml", ".yml"):
                    try:
                        with file_item.open("r", encoding="utf-8", errors="ignore") as f:
                            snippet = f.read(4096)
                    except OSError:
                        pass

                meta, result = self.route_document(
                    file_item,
                    action=action,
                    content_snippet=snippet,
                    verify_checksum=verify_checksum,
                )
                total_bytes += meta.size_bytes
                executions.append(result)

                if result.status in ("SUCCESS", "SIMULATED"):
                    routed_count += 1
                    tier_counts[result.tier] = tier_counts.get(result.tier, 0) + 1
                    cat_counts[result.category] = cat_counts.get(result.category, 0) + 1
                elif result.status == "SKIPPED_DUPLICATE":
                    duplicate_count += 1
                    space_saved += meta.size_bytes
            except (OSError, ValueError):
                continue

        return AuditReport(
            total_files_scanned=total_files,
            total_bytes_scanned=total_bytes,
            routed_files_count=routed_count,
            duplicate_files_count=duplicate_count,
            space_saved_bytes=space_saved,
            tier_breakdown=tier_counts,
            category_breakdown=cat_counts,
            executions=executions,
        )
