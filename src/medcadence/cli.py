# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for medcadence-core.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .advisor import HealthAdvisor
from .interactions import InteractionSafetyEngine
from .labs import BiomarkerLabEngine
from .models import (
    BiomarkerCategory,
    BiomarkerRecord,
    MedicationItem,
    WearableTelemetryPoint,
)
from .storage import HealthStore


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  medcadence v{__version__:<10}                                    │
│  Personal Health Telemetry & AI Medical Companion           │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="medcadence",
        description="Personal Health Telemetry, Lab Biomarker Ledger, Interaction Checker & AI Medical Companion.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Custom data directory.")
    parser.add_argument("--version", "-v", action="version", version=f"medcadence {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init
    init_p = subparsers.add_parser("init", help="Initialize health profile.")
    init_p.add_argument("--label", default="Primary User", help="User nickname or label")
    init_p.add_argument("--sex", choices=["male", "female", "other"], default="male", help="Biological sex")
    init_p.add_argument("--birth-year", type=int, default=1990, help="Birth year (YYYY)")

    # Lab Biomarkers
    lab_p = subparsers.add_parser("lab", help="Manage laboratory blood biomarkers.")
    lab_sub = lab_p.add_subparsers(dest="subcommand", required=True)

    lab_add = lab_sub.add_parser("add", help="Add a lab biomarker result.")
    lab_add.add_argument("--name", required=True, help="Biomarker name (e.g. 'LDL Cholesterol', 'HbA1c')")
    lab_add.add_argument("--category", choices=[c.value for c in BiomarkerCategory], default="lipid_panel")
    lab_add.add_argument("--value", type=float, required=True, help="Numerical lab measurement")
    lab_add.add_argument("--unit", default="mg/dL", help="Measurement unit")
    lab_add.add_argument("--low", type=float, default=0.0, help="Reference range low bound")
    lab_add.add_argument("--high", type=float, default=0.0, help="Reference range high bound")
    lab_add.add_argument("--date", default=None, help="Date of test (YYYY-MM-DD)")

    lab_sub.add_parser("list", help="List all logged laboratory biomarkers.")
    lab_trends = lab_sub.add_parser("trends", help="Analyze longitudinal trends and reference range deviations.")
    lab_trends.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Medications
    med_p = subparsers.add_parser("med", help="Manage medications and supplements.")
    med_sub = med_p.add_subparsers(dest="subcommand", required=True)

    med_add = med_sub.add_parser("add", help="Add a medication or dietary supplement.")
    med_add.add_argument("--name", required=True, help="Medication/supplement name (e.g. 'Atorvastatin', 'Vitamin K2')")
    med_add.add_argument("--dosage", default="", help="Dosage (e.g. '20mg')")
    med_add.add_argument("--frequency", default="daily", help="Frequency (daily, twice_daily, etc.)")
    med_add.add_argument("--supplement", action="store_true", help="Flag as over-the-counter dietary supplement")

    med_sub.add_parser("list", help="List all active medications.")
    med_audit = med_sub.add_parser("audit", help="Audit current regimen for drug-drug & drug-supplement interactions.")
    med_audit.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Telemetry
    tel_p = subparsers.add_parser("telemetry", help="Manage wearable biometric telemetry.")
    tel_sub = tel_p.add_subparsers(dest="subcommand", required=True)

    tel_add = tel_sub.add_parser("add", help="Log daily biometric telemetry point.")
    tel_add.add_argument("--rhr", type=float, default=0.0, help="Resting Heart Rate (bpm)")
    tel_add.add_argument("--hrv", type=float, default=0.0, help="HRV rMSSD (ms)")
    tel_add.add_argument("--sleep-hours", type=float, default=0.0, help="Total sleep hours")
    tel_add.add_argument("--vo2", type=float, default=0.0, help="VO2 Max (mL/kg/min)")
    tel_add.add_argument("--steps", type=int, default=0, help="Daily step count")

    tel_sub.add_parser("list", help="List biometric telemetry logs.")

    # Emergency Card
    em_p = subparsers.add_parser("emergency", help="Manage emergency medical profile.")
    em_sub = em_p.add_subparsers(dest="subcommand", required=True)

    em_set = em_sub.add_parser("set", help="Set emergency card information.")
    em_set.add_argument("--blood-type", default="O+", help="Blood Type (e.g. 'A+', 'O-')")
    em_set.add_argument("--allergies", default="", help="Comma-separated allergies (e.g. 'Penicillin,Peanuts')")
    em_set.add_argument("--conditions", default="", help="Comma-separated chronic conditions")
    em_set.add_argument("--contacts", default="", help="Emergency contact name/phone")

    em_sub.add_parser("show", help="Display emergency health card.")

    # Ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI Healthcare Companion.")
    ask_p.add_argument("query", help="Question about your lab biomarkers, interaction safety, or physician questions.")
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON analysis.")

    args = parser.parse_args(argv)
    store = HealthStore(args.data_dir)
    profile = store.load_profile()

    # Init
    if args.command == "init":
        profile.user_label = args.label
        profile.biological_sex = args.sex
        profile.year_of_birth = args.birth_year
        store.save_profile(profile)
        print(f"[✓] Initialized Health Profile for '{profile.user_label}' ({profile.biological_sex}, born {profile.year_of_birth})")
        return 0

    # Lab
    if args.command == "lab":
        if args.subcommand == "add":
            record = BiomarkerRecord(
                name=args.name,
                category=BiomarkerCategory(args.category),
                value=args.value,
                unit=args.unit,
                ref_low=args.low,
                ref_high=args.high,
                date=args.date or BiomarkerRecord().date,
            )
            profile.biomarkers.append(record)
            store.save_profile(profile)
            print(f"[✓] Logged Biomarker: {record.name} = {record.value} {record.unit} (Status: {record.status.value})")
            return 0

        elif args.subcommand == "list":
            print(f"\nLaboratory Biomarkers ({len(profile.biomarkers)} records):")
            print("=" * 75)
            for b in profile.biomarkers:
                ref_str = f"[{b.ref_low} - {b.ref_high} {b.unit}]" if b.ref_high > 0 else f"[>{b.ref_low} {b.unit}]"
                print(f"[{b.date}] {b.name:<25} : {b.value:>7.2f} {b.unit:<8} {ref_str:<18} | {b.status.value}")
            print("=" * 75 + "\n")
            return 0

        elif args.subcommand == "trends":
            trends = BiomarkerLabEngine.analyze_trends(profile)
            if args.json:
                print(json.dumps([t.__dict__ for t in trends], indent=2, default=str))
                return 0

            print("\n" + "=" * 75)
            print("                   LONGITUDINAL BIOMARKER TRENDS                 ")
            print("=" * 75)
            for t in trends:
                sign = "+" if t.delta_vs_previous >= 0 else ""
                delta_str = f"Delta: {sign}{t.delta_vs_previous} {t.unit} ({sign}{t.delta_pct}%)" if t.historical_count > 1 else "(Baseline)"
                print(f"  • {t.name:<24} : {t.latest_value:>7.2f} {t.unit:<8} [{t.latest_status.value:<14}] {delta_str}")
            print("=" * 75 + "\n")
            return 0

    # Med
    if args.command == "med":
        if args.subcommand == "add":
            item = MedicationItem(
                name=args.name,
                dosage=args.dosage,
                frequency=args.frequency,
                is_supplement=args.supplement,
            )
            profile.medications.append(item)
            store.save_profile(profile)
            kind = "Supplement" if item.is_supplement else "Medication"
            print(f"[✓] Added {kind}: {item.name} ({item.dosage} {item.frequency})")
            return 0

        elif args.subcommand == "list":
            print(f"\nActive Medications & Supplements ({len(profile.medications)} items):")
            print("=" * 75)
            for m in profile.medications:
                tag = "[OTC Supp]" if m.is_supplement else "[Rx Med  ]"
                print(f"{tag} {m.name:<26} : {m.dosage:<10} | {m.frequency}")
            print("=" * 75 + "\n")
            return 0

        elif args.subcommand == "audit":
            alerts = InteractionSafetyEngine.audit_profile(profile)
            if args.json:
                print(json.dumps([a.to_dict() for a in alerts], indent=2))
                return 0

            print("\n" + "=" * 75)
            print("               MEDICATION & SUPPLEMENT SAFETY AUDIT               ")
            print("=" * 75)
            if not alerts:
                print("  🟢 No known severe drug-drug or drug-supplement interactions detected.")
            else:
                for a in alerts:
                    print(f"\n🚨 [{a.severity.value.upper()}] {a.item_a} + {a.item_b}")
                    print(f"   Mechanism : {a.mechanism}")
                    print(f"   Guidance  : {a.clinical_note}")
            print("\n" + "=" * 75 + "\n")
            return 0

    # Telemetry
    if args.command == "telemetry":
        if args.subcommand == "add":
            pt = WearableTelemetryPoint(
                resting_heart_rate=args.rhr,
                hrv_rmssd=args.hrv,
                sleep_duration_hours=args.sleep_hours,
                vo2_max=args.vo2,
                step_count=args.steps,
            )
            profile.telemetry.append(pt)
            store.save_profile(profile)
            print(f"[✓] Logged Biometric Point: RHR={pt.resting_heart_rate} bpm | HRV={pt.hrv_rmssd} ms | Sleep={pt.sleep_duration_hours} hrs")
            return 0

        elif args.subcommand == "list":
            print(f"\nBiometric Telemetry Records ({len(profile.telemetry)} entries):")
            print("=" * 75)
            for t in profile.telemetry:
                print(f"[{t.date}] RHR: {t.resting_heart_rate:>4.1f} bpm | HRV: {t.hrv_rmssd:>4.1f} ms | Sleep: {t.sleep_duration_hours:>4.1f}h | Steps: {t.step_count:>6}")
            print("=" * 75 + "\n")
            return 0

    # Emergency
    if args.command == "emergency":
        if args.subcommand == "set":
            profile.emergency.blood_type = args.blood_type
            if args.allergies:
                profile.emergency.allergies = [a.strip() for a in args.allergies.split(",") if a.strip()]
            if args.conditions:
                profile.emergency.chronic_conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
            if args.contacts:
                profile.emergency.emergency_contacts = [ct.strip() for ct in args.contacts.split(",") if ct.strip()]
            store.save_profile(profile)
            print("[✓] Updated Emergency Health Card.")
            return 0

        elif args.subcommand == "show":
            em = profile.emergency
            print("\n" + "=" * 65)
            print("                     EMERGENCY HEALTH CARD                       ")
            print("=" * 65)
            print(f"  Blood Type         : {em.blood_type}")
            print(f"  Critical Allergies : {', '.join(em.allergies) if em.allergies else 'None Recorded'}")
            print(f"  Chronic Conditions : {', '.join(em.chronic_conditions) if em.chronic_conditions else 'None Recorded'}")
            print(f"  Emergency Contacts : {', '.join(em.emergency_contacts) if em.emergency_contacts else 'None Recorded'}")
            print("=" * 65 + "\n")
            return 0

    # Ask
    if args.command == "ask":
        advisor = HealthAdvisor()
        resp = advisor.consult(args.query, profile)

        if args.json:
            print(json.dumps(resp.to_dict(), indent=2))
            return 0

        print("\n" + "━" * 70)
        print(f"🤖 AI HEALTHCARE COMPANION: '{args.query}'")
        print("━" * 70)
        print(f"\n🎯 CLINICAL SYNTHESIS:\n{resp.clinical_synthesis}\n")
        if resp.abnormal_biomarkers:
            print("⚠️ OUT-OF-RANGE BIOMARKERS:")
            for ab in resp.abnormal_biomarkers:
                print(f"  • {ab}")
            print()
        if resp.medication_safety_flags:
            print("🚨 MEDICATION SAFETY ALERTS:")
            for fl in resp.medication_safety_flags:
                print(f"  • {fl}")
            print()
        if resp.questions_for_physician:
            print("📋 QUESTIONS FOR YOUR DOCTOR:")
            for q in resp.questions_for_physician:
                print(f"  • {q}")
            print()
        if resp.lifestyle_considerations:
            print("🌿 WELLNESS CONSIDERATIONS:")
            for ls in resp.lifestyle_considerations:
                print(f"  • {ls}")
            print()
        print("━" * 70 + "\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
