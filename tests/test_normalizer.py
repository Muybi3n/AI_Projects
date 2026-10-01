import tempfile

from socmesh.models import EventSource, SeverityLevel
from socmesh.normalizer import TelemetryNormalizer


def test_pihole_log_parsing():
    normalizer = TelemetryNormalizer()
    line_query = (
        "Sep 28 09:15:22 dnsmasq[1234]: query[A] evil-c2-beacon.example.com from 192.168.1.100"
    )
    ev = normalizer.parse_pihole_log_line(line_query)
    assert ev is not None
    assert ev.source == EventSource.PIHOLE_DNS
    assert ev.domain == "evil-c2-beacon.example.com"
    assert ev.severity == SeverityLevel.MEDIUM

    line_blocked = "Sep 28 09:15:22 dnsmasq[1234]: gravity blocked ads.example.com is 0.0.0.0"
    ev_blocked = normalizer.parse_pihole_log_line(line_blocked)
    assert ev_blocked is not None
    assert ev_blocked.action == "GRAVITY_BLOCKED"
    assert ev_blocked.severity == SeverityLevel.HIGH


def test_linux_auth_log_parsing():
    normalizer = TelemetryNormalizer()
    line_fail = "Sep 28 09:20:11 ubuntu sshd[5432]: Failed password for invalid user admin from 192.0.2.45 port 51234 ssh2"
    ev_fail = normalizer.parse_linux_auth_line(line_fail)
    assert ev_fail is not None
    assert ev_fail.action == "FAILED_AUTH"
    assert ev_fail.source_ip == "192.0.2.45"
    assert ev_fail.user == "admin"

    line_success = "Sep 28 09:22:00 ubuntu sshd[5432]: Accepted publickey for root from 192.168.1.50 port 51234 ssh2"
    ev_success = normalizer.parse_linux_auth_line(line_success)
    assert ev_success is not None
    assert ev_success.action == "ACCEPTED_AUTH"

    line_sudo = "Sep 28 09:25:00 ubuntu sudo:     soju : TTY=pts/0 ; PWD=/home/soju ; USER=root ; COMMAND=/bin/bash"
    ev_sudo = normalizer.parse_linux_auth_line(line_sudo)
    assert ev_sudo is not None
    assert ev_sudo.action == "SUDO_EXEC"


def test_wazuh_json_parsing():
    normalizer = TelemetryNormalizer()
    record = {
        "id": "12345",
        "rule": {
            "id": "5710",
            "level": 10,
            "description": "sshd: Attempt to login using a non-existent user",
            "groups": ["syslog", "sshd", "authentication_failed"],
        },
        "data": {"srcip": "198.51.100.22", "dstuser": "nobody"},
    }
    ev = normalizer.parse_wazuh_json_event(record)
    assert ev.source == EventSource.WAZUH_HIDS
    assert ev.severity == SeverityLevel.HIGH
    assert ev.source_ip == "198.51.100.22"


def test_file_parsing():
    normalizer = TelemetryNormalizer()
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write(
            "Sep 28 09:20:11 ubuntu sshd[5432]: Failed password for invalid user admin from 192.0.2.45 port 51234 ssh2\n"
        )
        f.write("Sep 28 09:15:22 dnsmasq[1234]: gravity blocked bad.example.com is 0.0.0.0\n")
        f.flush()
        events = normalizer.parse_file(f.name)
        assert len(events) == 2
