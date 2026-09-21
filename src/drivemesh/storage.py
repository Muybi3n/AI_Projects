"""SQLite storage backend with FTS5 search for drivemesh-core."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from drivemesh.models import (
    ClusterCategory,
    DriveAuditReport,
    DriveFile,
    DriveFolder,
    DuplicateGroup,
    DuplicateType,
    FileCluster,
    ResolutionAction,
)


class DriveStorage:
    """Local SQLite database manager for cataloging files, clusters, and duplicates."""

    def __init__(self, db_path: str | Path = "drivemesh.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema with tables and FTS5 search index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    mime_type TEXT,
                    size_bytes INTEGER,
                    md5_checksum TEXT,
                    sha256_checksum TEXT,
                    modified_time TEXT,
                    created_time TEXT,
                    parents TEXT,
                    path_hierarchy TEXT,
                    shared INTEGER,
                    starred INTEGER,
                    trashed INTEGER,
                    assigned_category TEXT,
                    cluster_label TEXT,
                    confidence REAL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    parents TEXT,
                    path TEXT,
                    modified_time TEXT
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clusters (
                    cluster_id TEXT PRIMARY KEY,
                    category TEXT,
                    label TEXT,
                    file_ids TEXT,
                    total_size_bytes INTEGER,
                    suggested_target_path TEXT,
                    confidence_score REAL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS duplicates (
                    group_id TEXT PRIMARY KEY,
                    canonical_file_id TEXT,
                    duplicate_file_ids TEXT,
                    duplicate_type TEXT,
                    wasted_bytes INTEGER,
                    resolution_suggestion TEXT,
                    explanation TEXT
                )
                """
            )

            # SQLite FTS5 for fast full-text querying
            cursor.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                    id UNINDEXED,
                    name,
                    path_hierarchy,
                    assigned_category,
                    cluster_label
                )
                """
            )
            conn.commit()

    def save_files(self, files: list[DriveFile]) -> int:
        """Upsert Drive files and populate FTS5 index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for f in files:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO files (
                        id, name, mime_type, size_bytes, md5_checksum, sha256_checksum,
                        modified_time, created_time, parents, path_hierarchy, shared,
                        starred, trashed, assigned_category, cluster_label, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f.id,
                        f.name,
                        f.mime_type,
                        f.size_bytes,
                        f.md5_checksum,
                        f.sha256_checksum,
                        f.modified_time,
                        f.created_time,
                        json.dumps(f.parents),
                        f.path_hierarchy,
                        1 if f.shared else 0,
                        1 if f.starred else 0,
                        1 if f.trashed else 0,
                        f.assigned_category.value
                        if isinstance(f.assigned_category, ClusterCategory)
                        else str(f.assigned_category),
                        f.cluster_label,
                        f.confidence,
                    ),
                )
                # Update FTS5
                cursor.execute("DELETE FROM files_fts WHERE id = ?", (f.id,))
                cursor.execute(
                    """
                    INSERT INTO files_fts (id, name, path_hierarchy, assigned_category, cluster_label)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        f.id,
                        f.name,
                        f.path_hierarchy,
                        f.assigned_category.value
                        if isinstance(f.assigned_category, ClusterCategory)
                        else str(f.assigned_category),
                        f.cluster_label,
                    ),
                )
            conn.commit()
            return len(files)

    def save_folders(self, folders: list[DriveFolder]) -> int:
        """Upsert Drive folders."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for f in folders:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO folders (id, name, parents, path, modified_time)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (f.id, f.name, json.dumps(f.parents), f.path, f.modified_time),
                )
            conn.commit()
            return len(folders)

    def save_clusters(self, clusters: list[FileCluster]) -> int:
        """Persist discovered subject clusters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clusters")
            for c in clusters:
                cursor.execute(
                    """
                    INSERT INTO clusters (
                        cluster_id, category, label, file_ids, total_size_bytes,
                        suggested_target_path, confidence_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.cluster_id,
                        c.category.value,
                        c.label,
                        json.dumps(c.file_ids),
                        c.total_size_bytes,
                        c.suggested_target_path,
                        c.confidence_score,
                    ),
                )
            conn.commit()
            return len(clusters)

    def save_duplicates(self, duplicates: list[DuplicateGroup]) -> int:
        """Persist duplicate groups."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM duplicates")
            for d in duplicates:
                cursor.execute(
                    """
                    INSERT INTO duplicates (
                        group_id, canonical_file_id, duplicate_file_ids, duplicate_type,
                        wasted_bytes, resolution_suggestion, explanation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.group_id,
                        d.canonical_file_id,
                        json.dumps(d.duplicate_file_ids),
                        d.duplicate_type.value,
                        d.wasted_bytes,
                        d.resolution_suggestion.value,
                        d.explanation,
                    ),
                )
            conn.commit()
            return len(duplicates)

    def load_files(self) -> list[DriveFile]:
        """Fetch all indexed files from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files")
            rows = cursor.fetchall()
            files: list[DriveFile] = []
            for r in rows:
                cat_val = r["assigned_category"]
                cat_enum = ClusterCategory.UNCATEGORIZED
                for member in ClusterCategory:
                    if member.value == cat_val:
                        cat_enum = member
                        break

                files.append(
                    DriveFile(
                        id=r["id"],
                        name=r["name"],
                        mime_type=r["mime_type"] or "",
                        size_bytes=r["size_bytes"] or 0,
                        md5_checksum=r["md5_checksum"] or "",
                        sha256_checksum=r["sha256_checksum"] or "",
                        modified_time=r["modified_time"] or "",
                        created_time=r["created_time"] or "",
                        parents=json.loads(r["parents"] or "[]"),
                        path_hierarchy=r["path_hierarchy"] or "/",
                        shared=bool(r["shared"]),
                        starred=bool(r["starred"]),
                        trashed=bool(r["trashed"]),
                        assigned_category=cat_enum,
                        cluster_label=r["cluster_label"] or "",
                        confidence=r["confidence"] or 0.0,
                    )
                )
            return files

    def search_fts(self, query: str) -> list[dict[str, Any]]:
        """Search files using SQLite FTS5."""
        clean_query = "".join(c if c.isalnum() or c in " *\"'" else " " for c in query).strip()
        if not clean_query:
            return []

        # Add prefix wildcard if not present
        if not any(c in clean_query for c in ['"', "*"]):
            fts_term = " OR ".join([f"{term}*" for term in clean_query.split()])
        else:
            fts_term = clean_query

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT f.* FROM files f
                    JOIN files_fts ON f.id = files_fts.id
                    WHERE files_fts MATCH ?
                    ORDER BY rank
                    LIMIT 50
                    """,
                    (fts_term,),
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                # Fallback to simple LIKE search if FTS query syntax is invalid
                cursor.execute(
                    """
                    SELECT * FROM files
                    WHERE name LIKE ? OR path_hierarchy LIKE ?
                    LIMIT 50
                    """,
                    (f"%{query}%", f"%{query}%"),
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]

    def get_audit_summary(self) -> DriveAuditReport:
        """Compute drive audit metrics directly from database."""
        files = self.load_files()
        total_files = len(files)
        total_storage = sum(f.size_bytes for f in files)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM folders")
            total_folders = cursor.fetchone()[0]

            cursor.execute("SELECT * FROM duplicates")
            dup_rows = cursor.fetchall()

        dup_groups: list[DuplicateGroup] = []
        reclaimable_bytes = 0

        for r in dup_rows:
            dup_type = DuplicateType(r["duplicate_type"])
            res_action = ResolutionAction(r["resolution_suggestion"])
            wasted = r["wasted_bytes"] or 0
            reclaimable_bytes += wasted
            dup_groups.append(
                DuplicateGroup(
                    group_id=r["group_id"],
                    canonical_file_id=r["canonical_file_id"],
                    duplicate_file_ids=json.loads(r["duplicate_file_ids"] or "[]"),
                    duplicate_type=dup_type,
                    wasted_bytes=wasted,
                    resolution_suggestion=res_action,
                    explanation=r["explanation"] or "",
                )
            )

        root_orphans = sum(1 for f in files if f.path_hierarchy in ("/", f"/{f.name}"))
        zero_bytes = sum(1 for f in files if f.size_bytes == 0)
        shared_count = sum(1 for f in files if f.shared)

        # Calculate category counts
        cat_counts: dict[str, int] = {}
        for f in files:
            cat_name = f.assigned_category.value
            cat_counts[cat_name] = cat_counts.get(cat_name, 0) + 1

        # Health score calculation (0 - 100)
        # Penalties: Duplicate bytes ratio, Root clutter, Zero byte files
        penalty = 0
        if total_storage > 0:
            dup_ratio = reclaimable_bytes / total_storage
            penalty += int(dup_ratio * 40)
        if total_files > 0:
            root_ratio = root_orphans / total_files
            penalty += int(root_ratio * 30)
            if zero_bytes > 0:
                penalty += min(15, zero_bytes * 3)

        health_score = max(10, 100 - penalty)

        recommendations: list[str] = []
        if reclaimable_bytes > 0:
            reclaim_mb = reclaimable_bytes / (1024 * 1024)
            recommendations.append(f"Purge duplicate files to reclaim {reclaim_mb:.1f} MB of cloud storage.")
        if root_orphans > 0:
            recommendations.append(
                f"Move {root_orphans} orphaned files from root 'My Drive' into categorized taxonomy meshes."
            )
        if zero_bytes > 0:
            recommendations.append(f"Delete {zero_bytes} empty/corrupted zero-byte files.")
        if not recommendations:
            recommendations.append("Cloud storage is in pristine condition! No immediate cleanups required.")

        return DriveAuditReport(
            total_files=total_files,
            total_folders=total_folders,
            total_storage_bytes=total_storage,
            reclaimable_bytes=reclaimable_bytes,
            duplicate_groups_count=len(dup_groups),
            orphaned_root_files_count=root_orphans,
            zero_byte_files_count=zero_bytes,
            shared_files_count=shared_count,
            health_score=health_score,
            top_categories=cat_counts,
            duplicate_groups=dup_groups,
            recommendations=recommendations,
        )
