# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Command-Line Interface (CLI) for lexicast-engine.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .db import Database
from .distiller import InsightDistiller
from .exporter import export_markdown, format_executive_brief
from .transcriber import AudioTranscriber

DEFAULT_DB_PATH = Path.home() / ".lexicast" / "lexicast.db"


def get_db(custom_path: Path | None = None) -> Database:
    db_file = custom_path or DEFAULT_DB_PATH
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return Database(db_file)


def print_banner():
    banner = f"""
┌─────────────────────────────────────────────────────────────┐
│  lexicast v{__version__:<10}                                      │
│  Local-First Knowledge Distillation & Search Engine        │
└─────────────────────────────────────────────────────────────┘
"""
    print(banner)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="lexicast",
        description="Local-First Audio Ingestion & 5-Layer Structured Insight Distillation Pipeline.",
    )
    parser.add_argument("--db", type=Path, default=None, help="Custom SQLite database path.")
    parser.add_argument("--version", "-v", action="version", version=f"lexicast {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    ingest_p = subparsers.add_parser("ingest", help="Ingest an audio or transcript file.")
    ingest_p.add_argument("file", type=Path, help="Audio or transcript file path (.mp3, .txt, .md, .vtt).")
    ingest_p.add_argument("--title", type=str, default=None, help="Episode title.")
    ingest_p.add_argument("--speaker", type=str, default="Unknown Speaker", help="Speaker / host name.")
    ingest_p.add_argument("--distill", action="store_true", help="Automatically distill upon ingestion.")

    # Distill
    distill_p = subparsers.add_parser("distill", help="Distill an existing episode by ID.")
    distill_p.add_argument("episode_id", type=str, help="Episode ID to distill.")

    # Search
    search_p = subparsers.add_parser("search", help="Full-text BM25 search across episodes.")
    search_p.add_argument("query", type=str, help="Search terms.")
    search_p.add_argument("--limit", type=int, default=10, help="Max results.")

    # List
    list_p = subparsers.add_parser("list", help="List all indexed episodes.")
    list_p.add_argument("--limit", type=int, default=20, help="Max episodes to display.")

    # Export
    export_p = subparsers.add_parser("export", help="Export episode to Markdown or JSON.")
    export_p.add_argument("episode_id", type=str, help="Episode ID.")
    export_p.add_argument("--out", "-o", type=Path, default=None, help="Output destination file path.")
    export_p.add_argument("--format", choices=["md", "json"], default="md", help="Export format.")

    # Brief
    brief_p = subparsers.add_parser("brief", help="Display concise executive brief for an episode.")
    brief_p.add_argument("episode_id", type=str, help="Episode ID.")

    args = parser.parse_args(argv)
    db = get_db(args.db)

    if args.command == "ingest":
        transcriber = AudioTranscriber()
        try:
            ep = transcriber.ingest_file(args.file, title=args.title, speaker=args.speaker)
        except (OSError, ValueError) as e:
            print(f"Error ingesting file: {e}", file=sys.stderr)
            return 1

        if args.distill:
            distiller = InsightDistiller()
            ep.distillation = distiller.distill(ep)

        db.save_episode(ep)
        print(f"[✓] Ingested: '{ep.title}' (ID: {ep.id})")
        if ep.distillation:
            print("[✓] Successfully distilled 5-layer knowledge artifact.")
        return 0

    elif args.command == "distill":
        ep = db.get_episode(args.episode_id)
        if not ep:
            print(f"Error: Episode '{args.episode_id}' not found.", file=sys.stderr)
            return 1

        distiller = InsightDistiller()
        ep.distillation = distiller.distill(ep)
        db.save_episode(ep)
        print(f"[✓] Distillation complete for '{ep.title}'.")
        print(format_executive_brief(ep))
        return 0

    elif args.command == "search":
        hits = db.search(args.query, limit=args.limit)
        print(f"\nSearch results for '{args.query}' ({len(hits)} hit(s)):")
        print("─" * 60)
        if not hits:
            print("No matching transcripts or quotes found.")
            return 0

        for h in hits:
            print(f"• [{h.episode_id}] {h.title} (Speaker: {h.speaker})")
            print(f"  Snippet: {h.matched_snippet}\n")
        return 0

    elif args.command == "list":
        episodes = db.list_episodes(limit=args.limit)
        print(f"\nIndexed Episodes ({len(episodes)} total):")
        print("─" * 65)
        if not episodes:
            print("No episodes in database. Use 'lexicast ingest <file>' to add one.")
            return 0

        for ep in episodes:
            status = "✓ Distilled" if ep.distillation else "○ Raw"
            print(f"[{ep.id}] {ep.title:<35} | {ep.speaker:<15} [{status}]")
        return 0

    elif args.command == "export":
        ep = db.get_episode(args.episode_id)
        if not ep:
            print(f"Error: Episode '{args.episode_id}' not found.", file=sys.stderr)
            return 1

        if args.format == "json":
            data = json.dumps(ep.to_dict(), indent=2)
            if args.out:
                args.out.write_text(data, encoding="utf-8")
                print(f"[✓] Exported JSON to: {args.out}")
            else:
                print(data)
        else:
            md = export_markdown(ep, output_path=args.out)
            if args.out:
                print(f"[✓] Exported Markdown to: {args.out}")
            else:
                print(md)
        return 0

    elif args.command == "brief":
        ep = db.get_episode(args.episode_id)
        if not ep:
            print(f"Error: Episode '{args.episode_id}' not found.", file=sys.stderr)
            return 1
        print(format_executive_brief(ep))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
