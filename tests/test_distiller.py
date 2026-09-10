# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for 5-layer insight distillation engine.
"""

from lexicast_engine.distiller import InsightDistiller
from lexicast_engine.models import Episode


def test_heuristic_distillation_layers():
    text = (
        "Building great systems requires thinking in feedback loops and first principles. "
        "The truth is, consistency beats intensity every single day. "
        "\"You do not rise to the level of your goals, you fall to the level of your systems.\" "
        "The meaning and wisdom of life comes from who you become in the pursuit of mastery. "
        "Start tracking your habits every morning in a journal. Focus on eliminating distractions."
    )
    ep = Episode(
        id="ep_test",
        title="Atomic Habits & Systems Thinking",
        speaker="James Clear",
        raw_transcript=text,
    )

    distiller = InsightDistiller()
    artifact = distiller.distill(ep)

    assert len(artifact.thesis) > 10
    assert len(artifact.quotes) >= 1
    assert "Feedback Loop" in artifact.mental_models or "First Principles" in artifact.mental_models
    assert len(artifact.moral_philosophy) > 10
    assert len(artifact.micro_habits) >= 1


def test_distillation_empty_transcript():
    ep = Episode(id="empty", title="Empty", raw_transcript="")
    distiller = InsightDistiller()
    artifact = distiller.distill(ep)
    assert artifact.thesis == "Empty transcript provided."


def test_custom_extractor_hook():
    ep = Episode(id="custom", title="Custom", raw_transcript="Sample transcript text")
    distiller = InsightDistiller()

    def mock_llm_extractor(text: str):
        return {
            "thesis": "Custom LLM Thesis",
            "quotes": ["Custom quote"],
            "mental_models": ["Custom Model"],
            "moral_philosophy": "Custom Moral",
            "micro_habits": ["Custom Habit"],
            "tags": ["ai", "custom"],
        }

    artifact = distiller.distill(ep, custom_extractor=mock_llm_extractor)
    assert artifact.thesis == "Custom LLM Thesis"
    assert artifact.tags == ["ai", "custom"]
