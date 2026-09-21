"""Duplicate detection algorithms: exact checksum, name/size, fuzzy revision, and zero-byte audits."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from drivemesh.models import DriveFile, DuplicateGroup, DuplicateType, ResolutionAction

RE_VERSION_PATTERN = re.compile(
    r"(?i)(?:^copy\s+of\s+|_copy\b|\s+copy\b|\s*\(\d+\)|[-_]v\d+(?:\.\d+)?|[-_]final(?:\d+)?|[-_]draft|[-_]backup|[-_]\d{4}[-_]\d{2}[-_]\d{2})",
)


def normalize_filename(name: str) -> str:
    """Normalize file name by stripping version tags, copy counters, and dates."""
    p = Path(name)
    stem = p.stem
    ext = p.suffix.lower()

    # Repeatedly strip known version/copy affixes
    cleaned = RE_VERSION_PATTERN.sub("", stem)
    # Clean redundant punctuation and spaces
    cleaned = re.sub(r"[\s_.-]+", "_", cleaned).strip("_- .").lower()
    return f"{cleaned}{ext}" if cleaned else stem.lower() + ext


class DuplicateDetector:
    """Engine for identifying exact, size-matched, fuzzy versioned, and zero-byte duplicates."""

    def __init__(self, files: list[DriveFile]) -> None:
        self.files = files
        self.files_by_id = {f.id: f for f in files}

    def _select_canonical(self, candidate_ids: list[str]) -> str:
        """Pick the best canonical file: prefer organized path depth, then newest modified time."""
        candidates = [self.files_by_id[cid] for cid in candidate_ids if cid in self.files_by_id]
        if not candidates:
            return candidate_ids[0]

        def sort_key(f: DriveFile) -> tuple[int, int, str]:
            # Favor deeper non-root paths (fewer slashes at root means shallow)
            path_depth = f.path_hierarchy.count("/") if f.path_hierarchy and f.path_hierarchy != "/" else 0
            # Deprecate names starting with "Copy of" or containing "(1)"
            name_penalty = 1 if ("copy" in f.name.lower() or "(" in f.name) else 0
            # Then modified time
            mtime = f.modified_time or ""
            return (-name_penalty, path_depth, mtime)

        sorted_candidates = sorted(candidates, key=sort_key, reverse=True)
        return sorted_candidates[0].id

    def find_exact_checksum_duplicates(self) -> list[DuplicateGroup]:
        """Find files with identical non-empty checksums."""
        hash_map: dict[str, list[str]] = defaultdict(list)
        for f in self.files:
            if f.size_bytes > 0:
                key = f.sha256_checksum or f.md5_checksum
                if key:
                    hash_map[key].append(f.id)

        groups: list[DuplicateGroup] = []
        for key, ids in hash_map.items():
            if len(ids) > 1:
                canonical = self._select_canonical(ids)
                dups = [fid for fid in ids if fid != canonical]
                sample_file = self.files_by_id[canonical]
                wasted = sum(self.files_by_id[fid].size_bytes for fid in dups)
                groups.append(
                    DuplicateGroup(
                        group_id=f"exact_{key[:12]}",
                        canonical_file_id=canonical,
                        duplicate_file_ids=dups,
                        duplicate_type=DuplicateType.EXACT_CHECKSUM,
                        wasted_bytes=wasted,
                        resolution_suggestion=ResolutionAction.DELETE_DUPLICATES,
                        explanation=f"Exact binary match across {len(ids)} files for '{sample_file.name}'",
                    )
                )
        return groups

    def find_name_and_size_duplicates(self, exclude_ids: set[str] | None = None) -> list[DuplicateGroup]:
        """Find files with identical filename and size when checksums are absent."""
        excluded = exclude_ids or set()
        name_size_map: dict[tuple[str, int], list[str]] = defaultdict(list)

        for f in self.files:
            if f.id in excluded or f.size_bytes == 0:
                continue
            name_size_map[(f.name.lower(), f.size_bytes)].append(f.id)

        groups: list[DuplicateGroup] = []
        for (name, size), ids in name_size_map.items():
            if len(ids) > 1:
                canonical = self._select_canonical(ids)
                dups = [fid for fid in ids if fid != canonical]
                groups.append(
                    DuplicateGroup(
                        group_id=f"namesize_{abs(hash((name, size))) & 0xFFFFFFFF:08x}",
                        canonical_file_id=canonical,
                        duplicate_file_ids=dups,
                        duplicate_type=DuplicateType.NAME_AND_SIZE,
                        wasted_bytes=size * len(dups),
                        resolution_suggestion=ResolutionAction.DELETE_DUPLICATES,
                        explanation=f"Matching name and exact byte size ({size} bytes) across {len(ids)} locations",
                    )
                )
        return groups

    def find_fuzzy_version_duplicates(self, exclude_ids: set[str] | None = None) -> list[DuplicateGroup]:
        """Group related revisions, draft iterations, and numbered copies."""
        excluded = exclude_ids or set()
        norm_map: dict[str, list[str]] = defaultdict(list)

        for f in self.files:
            if f.id in excluded or f.size_bytes == 0:
                continue
            norm_name = normalize_filename(f.name)
            norm_map[norm_name].append(f.id)

        groups: list[DuplicateGroup] = []
        for norm_name, ids in norm_map.items():
            if len(ids) > 1:
                canonical = self._select_canonical(ids)
                dups = [fid for fid in ids if fid != canonical]
                wasted = sum(self.files_by_id[fid].size_bytes for fid in dups)
                groups.append(
                    DuplicateGroup(
                        group_id=f"fuzzy_{abs(hash(norm_name)) & 0xFFFFFFFF:08x}",
                        canonical_file_id=canonical,
                        duplicate_file_ids=dups,
                        duplicate_type=DuplicateType.FUZZY_VERSION,
                        wasted_bytes=wasted,
                        resolution_suggestion=ResolutionAction.ARCHIVE_HISTORICAL,
                        explanation=f"Version iteration chain for base artifact '{norm_name}' ({len(ids)} versions)",
                    )
                )
        return groups

    def find_zero_byte_ghosts(self) -> list[DuplicateGroup]:
        """Identify empty zero-byte files that waste metadata and clutter directories."""
        zero_files = [f for f in self.files if f.size_bytes == 0]
        if not zero_files:
            return []

        return [
            DuplicateGroup(
                group_id="zerobyte_ghosts",
                canonical_file_id="",
                duplicate_file_ids=[f.id for f in zero_files],
                duplicate_type=DuplicateType.ORPHAN_ZERO_BYTE,
                wasted_bytes=0,
                resolution_suggestion=ResolutionAction.PURGE_EMPTY,
                explanation=f"{len(zero_files)} zero-byte ghost files detected with no data content",
            )
        ]

    def run_all(self) -> list[DuplicateGroup]:
        """Execute full duplicate detection pipeline with progressive exclusion."""
        all_groups: list[DuplicateGroup] = []
        handled_file_ids: set[str] = set()

        # 1. Exact Checksums
        exact = self.find_exact_checksum_duplicates()
        all_groups.extend(exact)
        for g in exact:
            handled_file_ids.add(g.canonical_file_id)
            handled_file_ids.update(g.duplicate_file_ids)

        # 2. Name & Size
        name_size = self.find_name_and_size_duplicates(exclude_ids=handled_file_ids)
        all_groups.extend(name_size)
        for g in name_size:
            handled_file_ids.add(g.canonical_file_id)
            handled_file_ids.update(g.duplicate_file_ids)

        # 3. Fuzzy Versions
        fuzzy = self.find_fuzzy_version_duplicates(exclude_ids=handled_file_ids)
        all_groups.extend(fuzzy)

        # 4. Zero-byte files
        ghosts = self.find_zero_byte_ghosts()
        all_groups.extend(ghosts)

        return all_groups
