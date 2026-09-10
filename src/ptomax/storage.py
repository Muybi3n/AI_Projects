# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Local JSON persistence store for PTO profile, custom holidays, and coverage handovers.
"""

import json
from pathlib import Path
from typing import Any

from .models import Holiday, PtoBreak, PtoProfile, WorkCoverage


class PtoStore:
    """Manages local JSON storage in ~/.ptomax/."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            self.base_dir = Path.home() / ".ptomax"
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.base_dir / "profile.json"

    def load_profile(self) -> PtoProfile:
        if not self.profile_file.is_file():
            return self._create_default_profile()

        try:
            with open(self.profile_file, encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (json.JSONDecodeError, OSError):
            return self._create_default_profile()

    def save_profile(self, profile: PtoProfile) -> None:
        temp_file = self.profile_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        temp_file.replace(self.profile_file)

    def _create_default_profile(self) -> PtoProfile:
        coverages = [
            WorkCoverage(
                id="cov-01",
                project_or_domain="Headless Mac Mini SOC & Wazuh SIEM",
                primary_cover_name="Sarah Jenkins",
                primary_cover_contact="sarah.jenkins@company.internal",
                backup_cover_name="Alex Rivera",
                backup_cover_contact="alex.rivera@company.internal",
                escalation_threshold="P0 Production Security Incidents only",
                notes="Runbooks located at internal wiki /soc-runbooks. Dashboard on Grafana port 3000.",
            ),
            WorkCoverage(
                id="cov-02",
                project_or_domain="Incident Response & Threat Intel Triage",
                primary_cover_name="Marcus Vance",
                primary_cover_contact="marcus.vance@company.internal",
                escalation_threshold="Critical malware detections or ransomware alerts",
                notes="VT API pipelines scheduled via cron; logs stream to Wazuh manager.",
            ),
        ]
        profile = PtoProfile(
            total_annual_allowance_days=20.0,
            current_balance_days=15.0,
            accrual_hours_per_pay_period=6.15,
            pay_periods_per_year=26,
            max_rollover_cap_days=5.0,
            coverage_handovers=coverages,
        )
        self.save_profile(profile)
        return profile

    def _deserialize(self, data: dict[str, Any]) -> PtoProfile:
        breaks = [
            PtoBreak(
                break_name=b.get("break_name", ""),
                start_date=b.get("start_date", ""),
                end_date=b.get("end_date", ""),
                pto_days_required=int(b.get("pto_days_required", 0)),
                total_consecutive_days_off=int(b.get("total_consecutive_days_off", 0)),
                holidays_bridged=list(b.get("holidays_bridged", [])),
                description=b.get("description", ""),
            )
            for b in data.get("planned_breaks", [])
        ]
        covs = [
            WorkCoverage(
                id=c.get("id", ""),
                project_or_domain=c.get("project_or_domain", ""),
                primary_cover_name=c.get("primary_cover_name", ""),
                primary_cover_contact=c.get("primary_cover_contact", ""),
                backup_cover_name=c.get("backup_cover_name", ""),
                backup_cover_contact=c.get("backup_cover_contact", ""),
                escalation_threshold=c.get("escalation_threshold", ""),
                handover_checklist_done=bool(c.get("handover_checklist_done", False)),
                notes=c.get("notes", ""),
            )
            for c in data.get("coverage_handovers", [])
        ]
        holidays = [
            Holiday(
                name=h.get("name", ""),
                date_str=h.get("date_str", ""),
                country=h.get("country", "US"),
            )
            for h in data.get("custom_holidays", [])
        ]
        return PtoProfile(
            total_annual_allowance_days=float(data.get("total_annual_allowance_days", 15.0)),
            current_balance_days=float(data.get("current_balance_days", 12.0)),
            accrual_hours_per_pay_period=float(data.get("accrual_hours_per_pay_period", 4.62)),
            pay_periods_per_year=int(data.get("pay_periods_per_year", 26)),
            max_rollover_cap_days=float(data.get("max_rollover_cap_days", 5.0)),
            planned_breaks=breaks,
            coverage_handovers=covs,
            custom_holidays=holidays,
        )
