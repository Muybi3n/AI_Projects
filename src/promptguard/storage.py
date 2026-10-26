"""Local file-based audit logger and storage for PromptGuard.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import json
from pathlib import Path
from typing import Any

from promptguard.models import AuditLogEntry


class AuditStorage:
    """Zero-dependency JSONL audit repository."""

    def __init__(self, data_dir: str | Path | None = None):
        if data_dir is None:
            self.base_dir = Path.home() / ".promptguard"
        else:
            self.base_dir = Path(data_dir)

        self.log_file = self.base_dir / "audit.jsonl"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.touch(mode=0o600)

    def append(self, entry: AuditLogEntry) -> None:
        """Appends an audit record to the persistent JSONL ledger."""
        data_line = json.dumps(entry.to_dict())
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(data_line + "\n")

    def load_all(self, limit: int = 100) -> list[AuditLogEntry]:
        """Loads historical audit records up to limit, newest last."""
        if not self.log_file.exists():
            return []

        entries: list[AuditLogEntry] = []
        try:
            with open(self.log_file, encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    line = line.strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                    entries.append(
                        AuditLogEntry(
                            request_id=payload["request_id"],
                            timestamp=payload["timestamp"],
                            client_ip=payload["client_ip"],
                            upstream_url=payload["upstream_url"],
                            verdict=payload["verdict"],
                            risk_tier=payload["risk_tier"],
                            risk_score=payload["risk_score"],
                            pii_count=payload["pii_count"],
                            threat_count=payload["threat_count"],
                            reasons=payload.get("reasons", []),
                            sanitized_preview=payload.get("sanitized_preview", ""),
                        )
                    )
        except (OSError, json.JSONDecodeError, KeyError):
            return []

        return entries

    def get_summary_stats(self) -> dict[str, Any]:
        """Aggregates security metrics across historical transactions."""
        entries = self.load_all(limit=1000)
        total_requests = len(entries)
        blocked = sum(1 for e in entries if e.verdict == "BLOCK")
        sanitized = sum(1 for e in entries if e.verdict == "SANITIZE_AND_FORWARD")
        allowed = sum(1 for e in entries if e.verdict == "ALLOW")
        total_pii = sum(e.pii_count for e in entries)
        total_threats = sum(e.threat_count for e in entries)

        return {
            "total_requests": total_requests,
            "blocked": blocked,
            "sanitized": sanitized,
            "allowed": allowed,
            "total_pii_redactions": total_pii,
            "total_threats_neutralized": total_threats,
        }

    def clear(self) -> None:
        """Truncates the audit log."""
        if self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.truncate(0)
