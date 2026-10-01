"""
Command-line interface for socmesh-audit.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .ai_companion import SocmeshAIAdvisor
from .correlator import ThreatCorrelationEngine
from .models import EventSource, SecurityEvent, SeverityLevel
from .normalizer import TelemetryNormalizer
from .storage import SocmeshCatalog
from .triage import AlertTriageGovernor

console = Console()


def create_demo_events() -> list[SecurityEvent]:
    """Generates synthetic security events for a live demonstration."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return [
        SecurityEvent(
            event_id="demo-auth-1",
            source=EventSource.LINUX_AUTH,
            timestamp=now,
            source_ip="192.0.2.145",
            destination_ip="10.0.0.5",
            severity=SeverityLevel.MEDIUM,
            action="FAILED_AUTH",
            event_type="ssh_login_failure",
            details="Failed password for invalid user admin from 192.0.2.145",
            user="admin",
        ),
        SecurityEvent(
            event_id="demo-auth-2",
            source=EventSource.LINUX_AUTH,
            timestamp=now,
            source_ip="192.0.2.145",
            destination_ip="10.0.0.5",
            severity=SeverityLevel.MEDIUM,
            action="FAILED_AUTH",
            event_type="ssh_login_failure",
            details="Failed password for invalid user root from 192.0.2.145",
            user="root",
        ),
        SecurityEvent(
            event_id="demo-auth-3",
            source=EventSource.LINUX_AUTH,
            timestamp=now,
            source_ip="192.0.2.145",
            destination_ip="10.0.0.5",
            severity=SeverityLevel.MEDIUM,
            action="FAILED_AUTH",
            event_type="ssh_login_failure",
            details="Failed password for invalid user test from 192.0.2.145",
            user="test",
        ),
        SecurityEvent(
            event_id="demo-dns-1",
            source=EventSource.PIHOLE_DNS,
            timestamp=now,
            source_ip="10.0.0.42",
            destination_ip="0.0.0.0",
            severity=SeverityLevel.HIGH,
            action="GRAVITY_BLOCKED",
            event_type="dns_sinkhole",
            details="Gravity sinkhole blocked domain: c2-beacon-malware.example.com",
            domain="c2-beacon-malware.example.com",
        ),
        SecurityEvent(
            event_id="demo-dns-2",
            source=EventSource.PIHOLE_DNS,
            timestamp=now,
            source_ip="10.0.0.42",
            destination_ip="0.0.0.0",
            severity=SeverityLevel.HIGH,
            action="GRAVITY_BLOCKED",
            event_type="dns_sinkhole",
            details="Gravity sinkhole blocked domain: phish-stealer.example.com",
            domain="phish-stealer.example.com",
        ),
        SecurityEvent(
            event_id="demo-dns-3",
            source=EventSource.PIHOLE_DNS,
            timestamp=now,
            source_ip="10.0.0.10",
            destination_ip="127.0.0.1",
            severity=SeverityLevel.INFORMATIONAL,
            action="DNS_QUERY",
            event_type="dns_query",
            details="DNS query for pool.ntp.org",
            domain="pool.ntp.org",
        ),
    ]


def handle_demo(catalog: SocmeshCatalog) -> None:
    events = create_demo_events()
    triage = AlertTriageGovernor()
    actionable, noise = triage.filter_noise(events)
    correlator = ThreatCorrelationEngine()
    incidents = correlator.correlate(actionable)

    catalog.save_events(events)
    catalog.save_incidents(incidents)

    console.print(
        Panel(
            "[bold green]Mini-SOC Telemetry Ingested & Analyzed[/bold green]",
            title="🚀 socmesh demo",
        )
    )
    console.print(
        f"Ingested **{len(events)}** raw events | Suppressed **{len(noise)}** background noise queries."
    )

    table = Table(
        title="🛡️ Correlated Security Incidents", show_header=True, header_style="bold magenta"
    )
    table.add_column("Incident ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Risk Score", justify="right")
    table.add_column("MITRE ATT&CK Tactic", style="yellow")
    table.add_column("Events", justify="right")

    for inc in incidents:
        score_color = (
            "red" if inc.risk_score >= 70 else "yellow" if inc.risk_score >= 40 else "green"
        )
        table.add_row(
            inc.incident_id,
            inc.title,
            f"[{score_color}]{inc.risk_score}/100[/{score_color}]",
            inc.primary_tactic.value,
            str(inc.event_count),
        )
    console.print(table)


def handle_ask(query: str, catalog: SocmeshCatalog) -> None:
    incidents = catalog.get_all_incidents()
    advisor = SocmeshAIAdvisor()
    response = advisor.answer_query(query, incidents)
    console.print(Panel(response, title=f"🤖 AI SOC Advisor: '{query}'", border_style="blue"))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="socmesh",
        description="Homelab & Mini-SOC Telemetry Normalizer, Threat Correlator & Alert Triage Governor.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # demo
    subparsers.add_parser("demo", help="Run interactive demonstration with synthetic telemetry")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Ingest and parse log files")
    scan_parser.add_argument("path", help="Path to syslog, Wazuh JSON, or Pi-hole log file")

    # correlate
    subparsers.add_parser("correlate", help="Run correlation engine over ingested logs")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Query the AI SOC Triage Companion")
    ask_parser.add_argument("query", help="Question about active threats or remediation steps")

    args = parser.parse_args()
    catalog = SocmeshCatalog()

    if args.command == "demo" or len(sys.argv) == 1:
        handle_demo(catalog)
    elif args.command == "ask":
        handle_ask(args.query, catalog)
    elif args.command == "scan":
        normalizer = TelemetryNormalizer()
        events = normalizer.parse_file(args.path)
        catalog.save_events(events)
        triage = AlertTriageGovernor()
        actionable, _ = triage.filter_noise(events)
        correlator = ThreatCorrelationEngine()
        incidents = correlator.correlate(actionable)
        catalog.save_incidents(incidents)
        console.print(
            f"[green]Successfully ingested {len(events)} events and identified {len(incidents)} incidents.[/green]"
        )
    elif args.command == "correlate":
        incidents = catalog.get_all_incidents()
        console.print(f"Found {len(incidents)} active correlated incidents.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
