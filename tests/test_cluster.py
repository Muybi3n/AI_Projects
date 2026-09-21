"""Tests for subject clustering and taxonomy mesh."""

from drivemesh.cluster import SubjectClusterer, tokenize_name
from drivemesh.models import ClusterCategory, DriveFile


def test_tokenize_name():
    tokens = tokenize_name("2024_W2_Tax_Filing_Final.pdf")
    assert "tax" in tokens
    assert "filing" in tokens


def test_classify_tax_file():
    f = DriveFile(id="f1", name="2024_W2_Tax_Return.pdf", path_hierarchy="/2024_W2_Tax_Return.pdf")
    clusterer = SubjectClusterer([f])
    cat, label, conf = clusterer.classify_file(f)

    assert cat == ClusterCategory.FINANCIAL_TAX
    assert "2024" in label
    assert conf > 0.6


def test_classify_medical_file():
    f = DriveFile(id="f2", name="Bloodwork_Lab_Results.pdf", path_hierarchy="/Medical/Bloodwork_Lab_Results.pdf")
    clusterer = SubjectClusterer([f])
    cat, label, conf = clusterer.classify_file(f)

    assert cat == ClusterCategory.HEALTH_MEDICAL


def test_cluster_all_and_mesh_plan():
    f1 = DriveFile(id="f1", name="2024_Tax.pdf", path_hierarchy="/2024_Tax.pdf", size_bytes=1000)
    f2 = DriveFile(id="f2", name="K8s_manifest.yaml", path_hierarchy="/k8s.yaml", size_bytes=2000)

    clusterer = SubjectClusterer([f1, f2])
    clusters = clusterer.cluster_all()

    assert len(clusters) >= 2
    assert any(c.category == ClusterCategory.FINANCIAL_TAX for c in clusters)
    assert any(c.category == ClusterCategory.ENGINEERING_DEV for c in clusters)

    plan = clusterer.build_mesh_plan()
    assert len(plan.proposed_moves) >= 2
    assert plan.proposed_moves[0].proposed_path.startswith("/")
