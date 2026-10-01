"""
Telemetry normalizer for Wazuh HIDS, Pi-hole DNS sinkholes, and Linux auth logs.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .models import EventSource, SecurityEvent, SeverityLevel


class TelemetryNormalizer:
    """Normalizes disparate homelab and mini-SOC log formats into structured SecurityEvents."""

    def __init__(self) -> None:
        pass

    def parse_pihole_log_line(self, line: str) -> SecurityEvent | None:
        """Parses a standard Pi-hole dnsmasq/FTL log line."""
        line = line.strip()
        if not line:
            return None

        # Example: Sep 28 09:15:22 dnsmasq[1234]: query[A] evil-c2.example.com from 192.168.1.100
        # Example: Sep 28 09:15:22 dnsmasq[1234]: gravity blocked evil-c2.example.com is 0.0.0.0
        # Example: Sep 28 09:15:22 dnsmasq[1234]: reply evil-c2.example.com is 192.0.2.1
        pihole_query_pattern = r"(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d+:\d+:\d+).*?query\[(?P<qtype>\w+)\]\s+(?P<domain>[^\s]+)\s+from\s+(?P<srcip>[^\s]+)"
        pihole_block_pattern = r"(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d+:\d+:\d+).*?gravity blocked\s+(?P<domain>[^\s]+)\s+is\s+(?P<dstip>[^\s]+)"

        event_id = hashlib.blake2b(line.encode("utf-8"), digest_size=12).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()

        m_q = re.search(pihole_query_pattern, line)
        if m_q:
            domain = m_q.group("domain")
            src_ip = m_q.group("srcip")
            severity = SeverityLevel.INFORMATIONAL
            if any(
                term in domain.lower()
                for term in ["c2", "beacon", "malware", "phish", "tor", "onion"]
            ):
                severity = SeverityLevel.MEDIUM

            return SecurityEvent(
                event_id=f"pihole-{event_id}",
                source=EventSource.PIHOLE_DNS,
                timestamp=now_iso,
                source_ip=src_ip,
                destination_ip="127.0.0.1",
                severity=severity,
                action="DNS_QUERY",
                event_type="dns_query",
                details=f"DNS query for {domain} (Type: {m_q.group('qtype')})",
                domain=domain,
                tags=["dns", "pihole", "query"],
            )

        m_b = re.search(pihole_block_pattern, line)
        if m_b:
            domain = m_b.group("domain")
            return SecurityEvent(
                event_id=f"pihole-{event_id}",
                source=EventSource.PIHOLE_DNS,
                timestamp=now_iso,
                source_ip="192.168.1.1",
                destination_ip=m_b.group("dstip"),
                severity=SeverityLevel.HIGH,
                action="GRAVITY_BLOCKED",
                event_type="dns_sinkhole",
                details=f"Gravity sinkhole blocked domain: {domain}",
                domain=domain,
                tags=["dns", "pihole", "blocked", "sinkhole"],
            )

        return None

    def parse_linux_auth_line(self, line: str) -> SecurityEvent | None:
        """Parses a Linux auth.log or secure log line."""
        line = line.strip()
        if not line:
            return None

        # Example: Sep 28 09:20:11 ubuntu-server sshd[5432]: Failed password for invalid user admin from 192.0.2.45 port 51234 ssh2
        # Example: Sep 28 09:22:00 ubuntu-server sshd[5432]: Accepted publickey for soju from 192.168.1.50 port 51234 ssh2
        # Example: Sep 28 09:25:00 ubuntu-server sudo:     soju : TTY=pts/0 ; PWD=/home/soju ; USER=root ; COMMAND=/bin/bash
        event_id = hashlib.blake2b(line.encode("utf-8"), digest_size=12).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()

        if "Failed password" in line:
            ip_match = re.search(r"from\s+(?P<ip>[0-9a-fA-F.:]+)", line)
            user_match = re.search(r"for\s+(?:invalid user\s+)?(?P<user>[^\s]+)", line)
            src_ip = ip_match.group("ip") if ip_match else "127.0.0.1"
            user = user_match.group("user") if user_match else "unknown"

            return SecurityEvent(
                event_id=f"auth-{event_id}",
                source=EventSource.LINUX_AUTH,
                timestamp=now_iso,
                source_ip=src_ip,
                destination_ip="127.0.0.1",
                severity=SeverityLevel.MEDIUM,
                action="FAILED_AUTH",
                event_type="ssh_login_failure",
                details=f"Failed SSH authentication for user '{user}' from {src_ip}",
                user=user,
                tags=["ssh", "auth", "failed_login"],
            )

        if "Accepted publickey" in line or "Accepted password" in line:
            ip_match = re.search(r"from\s+(?P<ip>[0-9a-fA-F.:]+)", line)
            user_match = re.search(r"for\s+(?P<user>[^\s]+)", line)
            src_ip = ip_match.group("ip") if ip_match else "127.0.0.1"
            user = user_match.group("user") if user_match else "root"

            return SecurityEvent(
                event_id=f"auth-{event_id}",
                source=EventSource.LINUX_AUTH,
                timestamp=now_iso,
                source_ip=src_ip,
                destination_ip="127.0.0.1",
                severity=SeverityLevel.LOW,
                action="ACCEPTED_AUTH",
                event_type="ssh_login_success",
                details=f"Successful SSH login for user '{user}' from {src_ip}",
                user=user,
                tags=["ssh", "auth", "success"],
            )

        if "COMMAND=" in line and "sudo:" in line:
            user_match = re.search(r"sudo:\s+(?P<user>[^\s]+)", line)
            cmd_match = re.search(r"COMMAND=(?P<cmd>.*)", line)
            user = user_match.group("user") if user_match else "root"
            cmd = cmd_match.group("cmd") if cmd_match else "unknown"

            return SecurityEvent(
                event_id=f"sudo-{event_id}",
                source=EventSource.LINUX_AUTH,
                timestamp=now_iso,
                source_ip="127.0.0.1",
                destination_ip="127.0.0.1",
                severity=SeverityLevel.LOW,
                action="SUDO_EXEC",
                event_type="privilege_escalation",
                details=f"Sudo command executed by {user}: {cmd}",
                user=user,
                tags=["sudo", "auth", "exec"],
            )

        return None

    def parse_wazuh_json_event(self, record: dict[str, Any]) -> SecurityEvent:
        """Parses a structured Wazuh HIDS alert record."""
        rule = record.get("rule", {})
        rule_level = rule.get("level", 3)
        rule_id = str(rule.get("id", "0"))
        description = rule.get("description", "Wazuh Alert")

        data = record.get("data", {})
        src_ip = data.get("srcip") or record.get("agent", {}).get("ip") or "127.0.0.1"
        dst_ip = data.get("dstip") or "127.0.0.1"
        user = data.get("dstuser") or data.get("srcuser") or "root"
        timestamp = record.get("timestamp") or datetime.now(timezone.utc).isoformat()

        if rule_level >= 12:
            severity = SeverityLevel.CRITICAL
        elif rule_level >= 8:
            severity = SeverityLevel.HIGH
        elif rule_level >= 5:
            severity = SeverityLevel.MEDIUM
        elif rule_level >= 3:
            severity = SeverityLevel.LOW
        else:
            severity = SeverityLevel.INFORMATIONAL

        event_id = (
            record.get("id")
            or hashlib.blake2b(json.dumps(record).encode(), digest_size=12).hexdigest()
        )

        return SecurityEvent(
            event_id=f"wazuh-{event_id}",
            source=EventSource.WAZUH_HIDS,
            timestamp=timestamp,
            source_ip=src_ip,
            destination_ip=dst_ip,
            severity=severity,
            action=rule.get("action", "ALERT"),
            event_type=rule.get("groups", ["wazuh"])[0] if rule.get("groups") else "wazuh_alert",
            details=description,
            user=user,
            rule_id=rule_id,
            tags=rule.get("groups", []) + ["wazuh"],
        )

    def parse_file(self, file_path: str) -> list[SecurityEvent]:
        """Auto-detects format and parses all security events from a file."""
        events: list[SecurityEvent] = []
        with open(file_path, "r", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                # Try JSON first
                if line_str.startswith("{") and line_str.endswith("}"):
                    try:
                        record = json.loads(line_str)
                        if "rule" in record or "agent" in record:
                            events.append(self.parse_wazuh_json_event(record))
                            continue
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

                # Try Pi-hole
                if "dnsmasq" in line_str or "gravity blocked" in line_str:
                    ev = self.parse_pihole_log_line(line_str)
                    if ev:
                        events.append(ev)
                        continue

                # Try Linux Auth
                ev = self.parse_linux_auth_line(line_str)
                if ev:
                    events.append(ev)

        return events
