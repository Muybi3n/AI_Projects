# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for lexicast data models and serialization.
"""

from lexicast_engine.models import DistillationArtifact, Episode, SearchHit


def test_distillation_artifact_serialization():
    art = DistillationArtifact(
        thesis="Compounding knowledge produces exponential leverage.",
        quotes=["First principles thinking cuts through dogma."],
        mental_models=["First Principles", "Inversion"],
        moral_philosophy="Discipline equals freedom.",
        micro_habits=["Write 250 words every morning."],
        tags=["mindset", "productivity"],
    )

    d = art.to_dict()
    assert d["thesis"] == "Compounding knowledge produces exponential leverage."
    assert len(d["quotes"]) == 1

    restored = DistillationArtifact.from_dict(d)
    assert restored.thesis == art.thesis
    assert restored.mental_models == art.mental_models


def test_episode_serialization():
    ep = Episode(
        id="ep123",
        title="Deep Work and Flow",
        speaker="Cal Newport",
        source_uri="/audio/ep1.mp3",
        raw_transcript="Focus without distraction is the superpower of the modern era.",
    )
    d = ep.to_dict()
    assert d["id"] == "ep123"
    assert d["speaker"] == "Cal Newport"


def test_search_hit_model():
    hit = SearchHit(
        episode_id="ep1",
        title="Title",
        speaker="Speaker",
        matched_snippet="matched word",
        rank=-1.5,
    )
    assert hit.episode_id == "ep1"
    assert hit.rank == -1.5
