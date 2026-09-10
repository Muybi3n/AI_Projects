# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Work coverage & handover delegation matrix engine.
"""

from .models import WorkCoverage


class CoverageMatrix:
    """Manages project delegation and pre-vacation handover checklists."""

    def __init__(self, coverages: list[WorkCoverage] | None = None) -> None:
        self.coverages = coverages or []

    def add_coverage(
        self,
        project_or_domain: str,
        primary_name: str,
        primary_contact: str,
        backup_name: str = "",
        backup_contact: str = "",
        escalation_threshold: str = "P0 production outages only",
        notes: str = "",
    ) -> WorkCoverage:
        cov_id = f"cov-{len(self.coverages) + 1:02d}"
        cov = WorkCoverage(
            id=cov_id,
            project_or_domain=project_or_domain,
            primary_cover_name=primary_name,
            primary_cover_contact=primary_contact,
            backup_cover_name=backup_name,
            backup_cover_contact=backup_contact,
            escalation_threshold=escalation_threshold,
            notes=notes,
        )
        self.coverages.append(cov)
        return cov

    def mark_handover_ready(self, cov_id: str, ready: bool = True) -> bool:
        for c in self.coverages:
            if c.id == cov_id or c.project_or_domain.lower() == cov_id.lower():
                c.handover_checklist_done = ready
                return True
        return False

    def generate_handover_brief(self) -> str:
        """Synthesizes a 1-page structured handover summary for the team."""
        lines = [
            "===========================================================================",
            "                  PRE-VACATION WORK HANDOVER MATRIX                        ",
            "===========================================================================",
        ]
        if not self.coverages:
            lines.append("  No active project coverage delegates configured.")
            lines.append("  Use 'ptomax coverage add' to delegate project responsibilities.")
        else:
            for c in self.coverages:
                status_icon = "✔ READY" if c.handover_checklist_done else "⏳ PENDING REVIEW"
                lines.append(f"  • Domain/Project : {c.project_or_domain} [{status_icon}]")
                lines.append(
                    f"    Primary Cover  : {c.primary_cover_name} ({c.primary_cover_contact})"
                )
                if c.backup_cover_name:
                    lines.append(
                        f"    Backup Cover   : {c.backup_cover_name} ({c.backup_cover_contact})"
                    )
                lines.append(f"    Escalation Rule: {c.escalation_threshold}")
                if c.notes:
                    lines.append(f"    Handover Notes : {c.notes}")
                lines.append(
                    "───────────────────────────────────────────────────────────────────────────"
                )
        lines.append("===========================================================================")
        return "\n".join(lines)
