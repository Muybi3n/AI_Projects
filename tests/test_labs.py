# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for lab biomarker trend tracking.
"""

from medcadence.labs import BiomarkerLabEngine
from medcadence.models import BiomarkerRecord, HealthProfile


def test_biomarker_trends_multi_test():
    b1 = BiomarkerRecord(name="Fasting Glucose", value=98.0, date="2025-01-01")
    b2 = BiomarkerRecord(name="Fasting Glucose", value=88.0, date="2025-06-01")

    profile = HealthProfile(biomarkers=[b1, b2])
    trends = BiomarkerLabEngine.analyze_trends(profile)

    assert len(trends) == 1
    t = trends[0]
    assert t.name == "Fasting Glucose"
    assert t.latest_value == 88.0
    assert t.historical_count == 2
    assert t.delta_vs_previous == -10.0
    assert t.trend_direction == "improving"
