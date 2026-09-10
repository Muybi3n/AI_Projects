# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for coverage matrix and OOO email generator.
"""

from ptomax.coverage import CoverageMatrix
from ptomax.emails import OooEmailGenerator
from ptomax.models import WorkCoverage


def test_coverage_matrix():
    cov_matrix = CoverageMatrix()
    c = cov_matrix.add_coverage(
        project_or_domain="Wazuh SIEM",
        primary_name="Sarah",
        primary_contact="sarah@corp.local",
    )
    assert c.id == "cov-01"
    assert cov_matrix.mark_handover_ready("cov-01", True) is True

    brief = cov_matrix.generate_handover_brief()
    assert "Wazuh SIEM" in brief
    assert "Sarah" in brief


def test_ooo_email_generator():
    cov = WorkCoverage(
        id="c1",
        project_or_domain="API Gateways",
        primary_cover_name="David",
        primary_cover_contact="david@corp.local",
    )
    res = OooEmailGenerator.generate_ooo_email(
        start_date="2026-07-01",
        end_date="2026-07-10",
        style="external",
        coverages=[cov],
    )
    assert "2026-07-01" in res["body"]
    assert "David" in res["body"]
    assert "API Gateways" in res["body"]
