# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for oncorenal-core.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .companion import SpecialtyCareCompanion
from .dialysis import DialysisEngine
from .models import (
    ChemoCycle,
    DialysisSession,
    FluidIntakeLog,
    SpecialtyLabRecord,
    SymptomToxicityLog,
)
from .oncology import OncologyEngine
from .storage import SpecialtyStore


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  oncorenal v{__version__:<10}                                   │
│  Oncology Chemo Cycles & Renal Dialysis Care Companion      │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="oncorenal",
        description="Oncology Chemotherapy Cycle Tracker, Renal Dialysis Fluid/Dry Weight Ledger & AI Specialty Companion.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Custom data directory.")
    parser.add_argument("--version", "-v", action="version", version=f"oncorenal {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init
    init_p = subparsers.add_parser("init", help="Initialize specialty patient profile.")
    init_p.add_argument("--name", required=True, help="Patient Name")
    init_p.add_argument("--relationship", default="Parent", help="Relationship (Mother, Father, Spouse, etc.)")
    init_p.add_argument("--cancer-dx", default="", help="Oncology diagnosis (e.g. 'Colorectal Cancer', 'Lymphoma')")
    init_p.add_argument("--renal-dx", default="End-Stage Renal Disease (ESRD)", help="Renal diagnosis")
    init_p.add_argument("--dry-weight", type=float, default=68.0, help="Prescribed target dry weight in kg")
    init_p.add_argument("--fluid-limit", type=float, default=1000.0, help="Daily fluid limit in mL")

    # Chemo
    chemo_p = subparsers.add_parser("chemo", help="Manage oncology chemotherapy cycles & nadir windows.")
    chemo_sub = chemo_p.add_subparsers(dest="subcommand", required=True)

    chemo_add = chemo_sub.add_parser("add", help="Add a chemotherapy infusion cycle.")
    chemo_add.add_argument("--regimen", required=True, help="Regimen Name (e.g. 'FOLFOX', 'AC-T', 'Carboplatin')")
    chemo_add.add_argument("--cycle", type=int, default=1, help="Cycle number")
    chemo_add.add_argument("--total", type=int, default=6, help="Total planned cycles")
    chemo_add.add_argument("--date", default=None, help="Infusion date (YYYY-MM-DD)")
    chemo_add.add_argument("--length", type=int, default=21, help="Cycle length in days (e.g. 14, 21, 28)")
    chemo_add.add_argument("--nadir-start", type=int, default=7, help="Nadir immune low start day")
    chemo_add.add_argument("--nadir-end", type=int, default=14, help="Nadir immune low end day")

    chemo_tox = chemo_sub.add_parser("log-tox", help="Log daily chemo side-effects and temperature.")
    chemo_tox.add_argument("--temp", type=float, default=98.6, help="Body temperature in Fahrenheit")
    chemo_tox.add_argument("--nausea", type=int, default=0, choices=[0, 1, 2, 3, 4], help="Nausea CTCAE grade (0-4)")
    chemo_tox.add_argument("--fatigue", type=int, default=0, choices=[0, 1, 2, 3, 4], help="Fatigue CTCAE grade (0-4)")
    chemo_tox.add_argument(
        "--neuropathy", type=int, default=0, choices=[0, 1, 2, 3, 4], help="Neuropathy tingling grade (0-4)"
    )
    chemo_tox.add_argument("--mucositis", type=int, default=0, choices=[0, 1, 2, 3, 4], help="Mouth sores grade (0-4)")
    chemo_tox.add_argument("--notes", default="", help="Notes")

    chemo_sub.add_parser("nadir", help="Check current immune nadir window status and precautions.")
    chemo_sub.add_parser("list", help="List chemotherapy cycle history.")

    # Dialysis
    dial_p = subparsers.add_parser("dialysis", help="Manage dialysis sessions and interdialytic weight gain (IDWG).")
    dial_sub = dial_p.add_subparsers(dest="subcommand", required=True)

    dial_add = dial_sub.add_parser("session", help="Log a completed dialysis session.")
    dial_add.add_argument("--pre-wt", type=float, required=True, help="Pre-dialysis weight in kg")
    dial_add.add_argument("--post-wt", type=float, required=True, help="Post-dialysis weight in kg")
    dial_add.add_argument("--pre-sys", type=int, default=140, help="Pre-dialysis systolic BP")
    dial_add.add_argument("--pre-dia", type=int, default=90, help="Pre-dialysis diastolic BP")
    dial_add.add_argument("--post-sys", type=int, default=125, help="Post-dialysis systolic BP")
    dial_add.add_argument("--post-dia", type=int, default=80, help="Post-dialysis diastolic BP")
    dial_add.add_argument("--uf", type=float, default=2.5, help="Ultrafiltration fluid volume removed in liters")
    dial_add.add_argument("--access-ok", action="store_true", default=True, help="Vascular access bruit/thrill normal")

    dial_sub.add_parser("idwg", help="Calculate Interdialytic Weight Gain (IDWG) vs target dry weight.")
    dial_sub.add_parser("list", help="List dialysis session history.")

    # Fluid
    fl_p = subparsers.add_parser("fluid", help="Track daily fluid intake and dietary renal macros.")
    fl_sub = fl_p.add_subparsers(dest="subcommand", required=True)

    fl_log = fl_sub.add_parser("log", help="Log daily fluid & mineral intake.")
    fl_log.add_argument("--ml", type=float, required=True, help="Total daily fluid in mL (including coffee, soup, ice)")
    fl_log.add_argument("--potassium", type=float, default=0.0, help="Potassium in mg")
    fl_log.add_argument("--phosphorus", type=float, default=0.0, help="Phosphorus in mg")
    fl_log.add_argument("--binders-taken", action="store_true", default=True, help="Phosphate binders taken with meals")

    fl_sub.add_parser("list", help="List fluid logs.")

    # Labs
    lab_p = subparsers.add_parser("labs", help="Log specialty oncology & renal lab panels.")
    lab_sub = lab_p.add_subparsers(dest="subcommand", required=True)

    lab_add = lab_sub.add_parser("add", help="Add specialty blood panel.")
    lab_add.add_argument("--wbc", type=float, default=0.0, help="White Blood Cells (x10^3/uL)")
    lab_add.add_argument("--anc", type=float, default=0.0, help="Absolute Neutrophil Count (/uL)")
    lab_add.add_argument("--potassium", type=float, default=0.0, help="Serum Potassium (mEq/L)")
    lab_add.add_argument("--phosphorus", type=float, default=0.0, help="Serum Phosphorus (mg/dL)")
    lab_add.add_argument("--creatinine", type=float, default=0.0, help="Serum Creatinine (mg/dL)")
    lab_add.add_argument("--albumin", type=float, default=0.0, help="Serum Albumin (g/dL)")

    lab_sub.add_parser("list", help="List specialty lab history.")

    # Ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI Oncology & Renal Specialty Companion.")
    ask_p.add_argument("query", help="Question regarding chemo nadir, fluid restriction, or emergency protocols.")
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON analysis.")

    args = parser.parse_args(argv)
    store = SpecialtyStore(args.data_dir)
    profile = store.load_profile()

    # Init
    if args.command == "init":
        profile.patient_name = args.name
        profile.relationship = args.relationship
        profile.primary_oncology_dx = args.cancer_dx
        profile.primary_renal_dx = args.renal_dx
        profile.target_dry_weight_kg = args.dry_weight
        profile.daily_fluid_limit_ml = args.fluid_limit
        store.save_profile(profile)
        print(
            f"[✓] Initialized Onco-Renal Profile for {profile.patient_name} (Dry Weight: {profile.target_dry_weight_kg} kg | Fluid Limit: {profile.daily_fluid_limit_ml} mL)"
        )
        return 0

    # Chemo
    if args.command == "chemo":
        if args.subcommand == "add":
            cycle = ChemoCycle(
                regimen_name=args.regimen,
                cycle_number=args.cycle,
                total_planned_cycles=args.total,
                infusion_date=args.date or ChemoCycle().infusion_date,
                cycle_length_days=args.length,
                nadir_start_day=args.nadir_start,
                nadir_end_day=args.nadir_end,
            )
            profile.chemo_cycles.append(cycle)
            store.save_profile(profile)
            print(
                f"[✓] Added Chemo Cycle: {cycle.regimen_name} Cycle {cycle.cycle_number}/{cycle.total_planned_cycles} (Infusion: {cycle.infusion_date})"
            )
            return 0

        elif args.subcommand == "log-tox":
            tox = SymptomToxicityLog(
                temperature_f=args.temp,
                nausea_ctcae_grade=args.nausea,
                fatigue_ctcae_grade=args.fatigue,
                neuropathy_ctcae_grade=args.neuropathy,
                mucositis_mouth_sores_grade=args.mucositis,
                notes=args.notes,
            )
            profile.toxicity_logs.append(tox)
            store.save_profile(profile)
            temp_flag = " 🚨 FEVER ALERT!" if tox.temperature_f >= 100.4 else ""
            print(
                f"[✓] Logged Toxicity: Temp: {tox.temperature_f}°F{temp_flag} | Nausea: G{tox.nausea_ctcae_grade} | Neuropathy: G{tox.neuropathy_ctcae_grade}"
            )
            return 0

        elif args.subcommand == "nadir":
            status = OncologyEngine.get_current_nadir_status(profile)
            if not status:
                print("No chemotherapy cycles found. Add one with 'oncorenal chemo add'.", file=sys.stderr)
                return 1

            badge = "🚨 IN IMMUNE NADIR WINDOW" if status.is_in_nadir_window else "🟢 RECOVERY / MONITORING"
            print("\n" + "=" * 75)
            print("                 CHEMOTHERAPY NADIR IMMUNE MONITOR               ")
            print("=" * 75)
            print(f"  Regimen          : {status.regimen_name} (Cycle {status.cycle_number})")
            print(f"  Current Cycle Day: Day {status.current_cycle_day} of {status.cycle_length_days} [{badge}]")
            print(f"  Nadir Window     : {status.nadir_start_date} to {status.nadir_end_date}")
            print(f"  Next Infusion    : {status.next_infusion_date}")
            print("─" * 75)
            print(f"  CLINICAL ADVISORY:\n  {status.precaution_advisory}")
            print("=" * 75 + "\n")
            return 0

        elif args.subcommand == "list":
            print(f"\nChemotherapy Cycle History ({len(profile.chemo_cycles)} cycles):")
            print("=" * 75)
            for c in profile.chemo_cycles:
                print(
                    f"[{c.infusion_date}] {c.regimen_name:<20} : Cycle {c.cycle_number}/{c.total_planned_cycles} (Length: {c.cycle_length_days}d | Nadir: D{c.nadir_start_day}-D{c.nadir_end_day})"
                )
            print("=" * 75 + "\n")
            return 0

    # Dialysis
    if args.command == "dialysis":
        if args.subcommand == "session":
            session = DialysisSession(
                pre_dialysis_weight_kg=args.pre_wt,
                post_dialysis_weight_kg=args.post_wt,
                pre_dialysis_bp_sys=args.pre_sys,
                pre_dialysis_bp_dia=args.pre_dia,
                post_dialysis_bp_sys=args.post_sys,
                post_dialysis_bp_dia=args.post_dia,
                ultrafiltration_removed_liters=args.uf,
                access_site_bruit_thrill_normal=args.access_ok,
            )
            profile.dialysis_sessions.append(session)
            store.save_profile(profile)
            print(
                f"[✓] Logged Dialysis Session: Pre: {session.pre_dialysis_weight_kg}kg -> Post: {session.post_dialysis_weight_kg}kg (UF Removed: {session.ultrafiltration_removed_liters}L)"
            )
            return 0

        elif args.subcommand == "idwg":
            idwg = DialysisEngine.calculate_idwg(profile)
            if not idwg:
                print("No dialysis sessions or dry weight configured.", file=sys.stderr)
                return 1

            print("\n" + "=" * 75)
            print("             INTERDIALYTIC WEIGHT GAIN (IDWG) AUDIT              ")
            print("=" * 75)
            print(
                f"  Target Dry Weight      : {idwg.target_dry_weight_kg:>6.1f} kg ({idwg.target_dry_weight_kg * 2.20462:.1f} lbs)"
            )
            print(
                f"  Latest Pre-Dialysis Wt : {idwg.latest_pre_weight_kg:>6.1f} kg ({idwg.latest_pre_weight_kg * 2.20462:.1f} lbs)"
            )
            print(
                f"  Fluid Gain Accumulation: +{idwg.interdialytic_weight_gain_kg:>5.1f} kg (+{idwg.interdialytic_weight_gain_lbs:.1f} lbs | {idwg.weight_gain_pct_of_dry_weight:.1f}%)"
            )
            print("─" * 75)
            print(f"  Fluid Overload Status  : {idwg.fluid_overload_tier}")
            print(f"  Guidance               : {idwg.clinical_risk_note}")
            print("=" * 75 + "\n")
            return 0

        elif args.subcommand == "list":
            print(f"\nDialysis Session History ({len(profile.dialysis_sessions)} sessions):")
            print("=" * 75)
            for s in profile.dialysis_sessions:
                print(
                    f"[{s.date}] Pre: {s.pre_dialysis_weight_kg:>5.1f}kg -> Post: {s.post_dialysis_weight_kg:>5.1f}kg | UF: {s.ultrafiltration_removed_liters:>4.1f}L | BP: {s.pre_dialysis_bp_sys}/{s.pre_dialysis_bp_dia}"
                )
            print("=" * 75 + "\n")
            return 0

    # Fluid
    if args.command == "fluid":
        if args.subcommand == "log":
            fl = FluidIntakeLog(
                fluid_intake_ml=args.ml,
                potassium_mg=args.potassium,
                phosphorus_mg=args.phosphorus,
                phosphate_binders_taken_with_meals=args.binders_taken,
            )
            profile.fluid_logs.append(fl)
            store.save_profile(profile)
            rem = profile.daily_fluid_limit_ml - fl.fluid_intake_ml
            sign = "Remaining" if rem >= 0 else "OVER LIMIT by"
            print(
                f"[✓] Logged Fluid: {fl.fluid_intake_ml} mL / {profile.daily_fluid_limit_ml} mL limit ({abs(rem):.0f} mL {sign})"
            )
            return 0

        elif args.subcommand == "list":
            print(f"\nDaily Fluid Logs ({len(profile.fluid_logs)} entries):")
            print("=" * 75)
            for f in profile.fluid_logs:
                print(
                    f"[{f.date}] Intake: {f.fluid_intake_ml:>6.0f} mL | Binders Taken: {f.phosphate_binders_taken_with_meals}"
                )
            print("=" * 75 + "\n")
            return 0

    # Labs
    if args.command == "labs":
        if args.subcommand == "add":
            lab = SpecialtyLabRecord(
                white_blood_cells=args.wbc,
                absolute_neutrophil_count_anc=args.anc,
                serum_potassium=args.potassium,
                serum_phosphorus=args.phosphorus,
                serum_creatinine=args.creatinine,
                serum_albumin=args.albumin,
            )
            profile.specialty_labs.append(lab)
            store.save_profile(profile)
            print(
                f"[✓] Logged Specialty Labs: ANC={lab.absolute_neutrophil_count_anc} | K+={lab.serum_potassium} | Phos={lab.serum_phosphorus}"
            )
            return 0

        elif args.subcommand == "list":
            print(f"\nSpecialty Lab History ({len(profile.specialty_labs)} records):")
            print("=" * 80)
            for lab in profile.specialty_labs:
                print(
                    f"[{lab.date}] ANC: {lab.absolute_neutrophil_count_anc:<6} | K+: {lab.serum_potassium:<4} mEq/L | Phos: {lab.serum_phosphorus:<4} mg/dL | Albumin: {lab.serum_albumin}"
                )
            print("=" * 80 + "\n")
            return 0

    # Ask
    if args.command == "ask":
        companion = SpecialtyCareCompanion()
        resp = companion.consult(args.query, profile)

        if args.json:
            print(json.dumps(resp.to_dict(), indent=2))
            return 0

        print("\n" + "━" * 75)
        print(f"🤖 AI ONCOLOGY & RENAL SPECIALTY COMPANION: '{args.query}'")
        print("━" * 75)
        print(f"\n🎯 CLINICAL SUMMARY:\n{resp.clinical_summary}\n")
        if resp.urgent_red_flags:
            print("🚨 URGENT SPECIALTY RED FLAGS:")
            for rf in resp.urgent_red_flags:
                print(f"  • {rf}")
            print()
        if resp.oncology_protocols:
            print("🎗️ ONCOLOGY PROTOCOLS & PRECAUTIONS:")
            for op in resp.oncology_protocols:
                print(f"  • {op}")
            print()
        if resp.dialysis_and_fluid_guidelines:
            print("💧 DIALYSIS & FLUID GUIDELINES:")
            for dg in resp.dialysis_and_fluid_guidelines:
                print(f"  • {dg}")
            print()
        if resp.caregiver_specialty_checklist:
            print("⚡ SPECIALTY CAREGIVER CHECKLIST:")
            for cl in resp.caregiver_specialty_checklist:
                print(f"  • {cl}")
            print()
        print("━" * 75 + "\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
