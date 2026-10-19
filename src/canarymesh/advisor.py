# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh AI companion: Deterministic honeynet advisor with pluggable local LLM (Ollama/vLLM) support."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from canarymesh.models import DecoyArtifact, TripwireAlert


@dataclass
class AdvisorResponse:
    query: str
    recommendations: list[str]
    threat_assessment: str
    suggested_actions: list[str]
    mitre_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "threat_assessment": self.threat_assessment,
            "recommendations": self.recommendations,
            "suggested_actions": self.suggested_actions,
            "mitre_references": self.mitre_references,
        }


def build_sanitized_fleet_context(decoys: list[DecoyArtifact], alerts: list[TripwireAlert]) -> dict[str, Any]:
    """Sanitizes sensitive file paths and identifiers into an anonymous context payload for AI reasoning."""
    categories: dict[str, int] = {}
    for d in decoys:
        cat = d.category.value
        categories[cat] = categories.get(cat, 0) + 1

    alert_summary: list[dict[str, Any]] = []
    for a in alerts[-10:]:  # last 10 alerts
        alert_summary.append(
            {
                "trigger_type": a.trigger_type.value,
                "severity": a.severity.value,
                "detected_at": a.detected_at,
                "mitre_technique": a.mitre_technique,
            }
        )

    return {
        "total_active_decoys": len([d for d in decoys if d.is_active]),
        "decoy_categories": categories,
        "total_alerts": len(alerts),
        "recent_alerts": alert_summary,
    }


class CanaryMeshAdvisor:
    """Security Advisor for evaluating decoy coverage, tripwire alerts, and deception defense posture."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(
        self,
        query: str,
        decoys: list[DecoyArtifact],
        alerts: list[TripwireAlert],
    ) -> AdvisorResponse:
        context = build_sanitized_fleet_context(decoys, alerts)

        if self.custom_llm_callable:
            raw = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw)
                return AdvisorResponse(
                    query=query,
                    threat_assessment=data.get("threat_assessment", "LLM-generated threat assessment"),
                    recommendations=data.get("recommendations", []),
                    suggested_actions=data.get("suggested_actions", []),
                    mitre_references=data.get("mitre_references", []),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return AdvisorResponse(
                    query=query,
                    threat_assessment=raw.strip(),
                    recommendations=["Refer to detailed assessment above"],
                    suggested_actions=["Review raw alerts in ~/.canarymesh/alerts.json"],
                )

        return self._heuristic_consult(query, context, alerts)

    def _heuristic_consult(
        self,
        query: str,
        context: dict[str, Any],
        alerts: list[TripwireAlert],
    ) -> AdvisorResponse:
        q = query.lower()
        recommendations: list[str] = []
        actions: list[str] = []
        mitre: list[str] = []

        # Check breach or active alerts
        critical_alerts = [a for a in alerts if a.severity.value in ("CRITICAL", "HIGH")]

        if critical_alerts:
            assessment = (
                f"HIGH ALERT: Detected {len(critical_alerts)} critical/high tripwire incidents! "
                "Canary decoy files have been modified, removed, or detonated."
            )
            recommendations.append("Assume immediate host compromise or insider unauthorized discovery.")
            recommendations.append("Isolate affected subnets or workstations from the core network.")
            actions.append("Execute containment protocol: freeze suspicious processes and preserve forensic logs.")
            actions.append("Rotate all production credentials and API keys in the affected environment.")
            mitre.extend(["T1552 - Unsecured Credentials", "T1070 - Indicator Removal", "T1078 - Valid Accounts"])
        elif context["total_active_decoys"] == 0:
            assessment = "DEFENSE GAP: No active decoy tripwires are deployed in the fleet."
            recommendations.append(
                "Deploy high-value bait files in common reconnaissance paths (~/.aws/, ~/.ssh/, git repos)."
            )
            recommendations.append("Cover multiple categories: AWS keys, SSH backup keys, and .env secrets.")
            actions.append("Run `canarymesh deploy --category aws_credentials` to arm initial tripwire.")
            actions.append("Run `canarymesh demo` to inspect an end-to-end multi-layer deception scenario.")
            mitre.append("M1047 - Deception Environment")
        elif context["total_active_decoys"] < 3:
            assessment = "PARTIAL COVERAGE: Few decoy artifacts deployed. Recommend defense-in-depth placement."
            recommendations.append(
                "Add database configuration and sensitive document honey-tokens to catch varied adversary behaviors."
            )
            actions.append("Deploy complementary bait in developer workspaces and backup mount points.")
            mitre.append("M1047 - Deception Environment")
        else:
            assessment = f"HEALTHY DECEPTION POSTURE: {context['total_active_decoys']} active tripwires armed with zero critical alerts."
            recommendations.append("Maintain recurring audit cadence via cron (`canarymesh audit`).")
            recommendations.append(
                "Verify decoy file permissions (0600) to ensure legitimate users are not falsely alerted."
            )
            actions.append("Perform scheduled quarterly canary detonation exercises to test SOC escalation paths.")

        # Intent handling for specific queries
        if any(w in q for w in ["mitre", "technique", "att&ck"]):
            mitre.extend(["T1083 - File & Directory Discovery", "T1552.001 - Credentials in Files"])
            recommendations.append("Map your tripwire triggers to SIEM/Wazuh alert rules.")

        if any(w in q for w in ["audit", "schedule", "cron"]):
            actions.append("Configure a cron job: `*/15 * * * * canarymesh audit --quiet`")

        return AdvisorResponse(
            query=query,
            threat_assessment=assessment,
            recommendations=list(dict.fromkeys(recommendations)),
            suggested_actions=list(dict.fromkeys(actions)),
            mitre_references=list(dict.fromkeys(mitre)),
        )
