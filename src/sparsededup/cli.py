# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) entrypoint for sparsededup.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from . import __version__
from .actions import (
    apply_deletion,
    apply_hardlinks,
    apply_symlinks,
    export_json_manifest,
    format_bytes,
)
from .core import DeduplicationScanner


def parse_size(size_str: str) -> int:
    """Parse human-friendly size strings like 10MB, 500KB, 2GB into integer bytes."""
    size_str = size_str.strip().upper()
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([KMGTPE]?B?)$", size_str)
    if not match:
        raise ValueError(f"Invalid size string: '{size_str}'. Use format like 100KB, 10MB, 1GB.")

    num, unit = match.groups()
    val = float(num)
    unit_multipliers = {
        "": 1,
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "T": 1024**4,
        "TB": 1024**4,
        "P": 1024**5,
        "PB": 1024**5,
        "E": 1024**6,
        "EB": 1024**6,
    }
    multiplier = unit_multipliers.get(unit, 1)
    return int(val * multiplier)


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  sparsededup v{__version__:<10}                                    │
│  High-Throughput Sparse-Block Deduplication Engine          │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="sparsededup",
        description="High-Throughput Sparse-Block Deduplication & Integrity Scanner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sparsededup /mnt/media /mnt/backup --dry-run
  sparsededup /data/videos --min-size 100MB --json-out manifest.json
  sparsededup /data/library --hardlink --min-size 1MB
  sparsededup /data/staging --delete --confirm
