# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Oncology chemotherapy cycle manager, nadir tracking, and CTCAE toxicity grading engine.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .models import OncoRenalProfile


@dataclass
class NadirStatus:
    cycle_number: int
    regimen_name: str
    current_cycle_day: int
    cycle_length_days: int
    is_in_nadir_window: bool
    nadir_start_date: str
    nadir_end_date: str
    next_infusion_date: str
    precaution_advisory: str


@dataclass
class OncologyAlert:
    severity: str  # "EMERGENCY_ONCOLOGY", "WARNING", "EVALUATE"
    category: str
    message: str
    action_required: str


class OncologyEngine:
    """Computes chemo cycle schedules, immune nadir windows, and toxicity alerts."""

    @staticmethod
    def get_current_nadir_status(profile: OncoRenalProfile) -> NadirStatus | None:
        if not profile.chemo_cycles:
            return None

        # Get latest cycle
        sorted_cycles = sorted(profile.chemo_cycles, key=lambda c: c.infusion_date)
        latest = sorted_cycles[-1]

        try:
            infusion_dt = date.fromisoformat(latest.infusion_date)
        except ValueError:
            infusion_dt = datetime.now(timezone.utc).date()

        today = datetime.now(timezone.utc).date()
        days_since_infusion = (today - infusion_dt).days + 1

        nadir_start = infusion_dt + timedelta(days=latest.nadir_start_day - 1)
        nadir_end = infusion_dt + timedelta(days=latest.nadir_end_day - 1)
        next_infusion = infusion_dt + timedelta(days=latest.cycle_length_days)

        in_nadir = latest.nadir_start_day <= days_since_infusion <= latest.nadir_end_day

        if in_nadir:
            advisory = (
                f"IMMUNE NADIR ALERT (Day {days_since_infusion} of {latest.cycle_length_days}): "
                "White blood cells and neutrophils are at expected cycle low. "
                "Avoid sick contacts and crowded indoor environments. "
                "ANY FEVER >= 100.4°F REQUIRES IMMEDIATE EMERGENCY ONCOLOGY EVALUATION."
            )
        elif days_since_infusion < latest.nadir_start_day:
            advisory = (
                f"Post-Infusion Recovery (Day {days_since_infusion}): Focus on antiemetic hydration and rest. "
                f"Immune nadir window begins on {nadir_start.isoformat()} (Day {latest.nadir_start_day})."
            )
        else:
            advisory = (
                f"Pre-Next Cycle Recovery (Day {days_since_infusion}): Marrow recovering. "
                f"Next planned infusion on {next_infusion.isoformat()}."
            )

        return NadirStatus(
            cycle_number=latest.cycle_number,
            regimen_name=latest.regimen_name,
            current_cycle_day=days_since_infusion,
            cycle_length_days=latest.cycle_length_days,
            is_in_nadir_window=in_nadir,
            nadir_start_date=nadir_start.isoformat(),
            nadir_end_date=nadir_end.isoformat(),
            next_infusion_date=next_infusion.isoformat(),
            precaution_advisory=advisory,
        )

    @staticmethod
    def audit_oncology_toxicities(profile: OncoRenalProfile) -> list[OncologyAlert]:
        alerts: list[OncologyAlert] = []
        nadir = OncologyEngine.get_current_nadir_status(profile)

        for tox in profile.toxicity_logs:
            # Neutropenic Fever Critical Check
            if tox.temperature_f >= 100.4:
                in_nadir_text = " (DURING IMMUNE NADIR WINDOW)" if (nadir and nadir.is_in_nadir_window) else ""
                alerts.append(
                    OncologyAlert(
                        severity="EMERGENCY_ONCOLOGY",
                        category="Neutropenic Fever Alert",
                        message=f"Recorded temperature of {tox.temperature_f}°F on {tox.date}{in_nadir_text}.",
                        action_required="CALL 24/7 ONCOLOGY TRIAGE NURSE OR GO TO NEAREST EMERGENCY ROOM IMMEDIATELY. Do not take antipyretics before consulting oncology.",
                    )
                )

            # High grade neuropathy
            if tox.neuropathy_ctcae_grade >= 2:
                alerts.append(
                    OncologyAlert(
                        severity="WARNING",
                        category="Chemotherapy-Induced Peripheral Neuropathy (CIPN)",
                        message=f"Grade {tox.neuropathy_ctcae_grade} neuropathy logged on {tox.date} (sensory impairment/tingling affecting motor tasks).",
                        action_required="Notify oncologist prior to next infusion for potential neurotoxic drug dose reduction (Oxaliplatin/Paclitaxel).",
                    )
                )

            # Severe Nausea / Mucositis
            if tox.nausea_ctcae_grade >= 3 or tox.mucositis_mouth_sores_grade >= 3:
                alerts.append(
                    OncologyAlert(
                        severity="WARNING",
                        category="Severe GI / Mucositis Toxicity",
                        message=f"Grade {max(tox.nausea_ctcae_grade, tox.mucositis_mouth_sores_grade)} GI/Mouth toxicity on {tox.date} (inability to maintain oral intake).",
                        action_required="Contact oncology clinic for breakthrough antiemetic prescription adjustment and IV hydration orders.",
                    )
                )

        return alerts
