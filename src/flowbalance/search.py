# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
SQLite FTS5 Full-Text Search Engine for transactions, recurring expenses, incomes, and accounts.
"""

import sqlite3
from pathlib import Path

from .models import Account, Expense, IncomeStream, SearchHit, Transaction


class SearchEngine:
    """Manages full-text search indexing across personal finance ledgers."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS finance_fts USING fts5(
                    item_type,
                    item_id UNINDEXED,
                    title,
                    category,
                    amount_text,
                    notes_text
                )
            """)
            conn.commit()

    def index_all(
        self,
        accounts: list[Account],
        incomes: list[IncomeStream],
        expenses: list[Expense],
        transactions: list[Transaction],
    ) -> None:
        """Re-index all entities in bulk."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM finance_fts")
            for a in accounts:
                conn.execute(
                    "INSERT INTO finance_fts VALUES (?, ?, ?, ?, ?, ?)",
                    ("account", a.id, a.name, "account", f"${a.balance:,.2f}", f"Liquid: {a.is_liquid}"),
                )
            for i in incomes:
                conn.execute(
                    "INSERT INTO finance_fts VALUES (?, ?, ?, ?, ?, ?)",
                    ("income", i.id, i.name, "income", f"${i.amount:,.2f}", f"{i.frequency} tax: {i.tax_withholding_pct}%"),
                )
            for e in expenses:
                conn.execute(
                    "INSERT INTO finance_fts VALUES (?, ?, ?, ?, ?, ?)",
                    ("expense", e.id, e.name, e.category, f"${e.amount:,.2f}", f"{e.frequency} essential: {e.is_essential}"),
                )
            for t in transactions:
                tag_str = " ".join(t.tags)
                conn.execute(
                    "INSERT INTO finance_fts VALUES (?, ?, ?, ?, ?, ?)",
                    ("transaction", t.id, t.description, t.category, f"${t.amount:,.2f}", f"{t.date_str} {tag_str} {t.notes}"),
                )
            conn.commit()

    def search(self, query: str, limit: int = 15) -> list[SearchHit]:
        """Perform BM25 search across indexed finance records."""
        clean_q = query.replace('"', '""').strip()
        if not clean_q:
            return []

        with self._get_conn() as conn:
            try:
                sql = """
                    SELECT 
                        item_type, 
                        item_id, 
                        title, 
                        snippet(finance_fts, 5, '[MATCH]', '[/MATCH]', '...', 12) AS snippet,
                        rank
                    FROM finance_fts
                    WHERE finance_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """
                rows = conn.execute(sql, (clean_q, limit)).fetchall()
                return [
                    SearchHit(
                        item_type=r["item_type"],
                        item_id=r["item_id"],
                        title=r["title"],
                        snippet=r["snippet"] or "",
                        rank=float(r["rank"]),
                    )
                    for r in rows
                ]
            except sqlite3.OperationalError:
                # Fallback to simple LIKE search if FTS query syntax error
                like_term = f"%{clean_q}%"
                fallback_sql = """
                    SELECT item_type, item_id, title, notes_text as snippet, 0.0 as rank
                    FROM finance_fts
                    WHERE title LIKE ? OR notes_text LIKE ? OR category LIKE ?
                    LIMIT ?
                """
                fb_rows = conn.execute(fallback_sql, (like_term, like_term, like_term, limit)).fetchall()
                return [
                    SearchHit(
                        item_type=r["item_type"],
                        item_id=r["item_id"],
                        title=r["title"],
                        snippet=r["snippet"],
                        rank=0.0,
                    )
                    for r in fb_rows
                ]
