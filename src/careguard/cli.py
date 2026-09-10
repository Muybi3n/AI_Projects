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
from .deid import ClinicalRedactor
from .engine import CareEngine
from .extractor import NoteExtractor
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
from .timeline import ClinicalTimelineEngine


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

    # Timeline
    tl_p = subparsers.add_parser("timeline", help="Display longitudinal clinical progression timeline.")
    tl_p.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Explain Doctor Note (Privacy-preserving jargon decoder)
    exp_p = subparsers.add_parser(
        "explain", help="Safely de-identify and explain a complex doctor note in plain English."
    )
    exp_p.add_argument("note", help="Raw clinical note text or path to .txt note file.")
    exp_p.add_argument("--no-mask-labs", action="store_true", help="Disable masking of sensitive lab numbers.")
    exp_p.add_argument("--json", action="store_true", help="Output raw JSON.")

    # Redact Preview
    red_p = subparsers.add_parser("redact", help="Preview HIPAA de-identification and sensitive finding redaction.")
    red_p.add_argument("note", help="Raw clinical note text or path to .txt note file.")

    # Import Note
    imp_p = subparsers.add_parser(
        "import-note", help="Import doctor note, extract clinical points, and save to patient record."
    )
    imp_p.add_argument("file", type=Path, help="Text file containing physician visit note.")
    imp_p.add_argument("--doctor", default="Specialist", help="Physician name")
    imp_p.add_argument(
        "--specialty", default="Specialty Care", help="Specialty (Cardiology, Neurology, Oncology, etc.)"
    )
    imp_p.add_argument("--date", default=None, help="Encounter date (YYYY-MM-DD)")

    # Ask
    ask_p = subparsers.add_parser("ask", help="Consult the AI Caregiver Medical Companion.")
    ask_p.add_argument("query", help="Question about care regimen, doctor visit summaries, or vitals.")
    ask_p.add_argument("--json", action="store_true", help="Output raw JSON analysis.")

    args = parser.parse_args(argv)
    store = CareStore(args.data_dir)
    recipient = store.load_recipient()

    # Helper to resolve text vs file
    def resolve_text_input(input_val: str) -> str:
        p = Path(input_val)
        if p.exists() and p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
        return input_val

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

    # Timeline
    if args.command == "timeline":
        report = ClinicalTimelineEngine.build_timeline(recipient)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
            return 0

        print("\n" + "=" * 75)
        print(f"        LONGITUDINAL CLINICAL ENCOUNTER TIMELINE ({report.patient_name})        ")
        print("=" * 75)
        print(f"  Total Encounters Logged : {report.total_encounters}")
        print(f"  Chronological Span      : {report.first_recorded_encounter} to {report.latest_recorded_encounter}")
        print("─" * 75)
        for e in report.encounters:
            print(f"\n📅 [{e.date}] {e.physician} ({e.specialty}) - Reason: {e.chief_complaint}")
            print(f"   Findings     : {e.clinical_summary}")
            if e.medications_altered:
                print(f"   Med Changes  : {', '.join(e.medications_altered)}")
            if e.tests_requested:
                print(f"   Tests/Orders : {', '.join(e.tests_requested)}")
        print("\n" + "=" * 75 + "\n")
        return 0

    # Explain Doctor Note
    if args.command == "explain":
        raw_text = resolve_text_input(args.note)
        companion = CareCompanion()
        resp = companion.explain_note(
            raw_text,
            patient_name=recipient.full_name,
            redact_sensitive_findings=not args.no_mask_labs,
        )

        if args.json:
            print(json.dumps(resp.to_dict(), indent=2))
            return 0

        print("\n" + "━" * 75)
        print("📖 PLAIN-ENGLISH DOCTOR NOTE TRANSLATION (PRIVACY-PROTECTED)")
        print("━" * 75)
        print(f"\n🎯 SUMMARY & TRANSLATION:\n{resp.plain_english_translation}\n")
        if resp.decoded_acronyms:
            print("🔤 DECODED MEDICAL ACRONYMS & JARGON:")
            for d in resp.decoded_acronyms:
                print(f"  • {d['acronym']:<8} -> {d['meaning']}")
            print()
        if resp.key_findings_summary:
            print("📋 KEY CLINICAL FINDINGS:")
            for k in resp.key_findings_summary:
                print(f"  • {k}")
            print()
        if resp.next_steps_and_orders:
            print("⚡ NEXT STEPS & DOCTOR'S ORDERS:")
            for n in resp.next_steps_and_orders:
                print(f"  • {n}")
            print()
        print(
            f"🛡️ PRIVACY SHIELD APPLIED: {resp.redaction_protection_applied.get('phi_redacted_count', 0)} PHI items masked | {resp.redaction_protection_applied.get('sensitive_findings_redacted_count', 0)} sensitive lab/cancer findings protected."
        )
        print("━" * 75 + "\n")
        return 0

    # Redact Preview
    if args.command == "redact":
        raw_text = resolve_text_input(args.note)
        res = ClinicalRedactor.deidentify(raw_text, patient_name_hint=recipient.full_name)
        print("\n" + "=" * 75)
        print("            HIPAA DE-IDENTIFICATION & SENSITIVE FINDING PREVIEW          ")
        print("=" * 75)
        print(f"\n🔒 SANITIZED TEXT (Safe for LLM):\n{res.sanitized_text}\n")
        print("─" * 75)
        print(f"🛡️ REDACTED PHI IDENTIFIERS ({len(res.redacted_phi_items)}):")
        for phi in res.redacted_phi_items:
            print(f"  • {phi}")
        print(f"\n🧪 REDACTED SENSITIVE FINDINGS ({len(res.redacted_sensitive_findings)}):")
        for fnd in res.redacted_sensitive_findings:
            print(f"  • {fnd}")
        print("=" * 75 + "\n")
        return 0

    # Import Note
    if args.command == "import-note":
        if not args.file.exists():
            print(f"Error: Note file '{args.file}' not found.", file=sys.stderr)
            return 1

        content = args.file.read_text(encoding="utf-8", errors="replace")
        extracted = NoteExtractor.extract_from_note(
            content, encounter_date=args.date or DoctorVisit().date, patient_name_hint=recipient.full_name
        )

        visit = DoctorVisit(
            date=extracted.encounter_date,
            physician_name=args.doctor,
            specialty=args.specialty,
            reason_for_visit=extracted.chief_complaint,
            physician_findings="; ".join(extracted.diagnoses_and_assessments)
            if extracted.diagnoses_and_assessments
            else "Clinical Encounter",
            medication_changes=", ".join(extracted.medication_changes),
            orders_and_tests=", ".join(extracted.follow_up_orders_and_labs),
        )
        recipient.doctor_visits.append(visit)
        store.save_recipient(recipient)
        print(f"[✓] Successfully Imported Note: [{visit.date}] {visit.physician_name} ({visit.specialty})")
        print(f"    Chief Complaint : {visit.reason_for_visit}")
        print(f"    Findings Extracted: {visit.physician_findings[:60]}...")
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
