# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Core deduplication scanning and analysis engine.
"""

import fnmatch
import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .hasher import calculate_full_hash, calculate_sparse_hash
from .models import DuplicateCluster, FileCandidate


@dataclass
class ScanResult:
    """Summary and details of a deduplication scan."""
    scanned_files_count: int = 0
    scanned_total_bytes: int = 0
    size_matched_count: int = 0
    sparse_hashed_count: int = 0
    full_hashed_count: int = 0
    duplicate_clusters: list[DuplicateCluster] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_duplicate_files(self) -> int:
        """Count of redundant duplicate files across all clusters."""
        return sum(len(cluster.duplicates) for cluster in self.duplicate_clusters)

    @property
    def total_reclaimable_bytes(self) -> int:
        """Total disk space that can be reclaimed."""
        return sum(cluster.total_reclaimable_bytes for cluster in self.duplicate_clusters)


class DeduplicationScanner:
    """
    3-Stage High-Throughput Deduplication Scanner.
    Stage 1: Size grouping (O(1) memory bucketing)
    Stage 2: 3-point sparse hashing (header, midpoint, footer)
    Stage 3: Full cryptographic SHA-256 streaming validation
    """

    def __init__(
        self,
        paths: list[Path],
        min_size: int = 1,
        max_size: int | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        follow_symlinks: bool = False,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ):
        self.paths = [Path(p).resolve() for p in paths]
        self.min_size = min_size
        self.max_size = max_size
        self.include_patterns = include_patterns or ["*"]
        self.exclude_patterns = exclude_patterns or []
        self.follow_symlinks = follow_symlinks
        self.progress_callback = progress_callback

    def _should_include(self, file_path: Path) -> bool:
        """Check if file matches inclusion/exclusion criteria."""
        name = file_path.name
        str_path = str(file_path)

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str_path, pattern):
                return False

        if self.include_patterns != ["*"]:
            matched = any(
                fnmatch.fnmatch(name, p) or fnmatch.fnmatch(str_path, p)
                for p in self.include_patterns
            )
            if not matched:
                return False

        return True

    def scan(self) -> ScanResult:
        """Execute full 3-stage scanning pipeline."""
        result = ScanResult()
        size_buckets: dict[int, list[FileCandidate]] = defaultdict(list)
        seen_inodes: set[tuple[int, int]] = set()

        # --- Stage 1: Discovery & Size Partitioning ---
        self._notify("stage1_start", 0, 0)
        for base_path in self.paths:
            if not base_path.exists():
                result.errors.append(f"Target path does not exist: {base_path}")
                continue

            if base_path.is_file():
                self._process_file(base_path, size_buckets, seen_inodes, result)
            else:
                for root, dirs, files in os.walk(base_path, followlinks=self.follow_symlinks):
                    # Filter out hidden or excluded directories in place
                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith(".") and not any(
                            fnmatch.fnmatch(d, p) for p in self.exclude_patterns
                        )
                    ]
                    for filename in files:
                        file_path = Path(root) / filename
                        self._process_file(file_path, size_buckets, seen_inodes, result)

        # Discard unique sizes
        candidate_buckets = {k: v for k, v in size_buckets.items() if len(v) > 1}
        result.size_matched_count = sum(len(v) for v in candidate_buckets.values())
        self._notify("stage1_done", result.scanned_files_count, result.size_matched_count)

        if not candidate_buckets:
            return result

        # --- Stage 2: Sparse 3-Block Hashing ---
        self._notify("stage2_start", 0, result.size_matched_count)
        sparse_buckets: dict[str, list[FileCandidate]] = defaultdict(list)
        processed_sparse = 0

        for file_size, candidates in candidate_buckets.items():
            for candidate in candidates:
                s_hash = calculate_sparse_hash(candidate.path, file_size)
                processed_sparse += 1
                self._notify("stage2_progress", processed_sparse, result.size_matched_count)

                if s_hash:
                    candidate.sparse_hash = s_hash
                    sparse_buckets[f"{file_size}:{s_hash}"].append(candidate)
                else:
                    result.errors.append(f"Failed to read sparse blocks: {candidate.path}")

        # Discard unique sparse hashes
        sparse_candidates = {k: v for k, v in sparse_buckets.items() if len(v) > 1}
        result.sparse_hashed_count = processed_sparse
        self._notify("stage2_done", processed_sparse, sum(len(v) for v in sparse_candidates.values()))

        if not sparse_candidates:
            return result

        # --- Stage 3: Full Cryptographic SHA-256 Verification ---
        candidate_count_for_full = sum(len(v) for v in sparse_candidates.values())
        self._notify("stage3_start", 0, candidate_count_for_full)
        full_buckets: dict[str, list[FileCandidate]] = defaultdict(list)
        processed_full = 0

        for candidates in sparse_candidates.values():
            for candidate in candidates:
                f_hash = calculate_full_hash(candidate.path)
                processed_full += 1
                self._notify("stage3_progress", processed_full, candidate_count_for_full)

                if f_hash:
                    candidate.full_hash = f_hash
                    full_buckets[f_hash].append(candidate)
                else:
                    result.errors.append(f"Failed to compute full hash: {candidate.path}")

        result.full_hashed_count = processed_full

        # Construct final duplicate clusters
        for full_hash, members in full_buckets.items():
            if len(members) > 1:
                # Sort members by mtime ascending (oldest is canonical)
                members.sort(key=lambda m: (m.mtime, str(m.path)))
                canonical = members[0]
                duplicates = members[1:]
                cluster = DuplicateCluster(
                    canonical_file=canonical,
                    duplicates=duplicates,
                    file_size=canonical.size,
                    full_hash=full_hash,
                )
                result.duplicate_clusters.append(cluster)

        self._notify("stage3_done", processed_full, len(result.duplicate_clusters))
        return result

    def _process_file(
        self,
        path: Path,
        size_buckets: dict[int, list[FileCandidate]],
        seen_inodes: set[tuple[int, int]],
        result: ScanResult
    ) -> None:
        """Inspect and register a file candidate."""
        try:
            if not self.follow_symlinks and path.is_symlink():
                return
            if not self._should_include(path):
                return

            stat = path.stat()
            size = stat.st_size
            mtime = stat.st_mtime

            # Filter by size bounds
            if size < self.min_size:
                return
            if self.max_size is not None and size > self.max_size:
                return

            # Inode tracking (prevent double-counting already hardlinked files)
            inode_key = (stat.st_dev, stat.st_ino)
            if inode_key in seen_inodes:
                return
            seen_inodes.add(inode_key)

            result.scanned_files_count += 1
            result.scanned_total_bytes += size

            candidate = FileCandidate(
                path=path,
                size=size,
                inode=stat.st_ino,
                device=stat.st_dev,
                mtime=mtime,
            )
            size_buckets[size].append(candidate)
        except (OSError, PermissionError) as e:
            result.errors.append(f"Cannot access {path}: {e}")

    def _notify(self, event: str, current: int, total: int) -> None:
        """Call progress callback if registered."""
        if self.progress_callback:
            self.progress_callback(event, current, total)
