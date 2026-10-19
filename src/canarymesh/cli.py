# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh CLI: Command-line interface for deploying, auditing, and managing defensive decoy tripwires."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canarymesh.advisor import CanaryMeshAdvisor
from canarymesh.generator import (
    DECOY_TEMPLATES,
    compute_file_hashes,
    deploy_decoy_file,
    generate_canary_identifier,
)
from canarymesh.models import DecoyArtifact, DecoyCategory, utc_now_iso
from canarymesh.storage import DecoyStore
from canarymesh.tripwire import TripwireEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="canarymesh",
        description="CanaryMesh: Local-first defensive decoy file generator, integrity tripwires & tampering sentinel.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom storage directory for CanaryMesh registry and logs (default: ~/.canarymesh).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. deploy
    deploy_p = subparsers.add_parser("deploy", help="Generate and deploy a defensive decoy tripwire file.")
    deploy_p.add_argument(
        "--category",
        choices=[c.value for c in DecoyCategory],
        default=DecoyCategory.AWS_CREDENTIALS.value,
        help="Type of decoy asset to synthesize.",
    )
    deploy_p.add_argument("--path", type=str, required=True, help="Destination filesystem path for the decoy.")
    deploy_p.add_argument("--name", type=str, default=None, help="Descriptive name/label for the decoy artifact.")
    deploy_p.add_argument("--label", type=str, default="homelab-decoy", help="Custom contextual tracking label.")

    # 2. register (existing file)
    reg_p = subparsers.add_parser("register", help="Register an existing decoy file under integrity tripwire tracking.")
    reg_p.add_argument("--path", type=str, required=True, help="Existing file path to track.")
    reg_p.add_argument("--name", type=str, default=None, help="Name for the registered decoy.")
    reg_p.add_argument(
        "--category",
        choices=[c.value for c in DecoyCategory],
        default=DecoyCategory.CUSTOM.value,
        help="Category of the asset.",
    )

    # 3. audit
    audit_p = subparsers.add_parser("audit", help="Audit all deployed decoys against their cryptographic baselines.")
    audit_p.add_argument("--json", action="store_true", help="Output audit report in structured JSON format.")
    audit_p.add_argument("--quiet", action="store_true", help="Suppress output unless a tampering alert is triggered.")

    # 4. list
    list_p = subparsers.add_parser("list", help="List all tracked decoy tripwires.")
    list_p.add_argument("--json", action="store_true", help="Output list in JSON format.")

    # 5. alerts
    alerts_p = subparsers.add_parser("alerts", help="Review security tripwire incident alerts.")
    alerts_p.add_argument("--clear", action="store_true", help="Acknowledge and purge all logged incident alerts.")
    alerts_p.add_argument("--json", action="store_true", help="Output alerts in JSON format.")

    # 6. ask (AI companion / advisor)
    ask_p = subparsers.add_parser("ask", help="Query the AI Deception Security Advisor.")
    ask_p.add_argument("query", type=str, help="Natural language question regarding deception strategy or alerts.")
    ask_p.add_argument("--json", action="store_true", help="Output advice in JSON format.")

    # 7. demo (Beginner quickstart seed command)
    demo_p = subparsers.add_parser("demo", help="Seed a multi-layer sample deception scenario for hands-on evaluation.")
    demo_p.add_argument("--force", action="store_true", help="Overwrite existing decoys if present in vault.")

    return parser


def cmd_deploy(args: argparse.Namespace, store: DecoyStore) -> int:
    category = DecoyCategory(args.category)
    target_path = Path(args.path).expanduser().resolve()
    name = args.name or f"{category.value}_{target_path.name}"
    canary_id = generate_canary_identifier()

    sha256_hash, blake2b_hash, size, meta = deploy_decoy_file(
        target_path=target_path,
        category=category,
        canary_id=canary_id,
        custom_label=args.label,
    )

    template = DECOY_TEMPLATES[category]
    now_str = utc_now_iso()

    artifact = DecoyArtifact(
        token_id=canary_id,
        name=name,
        category=category,
        file_path=str(target_path),
        expected_sha256=sha256_hash,
        expected_blake2b=blake2b_hash,
        file_size_bytes=size,
        created_at=now_str,
        last_checked_at=now_str,
        canary_identifier=canary_id,
        description=template.description,
        mitre_technique=template.default_technique,
        is_active=True,
        metadata=meta,
    )

    store.add_decoy(artifact)
    print(f"✅ Successfully deployed decoy tripwire: {name}")
    print(f"   Target Path: {target_path}")
    print(f"   Category:    {category.value}")
    print(f"   Canary ID:   {canary_id}")
    print(f"   SHA-256:     {sha256_hash[:16]}...{sha256_hash[-8:]}")
    print(f"   MITRE ATT&CK: {template.default_technique}")
    return 0


