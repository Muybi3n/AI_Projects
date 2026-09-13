"""Command-line interface for nasroute-core.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nasroute.ai_companion import NASRouteCompanion
from nasroute.engine import NASRouter, TaxonomyClassifier, extract_metadata
from nasroute.models import RouteAction, StorageTierConfig, TaxonomyRule
from nasroute.storage import NASRouteStore


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="nasroute",
        description="Homelab & document storage routing engine with deterministic taxonomy & integrity verification",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to local nasroute storage directory (default: ~/.nasroute)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Initialize workspace with default tiers and taxonomy rules")
    init_parser.add_argument("--json", action="store_true", help="Output result as JSON")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan a directory, extract checksums, and check taxonomy")
    scan_parser.add_argument("path", type=str, help="Directory path to scan")
    scan_parser.add_argument("--recursive", action="store_true", default=True, help="Recursively scan subdirectories")
    scan_parser.add_argument("--json", action="store_true", help="Output scan results as JSON")

    # Command: route
    route_parser = subparsers.add_parser("route", help="Route files from source directory into tiered homelab storage")
    route_parser.add_argument("source", type=str, help="Source directory containing documents to route")
    route_parser.add_argument(
        "--action",
        type=str,
        choices=["move", "copy", "symlink", "hardlink", "dry_run"],
        default="copy",
        help="Routing action to perform (default: copy)",
    )
    route_parser.add_argument("--dry-run", action="store_true", help="Simulate routing without moving/copying files")
    route_parser.add_argument(
        "--no-verify", action="store_true", help="Skip post-routing cryptographic checksum verification"
    )
    route_parser.add_argument("--json", action="store_true", help="Output routing audit report as JSON")

    # Command: rules
    rules_parser = subparsers.add_parser("rules", help="Manage taxonomy classification rules")
    rules_sub = rules_parser.add_subparsers(dest="rules_action", help="Rule actions")

    rules_list = rules_sub.add_parser("list", help="List active taxonomy rules")
    rules_list.add_argument("--json", action="store_true", help="Output rules as JSON")

    rules_add = rules_sub.add_parser("add", help="Add a new taxonomy rule")
    rules_add.add_argument("--id", required=True, help="Unique rule ID")
    rules_add.add_argument("--name", required=True, help="Descriptive rule name")
    rules_add.add_argument("--category", required=True, help="Taxonomy category")
    rules_add.add_argument("--tier", required=True, help="Target storage tier (e.g. HOT_NVME, WARM_SSD, COLD_NAS)")
    rules_add.add_argument(
        "--subpath", required=True, help="Destination subpath template (e.g. Finance/{year}/{filename})"
    )
    rules_add.add_argument("--keywords", type=str, default="", help="Comma-separated filename keywords")
    rules_add.add_argument("--priority", type=int, default=100, help="Rule priority (higher evaluated first)")

    rules_rm = rules_sub.add_parser("remove", help="Remove an existing taxonomy rule")
    rules_rm.add_argument("--id", required=True, help="Rule ID to remove")

    # Command: tiers
    tiers_parser = subparsers.add_parser("tiers", help="Manage storage mount tiers")
    tiers_sub = tiers_parser.add_subparsers(dest="tiers_action", help="Tier actions")

    tiers_list = tiers_sub.add_parser("list", help="List registered storage tiers")
    tiers_list.add_argument("--json", action="store_true", help="Output tiers as JSON")

    tiers_add = tiers_sub.add_parser("add", help="Register a storage tier mount")
    tiers_add.add_argument("--name", required=True, help="Tier name (e.g. HOT_NVME, WARM_SSD, COLD_NAS)")
    tiers_add.add_argument("--mount", required=True, help="Mount path directory")
    tiers_add.add_argument("--speed", default="NVMe_or_SATA", help="Speed class description")
    tiers_add.add_argument("--capacity-gb", type=int, default=0, help="Max capacity in GB")

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Display storage distribution and deduplication audit")
    audit_parser.add_argument("--json", action="store_true", help="Output audit report as JSON")

    # Command: ask
    ask_parser = subparsers.add_parser("ask", help="Query the AI Storage & Taxonomy Companion")
    ask_parser.add_argument("query", type=str, help="Question or optimization prompt for the AI companion")
    ask_parser.add_argument("--json", action="store_true", help="Output companion response as JSON")

    return parser


def handle_init(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Initialize or verify configuration."""
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "status": "INITIALIZED",
                    "data_dir": str(store.data_dir),
                    "tiers_count": len(store.tiers),
                    "rules_count": len(store.rules),
                },
                indent=2,
            )
        )
    else:
        print(f"[*] Initialized NASRoute repository at: {store.data_dir}")
        print(f"[*] Registered Storage Tiers: {len(store.tiers)}")
        print(f"[*] Active Taxonomy Rules:   {len(store.rules)}")
    return 0


