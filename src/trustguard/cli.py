# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for trustguard-core.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ai_advisor import EstateAdvisor
from .engine import EstateEngine
from .models import (
    AssetCategory,
    BeneficiaryRule,
    DistributionScheme,
    FiduciaryLogEntry,
    GuardianshipDirective,
    ScheduleAsset,
    TitlingStatus,
    TrustEntity,
    TrustType,
)
from .storage import TrustStore


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  trustguard v{__version__:<10}                                     │
│  Estate & Trust Fiduciary Ledger & AI Estate Companion      │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="trustguard",
        description="Estate Planning & Trust Fiduciary Ledger, Beneficiary Waterfall Engine & AI Estate Companion.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Custom data directory.")
    parser.add_argument("--version", "-v", action="version", version=f"trustguard {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init
    init_p = subparsers.add_parser("init", help="Initialize or configure a Trust entity.")
    init_p.add_argument("--name", required=True, help="Trust Name, e.g. 'Smith Family Revocable Trust'")
    init_p.add_argument("--type", choices=[t.value for t in TrustType], default="revocable_living", help="Trust type")
    init_p.add_argument("--state", default="Delaware", help="Governing State Jurisdiction")
    init_p.add_argument("--grantor", default="Grantor", help="Grantor / Settlor name")
    init_p.add_argument("--trustee", default="Trustee", help="Current Trustee name")
    init_p.add_argument("--successor", default="Successor Trustee", help="Designated Successor Trustee")

    # Asset
    asset_p = subparsers.add_parser("asset", help="Manage Schedule A estate assets.")
    asset_sub = asset_p.add_subparsers(dest="subcommand", required=True)

    asset_add = asset_sub.add_parser("add", help="Add an asset to Schedule A.")
    asset_add.add_argument("--name", required=True, help="Asset name / description")
    asset_add.add_argument(
        "--category", choices=[c.value for c in AssetCategory], default="real_estate", help="Asset category"
    )
    asset_add.add_argument("--value", type=float, required=True, help="Estimated asset valuation in USD")
    asset_add.add_argument(
        "--titling", choices=[s.value for s in TitlingStatus], default="titled_to_trust", help="Current titling status"
    )
    asset_add.add_argument("--parcel", default="", help="Institution name or real estate parcel ID")

    asset_sub.add_parser("list", help="List all scheduled estate assets.")
    asset_audit = asset_sub.add_parser("audit", help="Audit trust funding and identify unfunded probate risks.")
    asset_audit.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Beneficiary
    ben_p = subparsers.add_parser("beneficiary", help="Manage beneficiary distribution rules.")
    ben_sub = ben_p.add_subparsers(dest="subcommand", required=True)

    ben_add = ben_sub.add_parser("add", help="Add a beneficiary rule.")
    ben_add.add_argument("--name", required=True, help="Beneficiary full name")
    ben_add.add_argument("--relationship", default="child", help="Relationship (spouse, child, charity, etc.)")
    ben_add.add_argument("--pct", type=float, default=0.0, help="Percentage share of residual estate (0-100)")
    ben_add.add_argument("--specific-amount", type=float, default=0.0, help="Specific dollar bequest amount")
    ben_add.add_argument(
        "--scheme",
        choices=[s.value for s in DistributionScheme],
        default="outright_percentage",
        help="Distribution scheme",
    )

    ben_sub.add_parser("list", help="List all designated beneficiaries.")

    # Guardianship & Family Planning
    guard_p = subparsers.add_parser("guardianship", help="Manage minor child guardianship and family directives.")
    guard_sub = guard_p.add_subparsers(dest="subcommand", required=True)

    guard_add = guard_sub.add_parser("add", help="Add minor guardianship directive.")
    guard_add.add_argument("--child", required=True, help="Minor child full name")
    guard_add.add_argument("--dob", default="", help="Date of birth (YYYY-MM-DD)")
    guard_add.add_argument("--guardian", required=True, help="Primary designated legal guardian")
    guard_add.add_argument("--alternate", default="", help="Alternate / successor guardian")
    guard_add.add_argument("--notes", default="", help="Special health/care/educational instructions")

    guard_sub.add_parser("list", help="List all designated guardianship directives.")

    # Waterfall
    wf_p = subparsers.add_parser("waterfall", help="Simulate beneficiary distribution waterfall.")
    wf_p.add_argument("--estate-value", type=float, default=None, help="Override gross estate valuation in USD")
    wf_p.add_argument(
        "--admin-reserve-pct", type=float, default=3.0, help="Administrative reserve percentage (default: 3.0%)"
    )
    wf_p.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Fiduciary
    fid_p = subparsers.add_parser("fiduciary", help="Manage immutable fiduciary audit ledger.")
    fid_sub = fid_p.add_subparsers(dest="subcommand", required=True)

    fid_log = fid_sub.add_parser("log", help="Log a trustee action or distribution.")
    fid_log.add_argument(
        "--category",
        choices=["accounting", "distribution", "tax_filing", "appraisal", "asset_retitle"],
        default="accounting",
    )
    fid_log.add_argument("--desc", required=True, help="Description of trustee fiduciary action")
    fid_log.add_argument("--amount", type=float, default=0.0, help="Dollar impact of disbursement or appraisal")
    fid_log.add_argument("--doc", default="", help="Supporting document reference or hash")

    fid_sub.add_parser("list", help="List fiduciary log entries.")

    # Ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI Estate & Fiduciary Companion.")
    ask_p.add_argument(
        "query", help="Question regarding probate exposure, beneficiary waterfalls, or fiduciary duties."
    )
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON analysis.")

    args = parser.parse_args(argv)
    store = TrustStore(args.data_dir)
    trust = store.load_trust()

    # Init
    if args.command == "init":
        trust = TrustEntity(
            trust_name=args.name,
            trust_type=TrustType(args.type),
            jurisdiction_state=args.state,
            grantor_settlor=args.grantor,
            current_trustee=args.trustee,
            successor_trustee=args.successor,
        )
        store.save_trust(trust)
        print(f"[✓] Initialized Trust: '{trust.trust_name}' ({trust.trust_type.value}) in {trust.jurisdiction_state}")
        return 0

    # Asset
    if args.command == "asset":
        if args.subcommand == "add":
            asset = ScheduleAsset(
                name=args.name,
                category=AssetCategory(args.category),
                estimated_value=args.value,
                titling_status=TitlingStatus(args.titling),
                institution_or_parcel=args.parcel,
            )
            trust.assets.append(asset)
            store.save_trust(trust)
            print(
                f"[✓] Added Schedule A Asset: {asset.name} (${asset.estimated_value:,.2f}) [{asset.titling_status.value}]"
            )
            return 0

        elif args.subcommand == "list":
            print(f"\nSchedule A Assets for '{trust.trust_name}' ({len(trust.assets)} assets):")
            print("=" * 75)
            for a in trust.assets:
                status_icon = (
                    "🟢"
                    if a.titling_status in [TitlingStatus.TITLED_TO_TRUST, TitlingStatus.TITLED_TO_TRUST.value]
                    else "🔴"
                )
                print(
                    f"{status_icon} [{a.id}] {a.name:<28} : ${a.estimated_value:>12,.2f} | {a.titling_status.value:<20}"
                )
            print("=" * 75)
            print(f"  Total Scheduled Estate Value: ${trust.total_estate_value:>12,.2f}\n")
            return 0

        elif args.subcommand == "audit":
            audit = EstateEngine.audit_funding(trust)
            if args.json:
                print(
                    json.dumps(
                        {
                            "total_estate_value": audit.total_estate_value,
                            "funded_to_trust_pct": audit.funded_to_trust_pct,
                            "unfunded_probate_risk_value": audit.unfunded_probate_risk_value,
                            "unfunded_probate_risk_pct": audit.unfunded_probate_risk_pct,
                            "probate_risk_tier": audit.probate_risk_tier,
                            "at_risk_assets": [a.to_dict() for a in audit.at_risk_assets],
                        },
                        indent=2,
                    )
                )
                return 0

            print("\n" + "=" * 70)
            print("                 TRUST FUNDING & PROBATE AUDIT                    ")
            print("=" * 70)
            print(f"  Gross Estate Valuation       : ${audit.total_estate_value:>14,.2f}")
            print(
                f"  Formally Titled to Trust     : ${audit.funded_to_trust_value:>14,.2f} ({audit.funded_to_trust_pct:.1f}%)"
            )
            print(f"  Direct Beneficiary Designated: ${audit.beneficiary_designated_value:>14,.2f}")
            print(
                f"  Unfunded / At-Risk Probate   : ${audit.unfunded_probate_risk_value:>14,.2f} ({audit.unfunded_probate_risk_pct:.1f}%)"
            )
            print("─" * 70)
            print(f"  Probate Risk Tier            : {audit.probate_risk_tier}")
            print("=" * 70)

            if audit.at_risk_assets:
                print("\n⚠️  AT-RISK ASSETS REQUIRING RETITLING OR TOD/POD DESIGNATION:")
                for a in audit.at_risk_assets:
                    print(f"  • {a.name:<25} : ${a.estimated_value:>10,.2f} ({a.titling_status.value})")
            print()
            return 0

    # Beneficiary
    if args.command == "beneficiary":
        if args.subcommand == "add":
            ben = BeneficiaryRule(
                beneficiary_name=args.name,
                relationship=args.relationship,
                share_pct=args.pct,
                specific_dollar_amount=args.specific_amount,
                scheme=DistributionScheme(args.scheme),
            )
            trust.beneficiaries.append(ben)
            store.save_trust(trust)
            print(
                f"[✓] Added Beneficiary: {ben.beneficiary_name} ({ben.relationship}) | Scheme: {ben.scheme.value} ({ben.share_pct}%)"
            )
            return 0

        elif args.subcommand == "list":
            print(f"\nDesignated Beneficiaries for '{trust.trust_name}':")
            print("=" * 75)
            for b in trust.beneficiaries:
                share_str = (
                    f"${b.specific_dollar_amount:,.2f}" if b.specific_dollar_amount > 0 else f"{b.share_pct:.1f}%"
                )
                print(f"[{b.id}] {b.beneficiary_name:<22} ({b.relationship:<8}) : {share_str:<12} | {b.scheme.value}")
            print("=" * 75 + "\n")
            return 0

    # Guardianship
    if args.command == "guardianship":
        if args.subcommand == "add":
            directive = GuardianshipDirective(
                child_name=args.child,
                date_of_birth=args.dob,
                primary_guardian=args.guardian,
                alternate_guardian=args.alternate,
                special_care_instructions=args.notes,
            )
            trust.guardianship_directives.append(directive)
            store.save_trust(trust)
            print(f"[✓] Added Guardianship Directive for '{directive.child_name}' -> Primary Guardian: {directive.primary_guardian}")
            return 0

        elif args.subcommand == "list":
            print(f"\nMinor Guardianship Directives for '{trust.trust_name}':")
            print("=" * 80)
            for g in trust.guardianship_directives:
                alt = f" (Alt: {g.alternate_guardian})" if g.alternate_guardian else ""
                print(f"[{g.id}] Child: {g.child_name:<20} | Guardian: {g.primary_guardian:<20}{alt}")
            print("=" * 80 + "\n")
            return 0

    # Waterfall
    if args.command == "waterfall":
        res = EstateEngine.calculate_waterfall(
            trust,
            gross_estate_override=args.estate_value,
            administrative_reserve_pct=args.admin_reserve_pct,
        )
        if args.json:
            out_dict = {
                "gross_estate_value": res.gross_estate_value,
                "administrative_reserve_dollars": res.administrative_reserve_dollars,
                "distributable_net_estate": res.distributable_net_estate,
                "payouts": [p.__dict__ for p in res.payouts],
                "unallocated_remainder": res.unallocated_remainder,
            }
            print(json.dumps(out_dict, indent=2))
            return 0

        print("\n" + "=" * 70)
        print("                 BENEFICIARY DISTRIBUTION WATERFALL               ")
        print("=" * 70)
        print(f"  Gross Estate Valuation       : ${res.gross_estate_value:>14,.2f}")
        print(
            f"  Admin/Legal Reserve ({res.administrative_reserve_pct:.1f}%)    : -${res.administrative_reserve_dollars:>13,.2f}"
        )
        print(f"  Net Distributable Estate     : ${res.distributable_net_estate:>14,.2f}")
        print("─" * 70)
        print("  BENEFICIARY ALLOCATIONS:")
        for p in res.payouts:
            print(
                f"  • {p.beneficiary_name:<24} : ${p.total_dollar_amount:>12,.2f} ({p.allocation_pct:>5.1f}%) [Immediate: ${p.immediate_payout:>12,.2f}]"
            )
            for m in p.milestone_tranches:
                print(f"      ↳ Age {m['release_age']}: {m['fraction_pct']}% (${m['estimated_amount']:,.2f})")
        print("=" * 70 + "\n")
        return 0

    # Fiduciary
    if args.command == "fiduciary":
        if args.subcommand == "log":
            entry = FiduciaryLogEntry(
                trustee_name=trust.current_trustee,
                action_category=args.category,
                description=args.desc,
                dollar_impact=args.amount,
                supporting_doc_ref=args.doc,
            )
            trust.fiduciary_logs.append(entry)
            store.save_trust(trust)
            print(
                f"[✓] Logged Fiduciary Action [{entry.action_category}]: {entry.description} (${entry.dollar_impact:,.2f})"
            )
            return 0

        elif args.subcommand == "list":
            print(f"\nFiduciary Compliance Ledger for '{trust.trust_name}' ({len(trust.fiduciary_logs)} entries):")
            print("=" * 80)
            for log in trust.fiduciary_logs:
                print(
                    f"[{log.timestamp[:10]}] [{log.action_category:<12}] {log.description:<35} | ${log.dollar_impact:>10,.2f}"
                )
            print("=" * 80 + "\n")
            return 0

    # Ask
    if args.command == "ask":
        advisor = EstateAdvisor()
        resp = advisor.consult(args.query, trust)

        if args.json:
            print(json.dumps(resp.to_dict(), indent=2))
            return 0

        print("\n" + "━" * 70)
        print(f"🤖 AI ESTATE & FIDUCIARY COMPANION: '{args.query}'")
        print("━" * 70)
        print(f"\n🎯 EXECUTIVE SUMMARY:\n{resp.executive_summary}\n")
        if resp.fiduciary_findings:
            print("📜 FIDUCIARY FINDINGS:")
            for f in resp.fiduciary_findings:
                print(f"  • {f}")
            print()
        if resp.probate_risk_items:
            print("🚨 PROBATE / TITLING RISKS:")
            for r in resp.probate_risk_items:
                print(f"  • {r}")
            print()
        if resp.action_items:
            print("⚡ RECOMMENDED FIDUCIARY ACTIONS:")
            for act in resp.action_items:
                print(f"  • {act}")
            print()
        if resp.statutory_citations:
            print(f"⚖️ STATUTORY REFERENCE: {resp.statutory_citations}")
        print("━" * 70 + "\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
