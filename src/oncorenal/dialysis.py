# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Renal & dialysis engine: Interdialytic weight gain (IDWG), dry weight tracking, and fluid budget management.
"""

from dataclasses import dataclass

from .models import OncoRenalProfile


@dataclass
class IDWGAnalysis:
    target_dry_weight_kg: float
    latest_pre_weight_kg: float
    interdialytic_weight_gain_kg: float
    interdialytic_weight_gain_lbs: float
    weight_gain_pct_of_dry_weight: float
    fluid_overload_tier: str  # "SAFE", "MODERATE_RISK", "CRITICAL_OVERLOAD"
    clinical_risk_note: str


@dataclass
class RenalAlert:
    severity: str  # "CRITICAL_RENAL", "WARNING", "EVALUATE"
    category: str
    message: str
    action_required: str


class DialysisEngine:
    """Computes interdialytic weight gain, fluid compliance, and dialysis safety metrics."""

    @staticmethod
    def calculate_idwg(profile: OncoRenalProfile) -> IDWGAnalysis | None:
        if not profile.dialysis_sessions:
            return None

        sorted_sessions = sorted(profile.dialysis_sessions, key=lambda s: s.date)
        latest = sorted_sessions[-1]
        dry_wt = profile.target_dry_weight_kg

        if dry_wt <= 0 or latest.pre_dialysis_weight_kg <= 0:
            return None

        gain_kg = latest.pre_dialysis_weight_kg - dry_wt
        gain_lbs = gain_kg * 2.20462
        gain_pct = (gain_kg / dry_wt) * 100.0

        # Clinical Benchmarks for IDWG:
        # < 3.0% dry weight = Safe (Optimal fluid control)
        # 3.0% - 5.0% = Moderate Overload (Elevated BP, mild shortness of breath)
        # > 5.0% = Severe Fluid Overload (Pulmonary edema risk, severe intra-dialytic cramping)
        if gain_pct <= 3.0:
            tier = "SAFE (Optimal Fluid Management)"
            note = f"Fluid accumulation is within safe interdialytic limits (+{gain_lbs:.1f} lbs / {gain_pct:.1f}%)."
        elif gain_pct <= 5.0:
            tier = "MODERATE_RISK (Elevated Fluid Retention)"
            note = f"Moderate fluid gain (+{gain_lbs:.1f} lbs / {gain_pct:.1f}%). Requires strict adherence to daily fluid restriction."
        else:
            tier = "CRITICAL_OVERLOAD (High Risk of Pulmonary Edema & Cramping)"
            note = f"Severe fluid accumulation (+{gain_lbs:.1f} lbs / {gain_pct:.1f}%). Alert dialysis team for adjusted ultrafiltration rate."

        return IDWGAnalysis(
            target_dry_weight_kg=dry_wt,
            latest_pre_weight_kg=latest.pre_dialysis_weight_kg,
            interdialytic_weight_gain_kg=round(gain_kg, 2),
            interdialytic_weight_gain_lbs=round(gain_lbs, 1),
            weight_gain_pct_of_dry_weight=round(gain_pct, 1),
            fluid_overload_tier=tier,
            clinical_risk_note=note,
        )

    @staticmethod
    def audit_renal_safety(profile: OncoRenalProfile) -> list[RenalAlert]:
        alerts: list[RenalAlert] = []

        # 1. IDWG Overload Check
        idwg = DialysisEngine.calculate_idwg(profile)
        if idwg and idwg.weight_gain_pct_of_dry_weight > 5.0:
            alerts.append(
                RenalAlert(
                    severity="CRITICAL_RENAL",
                    category="Interdialytic Fluid Overload",
                    message=f"Pre-dialysis weight is {idwg.interdialytic_weight_gain_lbs} lbs (+{idwg.weight_gain_pct_of_dry_weight}%) above dry weight.",
                    action_required="Restrict immediate fluid intake to sips. If experiencing acute shortness of breath while lying flat (orthopnea), seek emergency care.",
                )
            )

        # 2. Access Site Health (AV Fistula / Graft check)
        for s in profile.dialysis_sessions:
            if not s.access_site_bruit_thrill_normal:
                alerts.append(
                    RenalAlert(
                        severity="CRITICAL_RENAL",
                        category="Vascular Access Thrombosis Alert",
                        message=f"Absence of normal bruit/thrill on dialysis access site logged on {s.date}.",
                        action_required="IMMEDIATE VASCULAR SURGEON / DIALYSIS CLINIC CONTACT. Clotted fistula requires urgent declotting to prevent permanent access failure.",
                    )
                )

        # 3. Phosphate Binder Timing Compliance
        for f in profile.fluid_logs:
            if not f.phosphate_binders_taken_with_meals:
                alerts.append(
                    RenalAlert(
                        severity="WARNING",
                        category="Phosphate Binder Missed Timing",
                        message=f"Phosphate binders were not synchronized with meals on {f.date}.",
                        action_required="Phosphate binders (Renvela, PhosLo) must be taken with the first bite of meals to bind dietary phosphorus in the gut.",
                    )
                )

        # 4. Serum Potassium Check (from labs)
        for lab in profile.specialty_labs:
            if lab.serum_potassium >= 5.5:
                alerts.append(
                    RenalAlert(
                        severity="CRITICAL_RENAL",
                        category="Hyperkalemia Alert (High Potassium)",
                        message=f"Serum Potassium of {lab.serum_potassium} mEq/L logged on {lab.date} (threshold >= 5.5).",
                        action_required="Risk of cardiac arrhythmias. Avoid all high-potassium foods (bananas, potatoes, tomatoes) and contact nephrologist.",
                    )
                )

        return alerts
