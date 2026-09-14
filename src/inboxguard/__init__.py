"""inboxguard-core: Local-first email triage, 5-tier classification, newsletter cleaner, and security filter engine.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

from inboxguard.ai_companion import InboxCompanion
from inboxguard.classifier import EmailClassifier
from inboxguard.models import EmailMessage, EmailTier, FilterRule, SecurityAssessment, SecurityRiskLevel, SenderProfile
from inboxguard.newsletter import NewsletterCleaner
from inboxguard.rules_exporter import RulesExporter
from inboxguard.security import SecurityAuditor
from inboxguard.storage import StorageEngine

__version__ = "0.1.0"

__all__ = [
    "EmailClassifier",
    "EmailMessage",
    "EmailTier",
    "FilterRule",
    "InboxCompanion",
    "NewsletterCleaner",
    "RulesExporter",
    "SecurityAssessment",
    "SecurityAuditor",
    "SecurityRiskLevel",
    "SenderProfile",
    "StorageEngine",
    "__version__",
]
