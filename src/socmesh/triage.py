"""
Alert Triage Governor and Noise Reduction Engine.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from .models import SecurityEvent, SeverityLevel


class AlertTriageGovernor:
    """Filters routine homelab background noise and suppresses false-positive storms."""

    BENIGN_DOMAINS: ClassVar[set[str]] = {
        "pool.ntp.org",
        "time.cloudflare.com",
        "archive.ubuntu.com",
        "pypi.org",
        "github.com",
        "docker.com",
        "ghcr.io",
        "dns.google",
    }

    BENIGN_SUDO_COMMANDS: ClassVar[set[str]] = {
        "/bin/systemctl status",
        "/usr/bin/uptime",
        "/usr/bin/apt update",
        "/usr/bin/docker ps",
    }

    def __init__(self, custom_whitelist: set[str] | None = None) -> None:
        self.whitelist = set(self.BENIGN_DOMAINS)
        if custom_whitelist:
            self.whitelist.update(custom_whitelist)

    def is_noise(self, event: SecurityEvent) -> bool:
        """Determines if a security event is routine background telemetry."""
        # Benign DNS queries
        if (
            event.domain
            and any(event.domain.endswith(d) or event.domain == d for d in self.whitelist)
            and event.severity == SeverityLevel.INFORMATIONAL
        ):
            return True

        # Benign routine sudo checks
        return event.action == "SUDO_EXEC" and any(
            cmd in event.details for cmd in self.BENIGN_SUDO_COMMANDS
        )

    def filter_noise(
        self, events: Sequence[SecurityEvent]
    ) -> tuple[list[SecurityEvent], list[SecurityEvent]]:
        """Splits events into (actionable_events, suppressed_noise)."""
        actionable: list[SecurityEvent] = []
        noise: list[SecurityEvent] = []

        for ev in events:
            if self.is_noise(ev):
                noise.append(ev)
            else:
                actionable.append(ev)

        return actionable, noise
