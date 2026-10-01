"""
Pluggable AI SOC Triage Advisor: Heuristic reasoner with offline deterministic mode and LLM adapter.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .models import CorrelatedIncident


class SocmeshAIAdvisor:
    """Security Copilot providing automated triage briefs and remediation guidance."""

    def __init__(self, custom_llm_callable: Callable[[str], str] | None = None) -> None:
        self.custom_llm = custom_llm_callable

    def answer_query(self, query: str, incidents: Sequence[CorrelatedIncident]) -> str:
        """Answers user inquiries regarding security posture and active incidents."""
        if self.custom_llm:
            prompt = f"User Question: {query}\nActive Incidents: {[i.to_dict() for i in incidents]}"
            return self.custom_llm(prompt)

        q_lower = query.lower()

        if "critical" in q_lower or "urgent" in q_lower or "high" in q_lower:
            high_risk = [i for i in incidents if i.risk_score >= 70]
            if not high_risk:
                return (
                    "✅ No high or critical severity incidents detected across monitored endpoints."
                )
            lines = [f"🚨 **{len(high_risk)} Critical/High Security Incidents Active:**"]
            for inc in high_risk:
                lines.append(
                    f"- **{inc.title}** (Risk Score: {inc.risk_score}/100, Tactic: {inc.primary_tactic.value})"
                )
                lines.append(f"  *Summary:* {inc.summary}")
                lines.append(
                    f"  *Top Action:* {inc.remediation_guidance[0] if inc.remediation_guidance else 'Inspect logs.'}"
                )
            return "\n".join(lines)

        if "remediate" in q_lower or "fix" in q_lower or "action" in q_lower:
            if not incidents:
                return "✅ All clear. No active remediation actions required."
            lines = ["🛠️ **Recommended Triage & Containment Actions:**"]
            for inc in incidents:
                lines.append(f"**[{inc.incident_id}] {inc.title}:**")
                for step in inc.remediation_guidance:
                    lines.append(f"  • {step}")
            return "\n".join(lines)

        if "mitre" in q_lower or "tactic" in q_lower:
            tactics = {i.primary_tactic.value for i in incidents}
            if not tactics:
                return "✅ No active MITRE ATT&CK adversary tactics observed."
            return "🛡️ **Observed MITRE ATT&CK Tactics:**\n" + "\n".join(
                f"- {t}" for t in sorted(tactics)
            )

        # Default overview
        total = len(incidents)
        max_score = max((i.risk_score for i in incidents), default=0)
        return (
            f"📊 **Mini-SOC Status Briefing:**\n"
            f"- Total Correlated Incidents: **{total}**\n"
            f"- Maximum Threat Risk Score: **{max_score}/100**\n"
            f"- System Health: **{'DEFENSIVE TRIAGE REQUIRED' if max_score >= 70 else 'NORMAL OBSERVABILITY'}**\n"
            f"Run `socmesh correlate` or `socmesh ask 'remediate'` for tactical step-by-step guidance."
        )
