"""Command-line interface for drivemesh-core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from drivemesh.advisor import DriveMeshAdvisor
from drivemesh.cluster import SubjectClusterer
from drivemesh.duplicates import DuplicateDetector
from drivemesh.importer import DriveImporter
from drivemesh.storage import DriveStorage


def format_bytes(num_bytes: int) -> str:
    """Format bytes to human readable format."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def cmd_scan(args: argparse.Namespace) -> None:
    """Scan and ingest files into local database."""
    storage = DriveStorage(args.db)
    source_path = Path(args.source)

    if not source_path.exists():
        print(f"❌ Error: Source path does not exist: {args.source}", file=sys.stderr)
        sys.exit(1)

    print(f"📥 Scanning metadata from: {source_path}...")
    if source_path.is_dir():
        files, folders = DriveImporter.scan_directory(source_path)
        storage.save_folders(folders)
    elif source_path.suffix.lower() == ".csv":
        files = DriveImporter.load_from_csv(source_path)
    else:
        files = DriveImporter.load_from_json(source_path)

    storage.save_files(files)

    # Automatically cluster and detect duplicates
    clusterer = SubjectClusterer(files)
    clusters = clusterer.cluster_all()
    storage.save_clusters(clusters)

    detector = DuplicateDetector(files)
    dups = detector.run_all()
    storage.save_duplicates(dups)

    print(f"✅ Ingestion complete: {len(files)} files indexed into SQLite ({args.db}).")


def cmd_cluster(args: argparse.Namespace) -> None:
    """Run subject clustering and print taxonomy mesh."""
    storage = DriveStorage(args.db)
    files = storage.load_files()
    if not files:
        print("⚠️ No files indexed yet. Run `drivemesh scan <path>` or `drivemesh demo` first.")
        return

    clusterer = SubjectClusterer(files)
    clusters = clusterer.cluster_all()
    storage.save_clusters(clusters)

    print("\n🗂️  === DISCOVERED SUBJECT CLUSTERS & TAXONOMY MESH ===")
    for c in clusters:
        size_str = format_bytes(c.total_size_bytes)
        print(f"\n📂 [{c.category.value}] - {c.label}")
        print(f"   ├─ Suggested Target: `{c.suggested_target_path}`")
        print(f"   ├─ Files: {len(c.file_ids)} | Total Size: {size_str} | Confidence: {int(c.confidence_score * 100)}%")
        # Show first 3 sample files
        sample_files = [f for f in files if f.id in c.file_ids][:3]
        for sf in sample_files:
            print(f"   │  • {sf.name} ({format_bytes(sf.size_bytes)})")
        if len(c.file_ids) > 3:
            print(f"   │  ... and {len(c.file_ids) - 3} more files")


def cmd_duplicates(args: argparse.Namespace) -> None:
    """Detect and display duplicate files."""
    storage = DriveStorage(args.db)
    files = storage.load_files()
    if not files:
        print("⚠️ No files indexed yet. Run `drivemesh scan <path>` or `drivemesh demo` first.")
        return

    detector = DuplicateDetector(files)
    groups = detector.run_all()
    storage.save_duplicates(groups)

    if args.type != "all":
        groups = [g for g in groups if g.duplicate_type.value.lower() == args.type.lower()]

    print(f"\n🔍 === DUPLICATE AUDIT REPORT ({len(groups)} Groups Detected) ===")
    total_wasted = sum(g.wasted_bytes for g in groups)
    print(f"💾 Total Reclaimable Space: {format_bytes(total_wasted)}\n")

    files_by_id = {f.id: f for f in files}
    for g in groups:
        print(f"📌 [{g.duplicate_type.value}] {g.explanation}")
        if g.canonical_file_id and g.canonical_file_id in files_by_id:
            cf = files_by_id[g.canonical_file_id]
            print(f"   ⭐ Keep Canonical: {cf.name} (Path: {cf.path_hierarchy})")
        for dup_id in g.duplicate_file_ids:
            if dup_id in files_by_id:
                df = files_by_id[dup_id]
                print(f"   🗑️  Duplicate: {df.name} (Path: {df.path_hierarchy})")
        print(f"   ⚡ Action: {g.resolution_suggestion.value} | Wasted: {format_bytes(g.wasted_bytes)}\n")


