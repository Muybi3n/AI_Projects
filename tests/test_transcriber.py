# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for transcriber audio and text ingestion.
"""

from pathlib import Path

from lexicast_engine.transcriber import AudioTranscriber


def test_ingest_text_file(tmp_path: Path):
    txt_file = tmp_path / "transcript.txt"
    txt_file.write_text("This is an interview transcript with Dr. Huberman.", encoding="utf-8")

    transcriber = AudioTranscriber()
    ep = transcriber.ingest_file(txt_file, speaker="Andrew Huberman")

    assert ep.title == "Transcript"
    assert ep.speaker == "Andrew Huberman"
    assert "Dr. Huberman" in ep.raw_transcript


def test_ingest_srt_file(tmp_path: Path):
    srt_file = tmp_path / "subtitles.srt"
    srt_content = """1
00:00:01,000 --> 00:00:04,000
Welcome to the podcast.

2
00:00:04,500 --> 00:00:08,000
Today we discuss focus and sleep.
"""
    srt_file.write_text(srt_content, encoding="utf-8")

    transcriber = AudioTranscriber()
    ep = transcriber.ingest_file(srt_file)

    assert "00:00:01" not in ep.raw_transcript
    assert "Welcome to the podcast." in ep.raw_transcript
    assert "Today we discuss focus and sleep." in ep.raw_transcript


def test_ingest_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.mp3"
    transcriber = AudioTranscriber()
    try:
        transcriber.ingest_file(missing)
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass
