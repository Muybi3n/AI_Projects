"""Tests for PII sanitization and restoration."""

from promptguard.sanitizer import PIISanitizer


def test_pii_sanitizer_redaction():
    sanitizer = PIISanitizer()
    text = (
        "User contact is user@example.com, phone is 555-123-4567, SSN 123-45-6789. "
        "Server is 10.0.0.5 with AWS key AKIAIOSFODNN7EXAMPLE."
    )
    sanitized, matches = sanitizer.sanitize(text)

    assert "user@example.com" not in sanitized
    assert "[EMAIL_REDACTED]" in sanitized
    assert "555-123-4567" not in sanitized
    assert "[PHONE_REDACTED]" in sanitized
    assert "123-45-6789" not in sanitized
    assert "[SSN_REDACTED]" in sanitized
    assert "10.0.0.5" not in sanitized
    assert "[INTERNAL_IP_REDACTED]" in sanitized
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "[AWS_KEY_REDACTED]" in sanitized
    assert len(matches) >= 5


def test_pii_sanitizer_empty_and_reversibility():
    sanitizer = PIISanitizer()
    assert sanitizer.sanitize("") == ("", [])

    original = "Ping me at dev@example.com."
    sanitized, matches = sanitizer.sanitize(original)
    restored = sanitizer.restore(sanitized, matches)
    assert restored == original


def test_pii_custom_rule():
    custom = [("PROJECT_CODENAME", r"Project\s+Hydra", "[PROJECT_REDACTED]")]
    sanitizer = PIISanitizer(custom_rules=custom)
    text = "We are shipping Project Hydra tomorrow."
    sanitized, matches = sanitizer.sanitize(text)
    assert "[PROJECT_REDACTED]" in sanitized
    assert matches[0].entity_type == "PROJECT_CODENAME"
