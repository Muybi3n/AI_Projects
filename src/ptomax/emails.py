# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Out-of-Office (OOO) email synthesizer tailored for clients, internal teams, and emergency boundaries.
"""

from typing import Any

from .models import WorkCoverage


class OooEmailGenerator:
    """Generates context-aware OOO emails with coverage delegation matrix integration."""

    @staticmethod
    def generate_ooo_email(
        start_date: str,
        end_date: str,
        style: str = "external",
        coverages: list[WorkCoverage] | None = None,
        return_buffer_day: bool = True,
    ) -> dict[str, Any]:
        """Synthesizes an Out-of-Office email template based on style and coverage delegates."""
        style_lower = style.lower().strip()
        cov_list = coverages or []

        # Build coverage delegation lines
        coverage_lines = []
        for c in cov_list:
            coverage_lines.append(
                f"• For {c.project_or_domain}: please contact {c.primary_cover_name} ({c.primary_cover_contact})"
            )

        coverage_text = (
            "\n".join(coverage_lines)
            if coverage_lines
            else "• For urgent matters: please reach out to my team lead or manager."
        )

        if style_lower == "external" or style_lower == "client":
            subject = f"Out of Office: {start_date} through {end_date}"
            body = (
                f"Hello,\n\n"
                f"Thank you for your message. I am currently out of the office on annual leave from {start_date} "
                f"through {end_date}, with limited access to email.\n\n"
                f"During my absence, the team is fully equipped to assist you:\n"
                f"{coverage_text}\n\n"
                f"I will be reviewing non-urgent inquiries upon my return. If your request is time-sensitive, "
                f"please contact the designated colleague listed above.\n\n"
                f"Best regards,\n"
                f"[Your Name]"
            )

        elif style_lower == "internal" or style_lower == "engineering":
            subject = f"[OOO] {start_date} to {end_date} (Coverage Mapped)"
            body = (
                f"Hi team,\n\n"
                f"I will be on PTO starting {start_date} and returning on {end_date}.\n\n"
                f"Project Handover & Coverage Matrix:\n"
                f"{coverage_text}\n\n"
                f"PRs and architectural reviews have been delegated. I will have Slack notifications muted "
                f"to fully recharge. If there is a true P0 production emergency, my primary covers know how to reach me.\n\n"
                f"Cheers,\n"
                f"[Your Name]"
            )

        elif style_lower == "urgent" or style_lower == "strict":
            subject = f"Out of Office (Offline) - Return: {end_date}"
            body = (
                f"Hello,\n\n"
                f"I am out of the office and completely offline from {start_date} to {end_date}.\n\n"
                f"Emails received during this period will not be forwarded. For immediate assistance:\n"
                f"{coverage_text}\n\n"
                f"Thank you for your understanding.\n\n"
                f"[Your Name]"
            )

        else:  # Witty / Conversational
            subject = f"Out of Office: Offline until {end_date} 🌴"
            body = (
                f"Hi there,\n\n"
                f"I am currently away from my keyboard on vacation from {start_date} until {end_date}.\n\n"
                f"I am deliberately disconnecting to recharge, but you are in great hands while I'm away:\n"
                f"{coverage_text}\n\n"
                f"I'll respond to your email shortly after I return on {end_date}.\n\n"
                f"Best,\n"
                f"[Your Name]"
            )

        buffer_tip = (
            "💡 Pro-Tip: Consider setting your calendar return date for external clients to 1 day later "
            "so you have an uninterrupted buffer morning to clear the inbox backlog."
        )

        return {
            "style": style_lower,
            "start_date": start_date,
            "end_date": end_date,
            "subject": subject,
            "body": body,
            "buffer_day_tip": buffer_tip,
        }
