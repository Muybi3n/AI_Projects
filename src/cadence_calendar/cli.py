"""
Command line interface for cadence-calendar.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time
from pathlib import Path

from cadence_calendar.ai_companion import CadenceCompanion
from cadence_calendar.auditor import CalendarAuditor
from cadence_calendar.models import WorkHoursConfig
from cadence_calendar.parser import CalendarParser
from cadence_calendar.protector import BufferProtector
from cadence_calendar.storage import CadenceStorage


def _parse_time_str(val: str) -> time:
    parts = val.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cadence",
        description="Cadence Calendar: Local-First Calendar Fatigue Auditor & Deep-Work Buffer Protector",
    )
    parser.add_argument("--data-dir", type=str, default=None, help="Custom data directory (default: ~/.cadence)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: init
    p_init = subparsers.add_parser("init", help="Initialize or update calendar configuration profile")
    p_init.add_argument("--name", type=str, default="Primary Work Calendar", help="Profile label")
    p_init.add_argument(
        "--work-hours", type=str, default="09:00-17:00", help="Core work hours window (e.g. 09:00-17:00)"
    )
    p_init.add_argument("--lunch", type=str, default="12:00-12:45", help="Lunch window (e.g. 12:00-12:45)")
    p_init.add_argument("--target-focus", type=float, default=3.5, help="Target daily deep focus hours")
    p_init.add_argument("--max-meetings", type=float, default=4.0, help="Maximum healthy meeting hours/day")
    p_init.add_argument("--min-buffer", type=int, default=10, help="Minimum transition buffer minutes")

    # Subcommand: ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest calendar events from .ics, .json, or .csv")
    p_ingest.add_argument("file", type=str, help="Path to calendar file (.ics, .json, .csv)")
    p_ingest.add_argument("--no-sanitize", action="store_true", help="Disable automatic PII / email / link scrubbing")
    p_ingest.add_argument("--clear", action="store_true", help="Clear existing events before ingesting")

    # Subcommand: audit
    p_audit = subparsers.add_parser("audit", help="Run cognitive fatigue and Swiss-cheese calendar audit")
    p_audit.add_argument("--from-date", type=str, default=None, help="Start date filter (YYYY-MM-DD)")
    p_audit.add_argument("--to-date", type=str, default=None, help="End date filter (YYYY-MM-DD)")
    p_audit.add_argument("--json", action="store_true", help="Output audit results in JSON format")

    # Subcommand: protect
    p_protect = subparsers.add_parser("protect", help="Generate buffer insertion and focus protection plan")
    p_protect.add_argument("--buffer-minutes", type=int, default=10, help="Buffer duration to insert between meetings")
    p_protect.add_argument(
        "--min-focus-hours", type=float, default=2.0, help="Minimum contiguous hours for deep work blocks"
    )
    p_protect.add_argument("--no-lunch-shield", action="store_true", help="Disable lunch break protection")
    p_protect.add_argument("--apply", action="store_true", help="Apply generated buffers directly to stored calendar")
    p_protect.add_argument("--export", type=str, default=None, help="Export protected calendar to .ics file")
    p_protect.add_argument("--json", action="store_true", help="Output protection plan in JSON format")

    # Subcommand: ask
    p_ask = subparsers.add_parser("ask", help="Query the AI Calendar Companion for scheduling strategy")
    p_ask.add_argument("query", type=str, help="Natural language question")
    p_ask.add_argument("--json", action="store_true", help="Output answer in JSON format")

    # Subcommand: stats
    p_stats = subparsers.add_parser("stats", help="Quick summary of stored calendar events and schedule")
    p_stats.add_argument("--json", action="store_true", help="Output stats in JSON format")

    # Subcommand: export
    p_export = subparsers.add_parser("export", help="Export stored calendar events to .ics or .json")
    p_export.add_argument("-o", "--output", type=str, required=True, help="Output destination file (.ics or .json)")
    p_export.add_argument("--cal-name", type=str, default="Cadence Calendar", help="Calendar name metadata")

    # Subcommand: clean
    p_clean = subparsers.add_parser("clean", help="Clear stored events from local vault")
    p_clean.add_argument("--all", action="store_true", help="Confirm deletion of all stored calendar events")

    return parser


def handle_init(args: argparse.Namespace, storage: CadenceStorage) -> int:
    try:
        wh_start_str, wh_end_str = args.work_hours.split("-")
        l_start_str, l_end_str = args.lunch.split("-")
        wh_start = _parse_time_str(wh_start_str)
        wh_end = _parse_time_str(wh_end_str)
        l_start = _parse_time_str(l_start_str)
        l_end = _parse_time_str(l_end_str)

        l_dur = (datetime.combine(date.today(), l_end) - datetime.combine(date.today(), l_start)).seconds // 60
    except (ValueError, IndexError):
        print("Error: Invalid time format. Please use HH:MM-HH:MM (e.g., 09:00-17:00).", file=sys.stderr)
        return 1

    wh = WorkHoursConfig(
        start_time=wh_start,
        end_time=wh_end,
        work_days=[0, 1, 2, 3, 4],
        lunch_start=l_start,
        lunch_duration_minutes=l_dur,
        target_focus_hours_per_day=args.target_focus,
        max_meeting_hours_per_day=args.max_meetings,
        min_buffer_minutes=args.min_buffer,
    )
    storage.save_profile(args.name, wh)
    print(f"✅ Initialized profile '{args.name}' successfully.")
    print(f"   • Core Work Window: {wh_start.strftime('%H:%M')} - {wh_end.strftime('%H:%M')}")
    print(f"   • Protected Lunch:  {l_start.strftime('%H:%M')} ({l_dur} min)")
    print(f"   • Target Deep Work: {args.target_focus}h/day | Max Meetings: {args.max_meetings}h/day")
    return 0


def handle_ingest(args: argparse.Namespace, storage: CadenceStorage) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f"Error: Calendar file not found at '{args.file}'", file=sys.stderr)
        return 1

    if args.clear:
        storage.clear_events()

    events = CalendarParser.parse_file(path, sanitize=(not args.no_sanitize))
    added = storage.append_events(events)

    print(f"📥 Successfully ingested {len(events)} events from {path.name} ({added} newly added).")
    print(f"   • PII Sanitization: {'Enabled (Emails/links scrubbed)' if not args.no_sanitize else 'Disabled'}")
    print("   • Run 'cadence audit' to analyze meeting fatigue and Swiss-cheese fragmentation.")
    return 0


def handle_audit(args: argparse.Namespace, storage: CadenceStorage) -> int:
    _name, wh, _meta = storage.load_profile()
    events = storage.load_events()

    st_date = date.fromisoformat(args.from_date) if args.from_date else None
    end_date = date.fromisoformat(args.to_date) if args.to_date else None

    auditor = CalendarAuditor(work_hours=wh)
    audit = auditor.audit_events(events, start_date=st_date, end_date=end_date)
    storage.save_audit(audit)

    if args.json:
        print(json.dumps(audit.to_dict(), indent=2))
        return 0

    print("═══════════════════════════════════════════════════════════════")
    print(" 📊 CADENCE CALENDAR: FATIGUE & COGNITIVE LOAD AUDIT REPORT ")
    print("═══════════════════════════════════════════════════════════════")
    print(f"Total Events:         {audit.total_events} events across {audit.analyzed_days_count} active days")
    print(
        f"Total Meeting Load:   {audit.total_meeting_hours:.1f} hrs (Avg: {audit.avg_daily_meeting_hours:.1f} hrs/day)"
    )
    print(f"Protected Focus Time: {audit.total_focus_hours:.1f} hrs")
    print(f"Fragmented Lost Time: {audit.total_fragmented_hours:.1f} hrs (Swiss-cheese gaps)")
    print(f"Back-to-Back Chains:  {audit.back_to_back_chains_count} back-to-back sequences")
    print(f"Context Switches:     {audit.context_switches_total} domain/attendee context switches")
    print("───────────────────────────────────────────────────────────────")
    print(f"Overall Fatigue Score: {audit.avg_daily_fatigue_score:.1f}/100")
    print(f"Burnout Risk Level:    [{audit.burnout_risk_level.value}]")
    print("───────────────────────────────────────────────────────────────")

    if audit.top_fatigue_days:
        print("🔥 Highest Fatigue Days:")
        for td in audit.top_fatigue_days:
            print(f"   • {td}")
        print("───────────────────────────────────────────────────────────────")

    print("💡 Strategic Recommendations:")
    for rec in audit.recommendations:
        print(f"   {rec}")
    print("═══════════════════════════════════════════════════════════════")
    return 0


def handle_protect(args: argparse.Namespace, storage: CadenceStorage) -> int:
    _name, wh, _meta = storage.load_profile()
    events = storage.load_events()

    if not events:
        print(
            "Error: No calendar events found in local vault. Ingest events first via 'cadence ingest'.", file=sys.stderr
        )
        return 1

    protector = BufferProtector(work_hours=wh)
    plan = protector.generate_protection_plan(
        events=events,
        buffer_minutes=args.buffer_minutes,
        min_focus_hours=args.min_focus_hours,
        protect_lunch=(not args.no_lunch_shield),
    )

    if args.json:
        print(json.dumps(plan.to_dict(), indent=2))
        return 0

    print("═══════════════════════════════════════════════════════════════")
    print(" 🛡️ CADENCE CALENDAR: DEEP WORK & BUFFER PROTECTION PLAN ")
    print("═══════════════════════════════════════════════════════════════")
    print(f"Total Protection Blocks:  {plan.total_buffers_generated}")
    print(f"Transition Buffers Added: {plan.total_buffer_minutes_added} min")
    print(
        f"Deep Work Focus Blocks:   {plan.total_deep_work_blocks_protected} blocks ({plan.protected_focus_hours_added:.1f} hrs)"
    )
    print("───────────────────────────────────────────────────────────────")

    for b in plan.buffers[:6]:
        t_str = f"{b.start.strftime('%a %H:%M')} - {b.end.strftime('%H:%M')}"
        print(f"   • [{b.buffer_type:<15}] {t_str} ({b.duration_minutes}m) -> {b.reason}")

    if len(plan.buffers) > 6:
        print(f"   ... and {len(plan.buffers) - 6} additional protection blocks.")

    if args.apply:
        combined = protector.apply_protection(events, plan)
        storage.save_events(combined)
        print("───────────────────────────────────────────────────────────────")
        print(f"✅ Applied {plan.total_buffers_generated} protection blocks directly to local calendar.")

    if args.export:
        out_path = Path(args.export)
        combined = protector.apply_protection(events, plan)
        ics_text = CalendarParser.export_to_ics(combined, cal_name="Cadence Protected Calendar")
        out_path.write_text(ics_text, encoding="utf-8")
        print(f"📦 Exported protected calendar ICS to: {out_path.resolve()}")

    print("═══════════════════════════════════════════════════════════════")
    return 0


def handle_ask(args: argparse.Namespace, storage: CadenceStorage) -> int:
    _name, wh, meta = storage.load_profile()
    events = storage.load_events()

    auditor = CalendarAuditor(work_hours=wh)
    audit = auditor.audit_events(events)

    companion = CadenceCompanion()
    response = companion.consult(args.query, audit_result=audit, profile_data=meta)

    if args.json:
        print(json.dumps(response.to_dict(), indent=2))
        return 0

    print("═══════════════════════════════════════════════════════════════")
    print(f' 🤖 CADENCE AI ADVISOR: "{args.query}"')
    print("═══════════════════════════════════════════════════════════════")
    print(response.summary)
    print("───────────────────────────────────────────────────────────────")
    if response.recommendations:
        print("💡 Actionable Recommendations:")
        for r in response.recommendations:
            print(f"   • {r}")
    if response.action_items:
        print("📌 Next Steps:")
        for a in response.action_items:
            print(f"   • {a}")
    print("═══════════════════════════════════════════════════════════════")
    return 0


def handle_stats(args: argparse.Namespace, storage: CadenceStorage) -> int:
    name, wh, _meta = storage.load_profile()
    events = storage.load_events()

    stats_data = {
        "profile_name": name,
        "total_events": len(events),
        "work_hours": f"{wh.start_time.strftime('%H:%M')} - {wh.end_time.strftime('%H:%M')}",
        "lunch_window": f"{wh.lunch_start.strftime('%H:%M')} ({wh.lunch_duration_minutes}m)",
        "earliest_event": events[0].start.isoformat() if events else None,
        "latest_event": events[-1].end.isoformat() if events else None,
    }

    if args.json:
        print(json.dumps(stats_data, indent=2))
        return 0

    print(f"📅 Profile: {name}")
    print(f"   • Stored Events: {len(events)}")
    print(f"   • Core Hours:    {stats_data['work_hours']}")
    print(f"   • Lunch Window:  {stats_data['lunch_window']}")
    if events:
        print(f"   • Date Span:     {events[0].start.strftime('%Y-%m-%d')} to {events[-1].end.strftime('%Y-%m-%d')}")
    return 0


def handle_export(args: argparse.Namespace, storage: CadenceStorage) -> int:
    events = storage.load_events()
    out_path = Path(args.output)

    if out_path.suffix.lower() == ".json":
        payload = [e.to_dict() for e in events]
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        ics_text = CalendarParser.export_to_ics(events, cal_name=args.cal_name)
        out_path.write_text(ics_text, encoding="utf-8")

    print(f"📦 Successfully exported {len(events)} events to {out_path.resolve()}")
    return 0


def handle_clean(args: argparse.Namespace, storage: CadenceStorage) -> int:
    if args.all:
        storage.clear_events()
        print("🧹 Successfully cleared all stored calendar events.")
        return 0
    print("Please provide --all to confirm clearing the local calendar store.", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    storage = CadenceStorage(data_dir=args.data_dir)

    if args.command == "init":
        return handle_init(args, storage)
    elif args.command == "ingest":
        return handle_ingest(args, storage)
    elif args.command == "audit":
        return handle_audit(args, storage)
    elif args.command == "protect":
        return handle_protect(args, storage)
    elif args.command == "ask":
        return handle_ask(args, storage)
    elif args.command == "stats":
        return handle_stats(args, storage)
    elif args.command == "export":
        return handle_export(args, storage)
    elif args.command == "clean":
        return handle_clean(args, storage)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
