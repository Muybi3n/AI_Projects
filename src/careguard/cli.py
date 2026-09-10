# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for careguard-core.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ai_companion import CareCompanion
from .engine import CareEngine
from .models import (
    CaregiverNote,
    DailyVitalsLog,
    DoctorVisit,
    MedicationSchedule,
    NoteCategory,
    PhysicianContact,
    TimingSlot,
)
from .storage import CareStore


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  careguard v{__version__:<10}                                    │
│  Family Medical Caregiver Journal & AI Clinical Briefing    │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="careguard",
        description="Family Caregiver Medical Record Tracker, Multi-Doctor Coordinator & AI Clinical Briefing Engine.",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="Custom data directory.")
    parser.add_argument("--version", "-v", action="version", version=f"careguard {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init
    init_p = subparsers.add_parser("init", help="Initialize care recipient profile.")
    init_p.add_argument("--name", required=True, help="Full name of family member")
    init_p.add_argument("--relationship", default="Parent", help="Relationship (Mother, Father, Spouse, etc.)")
    init_p.add_argument("--birth-year", type=int, default=1950, help="Birth year (YYYY)")
    init_p.add_argument("--diagnoses", default="", help="Comma-separated primary diagnoses")
    init_p.add_argument("--allergies", default="", help="Comma-separated allergies")
    init_p.add_argument("--code-status", default="Full Code", help="Code status (Full Code, DNR, POLST)")

    # Doctor
    doc_p = subparsers.add_parser("doctor", help="Manage physician & specialist directory.")
    doc_sub = doc_p.add_subparsers(dest="subcommand", required=True)

    doc_add = doc_sub.add_parser("add", help="Add a doctor / specialist.")
    doc_add.add_argument("--name", required=True, help="Doctor Name (e.g. 'Dr. Sarah Chen')")
    doc_add.add_argument(
        "--specialty", default="Primary Care", help="Medical Specialty (Cardiology, Neurology, Oncology, etc.)"
    )
    doc_add.add_argument("--clinic", default="", help="Clinic or Hospital system")
    doc_add.add_argument("--phone", default="", help="Clinic Phone number")

    doc_sub.add_parser("list", help="List all doctors.")

    # Visit
    vis_p = subparsers.add_parser("visit", help="Record doctor visit notes & order changes.")
    vis_sub = vis_p.add_subparsers(dest="subcommand", required=True)

    vis_add = vis_sub.add_parser("add", help="Log a completed doctor appointment.")
    vis_add.add_argument("--doctor", required=True, help="Physician name")
    vis_add.add_argument("--specialty", default="Primary Care", help="Specialty")
    vis_add.add_argument("--reason", default="", help="Reason for visit / Chief complaint")
    vis_add.add_argument("--findings", required=True, help="Doctor assessment and clinical findings")
    vis_add.add_argument("--changes", default="", help="Medication changes or new prescriptions ordered")
    vis_add.add_argument("--tests", default="", help="Lab orders, imaging, or follow-up tests requested")
    vis_add.add_argument("--follow-up", default="", help="Next follow-up date")

    vis_sub.add_parser("list", help="List past doctor visits.")

    # Medication
    med_p = subparsers.add_parser("med", help="Manage daily medication regimens & pillbox schedule.")
    med_sub = med_p.add_subparsers(dest="subcommand", required=True)

    med_add = med_sub.add_parser("add", help="Add prescription medication.")
    med_add.add_argument("--name", required=True, help="Drug name")
    med_add.add_argument("--dosage", required=True, help="Dosage (e.g. '25mg')")
    med_add.add_argument("--slot", choices=[s.value for s in TimingSlot], default="morning", help="Pillbox slot")
    med_add.add_argument("--purpose", default="", help="Medical purpose")
    med_add.add_argument("--doctor", default="", help="Prescribing physician")
    med_add.add_argument("--instructions", default="", help="Special instructions (with meals, etc.)")

    med_sub.add_parser("list", help="List active medications.")
    med_sub.add_parser("schedule", help="Display 4-slot daily pillbox administration schedule.")

    # Vitals
    vit_p = subparsers.add_parser("vitals", help="Log and audit daily vital signs.")
    vit_sub = vit_p.add_subparsers(dest="subcommand", required=True)

    vit_add = vit_sub.add_parser("add", help="Record daily vital signs.")
    vit_add.add_argument("--sys", type=int, default=0, help="Systolic Blood Pressure (mmHg)")
    vit_add.add_argument("--dia", type=int, default=0, help="Diastolic Blood Pressure (mmHg)")
    vit_add.add_argument("--hr", type=int, default=0, help="Heart Rate (bpm)")
    vit_add.add_argument("--spo2", type=float, default=0.0, help="Oxygen Saturation (%)")
    vit_add.add_argument("--weight", type=float, default=0.0, help="Weight (lbs)")
    vit_add.add_argument("--glucose", type=float, default=0.0, help="Blood Glucose (mg/dL)")
    vit_add.add_argument("--confusion", action="store_true", help="Flag cognitive confusion / brain fog incident")
    vit_add.add_argument("--notes", default="", help="Observation notes")

    vit_sub.add_parser("list", help="List vitals history.")
    vit_audit = vit_sub.add_parser("audit", help="Audit vitals for red-flag emergency deviations.")
    vit_audit.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Note
    note_p = subparsers.add_parser("note", help="Add caregiver observations and shift handoff notes.")
    note_sub = note_p.add_subparsers(dest="subcommand", required=True)

    note_add = note_sub.add_parser("add", help="Add caregiver note.")
    note_add.add_argument("--author", default="Primary Caregiver", help="Caregiver name")
    note_add.add_argument("--category", choices=[c.value for c in NoteCategory], default="observation")
    note_add.add_argument("--text", required=True, help="Caregiver journal note text")

    note_sub.add_parser("list", help="List caregiver journal notes.")

    # Brief
    brief_p = subparsers.add_parser("brief", help="Generate 1-page physician appointment prep briefing sheet.")
    brief_p.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI Caregiver Medical Companion.")
    ask_p.add_argument("query", help="Question about care regimen, doctor visit summaries, or vitals.")
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON analysis.")

    args = parser.parse_args(argv)
    store = CareStore(args.data_dir)
    recipient = store.load_recipient()

    # Init
    if args.command == "init":
        recipient.full_name = args.name
        recipient.relationship = args.relationship
        recipient.year_of_birth = args.birth_year
        if args.diagnoses:
            recipient.primary_diagnoses = [d.strip() for d in args.diagnoses.split(",") if d.strip()]
        if args.allergies:
            recipient.allergies = [a.strip() for a in args.allergies.split(",") if a.strip()]
        recipient.code_status = args.code_status
        store.save_recipient(recipient)
        print(
            f"[✓] Initialized Care Recipient: {recipient.full_name} ({recipient.relationship}, born {recipient.year_of_birth})"
        )
        return 0

    # Doctor
    if args.command == "doctor":
        if args.subcommand == "add":
            doc = PhysicianContact(
                name=args.name,
                specialty=args.specialty,
                clinic_or_hospital=args.clinic,
                phone=args.phone,
            )
            recipient.physicians.append(doc)
            store.save_recipient(recipient)
            print(f"[✓] Added Physician: {doc.name} ({doc.specialty}) - {doc.clinic_or_hospital}")
            return 0

        elif args.subcommand == "list":
            print(f"\nPhysician Directory for {recipient.full_name} ({len(recipient.physicians)} doctors):")
            print("=" * 75)
            for d in recipient.physicians:
                print(f"[{d.id}] {d.name:<25} : {d.specialty:<20} | Phone: {d.phone}")
            print("=" * 75 + "\n")
            return 0

    # Visit
    if args.command == "visit":
        if args.subcommand == "add":
            visit = DoctorVisit(
                physician_name=args.doctor,
                specialty=args.specialty,
                reason_for_visit=args.reason,
                physician_findings=args.findings,
                medication_changes=args.changes,
                orders_and_tests=args.tests,
                next_follow_up_date=args.follow_up,
            )
            recipient.doctor_visits.append(visit)
            store.save_recipient(recipient)
            print(f"[✓] Logged Doctor Visit: {visit.physician_name} ({visit.specialty}) on {visit.date}")
            return 0

        elif args.subcommand == "list":
            print(f"\nDoctor Visit History for {recipient.full_name} ({len(recipient.doctor_visits)} visits):")
            print("=" * 80)
            for v in recipient.doctor_visits:
                print(
                    f"[{v.date}] {v.physician_name:<22} ({v.specialty:<15}) -> Findings: {v.physician_findings[:40]}..."
                )
            print("=" * 80 + "\n")
            return 0

    # Medication
    if args.command == "med":
        if args.subcommand == "add":
            med = MedicationSchedule(
                name=args.name,
                dosage=args.dosage,
                timing_slot=TimingSlot(args.slot),
                purpose=args.purpose,
                prescribed_by=args.doctor,
                special_instructions=args.instructions,
            )
            recipient.medications.append(med)
            store.save_recipient(recipient)
            print(f"[✓] Added Medication: {med.name} ({med.dosage}) -> Slot: {med.timing_slot.value.upper()}")
            return 0

        elif args.subcommand == "list":
            print(f"\nActive Medications for {recipient.full_name} ({len(recipient.medications)} items):")
            print("=" * 75)
            for m in recipient.medications:
                print(f"[{m.timing_slot.value.upper():<8}] {m.name:<24} : {m.dosage:<8} | Purpose: {m.purpose}")
            print("=" * 75 + "\n")
            return 0

        elif args.subcommand == "schedule":
            pillbox = CareEngine.get_pillbox_schedule(recipient)
            print("\n" + "=" * 70)
            print(f"           DAILY PILLBOX SCHEDULE FOR {recipient.full_name.upper()}           ")
            print("=" * 70)
            for slot in ["morning", "noon", "evening", "bedtime", "as_needed"]:
                items = pillbox.get(slot, [])
                print(f"\n⏰ {slot.upper()} SLOT ({len(items)} items):")
                if not items:
                    print("   (No medications scheduled)")
                for it in items:
                    extra = f" [{it['instructions']}]" if it["instructions"] else ""
                    print(f"   • {it['name']} ({it['dosage']}) - {it['purpose']}{extra}")
            print("\n" + "=" * 70 + "\n")
            return 0

    # Vitals
    if args.command == "vitals":
        if args.subcommand == "add":
            log = DailyVitalsLog(
                systolic_bp=args.sys,
                diastolic_bp=args.dia,
                heart_rate=args.hr,
                spo2_pct=args.spo2,
                weight_lbs=args.weight,
                blood_glucose=args.glucose,
                confusion_or_cognitive_fog=args.confusion,
                notes=args.notes,
            )
            recipient.vitals_history.append(log)
            store.save_recipient(recipient)
            bp_str = f"BP: {log.systolic_bp}/{log.diastolic_bp} mmHg" if log.systolic_bp > 0 else ""
            spo2_str = f"SpO2: {log.spo2_pct}%" if log.spo2_pct > 0 else ""
            print(f"[✓] Logged Vitals: {bp_str} {spo2_str} (HR: {log.heart_rate} bpm)")
            return 0

        elif args.subcommand == "list":
            print(f"\nVitals History for {recipient.full_name} ({len(recipient.vitals_history)} logs):")
            print("=" * 80)
            for v in recipient.vitals_history:
                bp = f"{v.systolic_bp}/{v.diastolic_bp}" if v.systolic_bp > 0 else "N/A"
                print(
                    f"[{v.timestamp[:16]}] BP: {bp:<8} | HR: {v.heart_rate:<3} bpm | SpO2: {v.spo2_pct:>4.1f}% | Wt: {v.weight_lbs:>5.1f} lbs"
                )
            print("=" * 80 + "\n")
            return 0

        elif args.subcommand == "audit":
            anomalies = CareEngine.audit_vitals(recipient)
            if args.json:
                print(json.dumps([a.__dict__ for a in anomalies], indent=2))
                return 0

            print("\n" + "=" * 75)
            print(f"            VITALS ANOMALY & SAFETY AUDIT ({recipient.full_name})           ")
            print("=" * 75)
            if not anomalies:
                print("  🟢 No acute red-flag vitals deviations detected.")
            else:
                for a in anomalies:
                    print(f"\n🚨 [{a.severity}] {a.vital_metric} = {a.observed_value}")
                    print(f"   Timestamp : {a.timestamp}")
                    print(f"   Clinical  : {a.clinical_rationale}")
            print("\n" + "=" * 75 + "\n")
            return 0

    # Note
    if args.command == "note":
        if args.subcommand == "add":
            note = CaregiverNote(
                caregiver_name=args.author,
                category=NoteCategory(args.category),
                note_text=args.text,
            )
            recipient.caregiver_journal.append(note)
            store.save_recipient(recipient)
            print(f"[✓] Added Caregiver Note [{note.category.value}]: {note.note_text[:50]}...")
            return 0

        elif args.subcommand == "list":
            print(f"\nCaregiver Journal for {recipient.full_name} ({len(recipient.caregiver_journal)} notes):")
            print("=" * 80)
            for n in recipient.caregiver_journal:
                print(f"[{n.timestamp[:10]}] ({n.caregiver_name} - {n.category.value}): {n.note_text}")
            print("=" * 80 + "\n")
            return 0

    # Brief
    if args.command == "brief":
        briefing = CareEngine.generate_physician_briefing(recipient)
        if args.json:
            print(
                json.dumps(
                    {
                        "patient_name": briefing.patient_name,
                        "age": briefing.age,
                        "diagnoses": briefing.primary_diagnoses,
                        "allergies": briefing.allergies,
                        "code_status": briefing.code_status,
                        "active_medications": briefing.active_medications,
                        "recent_vitals_summary": briefing.recent_vitals_summary,
                        "flagged_anomalies": [a.__dict__ for a in briefing.flagged_anomalies],
                        "recent_caregiver_observations": briefing.recent_caregiver_observations,
                        "recommended_discussion_points": briefing.recommended_discussion_points,
                    },
                    indent=2,
                )
            )
            return 0

        print("\n" + "=" * 75)
        print("               CLINICAL APPOINTMENT BRIEFING SHEET               ")
        print("=" * 75)
        print(f"  PATIENT          : {briefing.patient_name} (Age {briefing.age} | {briefing.relationship})")
        print(f"  PRIMARY DIAGNOSES: {', '.join(briefing.primary_diagnoses) if briefing.primary_diagnoses else 'None'}")
        print(f"  ALLERGIES        : {', '.join(briefing.allergies) if briefing.allergies else 'None'}")
        print(f"  CODE STATUS      : {briefing.code_status}")
        print("─" * 75)
        print("  RECENT HOME VITALS (Past 7 Days):")
        for k, v in briefing.recent_vitals_summary.items():
            print(f"    • {k.replace('_', ' ').capitalize():<22} : {v}")
        print("─" * 75)
        print(f"  ACTIVE MEDICATIONS ({len(briefing.active_medications)} items):")
        for m in briefing.active_medications:
            print(f"    • {m['name']:<22} {m['dosage']:<8} [{m['timing']:<7}] - {m['purpose']}")
        if briefing.flagged_anomalies:
            print("─" * 75)
            print("  ⚠️ RECENT VITALS ANOMALIES:")
            for a in briefing.flagged_anomalies:
                print(f"    • [{a.severity}] {a.vital_metric}: {a.observed_value} ({a.clinical_rationale})")
        print("─" * 75)
        print("  PRIORITIZED DISCUSSION POINTS FOR DOCTOR:")
        for q in briefing.recommended_discussion_points:
            print(f"    [ ] {q}")
        print("=" * 75 + "\n")
        return 0

    # Ask
    if args.command == "ask":
        companion = CareCompanion()
        resp = companion.consult(args.query, recipient)

        if args.json:
            print(json.dumps(resp.to_dict(), indent=2))
            return 0

        print("\n" + "━" * 75)
        print(f"🤖 AI CAREGIVER MEDICAL ADVOCATE: '{args.query}'")
        print("━" * 75)
        print(f"\n🎯 ADVOCATE SUMMARY:\n{resp.advocate_summary}\n")
        if resp.doctor_visit_takeaways:
            print("🩺 DOCTOR VISIT & MEDICATION TAKEAWAYS:")
            for t in resp.doctor_visit_takeaways:
                print(f"  • {t}")
            print()
        if resp.vitals_red_flags:
            print("🚨 VITALS & CLINICAL RED FLAGS:")
            for rf in resp.vitals_red_flags:
                print(f"  • {rf}")
            print()
        if resp.questions_for_specialist:
            print("📋 QUESTIONS FOR THE DOCTOR / SPECIALIST:")
            for q in resp.questions_for_specialist:
                print(f"  • {q}")
            print()
        if resp.caregiver_action_plan:
            print("⚡ CAREGIVER ACTION PLAN:")
            for p in resp.caregiver_action_plan:
                print(f"  • {p}")
            print()
        print("━" * 75 + "\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
