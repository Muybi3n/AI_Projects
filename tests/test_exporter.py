# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for Markdown, JSON, and executive brief exporters.
"""

from pathlib import Path

from lexicast_engine.exporter import export_markdown, format_executive_brief
from lexicast_engine.models import DistillationArtifact, Episode


def test_export_markdown(tmp_path: Path):
    dist = DistillationArtifact(
        thesis="Knowledge is power.",
        quotes=["To know what you know and what you do not know, that is true knowledge."],
        mental_models=["First Principles"],
        moral_philosophy="Humility precedes wisdom.",
        micro_habits=["Reflect nightly."],
        tags=["wisdom"],
    )
    ep = Episode(
        id="ep_exp",
        title="Wisdom and Mastery",
        speaker="Socrates",
        distillation=dist,
    )

    out_file = tmp_path / "note.md"
    md = export_markdown(ep, output_path=out_file)

    assert "Wisdom and Mastery" in md
    assert "Socrates" in md
    assert "Executive Thesis" in md
    assert out_file.exists()


def test_format_executive_brief():
    dist = DistillationArtifact(
        thesis="High performance requires deep recovery.",
        quotes=["Rest is not the absence of work, it is the foundation of it."],
        mental_models=["Cyclical Recovery"],
        moral_philosophy="Sustainability over burnout.",
        micro_habits=["Sleep 8 hours."],
    )
    ep = Episode(
        id="ep_brief",
        title="Rest and Recovery",
        speaker="Matthew Walker",
        distillation=dist,
    )

    brief = format_executive_brief(ep)
    assert "REST AND RECOVERY" in brief
    assert "CORE THESIS:" in brief
    assert "Matthew Walker" in brief
