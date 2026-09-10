# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Data structures and models for sparsededup.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileCandidate:
    """Represents a discovered file candidate during scanning."""
    path: Path
    size: int
    inode: int | None = None
    device: int | None = None
    sparse_hash: str | None = None
    full_hash: str | None = None
    mtime: float = 0.0

    @property
    def is_hardlink_candidate(self) -> bool:
        """Return True if inode and device info are present."""
        return self.inode is not None and self.device is not None


@dataclass
class DuplicateCluster:
    """A cluster of confirmed identical duplicate files."""
    canonical_file: FileCandidate
    duplicates: list[FileCandidate] = field(default_factory=list)
    file_size: int = 0
    full_hash: str = ""

    @property
    def total_reclaimable_bytes(self) -> int:
        """Calculate total reclaimable disk space in bytes."""
        return len(self.duplicates) * self.file_size

    @property
    def member_count(self) -> int:
        """Total number of files in this duplicate cluster including canonical."""
        return len(self.duplicates) + 1
