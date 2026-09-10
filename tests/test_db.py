# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for SQLite FTS5 database indexing, retrieval, and search.
"""

from pathlib import Path

from lexicast_engine.db import Database
from lexicast_engine.models import DistillationArtifact, Episode


def test_db_save_and_get(tmp_path: Path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)

    dist = DistillationArtifact(
        thesis="Mastery requires deliberate practice.",
        quotes=["Talent is the floor, work is the ceiling."],
    )
    ep = Episode(
        id="ep001",
        title="The Art of Learning",
        speaker="Josh Waitzkin",
        raw_transcript="We must learn to embrace the plateau and love the process.",
        distillation=dist,
    )

    db.save_episode(ep)
    fetched = db.get_episode("ep001")

    assert fetched is not None
    assert fetched.id == "ep001"
    assert fetched.title == "The Art of Learning"
    assert fetched.distillation is not None
    assert fetched.distillation.thesis == dist.thesis


def test_db_fts5_search(tmp_path: Path):
    db_path = tmp_path / "search.db"
    db = Database(db_path)

    ep1 = Episode(
        id="ep1",
        title="Psychology of Money",
        speaker="Morgan Housel",
        raw_transcript="Doing well with money has a little to do with how smart you are and a lot to do with behavior.",
    )
    ep2 = Episode(
        id="ep2",
        title="Principles of Quantum Physics",
        speaker="Richard Feynman",
        raw_transcript="Nature isn't classical, dammit, and if you want to make a simulation of nature, you'd better make it quantum mechanical.",
    )

    db.save_episode(ep1)
    db.save_episode(ep2)

    hits_money = db.search("behavior")
    assert len(hits_money) == 1
    assert hits_money[0].episode_id == "ep1"

    hits_physics = db.search("quantum")
    assert len(hits_physics) == 1
    assert hits_physics[0].episode_id == "ep2"

    hits_empty = db.search("nonexistent_term_xyz")
    assert len(hits_empty) == 0


def test_db_list_episodes(tmp_path: Path):
    db_path = tmp_path / "list.db"
    db = Database(db_path)

    ep1 = Episode(id="ep1", title="Episode 1")
    ep2 = Episode(id="ep2", title="Episode 2")
    db.save_episode(ep1)
    db.save_episode(ep2)

    all_eps = db.list_episodes(limit=10)
    assert len(all_eps) == 2
