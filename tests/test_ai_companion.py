from socmesh.ai_companion import SocmeshAIAdvisor
from socmesh.models import CorrelatedIncident, MitreTactic


def test_heuristic_ai_advisor():
    advisor = SocmeshAIAdvisor()
    inc = CorrelatedIncident(
        incident_id="INC-1",
        title="Brute Force Attack",
        primary_tactic=MitreTactic.CREDENTIAL_ACCESS,
        risk_score=90,
        affected_hosts=["server1"],
        source_ips=["192.0.2.1"],
        event_count=10,
        first_seen="2026-09-28T10:00:00Z",
        last_seen="2026-09-28T10:01:00Z",
        summary="Brute force detected.",
        remediation_guidance=["Block IP 192.0.2.1"],
    )

    resp_crit = advisor.answer_query("What are the critical incidents?", [inc])
    assert "Critical/High" in resp_crit
    assert "Brute Force Attack" in resp_crit

    resp_fix = advisor.answer_query("How do I fix this?", [inc])
    assert "Block IP 192.0.2.1" in resp_fix

    resp_mitre = advisor.answer_query("What MITRE tactics were seen?", [inc])
    assert "Credential Access" in resp_mitre


def test_custom_llm_callable():
    mock_llm = lambda prompt: f"MOCK_LLM_OUTPUT for {len(prompt)} chars"
    advisor = SocmeshAIAdvisor(custom_llm_callable=mock_llm)
    resp = advisor.answer_query("Test query", [])
    assert "MOCK_LLM_OUTPUT" in resp
