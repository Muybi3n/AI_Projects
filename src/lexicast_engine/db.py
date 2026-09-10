# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
SQLite database storage layer with FTS5 full-text search indexing.
"""

import json
import sqlite3
from pathlib import Path

from .models import DistillationArtifact, Episode, SearchHit


class Database:
    """Manages local SQLite storage with FTS5 search table."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables and FTS5 virtual index."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    source_uri TEXT,
                    raw_transcript TEXT,
                    duration_seconds REAL,
                    created_at TEXT,
                    distillation_json TEXT
                )
            """)

            # Create FTS5 virtual table for full-text queries
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                    id UNINDEXED,
                    title,
                    speaker,
                    raw_transcript,
                    distillation_text,
                    content='episodes',
                    content_rowid='rowid'
                )
            """)

            # Triggers to keep FTS in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                    INSERT INTO episodes_fts(rowid, id, title, speaker, raw_transcript, distillation_text)
                    VALUES (new.rowid, new.id, new.title, new.speaker, new.raw_transcript, coalesce(new.distillation_json, ''));
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                    INSERT INTO episodes_fts(episodes_fts, rowid, id, title, speaker, raw_transcript, distillation_text)
                    VALUES('delete', old.rowid, old.id, old.title, old.speaker, old.raw_transcript, coalesce(old.distillation_json, ''));
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN
                    INSERT INTO episodes_fts(episodes_fts, rowid, id, title, speaker, raw_transcript, distillation_text)
                    VALUES('delete', old.rowid, old.id, old.title, old.speaker, old.raw_transcript, coalesce(old.distillation_json, ''));
                    INSERT INTO episodes_fts(rowid, id, title, speaker, raw_transcript, distillation_text)
                    VALUES (new.rowid, new.id, new.title, new.speaker, new.raw_transcript, coalesce(new.distillation_json, ''));
                END;
            """)
            conn.commit()

    def save_episode(self, episode: Episode) -> None:
        """Insert or update an episode."""
        dist_json = json.dumps(episode.distillation.to_dict()) if episode.distillation else None
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO episodes (
                    id, title, speaker, source_uri, raw_transcript, duration_seconds, created_at, distillation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode.id,
                episode.title,
                episode.speaker,
                episode.source_uri,
                episode.raw_transcript,
                episode.duration_seconds,
                episode.created_at,
                dist_json
            ))
            conn.commit()

    def get_episode(self, episode_id: str) -> Episode | None:
        """Retrieve single episode by ID."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
            if not row:
                return None
            return self._row_to_episode(row)

    def list_episodes(self, limit: int = 50) -> list[Episode]:
        """List all episodes sorted by creation date."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_episode(r) for r in rows]

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        """Execute BM25 ranked full-text query using FTS5."""
        clean_query = query.replace('"', '""').strip()
        if not clean_query:
            return []

        with self._get_conn() as conn:
            sql = """
                SELECT 
                    id, 
                    title, 
                    speaker, 
                    snippet(episodes_fts, 3, '[MATCH]', '[/MATCH]', '...', 16) AS matched_snippet,
                    rank
                FROM episodes_fts 
                WHERE episodes_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """
            try:
                rows = conn.execute(sql, (clean_query, limit)).fetchall()
                return [
                    SearchHit(
                        episode_id=r["id"],
                        title=r["title"],
                        speaker=r["speaker"],
                        matched_snippet=r["matched_snippet"] or "",
                        rank=float(r["rank"]),
                    )
                    for r in rows
                ]
            except sqlite3.OperationalError:
                # Fallback to simple LIKE query if query syntax error in FTS match
                like_term = f"%{clean_query}%"
                fallback_sql = """
                    SELECT id, title, speaker, substr(raw_transcript, 1, 100) as matched_snippet, 0.0 as rank
                    FROM episodes
                    WHERE raw_transcript LIKE ? OR title LIKE ?
                    LIMIT ?
                """
                fb_rows = conn.execute(fallback_sql, (like_term, like_term, limit)).fetchall()
                return [
                    SearchHit(
                        episode_id=r["id"],
                        title=r["title"],
                        speaker=r["speaker"],
                        matched_snippet=r["matched_snippet"],
                        rank=0.0,
                    )
                    for r in fb_rows
                ]

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        dist = None
        if row["distillation_json"]:
            try:
                dist = DistillationArtifact.from_dict(json.loads(row["distillation_json"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                dist = None

        return Episode(
            id=row["id"],
            title=row["title"],
            speaker=row["speaker"],
            source_uri=row["source_uri"] or "",
            raw_transcript=row["raw_transcript"] or "",
            duration_seconds=row["duration_seconds"] or 0.0,
            created_at=row["created_at"],
            distillation=dist,
        )