def cmd_register(args: argparse.Namespace, store: DecoyStore) -> int:
    target_path = Path(args.path).expanduser().resolve()
    if not target_path.exists():
        print(f"❌ Error: File not found: {target_path}", file=sys.stderr)
        return 1

    category = DecoyCategory(args.category)
    name = args.name or target_path.name
    canary_id = generate_canary_identifier()

    try:
        sha256_hash, blake2b_hash, size = compute_file_hashes(target_path)
    except OSError as e:
        print(f"❌ Error reading file: {e}", file=sys.stderr)
        return 1

    now_str = utc_now_iso()
    artifact = DecoyArtifact(
        token_id=canary_id,
        name=name,
        category=category,
        file_path=str(target_path),
        expected_sha256=sha256_hash,
        expected_blake2b=blake2b_hash,
        file_size_bytes=size,
        created_at=now_str,
        last_checked_at=now_str,
        canary_identifier=canary_id,
        description=f"Tracked decoy file: {target_path.name}",
        mitre_technique="T1078 - Valid Accounts",
        is_active=True,
    )
    store.add_decoy(artifact)
    print(f"✅ Registered decoy file for integrity monitoring: {name}")
    print(f"   Path:    {target_path}")
    print(f"   SHA-256: {sha256_hash[:16]}...{sha256_hash[-8:]}")
    return 0


def cmd_audit(args: argparse.Namespace, store: DecoyStore) -> int:
    decoys = store.list_decoys()
    engine = TripwireEngine()
    summary = engine.run_fleet_audit(decoys)

    # Persist updated check timestamps
    store.save_decoys(decoys)

    if summary.alerts:
        store.record_alerts(summary.alerts)

    if getattr(args, "json", False):
        print(json.dumps(summary.to_dict(), indent=2))
        return 0 if summary.tampered_decoys == 0 and summary.missing_decoys == 0 else 2

    if getattr(args, "quiet", False) and not summary.alerts:
        return 0

    print("=" * 65)
    print("   CANARYMESH DEFENSIVE TRIPWIRE FLEET AUDIT REPORT")
    print("=" * 65)
    print(f"Status:            {summary.overall_health}")
    print(f"Total Decoys:      {summary.total_decoys}")
    print(f"Active Monitored:  {summary.active_decoys}")
    print(f"Intact & Armed:    {summary.intact_decoys}")
    print(f"Tampered / Drift:  {summary.tampered_decoys}")
    print(f"Missing / Deleted: {summary.missing_decoys}")
    print(f"New Alerts:        {summary.alerts_generated}")

    if summary.alerts:
        print("\n🚨 INCIDENT ALERTS TRIGGERED:")
        for idx, alert in enumerate(summary.alerts, start=1):
            print(f"  [{idx}] [{alert.severity.value}] {alert.summary}")
            print(f"      Path: {alert.file_path}")
            print(f"      MITRE: {alert.mitre_technique}")
            if "actual_sha256" in alert.details:
                print(f"      New Hash: {alert.details['actual_sha256'][:16]}...")
        return 2

    print("\n✅ All decoy tripwires intact. No tampering or access drift detected.")
    return 0


def cmd_list(args: argparse.Namespace, store: DecoyStore) -> int:
    decoys = store.list_decoys()
    if getattr(args, "json", False):
        print(json.dumps([d.to_dict() for d in decoys], indent=2))
        return 0

    if not decoys:
        print("No decoy tripwires registered. Run `canarymesh demo` or `canarymesh deploy` to start.")
        return 0

    print(f"{'NAME':<24} {'CATEGORY':<18} {'STATUS':<8} {'PATH'}")
    print("-" * 75)
    for d in decoys:
        status = "ARMED" if d.is_active else "INACTIVE"
        print(f"{d.name:<24} {d.category.value:<18} {status:<8} {d.file_path}")
    return 0


def cmd_alerts(args: argparse.Namespace, store: DecoyStore) -> int:
    if getattr(args, "clear", False):
        count = store.clear_alerts()
        print(f"Cleared {count} logged incident alerts.")
        return 0

    alerts = store.list_alerts()
    if getattr(args, "json", False):
        print(json.dumps([a.to_dict() for a in alerts], indent=2))
        return 0

    if not alerts:
        print("No incident alerts logged. All tripwires secure.")
        return 0

    print(f"Total Logged Alerts: {len(alerts)}")
    print("-" * 70)
    for a in alerts:
        print(f"[{a.severity.value}] {a.detected_at} - {a.summary}")
        print(f"    File: {a.file_path}")
        print(f"    Technique: {a.mitre_technique}")
    return 0


def cmd_ask(args: argparse.Namespace, store: DecoyStore) -> int:
    decoys = store.list_decoys()
    alerts = store.list_alerts()
    advisor = CanaryMeshAdvisor()
    resp = advisor.consult(args.query, decoys, alerts)

    if getattr(args, "json", False):
        print(json.dumps(resp.to_dict(), indent=2))
        return 0

    print("🤖 CanaryMesh AI Deception Advisor")
    print("=" * 60)
    print(f"Threat Assessment:\n  {resp.threat_assessment}\n")
    if resp.recommendations:
        print("Strategic Recommendations:")
        for r in resp.recommendations:
            print(f"  • {r}")
    if resp.suggested_actions:
        print("\nSuggested Actions:")
        for act in resp.suggested_actions:
            print(f"  👉 {act}")
    if resp.mitre_references:
        print("\nMITRE ATT&CK Alignment:")
        for m in resp.mitre_references:
            print(f"  🛡️ {m}")
    return 0


def cmd_demo(args: argparse.Namespace, store: DecoyStore) -> int:
    existing = store.list_decoys()
    if existing and not getattr(args, "force", False):
        print("⚠️ Vault already contains active decoys. Use --force to re-seed the demo scenario.")
        return 1

    demo_root = store.data_dir / "demo_environment"
    demo_root.mkdir(parents=True, exist_ok=True)

    demos = [
        (DecoyCategory.AWS_CREDENTIALS, demo_root / ".aws" / "credentials", "aws-prod-admin-bait"),
        (DecoyCategory.SSH_KEY, demo_root / ".ssh" / "id_rsa_backup", "ssh-root-jumpbox-bait"),
        (DecoyCategory.ENV_SECRETS, demo_root / "workspace" / ".env.production", "microservice-env-bait"),
        (DecoyCategory.SENSITIVE_DOCUMENT, demo_root / "docs" / "q4_financials.md", "m-and-a-confidential-bait"),
    ]

    for cat, path, name in demos:
        canary_id = generate_canary_identifier()
        sha256_hash, blake2b_hash, size, meta = deploy_decoy_file(
            target_path=path,
            category=cat,
            canary_id=canary_id,
            custom_label="demo-seed",
        )
        template = DECOY_TEMPLATES[cat]
        now_str = utc_now_iso()
        artifact = DecoyArtifact(
            token_id=canary_id,
            name=name,
            category=cat,
            file_path=str(path),
            expected_sha256=sha256_hash,
            expected_blake2b=blake2b_hash,
            file_size_bytes=size,
            created_at=now_str,
            last_checked_at=now_str,
            canary_identifier=canary_id,
            description=template.description,
            mitre_technique=template.default_technique,
            is_active=True,
            metadata=meta,
        )
        store.add_decoy(artifact)

    print("🎉 CanaryMesh demo environment seeded successfully!")
    print(f"   Target Demo Directory: {demo_root}")
    print("   Seeded 4 multi-layer deception tripwires:\n")
    print("   1. AWS Credentials Honey-token      (~/.aws/credentials)")
    print("   2. SSH Backup Key Bait              (~/.ssh/id_rsa_backup)")
    print("   3. Production .env Secret Lure      (workspace/.env.production)")
    print("   4. M&A Sensitive Strategy Doc       (docs/q4_financials.md)\n")
    print("Next steps to test the deception tripwires:")
    print("   1. canarymesh list")
    print("   2. canarymesh audit")
    print("   3. Modify one of the demo files (simulating an adversary tampering or exfiltrating)")
    print("   4. canarymesh audit                 (observe the instant breach detection alert)")
    print("   5. canarymesh ask 'What should I do after this alert?'")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    store = DecoyStore(data_dir=args.data_dir)

    if args.command == "deploy":
        return cmd_deploy(args, store)
    elif args.command == "register":
        return cmd_register(args, store)
    elif args.command == "audit":
        return cmd_audit(args, store)
    elif args.command == "list":
        return cmd_list(args, store)
    elif args.command == "alerts":
        return cmd_alerts(args, store)
    elif args.command == "ask":
        return cmd_ask(args, store)
    elif args.command == "demo":
        return cmd_demo(args, store)

    return 0


if __name__ == "__main__":
    sys.exit(main())