""",
    )

    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more directories or files to scan for duplicate data.",
    )
    parser.add_argument(
        "--min-size",
        type=str,
        default="1B",
        help="Minimum file size to evaluate (e.g. 100KB, 10MB, 1GB). Default: 1B.",
    )
    parser.add_argument(
        "--max-size",
        type=str,
        default=None,
        help="Maximum file size to evaluate (e.g. 50GB). Default: None.",
    )
    parser.add_argument(
        "--include",
        nargs="+",
        default=["*"],
        help="File inclusion glob patterns (e.g. '*.mp4' '*.mkv' '*.iso').",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="File/Directory exclusion glob patterns (e.g. '.*' '*.tmp' 'cache*').",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow filesystem symbolic links during recursion.",
    )

    # Action modes
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Scan and report duplicate clusters without modifying files (default).",
    )
    action_group.add_argument(
        "--hardlink",
        action="store_true",
        help="Replace duplicate copies with atomic hardlinks to the canonical copy.",
    )
    action_group.add_argument(
        "--symlink",
        action="store_true",
        help="Replace duplicate copies with symbolic links to the canonical copy.",
    )
    action_group.add_argument(
        "--delete",
        action="store_true",
        help="Delete duplicate redundant files (leaves the canonical oldest file).",
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Bypass interactive confirmation prompt when running --delete or --hardlink.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Path to export structured scan results as a JSON manifest.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results to stdout for script pipelines.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress banner and non-essential progress output.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"sparsededup {__version__}",
    )

    args = parser.parse_args(argv)

    try:
        min_bytes = parse_size(args.min_size)
        max_bytes = parse_size(args.max_size) if args.max_size else None
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not args.quiet and not args.json:
        print_banner()

    def progress_callback(event: str, current: int, total: int):
        if args.quiet or args.json:
            return
        if event == "stage1_done":
            print(f"[+] Stage 1 (Discovery): Scanned {current} files. Found {total} size candidates.")
        elif event == "stage2_start":
            print(f"[*] Stage 2 (Sparse Hash): Evaluating {total} candidates with 3-block sampling...")
        elif event == "stage2_done":
            print(f"[+] Stage 2 (Sparse Hash): {total} candidate files matched sparse signatures.")
        elif event == "stage3_start":
            print(f"[*] Stage 3 (Full SHA-256): Cryptographically validating {total} files...")
        elif event == "stage3_done":
            print(f"[+] Stage 3 (Full SHA-256): Identified {total} verified duplicate cluster(s).\n")

    scanner = DeduplicationScanner(
        paths=args.paths,
        min_size=min_bytes,
        max_size=max_bytes,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        follow_symlinks=args.follow_symlinks,
        progress_callback=progress_callback,
    )

    result = scanner.scan()

    if args.json_out:
        export_json_manifest(result, args.json_out)
        if not args.quiet and not args.json:
            print(f"[i] Manifest written to: {args.json_out}")

    if args.json:
        manifest_dict = {
            "summary": {
                "scanned_files": result.scanned_files_count,
                "scanned_bytes": result.scanned_total_bytes,
                "duplicate_files": result.total_duplicate_files,
                "reclaimable_bytes": result.total_reclaimable_bytes,
                "duplicate_clusters": len(result.duplicate_clusters),
            },
            "clusters": [
                {
                    "full_hash": c.full_hash,
                    "file_size": c.file_size,
                    "canonical_file": str(c.canonical_file.path),
                    "duplicates": [str(d.path) for d in c.duplicates],
                }
                for c in result.duplicate_clusters
            ],
            "errors": result.errors,
        }
        print(json.dumps(manifest_dict, indent=2))
        return 0

    # Display Report
    print("=" * 63)
    print("                      SCAN SUMMARY                      ")
    print("=" * 63)
    print(f"  Total Files Scanned      : {result.scanned_files_count:,}")
    print(f"  Total Data Scanned       : {format_bytes(result.scanned_total_bytes)}")
    print(f"  Duplicate Clusters Found : {len(result.duplicate_clusters):,}")
    print(f"  Redundant Duplicate Files: {result.total_duplicate_files:,}")
    print(f"  Reclaimable Disk Space   : {format_bytes(result.total_reclaimable_bytes)}")
    print("=" * 63)

    if result.duplicate_clusters:
        print("\n--- Identified Duplicate Clusters ---")
        for idx, cluster in enumerate(result.duplicate_clusters, 1):
            print(f"\n[Cluster #{idx}] Size: {format_bytes(cluster.file_size)} | SHA-256: {cluster.full_hash[:12]}...")
            print(f"  [CANONICAL] {cluster.canonical_file.path}")
            for dup in cluster.duplicates:
                print(f"  [DUPLICATE] {dup.path}")

    if result.errors:
        print("\n[!] Warnings/Errors encountered during scan:")
        for err in result.errors:
            print(f"  - {err}")

    # Execution Actions
    if args.hardlink:
        if not args.confirm:
            ans = input(f"\nProceed to HARDLINK {result.total_duplicate_files} duplicate files? [y/N]: ").strip().lower()
            if ans != "y":
                print("Action cancelled.")
                return 0
        action_res = apply_hardlinks(result)
        print(f"\n[✓] Hardlinked {action_res.processed_files} files. Reclaimed: {format_bytes(action_res.reclaimed_bytes)}")

    elif args.symlink:
        if not args.confirm:
            ans = input(f"\nProceed to SYMLINK {result.total_duplicate_files} duplicate files? [y/N]: ").strip().lower()
            if ans != "y":
                print("Action cancelled.")
                return 0
        action_res = apply_symlinks(result)
        print(f"\n[✓] Symlinked {action_res.processed_files} files. Reclaimed: {format_bytes(action_res.reclaimed_bytes)}")

    elif args.delete:
        if not args.confirm:
            ans = input(f"\n⚠️  Proceed to PERMANENTLY DELETE {result.total_duplicate_files} files? [y/N]: ").strip().lower()
            if ans != "y":
                print("Action cancelled.")
                return 0
        action_res = apply_deletion(result)
        print(f"\n[✓] Deleted {action_res.processed_files} redundant files. Reclaimed: {format_bytes(action_res.reclaimed_bytes)}")

    else:
        print("\n[i] Mode: Dry Run (No filesystem modifications made).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
