# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for ptomax-core.
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .academic import AcademicEvent, AcademicEventType, FamilyCalendarBridge, SyllabusParser
from .accrual import AccrualEngine
from .advisor import PtoAdvisor
from .coverage import CoverageMatrix
from .emails import OooEmailGenerator
from .optimizer import PtoOptimizer
from .storage import PtoStore

console = Console()


def print_banner() -> None:
    console.print(
        """
[bold cyan]╔══════════════════════════════════════════════════════════════════╗
║               🌴 PTOMAX LEAVE & HOLIDAY OPTIMIZER                ║
║      Holiday Stacking, School Sync & Work Handover Matrix        ║
╚══════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
    )


def main(args_list: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ptomax",
        description="PTO Holiday Stacking Optimizer, School Calendar/Syllabus Sync & Handover Matrix.",
    )
    parser.add_argument(
        "--data-dir",
        help="Custom storage directory for PTO profile (defaults to ~/.ptomax)",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # balance
    subparsers.add_parser("balance", help="View current PTO balance and accrual metrics")

    # set-balance
    sb_p = subparsers.add_parser("set-balance", help="Update PTO balance and allowance")
    sb_p.add_argument("--balance", type=float, required=True, help="Current available PTO days")
    sb_p.add_argument(
        "--allowance", type=float, default=None, help="Total annual PTO allowance in days"
    )
    sb_p.add_argument("--rate", type=float, default=None, help="Accrual hours per pay period")
    sb_p.add_argument("--cap", type=float, default=None, help="Max rollover cap in days")

    # optimize / plan
    plan_p = subparsers.add_parser("optimize", help="Find highest-leverage holiday stacking breaks")
    plan_p.add_argument(
        "-d",
        "--days",
        type=int,
        default=None,
        help="PTO days to allocate (defaults to current balance)",
    )
    plan_p.add_argument(
        "-y", "--year", type=int, default=2026, help="Target calendar year (default: 2026)"
    )

    # school (academic calendars, syllabi & childcare conflict detector)
    school_p = subparsers.add_parser(
        "school", help="Manage generic school calendars, syllabi & family vacation sync"
    )
    school_sub = school_p.add_subparsers(dest="school_action")

    school_import = school_sub.add_parser(
        "import", help="Import school schedule, district calendar or syllabus"
    )
    school_import.add_argument(
        "-f", "--file", help="Path to text or CSV file containing school schedule"
    )
    school_import.add_argument(
        "-t", "--text", help="Raw inline text containing schedule or syllabus dates"
    )
    school_import.add_argument(
        "-s",
        "--source",
        default="School Calendar",
        help="Source name (e.g. 'Metro School District', 'University CS101')",
    )
    school_import.add_argument(
        "--students", default="", help="Comma-separated student/child names (e.g. 'Emma, Liam')"
    )
    school_import.add_argument("--year", type=int, default=2026, help="Default calendar year")

    school_sub.add_parser("list", help="List all parsed school events and student days off")
    school_sub.add_parser(
        "conflicts", help="Detect childcare conflict days (kids off school, parents working)"
    )
    school_sub.add_parser(
        "family-breaks",
        help="Find optimal family vacation windows combining school breaks & holidays",
    )
    school_sub.add_parser("clear", help="Clear all imported school events")

    # coverage
    cov_p = subparsers.add_parser(
        "coverage", help="Manage work handover and project coverage delegates"
    )
    cov_sub = cov_p.add_subparsers(dest="cov_action")
    cov_sub.add_parser("list", help="List all active coverage delegates")

    cov_add = cov_sub.add_parser("add", help="Add a project coverage delegate")
    cov_add.add_argument("--project", required=True, help="Project, domain, or client name")
    cov_add.add_argument("--primary-name", required=True, help="Primary delegate name")
    cov_add.add_argument("--primary-contact", required=True, help="Primary delegate email or Slack")
    cov_add.add_argument("--backup-name", default="", help="Backup delegate name")
    cov_add.add_argument("--backup-contact", default="", help="Backup delegate contact")
    cov_add.add_argument(
        "--threshold", default="P0 production outages only", help="Escalation threshold"
    )
    cov_add.add_argument("--notes", default="", help="Handover documentation notes")

    cov_ready = cov_sub.add_parser("ready", help="Mark a coverage handover checklist as ready")
    cov_ready.add_argument("--id", required=True, help="Coverage ID or project name")

    # ooo
    ooo_p = subparsers.add_parser("ooo", help="Generate customized Out-of-Office (OOO) email")
    ooo_p.add_argument("--start", required=True, help="Vacation start date YYYY-MM-DD")
    ooo_p.add_argument("--end", required=True, help="Return date YYYY-MM-DD")
    ooo_p.add_argument(
        "--style",
        choices=["external", "internal", "urgent", "witty"],
        default="external",
        help="Email tone style (default: external)",
    )

    # accrual
    subparsers.add_parser("accrual", help="Project year-end PTO balance and use-it-or-lose-it risk")

    # ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI PTO & Work-Life Balance Strategist")
    ask_p.add_argument(
        "query", help="Question regarding PTO stacking, holiday dates, or handover planning"
    )
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON context")

    args = parser.parse_args(args_list)

    if not args.subcommand:
        print_banner()
        parser.print_help()
        return 0

    base_dir = Path(args.data_dir) if args.data_dir else None
    store = PtoStore(base_dir)
    profile = store.load_profile()

    if args.subcommand == "balance":
        print_banner()
        accrual_engine = AccrualEngine(profile)
        acc_info = accrual_engine.project_year_end_balance()

        console.print("===========================================================================")
        console.print("                         PTO BALANCE & ACCRUAL SNAPSHOT                    ")
        console.print("===========================================================================")
        console.print(
            f"  Current Available Balance :   {profile.current_balance_days:.1f} Days ({profile.current_balance_days * 8.0:.1f} Hours)"
        )
        console.print(
            f"  Annual PTO Allowance      :   {profile.total_annual_allowance_days:.1f} Days / Year"
        )
        console.print(
            f"  Accrual Pace              :   {profile.accrual_hours_per_pay_period:.2f} Hours / Pay Period ({profile.pay_periods_per_year} periods/yr)"
        )
        console.print(f"  Max Year-End Rollover Cap :   {profile.max_rollover_cap_days:.1f} Days")
        console.print("───────────────────────────────────────────────────────────────────────────")
        console.print(
            f"  Projected Dec 31 Balance  :   {acc_info['projected_year_end_balance']:.1f} Days"
        )
        if acc_info["days_at_risk_of_forfeiture"] > 0:
            console.print(
                f"  [bold red]🚨 Forfeiture Risk (Lost PTO):   {acc_info['days_at_risk_of_forfeiture']:.1f} Days over rollover cap![/bold red]"
            )
        else:
            console.print(
                "  [bold green]✔ Status                  :   Healthy (Within rollover limit)[/bold green]"
            )
        console.print(
            "===========================================================================\n"
        )
        return 0

    elif args.subcommand == "set-balance":
        profile.current_balance_days = args.balance
        if args.allowance is not None:
            profile.total_annual_allowance_days = args.allowance
        if args.rate is not None:
            profile.accrual_hours_per_pay_period = args.rate
        if args.cap is not None:
            profile.max_rollover_cap_days = args.cap
        store.save_profile(profile)
        console.print(
            f"[green]✔ Updated PTO profile. Current balance: {profile.current_balance_days:.1f} days.[/green]"
        )
        return 0

    elif args.subcommand == "optimize":
        print_banner()
        budget = args.days if args.days is not None else int(profile.current_balance_days)
        year = args.year
        optimizer = PtoOptimizer(year, profile.custom_holidays)
        plan = optimizer.optimize_plan(budget)

        console.print(
            f"[bold]Target Year:[/bold] {year} | [bold]PTO Days Budget:[/bold] {budget} Days\n"
        )

        table = Table(title=f"🌴 Optimized Holiday Stacking Schedule ({year})")
        table.add_column("Break Name", style="cyan")
        table.add_column("Date Range", style="white")
        table.add_column("PTO Burned", style="yellow")
        table.add_column("Days Off", style="bold green")
        table.add_column("Leverage", style="magenta")
        table.add_column("Holidays Bridged", style="blue")

        for b in plan["recommended_breaks"]:
            table.add_row(
                b["break_name"],
                f"{b['start_date']} to {b['end_date']}",
                f"{b['pto_days_required']} Days",
                f"{b['total_consecutive_days_off']} Days",
                f"{b['leverage_multiplier']}x",
                ", ".join(b["holidays_bridged"]),
            )

        console.print(table)
        console.print()
        panel_msg = (
            f"[bold green]SUMMARY:[/bold green] By burning [bold yellow]{plan['pto_days_spent']}[/bold yellow] PTO days, "
            f"you unlock [bold green]{plan['total_consecutive_vacation_days_gained']} total consecutive days off[/bold green] "
            f"({plan['overall_leverage_multiplier']}x leverage!). PTO Days remaining: {plan['pto_days_remaining']}."
        )
        console.print(Panel(panel_msg, title="🌟 PTO Optimization Result", border_style="green"))
        return 0

    elif args.subcommand == "school":
        if args.school_action == "import":
            text_to_parse = ""
            if args.file:
                p = Path(args.file)
                if p.is_file():
                    text_to_parse = p.read_text(encoding="utf-8", errors="ignore")
                else:
                    console.print(f"[red]Error: File not found: {args.file}[/red]")
                    return 1
            elif args.text:
                text_to_parse = args.text
            else:
                console.print("[red]Error: Must provide --file or --text to import.[/red]")
                return 1

            students = [s.strip() for s in args.students.split(",") if s.strip()]
            events = SyllabusParser.parse_text(
                text=text_to_parse,
                source_label=args.source,
                default_year=args.year,
                students=students,
            )
            for ev in events:
                profile.academic_events.append(ev.to_dict())
            store.save_profile(profile)
            console.print(
                f"[green]✔ Successfully parsed & imported {len(events)} academic events from '{args.source}'.[/green]"
            )
            return 0

        elif args.school_action == "list" or not args.school_action:
            print_banner()
            if not profile.academic_events:
                console.print(
                    "[yellow]No school calendars or syllabi imported. Use 'ptomax school import' to load schedules.[/yellow]"
                )
                return 0

            table = Table(
                title=f"🎓 Academic Events & School Schedule ({len(profile.academic_events)} Events)"
            )
            table.add_column("Event Name", style="cyan")
            table.add_column("Dates", style="white")
            table.add_column("Type", style="yellow")
            table.add_column("Source", style="magenta")
            table.add_column("Students", style="green")

            for e in profile.academic_events:
                dt_str = (
                    e["start_date"]
                    if e["start_date"] == e["end_date"]
                    else f"{e['start_date']} to {e['end_date']}"
                )
                table.add_row(
                    e["name"][:35],
                    dt_str,
                    e["event_type"],
                    e.get("source_label", "")[:25],
                    ", ".join(e.get("affected_students", [])) or "All",
                )
            console.print(table)
            return 0

        elif args.school_action == "conflicts":
            print_banner()
            acad_objects = [
                AcademicEvent(
                    id=e.get("id", ""),
                    name=e.get("name", ""),
                    event_type=AcademicEventType(e.get("event_type", "student_holiday")),
                    start_date=e.get("start_date", ""),
                    end_date=e.get("end_date", ""),
                    source_label=e.get("source_label", ""),
                    affected_students=e.get("affected_students", []),
                )
                for e in profile.academic_events
            ]
            bridge = FamilyCalendarBridge(acad_objects)
            conflicts = bridge.find_childcare_conflicts()

            if not conflicts:
                console.print(
                    "[green]✔ No childcare conflicts detected. All school off-days align with weekends or federal holidays.[/green]"
                )
                return 0

            table = Table(
                title=f"🚨 Childcare Conflict Radar ({len(conflicts)} Workdays with No School)"
            )
            table.add_column("Date", style="cyan")
            table.add_column("Day", style="yellow")
            table.add_column("School Event", style="white")
            table.add_column("Source School", style="magenta")
            table.add_column("Action Needed", style="bold red")

            for c in conflicts:
                table.add_row(
                    c["date"],
                    c["day_of_week"],
                    ", ".join(c["event_names"])[:35],
                    ", ".join(c["sources"])[:25],
                    "Plan PTO / Childcare",
                )
            console.print(table)
            console.print(
                "\n[dim]💡 Tip: Use 'ptomax ooo' or submit a PTO request for these dates before calendar slots fill up.[/dim]\n"
            )
            return 0

        elif args.school_action == "family-breaks":
            print_banner()
            acad_objects = [
                AcademicEvent(
                    id=e.get("id", ""),
                    name=e.get("name", ""),
                    event_type=AcademicEventType(e.get("event_type", "student_holiday")),
                    start_date=e.get("start_date", ""),
                    end_date=e.get("end_date", ""),
                    source_label=e.get("source_label", ""),
                )
                for e in profile.academic_events
            ]
            bridge = FamilyCalendarBridge(acad_objects)
            windows = bridge.find_family_vacation_windows()

            table = Table(
                title=f"👨‍👩‍👧‍👦 Family Vacation Windows ({len(windows)} Contiguous Breaks)"
            )
            table.add_column("Window Name", style="cyan")
            table.add_column("Date Range", style="white")
            table.add_column("Days Off", style="bold green")
            table.add_column("PTO Needed", style="yellow")
            table.add_column("Leverage", style="magenta")

            for w in windows:
                table.add_row(
                    w["window_name"][:35],
                    f"{w['start_date']} to {w['end_date']}",
                    f"{w['total_consecutive_days_off']} Days",
                    f"{w['pto_days_required']} Days",
                    f"{w['leverage_multiplier']}x",
                )
            console.print(table)
            return 0

        elif args.school_action == "clear":
            profile.academic_events.clear()
            store.save_profile(profile)
            console.print("[green]✔ Cleared all imported school events.[/green]")
            return 0

    elif args.subcommand == "coverage":
        cov_matrix = CoverageMatrix(profile.coverage_handovers)
        if args.cov_action == "list" or not args.cov_action:
            print_banner()
            console.print(cov_matrix.generate_handover_brief())
            return 0
        elif args.cov_action == "add":
            cov_matrix.add_coverage(
                project_or_domain=args.project,
                primary_name=args.primary_name,
                primary_contact=args.primary_contact,
                backup_name=args.backup_name,
                backup_contact=args.backup_contact,
                escalation_threshold=args.threshold,
                notes=args.notes,
            )
            profile.coverage_handovers = cov_matrix.coverages
            store.save_profile(profile)
            console.print(f"[green]✔ Added coverage delegation for '{args.project}'.[/green]")
            return 0
        elif args.cov_action == "ready":
            if cov_matrix.mark_handover_ready(args.id, True):
                profile.coverage_handovers = cov_matrix.coverages
                store.save_profile(profile)
                console.print(f"[green]✔ Marked handover for '{args.id}' as READY.[/green]")
                return 0
            else:
                console.print(f"[red]Could not find coverage delegation for '{args.id}'.[/red]")
                return 1

    elif args.subcommand == "ooo":
        print_banner()
        result = OooEmailGenerator.generate_ooo_email(
            start_date=args.start,
            end_date=args.end,
            style=args.style,
            coverages=profile.coverage_handovers,
        )
        console.print(f"[bold]Style Tone:[/bold] [cyan]{args.style.upper()}[/cyan]")
        console.print(f"[bold]Subject Line:[/bold] [yellow]{result['subject']}[/yellow]\n")

        console.print(
            Panel(result["body"], title="✉️ Generated Out-of-Office Email", border_style="cyan")
        )
        console.print(f"\n[dim]{result['buffer_day_tip']}[/dim]\n")
        return 0

    elif args.subcommand == "accrual":
        print_banner()
        accrual_engine = AccrualEngine(profile)
        acc_info = accrual_engine.project_year_end_balance()
        console.print(
            Panel(
                acc_info["advisory"],
                title="📈 PTO Accrual & Rollover Audit",
                border_style="yellow" if acc_info["days_at_risk_of_forfeiture"] > 0 else "green",
            )
        )
        return 0

    elif args.subcommand == "ask":
        advisor = PtoAdvisor(profile)
        result = advisor.consult(args.query)

        if args.json:
            console.print(json.dumps(result, indent=2))
            return 0

        print_banner()
        console.print(f"[bold cyan]🤖 PTOMAX STRATEGIST:[/bold cyan] '{args.query}'\n")
        console.print(f"[bold]Summary:[/bold] {result.get('summary', '')}\n")
        console.print("[bold green]Recommendations:[/bold green]")
        for rec in result.get("recommendations", []):
            console.print(f"  • {rec}")
        console.print("\n[bold yellow]High-Leverage Action Plan:[/bold yellow]")
        for act in result.get("action_plan", []):
            console.print(f"  ⚡ {act}")
        console.print()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
