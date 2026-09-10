# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for cryptographic and sparse hashing algorithms.
"""

from pathlib import Path

from sparsededup.hasher import calculate_full_hash, calculate_sparse_hash


def test_sparse_hash_small_file(tmp_path: Path):
    """Small files below 3 * block_size should hash the whole content."""
    test_file = tmp_path / "small.dat"
    content = b"Hello, World! " * 100
    test_file.write_bytes(content)

    h1 = calculate_sparse_hash(test_file, len(content), block_size=1024)
    h2 = calculate_sparse_hash(test_file, len(content), block_size=1024)
    assert h1 is not None
    assert h1 == h2


def test_sparse_hash_large_file(tmp_path: Path):
    """Large files should sample head, midpoint, and tail correctly."""
    test_file1 = tmp_path / "large1.dat"
    test_file2 = tmp_path / "large2.dat"
    test_file3 = tmp_path / "large3.dat"

    block_size = 1024
    total_size = block_size * 10

    # File 1 & File 2: Identical blocks at head, midpoint, tail
    base_data = bytearray(total_size)
    base_data[:block_size] = b"A" * block_size
    base_data[total_size // 2 : total_size // 2 + block_size] = b"M" * block_size
    base_data[-block_size:] = b"Z" * block_size

    test_file1.write_bytes(base_data)
    test_file2.write_bytes(base_data)

    # File 3: Modified midpoint
    mod_data = bytearray(base_data)
    mod_data[total_size // 2 : total_size // 2 + block_size] = b"X" * block_size
    test_file3.write_bytes(mod_data)

    h1 = calculate_sparse_hash(test_file1, total_size, block_size=block_size)
    h2 = calculate_sparse_hash(test_file2, total_size, block_size=block_size)
    h3 = calculate_sparse_hash(test_file3, total_size, block_size=block_size)

    assert h1 is not None
    assert h1 == h2
    assert h1 != h3


def test_full_hash_sha256(tmp_path: Path):
    """Verify streaming SHA-256 calculation."""
    f1 = tmp_path / "f1.bin"
    f2 = tmp_path / "f2.bin"

    f1.write_bytes(b"Exact duplicate payload")
    f2.write_bytes(b"Exact duplicate payload")

    h1 = calculate_full_hash(f1)
    h2 = calculate_full_hash(f2)

    assert h1 is not None
    assert h1 == h2


def test_hash_nonexistent_file(tmp_path: Path):
    """Gracefully handle missing files."""
    missing = tmp_path / "does_not_exist.bin"
    assert calculate_sparse_hash(missing, 100) is None
    assert calculate_full_hash(missing) is None
