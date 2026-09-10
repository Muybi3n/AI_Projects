# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
5-Layer Structured Insight Distillation Engine.
"""

import re
from typing import Any

from .models import DistillationArtifact, Episode

DISTILLATION_PROMPT_TEMPLATE = """
You are an expert knowledge engineer. Distill the following podcast/lecture transcript into a structured 5-layer knowledge artifact.

Transcript:
\"\"\"
{transcript}
\"\"\"

Output strictly in valid JSON matching this schema:
{{
  "thesis": "<1-2 sentence core thesis and executive context>",
  "quotes": ["<unabridged key quote 1>", "<unabridged key quote 2>"],
  "mental_models": ["<first principle or scientific model 1>", "<model 2>"],
  "moral_philosophy": "<underlying moral/philosophical takeaway>",
  "micro_habits": ["<actionable daily micro-habit 1>", "<actionable daily micro-habit 2>"],
  "tags": ["<tag1>", "<tag2>"]
}}
"""


class InsightDistiller:
    """Extracts high-EQ, multi-layered structured insights from transcripts."""

    def distill(self, episode: Episode, custom_extractor: Any = None) -> DistillationArtifact:
        """
        Distill an episode into a 5-layer artifact.
        Uses custom_extractor if provided, otherwise applies the built-in rule-based extractor.
        """
        transcript = episode.raw_transcript.strip()
        if not transcript:
            return DistillationArtifact(
                thesis="Empty transcript provided.",
                moral_philosophy="No content to analyze."
            )

        if custom_extractor and callable(custom_extractor):
            extracted_dict = custom_extractor(transcript)
            return DistillationArtifact.from_dict(extracted_dict)

        return self._heuristic_distill(episode)

    def _heuristic_distill(self, episode: Episode) -> DistillationArtifact:
        """
        Built-in offline heuristic extractor.
        Extracts key sentences, quotes, principles, and action verbs.
        """
        text = episode.raw_transcript
        sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15
        ]

        # 1. Thesis
        thesis = sentences[0] if sentences else f"Discussion on {episode.title}"
        if len(sentences) > 1 and len(thesis) < 40:
            thesis += " " + sentences[1]

        # 2. Quotes (look for quoted text or emphatic statements)
        quotes = re.findall(r'"([^"]{15,200})"', text)
        if not quotes:
            # Pick strong emphatic sentences
            quotes = [
                s for s in sentences
                if any(w in s.lower() for w in ["always", "never", "must", "the truth is", "key is"])
            ][:3]
        if not quotes and sentences:
            quotes = sentences[:2]

        # 3. Mental Models
        model_keywords = [
            "first principles", "compounding", "feedback loop", "entropy",
            "inversion", "pareto", "leverage", "asymmetry", "incentives", "systems"
        ]
        mental_models = []
        for kw in model_keywords:
            if kw in text.lower():
                mental_models.append(kw.title())
        if not mental_models:
            mental_models = ["Progressive Adaptation", "First-Order Thinking"]

        # 4. Moral & Philosophy
        moral_sentences = [
            s for s in sentences
            if any(w in s.lower() for w in ["meaning", "purpose", "lesson", "character", "life", "wisdom"])
        ]
        moral = moral_sentences[0] if moral_sentences else "Consistency and deliberate effort compound over time into mastery."

        # 5. Micro-Habits (sentences with imperative verbs)
        action_verbs = ["start", "track", "write", "focus", "eliminate", "build", "practice", "review"]
        micro_habits = []
        for s in sentences:
            first_word = s.split()[0].lower() if s.split() else ""
            if first_word in action_verbs or any(phrase in s.lower() for phrase in ["daily", "every day", "habit"]):
                micro_habits.append(s)
                if len(micro_habits) >= 3:
                    break

        if not micro_habits:
            micro_habits = [
                f"Schedule 15 minutes daily to review and apply principles from '{episode.title}'.",
                "Track incremental progress weekly to verify compounding gains."
            ]

        # Tags
        tags = [w.lower() for w in episode.title.split() if len(w) > 4][:4]
        if not tags:
            tags = ["mindset", "productivity"]

        return DistillationArtifact(
            thesis=thesis,
            quotes=quotes[:3],
            mental_models=mental_models[:4],
            moral_philosophy=moral,
            micro_habits=micro_habits[:3],
            tags=tags,
        )
