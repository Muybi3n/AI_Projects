"""Deterministic PII and sensitive secret sanitizer for prompts.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import re

from promptguard.models import PIIMatch

# Pre-compiled high-precision standard expressions for sensitive entities and secrets
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
        "[EMAIL_REDACTED]",
    ),
    (
        "PHONE",
        re.compile(r"\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b"),
        "[PHONE_REDACTED]",
    ),
    (
        "SSN",
        re.compile(r"\b(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b"),
        "[SSN_REDACTED]",
    ),
    (
        "CREDIT_CARD",
        re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b"
        ),
        "[CREDIT_CARD_REDACTED]",
    ),
    (
        "IPV4_PRIVATE",
        re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
        ),
        "[INTERNAL_IP_REDACTED]",
    ),
    (
        "AWS_KEY",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "[AWS_KEY_REDACTED]",
    ),
    (
        "GENERIC_API_KEY",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,80})['\"]?"
        ),
        "[SECRET_KEY_REDACTED]",
    ),
    (
        "BEARER_AUTH",
        re.compile(r"\bBearer\s+[a-zA-Z0-9_\-\.]{20,}\b"),
        "Bearer [TOKEN_REDACTED]",
    ),
    (
        "JWT_TOKEN",
        re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
        "[JWT_REDACTED]",
    ),
]


class PIISanitizer:
    """Zero-dependency deterministic PII and confidential token redaction engine."""

    def __init__(self, custom_rules: list[tuple[str, str, str]] | None = None):
        """Optionally register user-defined pattern rules: (entity_type, regex_pattern, token)."""
        self.rules: list[tuple[str, re.Pattern[str], str]] = list(PATTERNS)
        if custom_rules:
            for entity_type, pat_str, token in custom_rules:
                self.rules.append((entity_type, re.compile(pat_str), token))

    def sanitize(self, text: str) -> tuple[str, list[PIIMatch]]:
        """Sanitizes text, replacing sensitive matches with safe synthetic placeholders.

        Returns:
            Tuple of (sanitized_string, list_of_PIIMatch)
        """
        if not text:
            return "", []

        matches: list[PIIMatch] = []
        sanitized = text

        for entity_type, compiled_pattern, default_token in self.rules:
            # We iterate finding matches
            for found in compiled_pattern.finditer(sanitized):
                val = found.group(0)
                # Avoid re-redacting already redacted markers
                if val.startswith("[") and val.endswith("REDACTED]"):
                    continue

                token = default_token
                matches.append(
                    PIIMatch(
                        entity_type=entity_type,
                        original_value=val,
                        redacted_token=token,
                        start=found.start(),
                        end=found.end(),
                    )
                )

            # Perform substitution
            sanitized = compiled_pattern.sub(default_token, sanitized)

        return sanitized, matches

    def restore(self, sanitized_text: str, matches: list[PIIMatch]) -> str:
        """Restores original values into sanitized text (for reversible downstream response routing)."""
        restored = sanitized_text
        for match in matches:
            restored = restored.replace(match.redacted_token, match.original_value, 1)
        return restored
