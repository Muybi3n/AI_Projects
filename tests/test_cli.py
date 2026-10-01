import tempfile

from socmesh.cli import handle_ask, handle_demo
from socmesh.storage import SocmeshCatalog


def test_cli_demo_execution(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog = SocmeshCatalog(db_path=f"{tmpdir}/test.db")
        handle_demo(catalog)
        handle_ask("What are my critical alerts?", catalog)
        handle_ask("How do I remediate?", catalog)
        handle_ask("What MITRE tactics?", catalog)
        handle_ask("General overview", catalog)
        captured = capsys.readouterr()
        assert "Mini-SOC" in captured.out or "Correlated Security Incidents" in captured.out
