"""Local SQLite Storage and File Ingestion (MBOX, EML, JSON, CSV) with FTS5 search.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import csv
import email
import json
import mailbox
import sqlite3
from email import policy
from pathlib import Path
from typing import Any

from inboxguard.classifier import EmailClassifier
from inboxguard.models import EmailMessage, EmailTier, FilterRule, SecurityRiskLevel, UnsubscribeMechanism
from inboxguard.newsletter import NewsletterCleaner
from inboxguard.security import SecurityAuditor


class StorageEngine:
    """Manages SQLite storage, FTS5 full-text indexing, and email ingestion."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            data_dir = Path.home() / ".inboxguard"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "inboxguard.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    message_id TEXT,
                    thread_id TEXT,
                    subject TEXT,
                    sender_name TEXT,
                    sender_email TEXT,
                    recipient TEXT,
                    date TEXT,
                    body TEXT,
                    headers_json TEXT,
                    tier TEXT,
                    tier_reasons_json TEXT,
                    security_risk TEXT,
                    security_reasons_json TEXT,
                    unsubscribe_type TEXT,
                    unsubscribe_url TEXT,
                    unsubscribe_mailto TEXT,
                    is_read INTEGER,
                    is_starred INTEGER
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
                    id UNINDEXED,
                    subject,
                    body,
                    sender_name,
                    sender_email,
                    tokenize = 'porter unicode61'
                );

                CREATE TABLE IF NOT EXISTS filter_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    criteria_from TEXT,
                    criteria_subject TEXT,
                    criteria_has_words TEXT,
                    action_apply_label TEXT,
                    action_archive INTEGER,
                    action_star INTEGER,
                    action_mark_read INTEGER,
                    action_trash INTEGER
                );
                """
            )

    def save_email(self, msg: EmailMessage) -> None:
        """Insert or replace an email message and sync its FTS index."""
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO emails (
                    id, message_id, thread_id, subject, sender_name, sender_email,
                    recipient, date, body, headers_json, tier, tier_reasons_json,
                    security_risk, security_reasons_json, unsubscribe_type,
                    unsubscribe_url, unsubscribe_mailto, is_read, is_starred
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg.id,
                    msg.message_id,
                    msg.thread_id,
                    msg.subject,
                    msg.sender_name,
                    msg.sender_email,
                    msg.recipient,
                    msg.date,
                    msg.body,
                    json.dumps(msg.headers),
                    msg.tier.value if isinstance(msg.tier, EmailTier) else str(msg.tier),
                    json.dumps(msg.tier_reasons),
                    msg.security_risk.value
                    if isinstance(msg.security_risk, SecurityRiskLevel)
                    else str(msg.security_risk),
                    json.dumps(msg.security_reasons),
                    msg.unsubscribe_type.value
                    if isinstance(msg.unsubscribe_type, UnsubscribeMechanism)
                    else str(msg.unsubscribe_type),
                    msg.unsubscribe_url,
                    msg.unsubscribe_mailto,
                    1 if msg.is_read else 0,
                    1 if msg.is_starred else 0,
                ),
            )
            conn.execute("DELETE FROM emails_fts WHERE id = ?", (msg.id,))
            conn.execute(
                """
                INSERT INTO emails_fts (id, subject, body, sender_name, sender_email)
                VALUES (?, ?, ?, ?, ?)
                """,
                (msg.id, msg.subject, msg.body, msg.sender_name, msg.sender_email),
            )

    def save_emails_batch(self, messages: list[EmailMessage]) -> int:
        """Batch save multiple email messages."""
        for msg in messages:
            self.save_email(msg)
        return len(messages)

    def list_emails(
        self,
        tier: str | None = None,
        sender: str | None = None,
        unread_only: bool = False,
        security_risk: str | None = None,
        limit: int = 100,
    ) -> list[EmailMessage]:
        """Query emails with optional filtering."""
        query = "SELECT * FROM emails WHERE 1=1"
        params: list[Any] = []

        if tier:
            query += " AND tier = ?"
            params.append(tier.upper())
        if sender:
            query += " AND (sender_email LIKE ? OR sender_name LIKE ?)"
            params.extend([f"%{sender}%", f"%{sender}%"])
        if unread_only:
            query += " AND is_read = 0"
        if security_risk:
            query += " AND security_risk = ?"
            params.append(security_risk.upper())

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_email(r) for r in rows]

    def get_email_by_id(self, email_id: str) -> EmailMessage | None:
        """Fetch a single email by id."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
            if row:
                return self._row_to_email(row)
        return None

    def search_fts(self, search_query: str, limit: int = 50) -> list[EmailMessage]:
        """Perform SQLite FTS5 full text search across subject, body, and sender."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT e.* FROM emails e
                JOIN emails_fts f ON e.id = f.id
                WHERE emails_fts MATCH ?
                ORDER BY rank LIMIT ?
                """,
                (search_query, limit),
            ).fetchall()
            return [self._row_to_email(r) for r in rows]

    def save_rule(self, rule: FilterRule) -> None:
        """Save or update a filter rule."""
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO filter_rules (
                    name, criteria_from, criteria_subject, criteria_has_words,
                    action_apply_label, action_archive, action_star, action_mark_read, action_trash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule.name,
                    rule.criteria_from,
                    rule.criteria_subject,
                    rule.criteria_has_words,
                    rule.action_apply_label,
                    1 if rule.action_archive else 0,
                    1 if rule.action_star else 0,
                    1 if rule.action_mark_read else 0,
                    1 if rule.action_trash else 0,
                ),
            )

    def list_rules(self) -> list[FilterRule]:
        """Retrieve all saved filter rules."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM filter_rules ORDER BY id ASC").fetchall()
            return [
                FilterRule(
                    name=r["name"],
                    criteria_from=r["criteria_from"] or "",
                    criteria_subject=r["criteria_subject"] or "",
                    criteria_has_words=r["criteria_has_words"] or "",
                    action_apply_label=r["action_apply_label"] or "",
                    action_archive=bool(r["action_archive"]),
                    action_star=bool(r["action_star"]),
                    action_mark_read=bool(r["action_mark_read"]),
                    action_trash=bool(r["action_trash"]),
                )
                for r in rows
            ]

    def count_by_tier(self) -> dict[str, int]:
        """Return counts of emails by tier."""
        counts = {t.value: 0 for t in EmailTier}
        with self._get_conn() as conn:
            rows = conn.execute("SELECT tier, COUNT(*) as cnt FROM emails GROUP BY tier").fetchall()
            for r in rows:
                if r["tier"] in counts:
                    counts[r["tier"]] = r["cnt"]
        return counts

    def _row_to_email(self, r: sqlite3.Row) -> EmailMessage:
        headers = json.loads(r["headers_json"]) if r["headers_json"] else {}
        tier_reasons = json.loads(r["tier_reasons_json"]) if r["tier_reasons_json"] else []
        security_reasons = json.loads(r["security_reasons_json"]) if r["security_reasons_json"] else []

        return EmailMessage(
            id=r["id"],
            message_id=r["message_id"] or "",
            thread_id=r["thread_id"] or "",
            subject=r["subject"] or "",
            sender_name=r["sender_name"] or "",
            sender_email=r["sender_email"] or "",
            recipient=r["recipient"] or "",
            date=r["date"] or "",
            body=r["body"] or "",
            headers=headers,
            tier=EmailTier(r["tier"]) if r["tier"] in [t.value for t in EmailTier] else EmailTier.TIER_2_ACTIONABLE,
            tier_reasons=tier_reasons,
            security_risk=SecurityRiskLevel(r["security_risk"])
            if r["security_risk"] in [s.value for s in SecurityRiskLevel]
            else SecurityRiskLevel.SAFE,
            security_reasons=security_reasons,
            unsubscribe_type=UnsubscribeMechanism(r["unsubscribe_type"])
            if r["unsubscribe_type"] in [u.value for u in UnsubscribeMechanism]
            else UnsubscribeMechanism.NONE,
            unsubscribe_url=r["unsubscribe_url"] or "",
            unsubscribe_mailto=r["unsubscribe_mailto"] or "",
            is_read=bool(r["is_read"]),
            is_starred=bool(r["is_starred"]),
        )

    # Ingestion Parsers
    def ingest_mbox(self, mbox_file_path: str | Path) -> list[EmailMessage]:
        """Parse an RFC 4155 MBOX file."""
        mbox = mailbox.mbox(str(mbox_file_path))
        classifier = EmailClassifier()
        auditor = SecurityAuditor()
        messages: list[EmailMessage] = []

        for idx, m in enumerate(mbox):
            msg_id = m.get("Message-ID", f"mbox-{idx}")
            subject = m.get("Subject", "(No Subject)")
            from_hdr = m.get("From", "")
            to_hdr = m.get("To", "")
            date_hdr = m.get("Date", "")

            # Parse sender name and email
            sender_name, sender_email = email.utils.parseaddr(from_hdr)
            if not sender_email and "@" in from_hdr:
                sender_email = from_hdr

            # Extract body
            body = ""
            if m.is_multipart():
                for part in m.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get("Content-Disposition"))
                    if ctype == "text/plain" and "attachment" not in cdispo:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="replace")
                            break
            else:
                payload = m.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")

            # Extract headers
            headers = {k: str(v) for k, v in m.items()}
            unsub_hdr = headers.get("List-Unsubscribe", "")
            unsub_post = headers.get("List-Unsubscribe-Post", "")
            unsub_type, unsub_url, unsub_mailto = NewsletterCleaner.parse_unsubscribe_header(unsub_hdr, unsub_post)

            msg_obj = EmailMessage(
                id=f"msg_{idx + 1:05d}",
                message_id=msg_id,
                thread_id=m.get("Thread-Topic", msg_id),
                subject=subject,
                sender_name=sender_name or sender_email,
                sender_email=sender_email,
                recipient=to_hdr,
                date=date_hdr,
                body=body,
                headers=headers,
                unsubscribe_type=unsub_type,
                unsubscribe_url=unsub_url,
                unsubscribe_mailto=unsub_mailto,
                is_read=False,
                is_starred=False,
            )
            classifier.classify(msg_obj)
            auditor.audit(msg_obj)
            messages.append(msg_obj)

        self.save_emails_batch(messages)
        return messages

    def ingest_eml(self, eml_file_path: str | Path) -> EmailMessage:
        """Parse a standalone .eml RFC 822 file."""
        with open(eml_file_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        classifier = EmailClassifier()
        auditor = SecurityAuditor()

        msg_id = msg.get("Message-ID", Path(eml_file_path).stem)
        subject = msg.get("Subject", "(No Subject)")
        from_hdr = msg.get("From", "")
        to_hdr = msg.get("To", "")
        date_hdr = str(msg.get("Date", ""))

        sender_name, sender_email = email.utils.parseaddr(str(from_hdr))
        if not sender_email and "@" in str(from_hdr):
            sender_email = str(from_hdr)

        body = ""
        body_part = msg.get_body(preferencelist=("plain", "html"))
        if body_part:
            body = body_part.get_content()

        headers = {k: str(v) for k, v in msg.items()}
        unsub_hdr = headers.get("List-Unsubscribe", "")
        unsub_post = headers.get("List-Unsubscribe-Post", "")
        unsub_type, unsub_url, unsub_mailto = NewsletterCleaner.parse_unsubscribe_header(unsub_hdr, unsub_post)

        msg_obj = EmailMessage(
            id=f"eml_{Path(eml_file_path).stem}",
            message_id=msg_id,
            thread_id=msg.get("Thread-Topic", msg_id),
            subject=subject,
            sender_name=sender_name or sender_email,
            sender_email=sender_email,
            recipient=to_hdr,
            date=date_hdr,
            body=body,
            headers=headers,
            unsubscribe_type=unsub_type,
            unsubscribe_url=unsub_url,
            unsubscribe_mailto=unsub_mailto,
            is_read=False,
            is_starred=False,
        )
        classifier.classify(msg_obj)
        auditor.audit(msg_obj)
        self.save_email(msg_obj)
        return msg_obj

    def ingest_json(self, json_file_path: str | Path) -> list[EmailMessage]:
        """Ingest emails from a JSON array of message objects."""
        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)

        classifier = EmailClassifier()
        auditor = SecurityAuditor()
        messages: list[EmailMessage] = []

        for idx, item in enumerate(data, 1):
            unsub_hdr = item.get("headers", {}).get("List-Unsubscribe", "")
            unsub_post = item.get("headers", {}).get("List-Unsubscribe-Post", "")
            unsub_type, unsub_url, unsub_mailto = NewsletterCleaner.parse_unsubscribe_header(unsub_hdr, unsub_post)

            msg_obj = EmailMessage(
                id=item.get("id", f"msg_{idx:05d}"),
                message_id=item.get("message_id", f"id_{idx}"),
                thread_id=item.get("thread_id", f"thread_{idx}"),
                subject=item.get("subject", ""),
                sender_name=item.get("sender_name", ""),
                sender_email=item.get("sender_email", ""),
                recipient=item.get("recipient", "user@example.com"),
                date=item.get("date", ""),
                body=item.get("body", ""),
                headers=item.get("headers", {}),
                unsubscribe_type=unsub_type
                if unsub_type != UnsubscribeMechanism.NONE
                else UnsubscribeMechanism(item.get("unsubscribe_type", "NONE")),
                unsubscribe_url=unsub_url or item.get("unsubscribe_url", ""),
                unsubscribe_mailto=unsub_mailto or item.get("unsubscribe_mailto", ""),
                is_read=item.get("is_read", False),
                is_starred=item.get("is_starred", False),
            )
            classifier.classify(msg_obj)
            auditor.audit(msg_obj)
            messages.append(msg_obj)

        self.save_emails_batch(messages)
        return messages

    def ingest_csv(self, csv_file_path: str | Path) -> list[EmailMessage]:
        """Ingest emails from a standard CSV file."""
        classifier = EmailClassifier()
        auditor = SecurityAuditor()
        messages: list[EmailMessage] = []

        with open(csv_file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, 1):
                msg_obj = EmailMessage(
                    id=row.get("id", f"csv_{idx:05d}"),
                    message_id=row.get("message_id", f"msg_id_{idx}"),
                    thread_id=row.get("thread_id", f"thread_{idx}"),
                    subject=row.get("subject", ""),
                    sender_name=row.get("sender_name", ""),
                    sender_email=row.get("sender_email", ""),
                    recipient=row.get("recipient", "user@example.com"),
                    date=row.get("date", ""),
                    body=row.get("body", ""),
                    headers={},
                    is_read=row.get("is_read", "").lower() in ["true", "1", "yes"],
                    is_starred=row.get("is_starred", "").lower() in ["true", "1", "yes"],
                )
                classifier.classify(msg_obj)
                auditor.audit(msg_obj)
                messages.append(msg_obj)

        self.save_emails_batch(messages)
        return messages