def cmd_audit(args: argparse.Namespace) -> None:
    """Run comprehensive drive health and storage audit."""
    storage = DriveStorage(args.db)
    report = storage.get_audit_summary()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    print("\n" + "=" * 60)
    print("📊 GOOGLE DRIVE / CLOUD STORAGE HEALTH & MESH AUDIT")
    print("=" * 60)
    print(f"🏆 Health Score:             {report.health_score} / 100")
    print(f"📁 Total Files Indexed:       {report.total_files}")
    print(f"💾 Total Storage Used:        {format_bytes(report.total_storage_bytes)}")
    print(f"🧹 Reclaimable Space:         {format_bytes(report.reclaimable_bytes)}")
    print(f"⚠️  Duplicate Groups:          {report.duplicate_groups_count}")
    print(f"🏚️  Orphaned Root Clutter:     {report.orphaned_root_files_count} files")
    print(f"👻 Zero-Byte Ghost Files:     {report.zero_byte_files_count} files")
    print(f"👥 Shared Files:              {report.shared_files_count} files")

    print("\n📂 Category Distribution:")
    for cat, count in report.top_categories.items():
        print(f"   • {cat:<25}: {count} files")

    print("\n💡 Actionable Recommendations:")
    for idx, rec in enumerate(report.recommendations, 1):
        print(f"   {idx}. {rec}")
    print("=" * 60)


def cmd_plan(args: argparse.Namespace) -> None:
    """Generate reorganization move plan and deletion manifest."""
    storage = DriveStorage(args.db)
    files = storage.load_files()
    if not files:
        print("⚠️ No files indexed yet. Run `drivemesh scan <path>` or `drivemesh demo` first.")
        return

    detector = DuplicateDetector(files)
    dup_groups = detector.run_all()
    deletion_ids: list[str] = []
    for g in dup_groups:
        deletion_ids.extend(g.duplicate_file_ids)

    clusterer = SubjectClusterer(files)
    plan = clusterer.build_mesh_plan(duplicate_deletions=deletion_ids)

    if args.out:
        out_path = Path(args.out)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2)
        print(f"✅ Mesh execution plan saved to: {out_path}")
    else:
        print(f"\n📋 === DRIVE RESTRUCTURING PLAN ({plan.plan_id}) ===")
        print(f"🔄 Proposed Relocations: {len(plan.proposed_moves)}")
        print(f"🗑️  Proposed Deletions:   {len(plan.proposed_deletions)}")
        print(f"💾 Storage Reclaimable:  {format_bytes(plan.total_reclaimable_bytes)}\n")
        for m in plan.proposed_moves[:5]:
            print(f"➡️  MOVE: '{m.file_name}'")
            print(f"    From: {m.current_path}")
            print(f"    To:   {m.proposed_path}")
        if len(plan.proposed_moves) > 5:
            print(f"    ... and {len(plan.proposed_moves) - 5} additional move operations.")


def cmd_search(args: argparse.Namespace) -> None:
    """Full-text search indexed files."""
    storage = DriveStorage(args.db)
    results = storage.search_fts(args.query)
    print(f"\n🔎 Search Results for '{args.query}' ({len(results)} found):")
    for r in results:
        size_str = format_bytes(r.get("size_bytes", 0))
        print(f"   • {r.get('name')} [{r.get('assigned_category')}] ({size_str}) -> {r.get('path_hierarchy')}")


def cmd_ask(args: argparse.Namespace) -> None:
    """Consult the AI Advisor."""
    storage = DriveStorage(args.db)
    files = storage.load_files()
    report = storage.get_audit_summary()
    clusterer = SubjectClusterer(files)
    clusters = clusterer.cluster_all()

    advisor = DriveMeshAdvisor(files=files, clusters=clusters, audit_report=report)
    answer = advisor.ask(args.question)
    print(f"\n{answer}\n")


