# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
lexicast-engine - Local-First Audio Transcription & 5-Layer Structured Insight Distillation.
"""

__version__ = "0.1.0"
__author__ = "bi3n"
__license__ = "MIT"

from .db import Database
from .distiller import InsightDistiller
from .exporter import export_markdown, format_executive_brief
from .models import DistillationArtifact, Episode, SearchHit
from .transcriber import AudioTranscriber

__all__ = [
    "AudioTranscriber",
    "Database",
    "DistillationArtifact",
    "Episode",
    "InsightDistiller",
    "SearchHit",
    "export_markdown",
    "format_executive_brief",
]
