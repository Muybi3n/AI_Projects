"""Heuristic prompt injection detector and threat evaluator.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import re
from typing import Any

from promptguard.models import (
    ActionVerdict,
    InjectionThreat,
    PromptScanResult,
    RiskTier,
)
from promptguard.sanitizer import PIISanitizer

# Pattern definitions for jailbreak, system prompt override, exfiltration, and delimiter escape
INJECTION_RULES: list[dict[str, Any]] = [
    {
        "category": "DIRECT_INSTRUCTION_OVERRIDE",
        "pattern": re.compile(
            r"(?i)\b(?:ignore|disregard|forget|bypass)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|commands|constraints)\b"
        ),
        "confidence": 0.95,
        "weight": 50,
        "description": "Attempt to purge or override prior context and foundational instructions.",
        "mitre_technique": "AML.T0051.000 - Direct Prompt Injection",
    },
    {
        "category": "ROLEPLAY_JAILBREAK",
        "pattern": re.compile(
            r"(?i)\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:DAN|unfiltered|jailbroken|an\s+adversary|a\s+hacker|an\s+evil\s+AI|godmode)\b"
        ),
        "confidence": 0.90,
        "weight": 45,
        "description": "Adversarial persona adoption intended to bypass alignment guardrails.",
        "mitre_technique": "AML.T0054 - LLM Jailbreak",
    },
    {
        "category": "SYSTEM_PROMPT_LEAK",
        "pattern": re.compile(
            r"(?i)\b(?:print|repeat|show|reveal|output|display|dump)\s+(?:the\s+)?(?:entire\s+)?(?:system\s+prompt|developer\s+message|initial\s+prompt|hidden\s+instructions)\b"
        ),
        "confidence": 0.90,
        "weight": 40,
        "description": "Attempt to extract confidential system instructions and underlying developer prompts.",
        "mitre_technique": "AML.T0024 - Exfiltration of Model Artifacts & System Prompt",
    },
    {
        "category": "DELIMITER_HIJACKING",
        "pattern": re.compile(
            r"(?i)(?:```(?:system|admin|root)|\[\s*SYSTEM\s*\]|<\|im_start\|>system|<\|system\|>|<<SYS>>|---\s*BEGIN\s+SYSTEM)"
        ),
        "confidence": 0.85,
        "weight": 35,
        "description": "Adversarial structural tags attempting delimiter confusion or privilege escalation.",
        "mitre_technique": "AML.T0051.001 - Delimiter Escapes",
    },
    {
        "category": "SECRET_EXFILTRATION_CALL",
        "pattern": re.compile(
            r"(?i)\b(?:send\s+(?:data\s+)?to|exfiltrate\s+(?:data\s+)?to|fetch|curl|wget|post\s+(?:data\s+)?to)\s+(?:https?://[a-zA-Z0-9_\-\.]+)\b"
        ),
        "confidence": 0.80,
        "weight": 30,
        "description": "Adversarial command directing the LLM to phone out data to external endpoints.",
        "mitre_technique": "AML.T0025 - Data Exfiltration via External Endpoint",
    },
    {
        "category": "BASE64_OBFUSCATION",
        "pattern": re.compile(r"\b(?:[A-Za-z0-9+/]{40,}={0,2})\b"),
        "confidence": 0.70,
        "weight": 20,
        "description": "High-entropy long base64 string suggesting obfuscated payload delivery.",
        "mitre_technique": "AML.T0015 - Obfuscated Payload Delivery",
    },
]


class InjectionDetector:
    """Multi-vector rule and heuristic engine detecting prompt injection attacks."""

    def __init__(self, block_threshold: int = 70):
        self.block_threshold = block_threshold
        self.rules = INJECTION_RULES
        self.sanitizer = PIISanitizer()

    def evaluate(self, text: str) -> PromptScanResult:
        """Evaluates input text against known injection patterns and PII rules."""
        sanitized_text, pii_matches = self.sanitizer.sanitize(text)

        threats: list[InjectionThreat] = []
        accumulated_score = 0
        reasons: list[str] = []

        # Analyze injection threat vectors
        for rule in self.rules:
            pattern: re.Pattern[str] = rule["pattern"]
            match = pattern.search(text)
            if match:
                threat = InjectionThreat(
                    category=rule["category"],
                    matched_pattern=match.group(0),
                    confidence=rule["confidence"],
                    description=rule["description"],
                    mitre_technique=rule["mitre_technique"],
                )
                threats.append(threat)
                accumulated_score += rule["weight"]
                reasons.append(f"[{threat.category}] {threat.description} (MITRE: {threat.mitre_technique})")

        # PII presence contributes modestly to overall security attention score
        if pii_matches:
            pii_points = min(len(pii_matches) * 10, 30)
            accumulated_score += pii_points
            reasons.append(f"Detected {len(pii_matches)} sensitive PII / secret token(s) requiring redaction.")

        total_risk_score = min(accumulated_score, 100)

        # Risk tiering
        if total_risk_score >= 80:
            risk_tier = RiskTier.CRITICAL
        elif total_risk_score >= 60:
            risk_tier = RiskTier.HIGH
        elif total_risk_score >= 35:
            risk_tier = RiskTier.MEDIUM
        elif total_risk_score > 0:
            risk_tier = RiskTier.LOW
        else:
            risk_tier = RiskTier.SAFE

        # Verdict calculation
        if total_risk_score >= self.block_threshold:
            verdict = ActionVerdict.BLOCK
        elif pii_matches or total_risk_score > 0:
            verdict = ActionVerdict.SANITIZE_AND_FORWARD
        else:
            verdict = ActionVerdict.ALLOW

        return PromptScanResult(
            original_text=text,
            sanitized_text=sanitized_text,
            verdict=verdict,
            risk_tier=risk_tier,
            risk_score=total_risk_score,
            pii_matches=pii_matches,
            threats=threats,
            reasons=reasons,
        )
