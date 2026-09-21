"""Extended tests for advisor."""

from drivemesh.advisor import DriveMeshAdvisor
from drivemesh.cluster import SubjectClusterer
from drivemesh.duplicates import DuplicateDetector
from drivemesh.importer import DriveImporter
from drivemesh.models import DriveAuditReport, DriveFile


def test_advisor_heuristic_responses():
    demo_files = DriveImporter.generate_demo_dataset()
    clusterer = SubjectClusterer(demo_files)
    clusters = clusterer.cluster_all()
    detector = DuplicateDetector(demo_files)
    dups = detector.run_all()

    audit = DriveAuditReport(
        total_files=len(demo_files),
        total_storage_bytes=10000000,
        reclaimable_bytes=5000000,
        duplicate_groups=dups,
        health_score=80,
        orphaned_root_files_count=3,
        recommendations=["Purge duplicate files."],
    )

    advisor = DriveMeshAdvisor(files=demo_files, clusters=clusters, audit_report=audit)

    dup_ans = advisor.ask("How many duplicates do I have and how much space can I save?")
    assert "Duplicate Resolution Advisory" in dup_ans
    assert "reclaimable space" in dup_ans

    struct_ans = advisor.ask("How should I structure my folders?")
    assert "Recommended Drive Mesh Structure" in struct_ans

    health_ans = advisor.ask("What is my drive health score?")
    assert "Health Score: **80/100**" in health_ans

    # Fallback default response
    generic_ans = advisor.ask("Tell me what you can do")
    assert "DriveMesh Advisor" in generic_ans


def test_advisor_clean_empty_scenarios():
    # Empty / clean state
    advisor_empty = DriveMeshAdvisor()
    dup_clean = advisor_empty.ask("duplicates")
    assert "No duplicate bloat detected" in dup_clean

    tax_advice = advisor_empty.ask("how to organize folders?")
    assert "Taxonomy Advice" in tax_advice

    health_prompt = advisor_empty.ask("health score")
    assert "Run `drivemesh audit`" in health_prompt


def test_advisor_custom_llm_callable():
    demo_files = [DriveFile(id="f1", name="tax.pdf", size_bytes=1024)]

    def mock_llm(prompt: str) -> str:
        return f"LLM_RESPONSE: Processed prompt of length {len(prompt)}"

    advisor = DriveMeshAdvisor(files=demo_files, custom_llm_callable=mock_llm)
    res = advisor.ask("Any advice?")
    assert res.startswith("LLM_RESPONSE:")