def cmd_demo(args: argparse.Namespace) -> None:
    """Generate synthetic drive dataset and run complete workflow walkthrough."""
    print("🚀 Initializing DriveMesh Demo Mode with synthetic dataset...")
    storage = DriveStorage(args.db)
    demo_files = DriveImporter.generate_demo_dataset()
    storage.save_files(demo_files)

    # Run cluster
    clusterer = SubjectClusterer(demo_files)
    clusters = clusterer.cluster_all()
    storage.save_clusters(clusters)

    # Run duplicates
    detector = DuplicateDetector(demo_files)
    dups = detector.run_all()
    storage.save_duplicates(dups)

    print("✅ Demo dataset indexed and processed successfully!")

    # Display audit
    report = storage.get_audit_summary()
    print("\n" + "=" * 60)
    print("📊 DEMO RUN: DRIVE HEALTH & STORAGE AUDIT")
    print("=" * 60)
    print(f"🏆 Health Score:             {report.health_score} / 100")
    print(f"📁 Total Files:              {report.total_files}")
    print(f"💾 Total Storage:            {format_bytes(report.total_storage_bytes)}")
    print(f"🧹 Reclaimable Duplicate:    {format_bytes(report.reclaimable_bytes)}")
    print(f"⚠️  Duplicate Groups:          {report.duplicate_groups_count}")
    print(f"👻 Zero-Byte Ghosts:         {report.zero_byte_files_count}")

    print("\n🗂️ Discovered Clusters:")
    for c in clusters[:4]:
        print(f"   • {c.category.value} -> `{c.suggested_target_path}` ({len(c.file_ids)} files)")

    print("\n💡 Immediate Recommendations:")
    for idx, rec in enumerate(report.recommendations, 1):
        print(f"   {idx}. {rec}")
    print("=" * 60)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="drivemesh",
        description="Local-first Google Drive & cloud storage metadata clustering, subject grouping, and fuzzy duplicate detection engine.",
    )
    parser.add_argument("--db", default="drivemesh.db", help="Path to SQLite database file (default: drivemesh.db)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan and ingest Drive metadata from JSON/CSV/directory")
    p_scan.add_argument("source", help="Path to metadata export file (.json/.csv) or directory")

    # cluster
    subparsers.add_parser("cluster", help="Group files into subject clusters and taxonomy meshes")

    # duplicates
    p_dups = subparsers.add_parser("duplicates", help="Find exact, fuzzy, and zero-byte duplicates")
    p_dups.add_argument(
        "--type",
        choices=["all", "exact_checksum", "name_and_size", "fuzzy_version", "orphan_zero_byte"],
        default="all",
        help="Filter duplicate type",
    )

    # audit
    p_audit = subparsers.add_parser("audit", help="Generate comprehensive health and storage report")
    p_audit.add_argument("--json", action="store_true", help="Output audit report as JSON")

    # plan
    p_plan = subparsers.add_parser("plan", help="Generate reorganization move and cleanup plan")
    p_plan.add_argument("--out", help="Optional output JSON file path")

    # search
    p_search = subparsers.add_parser("search", help="Full-text search indexed files")
    p_search.add_argument("query", help="Search query string")

    # ask
    p_ask = subparsers.add_parser("ask", help="Ask AI advisor questions about drive organization")
    p_ask.add_argument("question", help="Question to ask")

    # demo
    subparsers.add_parser("demo", help="Generate synthetic test files and run demo audit")

    args = parser.parse_args()

    commands = {
        "scan": cmd_scan,
        "cluster": cmd_cluster,
        "duplicates": cmd_duplicates,
        "audit": cmd_audit,
        "plan": cmd_plan,
        "search": cmd_search,
        "ask": cmd_ask,
        "demo": cmd_demo,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn(args)


if __name__ == "__main__":
    main()
