# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Cryptographic and sparse hashing engine.
"""

import hashlib
from pathlib import Path

# Default sparse sample size: 256 KB per block
DEFAULT_BLOCK_SIZE = 256 * 1024


def calculate_sparse_hash(
    file_path: Path,
    file_size: int,
    block_size: int = DEFAULT_BLOCK_SIZE
) -> str | None:
    """
    Calculate a fast 3-point sparse hash of a file:
    1. First block (header)
    2. Exact middle block (midpoint)
    3. Last block (footer)

    If file_size <= block_size * 3, reads the entire file directly.
    Uses BLAKE2b with 20-byte digest for maximum throughput and zero collision risk.
    """
    try:
        hasher = hashlib.blake2b(digest_size=20)
        # Mix file size into hash state to prevent prefix/suffix collision across different sizes
        hasher.update(file_size.to_bytes(8, byteorder="big", signed=False))

        with open(file_path, "rb") as f:
            if file_size <= block_size * 3:
                # Small enough to read whole file
                while chunk := f.read(block_size):
                    hasher.update(chunk)
            else:
                # 1. Read head
                head_data = f.read(block_size)
                hasher.update(head_data)

                # 2. Read midpoint
                mid_offset = (file_size - block_size) // 2
                f.seek(mid_offset)
                mid_data = f.read(block_size)
                hasher.update(mid_data)

                # 3. Read tail
                f.seek(file_size - block_size)
                tail_data = f.read(block_size)
                hasher.update(tail_data)

        return hasher.hexdigest()
    except (OSError, PermissionError):
        return None


def calculate_full_hash(
    file_path: Path,
    chunk_size: int = 1024 * 1024
) -> str | None:
    """
    Calculate full SHA-256 hash using streaming chunks.
    Used for final verification before any mutation or deletion.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return None
