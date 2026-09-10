# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Core data models for episode transcripts, distillation layers, and search results.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DistillationArtifact:
    """The 5-Layer Structured Distillation Schema."""
    thesis: str = ""
    quotes: list[str] = field(default_factory=list)
    mental_models: list[str] = field(default_factory=list)
    moral_philosophy: str = ""
    micro_habits: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DistillationArtifact":
        return cls(
            thesis=data.get("thesis", ""),
            quotes=data.get("quotes", []),
            mental_models=data.get("mental_models", []),
            moral_philosophy=data.get("moral_philosophy", ""),
            micro_habits=data.get("micro_habits", []),
            tags=data.get("tags", []),
        )


@dataclass
class Episode:
    """Represents an ingested audio or transcript recording."""
    id: str
    title: str
    speaker: str = "Unknown Speaker"
    source_uri: str = ""
    raw_transcript: str = ""
    duration_seconds: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    distillation: DistillationArtifact | None = None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        if self.distillation:
            res["distillation"] = self.distillation.to_dict()
        return res


@dataclass
class SearchHit:
    """Search match returned from SQLite FTS5 queries."""
    episode_id: str
    title: str
    speaker: str
    matched_snippet: str
    rank: float
