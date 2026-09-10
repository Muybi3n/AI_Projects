# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for oncology chemo nadir and toxicity auditing.
"""

from datetime import datetime, timezone

from oncorenal.models import ChemoCycle, OncoRenalProfile, SymptomToxicityLog
from oncorenal.oncology import OncologyEngine


def test_nadir_calculation():
    today_str = datetime.now(timezone.utc).date().isoformat()
    cycle = ChemoCycle(
        regimen_name="AC-T", cycle_number=1, infusion_date=today_str, nadir_start_day=7, nadir_end_day=14
    )

    profile = OncoRenalProfile(chemo_cycles=[cycle])
    nadir = OncologyEngine.get_current_nadir_status(profile)

    assert nadir is not None
    assert nadir.cycle_number == 1
    assert nadir.current_cycle_day == 1
    assert not nadir.is_in_nadir_window  # Day 1 is not in nadir window


def test_neutropenic_fever_emergency_alert():
    tox = SymptomToxicityLog(temperature_f=101.2, nausea_ctcae_grade=2)
    profile = OncoRenalProfile(toxicity_logs=[tox])

    alerts = OncologyEngine.audit_oncology_toxicities(profile)
    assert len(alerts) >= 1
    assert alerts[0].severity == "EMERGENCY_ONCOLOGY"
    assert "Neutropenic Fever Alert" in alerts[0].category
