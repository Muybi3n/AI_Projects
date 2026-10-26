"""Pluggable AI Security Advisor for PromptGuard.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from promptguard.models import PromptScanResult


@dataclass
class AdvisorResponse:
    """Security advisory output for prompt analysis or configuration questions."""

    query: str
    recommendation: str
    mitigation_steps: list[str] = field(default_factory=list)
    risk_assessment: str = "SAFE"
    confidence: float = 0.95

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "recommendation": self.recommendation,
            "mitigation_steps": self.mitigation_steps,
            "risk_assessment": self.risk_assessment,
            "confidence": self.confidence,
        }


def build_context(stats: dict[str, Any], last_scan: PromptScanResult | None = None) -> dict[str, Any]:
    """Extracts non-sensitive metadata for LLM ingestion."""
    ctx: dict[str, Any] = {
        "proxy_mode": "reverse_proxy",
        "total_requests": stats.get("total_requests", 0),
        "blocked_count": stats.get("blocked", 0),
        "sanitized_count": stats.get("sanitized", 0),
        "allowed_count": stats.get("allowed", 0),
    }
    if last_scan:
        ctx["last_scan_risk_score"] = last_scan.risk_score
        ctx["last_scan_verdict"] = last_scan.verdict.value
        ctx["threat_categories"] = [t.category for t in last_scan.threats]
        ctx["pii_redacted_count"] = len(last_scan.pii_matches)
    return ctx


class SecurityAdvisor:
    """Deterministic security advisor with pluggable local/remote LLM support."""

    def __init__(self, custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None):
        self.custom_llm_callable = custom_llm_callable

    def consult(
        self,
        query: str,
        stats: dict[str, Any],
        last_scan: PromptScanResult | None = None,
    ) -> AdvisorResponse:
        """Advises on threat mitigations, policy tuning, or prompt safety."""
        context = build_context(stats, last_scan)

        if self.custom_llm_callable:
            raw = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw)
                return AdvisorResponse(
                    query=query,
                    recommendation=data.get("recommendation", raw),
                    mitigation_steps=data.get("mitigation_steps", []),
                    risk_assessment=data.get("risk_assessment", "UNKNOWN"),
                    confidence=data.get("confidence", 0.90),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return AdvisorResponse(
                    query=query,
                    recommendation=raw,
                    mitigation_steps=["Review local audit ledger for anomalies."],
                    risk_assessment="CUSTOM_LLM",
                )

        return self._heuristic_consult(query, context)

    def _heuristic_consult(self, query: str, context: dict[str, Any]) -> AdvisorResponse:
        """Rule-based security response covering key LLM threat categories."""
        q = query.lower()

        # Check for injection defense queries
        if any(w in q for w in ["injection", "jailbreak", "override", "bypass"]):
            return AdvisorResponse(
                query=query,
                recommendation="Enforce strict structural separation of user input from system instructions and maintain low temperature settings.",
                mitigation_steps=[
                    "Isolate user prompts using deterministic XML/Markdown delimiters.",
                    "Set block_threshold to 60 or below for sensitive production pipelines.",
                    "Implement second-pass verification for high-impact actions (API executions, file writes).",
                    "Audit proxy logs regularly for recurring attack signatures.",
                ],
                risk_assessment="HIGH_ATTENTION",
                confidence=0.98,
            )

        # Check for PII / privacy leakage queries
        if any(w in q for w in ["pii", "privacy", "leak", "secret", "token", "ssn", "credit card"]):
            return AdvisorResponse(
                query=query,
                recommendation="Activate zero-trust client-side scrubbing for all outgoing prompts before transmission to 3rd-party models.",
                mitigation_steps=[
                    "Ensure enable_pii_redaction=True in PromptGuard configuration.",
                    "Verify regex patterns capture internal IP ranges and corporate API key formats.",
                    "Utilize reversible pseudonymization tokens if downstream model must preserve syntactic structure.",
                    "Conduct regular audits on ~/.promptguard/audit.jsonl to verify zero unredacted PII.",
                ],
                risk_assessment="CONFIDENTIALITY_CRITICAL",
                confidence=0.95,
            )

        # Audit / metrics questions
        if any(w in q for w in ["audit", "stats", "history", "blocked", "metrics"]):
            blocked = context.get("blocked_count", 0)
            total = context.get("total_requests", 0)
            return AdvisorResponse(
                query=query,
                recommendation=f"System has evaluated {total} request(s), intercepting and blocking {blocked} potential attack(s).",
                mitigation_steps=[
                    "Run 'promptguard audit' to inspect recent event details.",
                    "Export metrics for SIEM ingestion via JSONL parsing.",
                    "Tune false positive ratios by reviewing borderline requests (scores 50-69).",
                ],
                risk_assessment="OPERATIONAL_STATUS",
                confidence=0.99,
            )

        # Default fallback guidance
        return AdvisorResponse(
            query=query,
            recommendation="PromptGuard Proxy acts as a defensive shield between client applications and LLMs, filtering PII and neutralizing prompt injections.",
            mitigation_steps=[
                "Point your client's OpenAI base URL to http://127.0.0.1:8088/v1.",
                "Run 'promptguard scan <text>' to test prompt payloads interactively.",
                "Consult 'promptguard stats' to review proxy operational efficacy.",
            ],
            risk_assessment="STANDARD_BASELINE",
            confidence=0.90,
        )
