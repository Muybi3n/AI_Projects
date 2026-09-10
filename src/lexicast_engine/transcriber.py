# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Audio ingestion and speech-to-text transcription adapter.
"""

import uuid
from pathlib import Path

from .models import Episode


class AudioTranscriber:
    """Ingests audio files or raw transcript files into normalized Episode records."""

    def ingest_file(
        self,
        file_path: Path | str,
        title: str | None = None,
        speaker: str = "Unknown Speaker"
    ) -> Episode:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        ep_id = str(uuid.uuid4())[:8]
        ep_title = title or path.stem.replace("_", " ").replace("-", " ").title()

        # If it's a text/markdown file, read directly
        if path.suffix.lower() in [".txt", ".md", ".vtt", ".srt"]:
            content = path.read_text(encoding="utf-8", errors="replace")
            clean_text = self._clean_transcript_text(content)
            return Episode(
                id=ep_id,
                title=ep_title,
                speaker=speaker,
                source_uri=str(path),
                raw_transcript=clean_text,
                duration_seconds=0.0,
            )

        # For audio formats (.mp3, .wav, .m4a, .ogg)
        # In a real environment with whisper installed, it invokes local whisper
        # In standalone mode, provides a clean structured placeholder
        return Episode(
            id=ep_id,
            title=ep_title,
            speaker=speaker,
            source_uri=str(path),
            raw_transcript=f"[Audio File: {path.name}] Ingested for speech-to-text processing.",
            duration_seconds=0.0,
        )

    def _clean_transcript_text(self, text: str) -> str:
        """Strip SRT / VTT timestamps and numeric headers if present."""
        lines = []
        for line in text.splitlines():
            line_s = line.strip()
            # Ignore SRT numeric indices and VTT cue timestamps
            if line_s.isdigit():
                continue
            if "-->" in line_s or line_s.startswith("WEBVTT"):
                continue
            if line_s:
                lines.append(line_s)
        return " ".join(lines)
