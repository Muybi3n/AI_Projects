# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
sparsededup - High-Throughput Sparse-Block Deduplication & Integrity Scanner.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .core import DeduplicationScanner, ScanResult
from .hasher import calculate_full_hash, calculate_sparse_hash
from .models import DuplicateCluster, FileCandidate

__all__ = [
    "DeduplicationScanner",
    "DuplicateCluster",
    "FileCandidate",
    "ScanResult",
    "calculate_full_hash",
    "calculate_sparse_hash",
]
