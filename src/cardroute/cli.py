# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for cardroute-engine.
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .advisor import CardAdvisor
from .engine import CardRoutingEngine
from .models import CreditCard, SubTracker
from .storage import PortfolioStore

console = Console()


def print_banner() -> None:
    console.print(
        """
[bold cyan]╔══════════════════════════════════════════════════════════════════╗
║               💳 CARDROUTE REWARDS & CHURNING ENGINE             ║
║     Dynamic Spend Routing, 5/24 Rules & AI Portfolio Advisor     ║
╚══════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
    )


def main(args_list: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cardroute",
        description="Credit Card Spend Routing Optimizer & Bank Churning Rule Engine.",
    )
    parser.add_argument(
        "--data-dir",
        help="Custom storage directory for card portfolio (defaults to ~/.cardroute)",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # list
    subparsers.add_parser("list", help="List all credit cards in portfolio")

    # add card
    add_p = subparsers.add_parser("add", help="Add a credit card to portfolio")
    add_p.add_argument("--id", required=True, help="Unique Card ID (e.g. chase-csp)")
    add_p.add_argument("--name", required=True, help="Card Name")
    add_p.add_argument(
        "--issuer", default="Chase", help="Issuer (Chase, Amex, Citi, Capital One, BoA)"
    )
    add_p.add_argument(
        "--network", default="Visa", help="Network (Visa, Mastercard, Amex, Discover)"
    )
    add_p.add_argument("--fee", type=float, default=0.0, help="Annual fee in dollars")
    add_p.add_argument("--opened", default="", help="Opened date YYYY-MM-DD")
    add_p.add_argument("--business", action="store_true", help="Mark as business card")
    add_p.add_argument(
        "--points", default="Cash Back", help="Point type (Chase UR, Amex MR, Cash Back)"
    )
    add_p.add_argument(
        "--cpp", type=float, default=1.0, help="Point valuation in cents per point (e.g. 2.0)"
    )
    add_p.add_argument("--credits", type=float, default=0.0, help="Annual statement credits value")

    # route
    route_p = subparsers.add_parser("route", help="Determine optimal card for a transaction")
    route_p.add_argument(
        "-c",
        "--category",
        required=True,
        help="Category (dining, groceries, travel, gas, catch_all)",
    )
    route_p.add_argument(
        "-a", "--amount", type=float, default=100.0, help="Purchase amount in dollars"
    )
    route_p.add_argument("-m", "--merchant", default="", help="Merchant name (e.g. Costco, Uber)")
    route_p.add_argument("--ignore-sub", action="store_true", help="Ignore sign-up bonus priority")

    # 524
    subparsers.add_parser("524", help="Audit Chase 5/24 status and bank churning eligibility")

    # sub
    sub_p = subparsers.add_parser("sub", help="Manage Sign-Up Bonus Minimum Spend Requirements")
    sub_sub = sub_p.add_subparsers(dest="sub_action")
    sub_sub.add_parser("list", help="List active SUB trackers")
    sub_add = sub_sub.add_parser("add", help="Add new SUB tracker")
    sub_add.add_argument("--id", required=True, help="Card ID")
    sub_add.add_argument("--name", required=True, help="Card Name")
    sub_add.add_argument("--spend", type=float, required=True, help="Target spend requirement ($)")
    sub_add.add_argument("--deadline", required=True, help="Deadline YYYY-MM-DD")
    sub_add.add_argument("--bonus", type=int, default=60000, help="Bonus points")
    sub_add.add_argument("--points", default="Chase UR", help="Bonus point type")

    sub_log = sub_sub.add_parser("log", help="Log spend toward active SUB")
    sub_log.add_argument("--id", required=True, help="Card ID")
    sub_log.add_argument("--amount", type=float, required=True, help="Amount spent ($)")

    # audit
    subparsers.add_parser("audit", help="Audit net annual wallet economics and deadweight cards")

    # ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI Credit Card Portfolio Advisor")
    ask_p.add_argument("query", help="Question about credit card strategy or 5/24 rules")
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON context")

    args = parser.parse_args(args_list)

    if not args.subcommand:
        print_banner()
        parser.print_help()
        return 0

    base_dir = Path(args.data_dir) if args.data_dir else None
    store = PortfolioStore(base_dir)
    portfolio = store.load_portfolio()
    engine = CardRoutingEngine(portfolio)

    if args.subcommand == "list":
        print_banner()
        table = Table(title=f"Wallet Portfolio ({len(portfolio.cards)} Cards)")
        table.add_column("ID", style="cyan")
        table.add_column("Card Name", style="bold white")
        table.add_column("Issuer", style="magenta")
        table.add_column("Fee", style="red")
        table.add_column("Points", style="green")
        table.add_column("Valuation", style="yellow")
        table.add_column("Top Multipliers", style="blue")

        for c in portfolio.cards:
            mults = ", ".join([f"{k}:{v}x" for k, v in list(c.multipliers.items())[:3]])
            table.add_row(
                c.card_id,
                c.card_name,
                c.issuer,
                f"${c.annual_fee:.0f}",
                c.point_type,
                f"{c.point_valuation_cents}¢",
                mults or "1x",
            )
        console.print(table)
        return 0

    elif args.subcommand == "add":
        new_card = CreditCard(
            card_id=args.id,
            card_name=args.name,
            issuer=args.issuer,
            network=args.network,
            annual_fee=args.fee,
            opened_date=args.opened,
            is_business=args.business,
            point_type=args.points,
            point_valuation_cents=args.cpp,
            annual_credits_value=args.credits,
        )
        portfolio.cards.append(new_card)
        store.save_portfolio(portfolio)
        console.print(f"[green]✔ Added card '{args.name}' to portfolio.[/green]")
        return 0

    elif args.subcommand == "route":
        print_banner()
        result = engine.route_purchase(
            category=args.category,
            amount=args.amount,
            merchant=args.merchant,
            prioritize_sub=not args.ignore_sub,
        )
        rec = result.get("recommended_card")
        if not rec:
            console.print("[red]No card found in portfolio.[/red]")
            return 1

        console.print(
            f"[bold]Purchase Context:[/bold] ${args.amount:.2f} in [cyan]{args.category.upper()}[/cyan]"
        )
        console.print(f"[bold]Strategy:[/bold] [yellow]{result['strategy']}[/yellow]")
        console.print()

        panel_content = (
            f"[bold green]RECOMMENDED CARD:[/bold green] [bold white]{rec['card_name']}[/bold white] ({rec['issuer']})\n"
            f"[bold]Reason:[/bold] {result['reason']}\n"
            f"[bold]Multiplier:[/bold] {result['multiplier']}x {result['point_type']}\n"
            f"[bold]Estimated Net Return:[/bold] [bold green]{result['estimated_return_pct']}%[/bold green] (${result['estimated_value_dollars']:.2f})"
        )
        console.print(
            Panel(panel_content, title="🎯 Optimal Checkout Decision", border_style="green")
        )

        alts = result.get("alternatives", [])
        if alts:
            console.print("[dim]Alternative Options in Wallet:[/dim]")
            for a in alts:
                console.print(
                    f"  • {a['card_name']}: {a['multiplier']}x ({a['return_pct']}%) → ${a['dollar_value']:.2f}"
                )
        return 0

    elif args.subcommand == "524":
        print_banner()
        res = engine.evaluate_bank_rules()
        c524 = res["chase_524_status"]

        color = "green" if c524["is_eligible_for_chase"] else "red"
        console.print(f"[bold]Chase 5/24 Status:[/bold] [{color}]{c524['status']}[/{color}]")
        console.print(f"[bold]Slots Available:[/bold] {c524['slots_available']}")
        console.print(
            f"[bold]Chase Application Eligibility:[/bold] [{color}]{c524['guidance']}[/{color}]"
        )
        if c524["next_slot_dropoff_date"]:
            console.print(
                f"[bold]Next Slot Drop-off Date:[/bold] [yellow]{c524['next_slot_dropoff_date']}[/yellow]"
            )
        console.print()
        console.print(f"[dim]Total Active Personal/Biz Cards: {res['total_portfolio_cards']}[/dim]")
        return 0

    elif args.subcommand == "sub":
        if args.sub_action == "list" or not args.sub_action:
            print_banner()
            table = Table(title="Sign-Up Bonus (SUB) Minimum Spend Trackers")
            table.add_column("Card Name", style="cyan")
            table.add_column("Target Spend", style="white")
            table.add_column("Current Spend", style="green")
            table.add_column("Remaining", style="red")
            table.add_column("Progress", style="yellow")
            table.add_column("Days Left", style="blue")
            table.add_column("Req Spend/Day", style="magenta")

            for s in portfolio.sub_trackers:
                table.add_row(
                    s.card_name,
                    f"${s.target_spend:,.2f}",
                    f"${s.current_spend:,.2f}",
                    f"${s.remaining_spend:,.2f}",
                    f"{s.progress_pct:.1f}%",
                    str(s.days_remaining()),
                    f"${s.required_daily_spend():.2f}/day",
                )
            console.print(table)
            return 0

        elif args.sub_action == "add":
            tracker = SubTracker(
                card_id=args.id,
                card_name=args.name,
                target_spend=args.spend,
                deadline_date=args.deadline,
                bonus_points=args.bonus,
                bonus_point_type=args.points,
            )
            portfolio.sub_trackers.append(tracker)
            store.save_portfolio(portfolio)
            console.print(f"[green]✔ Added SUB tracker for '{args.name}'.[/green]")
            return 0

        elif args.sub_action == "log":
            matched = [
                s
                for s in portfolio.sub_trackers
                if s.card_id == args.id or s.card_name.lower() == args.id.lower()
            ]
            if not matched:
                console.print(f"[red]No SUB tracker found for card ID: {args.id}[/red]")
                return 1
            tracker = matched[0]
            tracker.current_spend += args.amount
            if tracker.current_spend >= tracker.target_spend:
                tracker.is_completed = True
            store.save_portfolio(portfolio)
            console.print(
                f"[green]✔ Logged ${args.amount:.2f} on {tracker.card_name}. Total spend: ${tracker.current_spend:.2f} / ${tracker.target_spend:.2f}[/green]"
            )
            return 0

    elif args.subcommand == "audit":
        print_banner()
        audit = engine.audit_wallet_value()
        console.print("===========================================================================")
        console.print("                     WALLET ANNUAL NET VALUE AUDIT                        ")
        console.print("===========================================================================")
        console.print(f"  Gross Annual Fees       :   ${audit['total_annual_fees']:.2f}")
        console.print(f"  Statement Credits Offset: - ${audit['total_annual_credits']:.2f}")
        console.print(f"  Net Annual Fee Cost     :   ${audit['net_effective_annual_fee']:.2f}")
        console.print(
            f"  Projected Rewards Value : + ${audit['projected_annual_rewards_value']:.2f}"
        )
        console.print("───────────────────────────────────────────────────────────────────────────")
        console.print(
            f"  [bold]NET ANNUAL WALLET PROFIT :   [bold green]${audit['net_annual_wallet_profit']:.2f}[/bold green][/bold]"
        )
        console.print(
            "===========================================================================\n"
        )
        return 0

    elif args.subcommand == "ask":
        advisor = CardAdvisor(portfolio)
        result = advisor.consult(args.query)

        if args.json:
            console.print(json.dumps(result, indent=2))
            return 0

        print_banner()
        console.print(f"[bold cyan]🤖 CARDROUTE ADVISOR:[/bold cyan] '{args.query}'\n")
        console.print(f"[bold]Summary:[/bold] {result.get('summary', '')}\n")
        console.print("[bold green]Recommendations:[/bold green]")
        for rec in result.get("recommendations", []):
            console.print(f"  • {rec}")
        console.print("\n[bold yellow]Action Plan & Insights:[/bold yellow]")
        for act in result.get("action_plan", []):
            console.print(f"  ⚡ {act}")
        console.print()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
