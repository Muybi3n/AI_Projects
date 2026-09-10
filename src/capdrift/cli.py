# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for capdrift-engine.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .analytics import PortfolioAnalyzer
from .ingest import PortfolioIngester
from .llm_companion import PortfolioCompanion
from .storage import SnapshotStore


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  capdrift v{__version__:<10}                                       │
│  Portfolio Drift Auditor & AI Investment Companion          │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def parse_target_str(target_str: str) -> dict[str, float]:
    """Parse format like 'us_equities:60,intl_equities:20,fixed_income:10,cash:10'."""
    res = {}
    for pair in target_str.split(","):
        if ":" in pair:
            k, v = pair.split(":")
            res[k.strip().lower()] = float(v.strip())
    return res


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="capdrift",
        description="Local-First Portfolio Analytics, Capital Drift Auditor & AI Investment Companion.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Custom data directory.")
    parser.add_argument("--version", "-v", action="version", version=f"capdrift {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    ingest_p = subparsers.add_parser("ingest", help="Ingest a broker CSV or JSON portfolio snapshot.")
    ingest_p.add_argument("file", type=Path, help="CSV or JSON exported portfolio file.")
    ingest_p.add_argument("--broker", default=None, help="Broker label (e.g. 'Robinhood', 'Schwab').")

    # Audit
    audit_p = subparsers.add_parser("audit", help="Run full concentration, asset allocation, and health audit.")
    audit_p.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Rebalance
    reb_p = subparsers.add_parser("rebalance", help="Calculate rebalancing trade deltas vs target allocation.")
    reb_p.add_argument("--target", default=None, help="Target weights, e.g. 'us_equities:60,intl_equities:20,fixed_income:10,cash:10'")

    # Stress-Test
    subparsers.add_parser("stress-test", help="Simulate historical crash drawdowns (2008 GFC, 2020 Covid, 2022 Shock).")

    # Dividends
    div_p = subparsers.add_parser("dividends", help="Simulate dividend compounding snowball projection.")
    div_p.add_argument("--years", type=int, default=5, help="Projection years (default: 5).")

    # Ask
    ask_p = subparsers.add_parser("ask", help="Ask the AI Investment Companion a natural-language question.")
    ask_p.add_argument("query", help="Question about your portfolio risk, rebalancing, or allocation.")
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON analysis.")

    # History
    subparsers.add_parser("history", help="List historical portfolio snapshots.")

    args = parser.parse_args(argv)
    store = SnapshotStore(args.data_dir)

    # Ingest
    if args.command == "ingest":
        ingester = PortfolioIngester()
        try:
            snapshot = ingester.ingest_file(args.file, broker_hint=args.broker)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            print(f"Error ingesting portfolio: {e}", file=sys.stderr)
            return 1

        store.save_snapshot(snapshot)
        print(f"[✓] Ingested Snapshot: {len(snapshot.holdings)} holdings | Total Equity: ${snapshot.total_equity:,.2f} [ID: {snapshot.id}]")
        return 0

    # For other commands, load latest snapshot
    snapshot = store.get_latest_snapshot()
    if not snapshot:
        print("No portfolio snapshot found in database. Ingest one first with 'capdrift ingest <file.csv>'.", file=sys.stderr)
        return 1

    # Audit
    if args.command == "audit":
        conc = PortfolioAnalyzer.evaluate_concentration(snapshot)
        drift = PortfolioAnalyzer.evaluate_drift(snapshot)

        if args.json:
            out_data = {
                "snapshot": snapshot.to_dict(),
                "concentration": conc.__dict__,
                "drift": [d.__dict__ for d in drift],
            }
            print(json.dumps(out_data, indent=2))
            return 0

        print("\n" + "=" * 65)
        print("                    PORTFOLIO HEALTH AUDIT                       ")
        print("=" * 65)
        print(f"  Total Portfolio Equity   : ${snapshot.total_equity:>14,.2f}")
        print(f"  Total Cost Basis         : ${snapshot.total_cost:>14,.2f}")
        sign = "+" if snapshot.total_unrealized_pnl >= 0 else "-"
        print(f"  Unrealized Gain/Loss     : {sign}${abs(snapshot.total_unrealized_pnl):>13,.2f} ({snapshot.total_unrealized_pnl_pct:+.1f}%)")
        print(f"  Annual Dividend Income   : ${snapshot.total_annual_dividends:>14,.2f} ({snapshot.portfolio_yield_pct:.2f}% Yield)")
        print(f"  Unallocated Cash Balance : ${snapshot.cash_balance:>14,.2f}")
        print("─" * 65)
        print(f"  Concentration HHI Score  : {conc.hhi_score} ({conc.risk_assessment})")
        print(f"  Top Asset ({conc.top_holding_symbol}) Weight   : {conc.top_holding_weight_pct}% (Top 3: {conc.top_3_weight_pct}%)")
        print("=" * 65)

        print("\n--- Asset Allocation Breakdown vs Baseline ---")
        for d in drift:
            d_sign = "+" if d.drift_pct >= 0 else ""
            print(f"  • {d.asset_class:<15} : {d.current_weight_pct:>5.1f}%  (Target: {d.target_weight_pct:>5.1f}% | Drift: {d_sign}{d.drift_pct:>5.1f}%)")
        print()

    # Rebalance
    elif args.command == "rebalance":
        targets = parse_target_str(args.target) if args.target else None
        drift = PortfolioAnalyzer.evaluate_drift(snapshot, target_allocation=targets)

        print("\n" + "=" * 65)
        print("                    REBALANCING TRADE DELTAS                     ")
        print("=" * 65)
        for d in drift:
            action = "BUY / ALLOCATE" if d.rebalance_dollar_delta > 0 else ("TRIM / HARVEST" if d.rebalance_dollar_delta < 0 else "BALANCED")
            sign = "+" if d.rebalance_dollar_delta > 0 else "-"
            print(f"  [{action:<14}] {d.asset_class:<15} {sign}${abs(d.rebalance_dollar_delta):>10,.2f} (Drift: {d.drift_pct:+.1f}%)")
        print("=" * 65 + "\n")

    # Stress-Test
    elif args.command == "stress-test":
        scenarios = PortfolioAnalyzer.run_stress_test(snapshot)
        print("\n" + "=" * 65)
        print("             HISTORICAL MACRO CRASH STRESS-TESTS                 ")
        print("=" * 65)
        for sc in scenarios:
            print(f"\n🚨 {sc.scenario_name}")
            print(f"   Context             : {sc.description}")
            print(f"   Projected Drawdown  : {sc.projected_drawdown_pct}% (-${sc.projected_dollar_loss:,.2f})")
            print(f"   Estimated Recovery  : {sc.estimated_recovery_period}")
        print("\n" + "=" * 65 + "\n")

    # Dividends
    elif args.command == "dividends":
        snowball = PortfolioAnalyzer.project_dividend_snowball(snapshot, years=args.years)
        print("\n" + "=" * 65)
        print(f"       DIVIDEND COMPOUNDING SNOWBALL ({args.years}-YEAR PROJECTION)       ")
        print("=" * 65)
        for pt in snowball:
            print(f"  Year {pt.year}: Value: ${pt.portfolio_value:>12,.2f} | Annual Div: ${pt.annual_dividend:>9,.2f} (${pt.monthly_passive_income:>7,.2f}/mo)")
        print("=" * 65 + "\n")

    # Ask (LLM Companion)
    elif args.command == "ask":
        companion = PortfolioCompanion()
        resp = companion.consult(args.query, snapshot)

        if args.json:
            print(json.dumps(resp.to_dict(), indent=2))
            return 0

        print("\n" + "━" * 65)
        print(f"🤖 AI PORTFOLIO COMPANION: '{args.query}'")
        print("━" * 65)
        print(f"\n🎯 EXECUTIVE THESIS:\n{resp.executive_thesis}\n")
        if resp.observations:
            print("🔍 OBSERVATIONS:")
            for obs in resp.observations:
                print(f"  • {obs}")
            print()
        if resp.risk_flags:
            print("⚠️ RISK FLAGS:")
            for r in resp.risk_flags:
                print(f"  • {r}")
            print()
        if resp.rebalance_actions:
            print("⚡ RECOMMENDED ACTIONS:")
            for act in resp.rebalance_actions:
                print(f"  • {act}")
            print()
        if resp.macro_context:
            print(f"🌐 MACRO CONTEXT: {resp.macro_context}")
        print("━" * 65 + "\n")

    # History
    elif args.command == "history":
        snapshots = store.list_snapshots()
        print(f"\nPortfolio History ({len(snapshots)} snapshots):")
        print("─" * 65)
        for s in snapshots:
            print(f"[{s.id}] {s.timestamp[:19]} | Holdings: {len(s.holdings):<3} | Equity: ${s.total_equity:>12,.2f} | ({s.broker_source})")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
