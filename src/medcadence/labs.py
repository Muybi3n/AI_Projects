# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Longitudinal biomarker tracking and laboratory trend engine.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .models import BiomarkerRecord, BiomarkerStatus, HealthProfile

STANDARD_REFERENCE_RANGES: dict[str, dict[str, Any]] = {
    "total_cholesterol": {"low": 125.0, "high": 200.0, "unit": "mg/dL", "cat": "lipid_panel"},
    "ldl_cholesterol": {"low": 0.0, "high": 100.0, "unit": "mg/dL", "cat": "lipid_panel"},
    "hdl_cholesterol": {"low": 40.0, "high": 90.0, "unit": "mg/dL", "cat": "lipid_panel"},
    "triglycerides": {"low": 0.0, "high": 150.0, "unit": "mg/dL", "cat": "lipid_panel"},
    "fasting_glucose": {"low": 70.0, "high": 99.0, "unit": "mg/dL", "cat": "metabolic_glycemic"},
    "hba1c": {"low": 4.0, "high": 5.6, "unit": "%", "cat": "metabolic_glycemic"},
    "hs_crp": {"low": 0.0, "high": 1.0, "unit": "mg/L", "cat": "inflammatory_cardio"},
    "vitamin_d_25_oh": {"low": 30.0, "high": 80.0, "unit": "ng/mL", "cat": "vitamins_minerals"},
    "tsh": {"low": 0.45, "high": 4.5, "unit": "uIU/mL", "cat": "hormonal_endocrine"},
    "egfr": {"low": 60.0, "high": 120.0, "unit": "mL/min/1.73m2", "cat": "kidney_liver_renal"},
}


@dataclass
class BiomarkerTrend:
    name: str
    latest_value: float
    latest_status: BiomarkerStatus
    unit: str
    historical_count: int
    delta_vs_previous: float
    delta_pct: float
    trend_direction: str  # "improving", "worsening", "stable", "initial"


class BiomarkerLabEngine:
    """Computes lab biomarker trajectories and flags out-of-range deviations."""

    @staticmethod
    def analyze_trends(profile: HealthProfile) -> list[BiomarkerTrend]:
        grouped: dict[str, list[BiomarkerRecord]] = defaultdict(list)
        for b in profile.biomarkers:
            key = b.name.strip().lower()
            grouped[key].append(b)

        trends: list[BiomarkerTrend] = []
        for _name, records in grouped.items():
            records.sort(key=lambda r: r.date)
            latest = records[-1]
            hist_count = len(records)

            if hist_count > 1:
                prev = records[-2]
                delta = latest.value - prev.value
                delta_pct = (delta / prev.value * 100.0) if prev.value != 0 else 0.0

                # Direction heuristic
                if abs(delta_pct) < 3.0:
                    direction = "stable"
                elif latest.status in [BiomarkerStatus.OPTIMAL, BiomarkerStatus.NORMAL]:
                    direction = "improving"
                else:
                    direction = "worsening"
            else:
                delta = 0.0
                delta_pct = 0.0
                direction = "initial"

            trends.append(
                BiomarkerTrend(
                    name=latest.name,
                    latest_value=latest.value,
                    latest_status=latest.status,
                    unit=latest.unit,
                    historical_count=hist_count,
                    delta_vs_previous=round(delta, 2),
                    delta_pct=round(delta_pct, 1),
                    trend_direction=direction,
                )
            )

        trends.sort(key=lambda t: t.name.lower())
        return trends
