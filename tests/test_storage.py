import tempfile
from pathlib import Path

from socmesh.models import (
    CorrelatedIncident,
    EventSource,
    MitreTactic,
    SecurityEvent,
    SeverityLevel,
)
from socmesh.storage import SocmeshCatalog


def test_catalog_storage_and_retrieval():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        catalog = SocmeshCatalog(db_path=db_path)

        event = SecurityEvent(
            event_id="ev-1",
            source=EventSource.LINUX_AUTH,
            timestamp="2026-09-28T10:00:00Z",
            source_ip="192.0.2.10",
            destination_ip="127.0.0.1",
            severity=SeverityLevel.LOW,
            action="ACCEPTED_AUTH",
            event_type="ssh_login_success",
            details="Login success",
        )
        catalog.save_events([event])

        inc = CorrelatedIncident(
            incident_id="inc-1",
            title="SSH Surge",
            primary_tactic=MitreTactic.INITIAL_ACCESS,
            risk_score=75,
            affected_hosts=["homelab"],
            source_ips=["192.0.2.10"],
            event_count=1,
            first_seen="2026-09-28T10:00:00Z",
            last_seen="2026-09-28T10:01:00Z",
            summary="Surge summary",
            remediation_guidance=["Check firewall"],
        )
        catalog.save_incidents([inc])

        retrieved = catalog.get_all_incidents()
        assert len(retrieved) == 1
        assert retrieved[0].incident_id == "inc-1"
        assert retrieved[0].risk_score == 75
