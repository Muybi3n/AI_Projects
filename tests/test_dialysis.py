# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for dialysis IDWG and renal safety rules.
"""

from oncorenal.dialysis import DialysisEngine
from oncorenal.models import DialysisSession, FluidIntakeLog, OncoRenalProfile, SpecialtyLabRecord


def test_idwg_calculation():
    session = DialysisSession(pre_dialysis_weight_kg=71.5, post_dialysis_weight_kg=68.0)
    profile = OncoRenalProfile(target_dry_weight_kg=68.0, dialysis_sessions=[session])

    idwg = DialysisEngine.calculate_idwg(profile)
    assert idwg is not None
    assert idwg.interdialytic_weight_gain_kg == 3.5
    assert idwg.weight_gain_pct_of_dry_weight > 5.0
    assert "CRITICAL_OVERLOAD" in idwg.fluid_overload_tier


def test_hyperkalemia_and_binder_alerts():
    fluid = FluidIntakeLog(phosphate_binders_taken_with_meals=False)
    lab = SpecialtyLabRecord(serum_potassium=5.8)  # High K+

    profile = OncoRenalProfile(fluid_logs=[fluid], specialty_labs=[lab])
    alerts = DialysisEngine.audit_renal_safety(profile)

    severities = [a.severity for a in alerts]
    assert "CRITICAL_RENAL" in severities
    categories = [a.category for a in alerts]
    assert "Hyperkalemia Alert (High Potassium)" in categories
    assert "Phosphate Binder Missed Timing" in categories
