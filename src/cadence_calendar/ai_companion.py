"""
Deterministic offline heuristic calendar advisor with pluggable LLM adapter.
NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from cadence_calendar.models import CompanionResponse, FatigueAuditResult


class CadenceCompanion:
    """Intelligent calendar strategy advisor operating offline deterministically or via pluggable LLMs."""

    def __init__(
        self,
        custom_llm_callable: Callable[[str, dict[str, Any]], str] | None = None,
    ):
        self.custom_llm_callable = custom_llm_callable

    def consult(
        self,
        query: str,
        audit_result: FatigueAuditResult,
        profile_data: dict[str, Any] | None = None,
    ) -> CompanionResponse:
        """Provide intelligent schedule and fatigue guidance."""
        context = self._build_context(audit_result, profile_data)

        if self.custom_llm_callable:
            raw = self.custom_llm_callable(query, context)
            try:
                data = json.loads(raw)
                return CompanionResponse(
                    query=query,
                    summary=str(data.get("summary", "")),
                    metrics_highlight=dict(data.get("metrics_highlight", {})),
                    recommendations=list(data.get("recommendations", [])),
                    action_items=list(data.get("action_items", [])),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return CompanionResponse(
                    query=query,
                    summary=raw,
                    metrics_highlight={"fatigue_score": audit_result.avg_daily_fatigue_score},
                    recommendations=audit_result.recommendations,
                    action_items=["Review customized AI output above and adjust calendar cadence."],
                )

        return self._heuristic_consult(query, context, audit_result)

    def _build_context(
        self,
        audit: FatigueAuditResult,
        profile_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Construct a privacy-sanitized structured context dict for reasoning."""
        return {
            "total_events": audit.total_events,
            "analyzed_days_count": audit.analyzed_days_count,
            "total_meeting_hours": audit.total_meeting_hours,
            "total_focus_hours": audit.total_focus_hours,
            "total_fragmented_hours": audit.total_fragmented_hours,
            "avg_daily_fatigue_score": audit.avg_daily_fatigue_score,
            "burnout_risk_level": audit.burnout_risk_level.value,
            "back_to_back_chains_count": audit.back_to_back_chains_count,
            "lunch_compromised_days_count": audit.lunch_compromised_days_count,
            "top_fatigue_days": audit.top_fatigue_days,
            "profile": profile_data or {},
        }

    def _heuristic_consult(
        self,
        query: str,
        context: dict[str, Any],
        audit: FatigueAuditResult,
    ) -> CompanionResponse:
        """Deterministic offline rule-based advisor answering natural-language queries."""
        q = query.lower()
        recommendations: list[str] = []
        action_items: list[str] = []
        summary_lines: list[str] = []

        metrics = {
            "avg_daily_fatigue_score": f"{audit.avg_daily_fatigue_score:.1f}/100",
            "burnout_risk_level": audit.burnout_risk_level.value,
            "total_meeting_hours": f"{audit.total_meeting_hours:.1f} hrs",
            "fragmented_time_lost": f"{audit.total_fragmented_hours:.1f} hrs",
            "back_to_back_chains": audit.back_to_back_chains_count,
        }

        # Intent 1: Fatigue / Burnout / Overload
        if any(w in q for w in ["fatigue", "burnout", "tired", "overload", "exhaust", "drain"]):
            summary_lines.append(
                f"Your current schedule exhibits a **{audit.burnout_risk_level.value}** fatigue profile "
                f"with an average daily strain score of **{audit.avg_daily_fatigue_score:.1f}/100**."
            )
            if audit.avg_daily_fatigue_score > 60:
                recommendations.append("🚨 **Cap Daily Meeting Hours:** Limit calendar commitments to max 3.5 hrs/day.")
                action_items.append("Audit recurring meetings and decline or delegate at least 2 non-essential syncs.")
            else:
                recommendations.append(
                    "✅ **Maintain Buffer Hygiene:** Meeting density is manageable; preserve 10m buffers."
                )
                action_items.append("Keep current meeting pacing stable.")

        # Intent 2: Buffers / Back-to-Back
        if any(w in q for w in ["buffer", "back to back", "back-to-back", "b2b", "transition", "breath"]):
            summary_lines.append(
                f"Identified **{audit.back_to_back_chains_count}** back-to-back meeting chains causing acute cognitive switching drag."
            )
            recommendations.append(
                "🛡️ **Enforce 25/50m Meeting Discipline:** Shorten 30m meetings to 25m and 60m meetings to 50m to guarantee 5-10m recovery."
            )
            action_items.append(
                "Run `cadence protect --buffer-minutes 10 --apply` to automatically reserve transition blocks."
            )

        # Intent 3: Focus Time / Deep Work / Flow
        if any(w in q for w in ["focus", "deep work", "coding", "flow", "uninterrupted"]):
            summary_lines.append(
                f"You currently have **{audit.total_focus_hours:.1f} hours** of protected focus slots across {audit.analyzed_days_count} days."
            )
            recommendations.append(
                "🚀 **Defend 2-Hour Focus Monoliths:** Protect uninterrupted morning blocks (09:00 - 11:30) for highest cognitive tasks."
            )
            action_items.append("Place proactive 'Deep Work (Do Not Book)' recurring blocks in calendar.")

        # Intent 4: Swiss Cheese / Fragmentation
        if any(w in q for w in ["swiss", "cheese", "fragment", "gaps", "scatter", "broken"]):
            summary_lines.append(
                f"Detected **{audit.total_fragmented_hours:.1f} hours** lost to unworkable 15-25m fragmented dead zones between scattered syncs."
            )
            recommendations.append(
                "🧀 **Swiss-Cheese Fragmentation Fix (Cluster & Batch):** Consolidate 1:1s and administrative check-ins into contiguous blocks (e.g. Tuesday afternoon)."
            )
            action_items.append("Move isolated 30-minute meetings adjacent to existing calendar commitments.")

        # Intent 5: Decline / Script / Negotiate
        if any(w in q for w in ["decline", "say no", "refuse", "script", "template", "politely"]):
            summary_lines.append("Here is an enterprise-tested, professional async delegation script:")
            recommendations.append(
                "💬 *'Thanks for the invite! I am heads-down delivering on [Key Deliverable] during this slot. Could you share the agenda/pre-read? I will review and add my input asynchronously via doc/Slack.'*"
            )
            action_items.append("Use async delegation for meetings lacking clear agendas or decision criteria.")

        # Intent 6: Friday / Focus Friday
        if any(w in q for w in ["friday", "weekend", "no meeting friday", "focus friday"]):
            summary_lines.append("Friday meeting loads severely impede weekly close-out and sprint velocity.")
            recommendations.append(
                "🎉 **Enforce Focus Friday:** Protect Friday afternoon from internal meetings to clear backlogs and prep for next week."
            )
            action_items.append("Declare 13:00 - 17:00 Friday as an org-wide or personal focus sanctuary.")

        # Default fallback if no specific keywords triggered
        if not summary_lines:
            summary_lines.append(
                f"Calendar Health Overview: Average daily fatigue is **{audit.avg_daily_fatigue_score:.1f}/100** ({audit.burnout_risk_level.value}). "
                f"Total meeting volume is **{audit.total_meeting_hours:.1f} hours** with **{audit.total_fragmented_hours:.1f} hours** in fragmented gaps."
            )
            recommendations.extend(audit.recommendations)
            action_items.append(
                "Run `cadence audit` to inspect daily breakdowns and `cadence protect` to inject recovery buffers."
            )

        return CompanionResponse(
            query=query,
            summary="\n\n".join(summary_lines),
            metrics_highlight=metrics,
            recommendations=recommendations,
            action_items=action_items,
        )