def handle_scan(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Scan directory and print metadata & taxonomy evaluation."""
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path not found: {target_path}", file=sys.stderr)
        return 1

    classifier = TaxonomyClassifier(store.rules)
    known_hashes = store.get_known_hashes()

    files = []
    if target_path.is_file():
        files.append(target_path)
    else:
        pattern = "**/*" if args.recursive else "*"
        files = [p for p in target_path.glob(pattern) if p.is_file()]

    results = []
    total_bytes = 0
    duplicate_count = 0

    for f in sorted(files):
        try:
            meta = extract_metadata(f)
            total_bytes += meta.size_bytes
            rule, cat, tier, subpath = classifier.classify(meta)
            is_dup = meta.sha256 in known_hashes
            if is_dup:
                duplicate_count += 1

            results.append(
                {
                    "file_name": meta.file_name,
                    "path": str(f),
                    "size_bytes": meta.size_bytes,
                    "size_formatted": format_bytes(meta.size_bytes),
                    "sha256_short": meta.sha256[:12],
                    "blake2b_short": meta.blake2b[:12],
                    "matched_rule": rule.rule_id if rule else "NONE",
                    "category": cat,
                    "tier": tier,
                    "suggested_subpath": subpath,
                    "is_duplicate": is_dup,
                }
            )
        except (OSError, ValueError) as err:
            results.append({"file_name": f.name, "error": str(err)})

    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "scanned_path": str(target_path),
                    "total_files": len(results),
                    "total_bytes": total_bytes,
                    "total_duplicates": duplicate_count,
                    "files": results,
                },
                indent=2,
            )
        )
    else:
        print("================================================================================")
        print(f" NASRoute File Scan: {target_path}")
        print("================================================================================")
        print(
            f"Files Scanned: {len(results)} | Total Volume: {format_bytes(total_bytes)} | Duplicates: {duplicate_count}"
        )
        print("--------------------------------------------------------------------------------")
        for item in results:
            if "error" in item:
                print(f" [!] {item['file_name']}: {item['error']}")
                continue
            dup_tag = "[DUPLICATE] " if item["is_duplicate"] else ""
            print(f" • {dup_tag}{item['file_name']} ({item['size_formatted']})")
            print(f"   Category: {item['category']} | Target Tier: {item['tier']}")
            print(f"   Destination: {item['suggested_subpath']}")
            print(f"   SHA-256: {item['sha256_short']}... | BLAKE2b: {item['blake2b_short']}...")
        print("================================================================================")

    return 0


def handle_route(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Execute document routing into tiered homelab storage."""
    src_dir = Path(args.source).resolve()
    if not src_dir.is_dir():
        print(f"Error: Source directory not found: {src_dir}", file=sys.stderr)
        return 1

    action_str = "dry_run" if args.dry_run else args.action
    action_enum = RouteAction(action_str.upper())

    classifier = TaxonomyClassifier(store.rules)
    router = NASRouter(
        classifier=classifier,
        tier_configs=store.tiers,
        existing_hashes=store.get_known_hashes(),
    )

    verify_chk = not args.no_verify
    report = router.scan_and_route_directory(
        source_dir=src_dir,
        action=action_enum,
        recursive=True,
        verify_checksum=verify_chk,
    )

    # Record in history & catalog if not dry-run
    if action_enum != RouteAction.DRY_RUN:
        store.record_audit(report)

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("================================================================================")
        print(f" NASRoute Routing Execution: {action_enum.value}")
        print("================================================================================")
        print(f"Total Scanned:    {report.total_files_scanned} files ({format_bytes(report.total_bytes_scanned)})")
        print(f"Routed Count:     {report.routed_files_count}")
        print(f"Duplicates Skipped: {report.duplicate_files_count}")
        print(f"Storage Saved:    {format_bytes(report.space_saved_bytes)}")
        print("--------------------------------------------------------------------------------")
        print("Tier Distribution:")
        for tier_name, count in sorted(report.tier_breakdown.items()):
            print(f"  • {tier_name:<16}: {count} files")
        print("Category Distribution:")
        for cat_name, count in sorted(report.category_breakdown.items()):
            print(f"  • {cat_name:<20}: {count} files")
        print("--------------------------------------------------------------------------------")
        print("Execution Log:")
        for exc in report.executions:
            status_symbol = "[+]" if exc.status == "SUCCESS" else "[*]" if exc.status == "SIMULATED" else "[!]"
            print(f"  {status_symbol} {exc.status}: {Path(exc.source_path).name} -> {exc.dest_path}")
            if exc.message and exc.status != "SUCCESS":
                print(f"      Details: {exc.message}")
        print("================================================================================")

    return 0


def handle_rules(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Manage taxonomy rules."""
    action = getattr(args, "rules_action", None)
    if action == "list" or action is None:
        if getattr(args, "json", False):
            print(json.dumps([r.to_dict() for r in store.rules], indent=2))
        else:
            print("================================================================================")
            print(" NASRoute Taxonomy Rules")
            print("================================================================================")
            for r in store.rules:
                print(f"[{r.priority:>3}] Rule ID: {r.rule_id}")
                print(f"      Name:        {r.name}")
                print(f"      Category:    {r.category} -> Tier: {r.target_tier}")
                print(f"      Destination: {r.destination_subpath}")
                if r.name_keywords:
                    print(f"      Keywords:    {', '.join(r.name_keywords)}")
                print("--------------------------------------------------------------------------------")
        return 0

    if action == "add":
        kw_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
        new_rule = TaxonomyRule(
            rule_id=args.id,
            name=args.name,
            category=args.category,
            target_tier=args.tier,
            destination_subpath=args.subpath,
            name_keywords=kw_list,
            priority=args.priority,
        )
        store.add_rule(new_rule)
        print(f"[+] Added taxonomy rule '{new_rule.rule_id}' (Priority {new_rule.priority})")
        return 0

    if action == "remove":
        removed = store.remove_rule(args.id)
        if removed:
            print(f"[+] Removed taxonomy rule '{args.id}'")
            return 0
        print(f"Error: Rule '{args.id}' not found", file=sys.stderr)
        return 1

    return 0


def handle_tiers(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Manage storage tiers."""
    action = getattr(args, "tiers_action", None)
    if action == "list" or action is None:
        if getattr(args, "json", False):
            print(json.dumps({k: v.to_dict() for k, v in store.tiers.items()}, indent=2))
        else:
            print("================================================================================")
            print(" NASRoute Storage Tiers")
            print("================================================================================")
            for name, t in store.tiers.items():
                cap_str = format_bytes(t.max_capacity_bytes) if t.max_capacity_bytes else "Unlimited"
                print(f" • Tier: {name}")
                print(f"   Mount Path: {t.mount_path}")
                print(f"   Speed:      {t.speed_class}")
                print(f"   Capacity:   {cap_str}")
                print("--------------------------------------------------------------------------------")
        return 0

    if action == "add":
        cap_bytes = args.capacity_gb * (1024**3)
        new_tier = StorageTierConfig(
            tier_name=args.name,
            mount_path=args.mount,
            speed_class=args.speed,
            max_capacity_bytes=cap_bytes,
        )
        store.add_or_update_tier(new_tier)
        print(f"[+] Registered storage tier '{new_tier.tier_name}' at mount '{new_tier.mount_path}'")
        return 0

    return 0


def handle_audit(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Show global catalog and deduplication metrics."""
    total_indexed = len(store.catalog)
    cat_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for item in store.catalog.values():
        cat = item.get("category", "UNCATEGORIZED")
        tier = item.get("tier", "COLD_NAS")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    total_space_saved = 0
    total_duplicates = 0
    for h in store.history:
        total_space_saved += h.get("space_saved_bytes", 0)
        total_duplicates += h.get("duplicate_files_count", 0)

    data = {
        "total_indexed_files": total_indexed,
        "total_duplicates_blocked": total_duplicates,
        "total_space_saved_bytes": total_space_saved,
        "total_space_saved_formatted": format_bytes(total_space_saved),
        "tier_distribution": tier_counts,
        "category_distribution": cat_counts,
        "recent_executions_count": len(store.history),
    }

    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print("================================================================================")
        print(" NASRoute System Storage Audit")
        print("================================================================================")
        print(f"Total Files Indexed:      {total_indexed}")
        print(f"Total Duplicates Blocked: {total_duplicates}")
        print(f"Total Storage Saved:      {format_bytes(total_space_saved)}")
        print("--------------------------------------------------------------------------------")
        print("Storage Tier Distribution:")
        for t_name, count in sorted(tier_counts.items()):
            print(f"  • {t_name:<16}: {count} files")
        print("Category Distribution:")
        for c_name, count in sorted(cat_counts.items()):
            print(f"  • {c_name:<20}: {count} files")
        print("================================================================================")

    return 0


def handle_ask(store: NASRouteStore, args: argparse.Namespace) -> int:
    """Query the AI Storage & Taxonomy Companion."""
    companion = NASRouteCompanion()
    response = companion.consult(args.query, store)

    if getattr(args, "json", False):
        print(json.dumps(response.to_dict(), indent=2))
    else:
        print("================================================================================")
        print(" 🤖 NASRoute AI Storage Companion")
        print("================================================================================")
        print(f"Query: {response.query}\n")
        print(f"Summary:\n{response.summary}\n")
        if response.recommendations:
            print("Recommendations:")
            for rec in response.recommendations:
                print(f" • {rec}")
            print()
        if response.suggested_rules:
            print("Suggested Taxonomy Rules:")
            for s_rule in response.suggested_rules:
                print(f" • [{s_rule.get('rule_id')}] {s_rule.get('name')} -> {s_rule.get('target_tier')}")
                print(f"   Subpath: {s_rule.get('destination_subpath')}")
            print()
        if response.storage_optimization:
            print("Storage Optimization Architecture:")
            for k, v in response.storage_optimization.items():
                print(f" • {k}: {v}")
            print()
        print("================================================================================")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    store = NASRouteStore(data_dir=args.data_dir)

    handlers = {
        "init": handle_init,
        "scan": handle_scan,
        "route": handle_route,
        "rules": handle_rules,
        "tiers": handle_tiers,
        "audit": handle_audit,
        "ask": handle_ask,
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    try:
        return handler(store, args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Execution error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
