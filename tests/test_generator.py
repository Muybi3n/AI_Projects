from canarymesh.generator import (
    build_decoy_payload,
    compute_file_hashes,
    deploy_decoy_file,
    generate_canary_identifier,
)
from canarymesh.models import DecoyCategory


def test_generate_canary_identifier():
    cid = generate_canary_identifier()
    assert cid.startswith("CANARY-")
    assert len(cid) == 23


def test_build_decoy_payload_categories():
    for cat in DecoyCategory:
        content, meta = build_decoy_payload(cat, "CANARY-TEST1234", "custom-label")
        assert len(content) > 10
        assert "canary_id" in meta


def test_deploy_decoy_file(tmp_path):
    target = tmp_path / "subdir" / ".env"
    sha, blake, size, meta = deploy_decoy_file(target, DecoyCategory.ENV_SECRETS, "CANARY-9999", "test-run")

    assert target.exists()
    assert size > 0
    assert len(sha) == 64
    assert len(blake) == 128
    assert "CANARY-9999" in target.read_text(encoding="utf-8")


def test_compute_file_hashes(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_bytes(b"hello canary tripwire")
    sha, blake, sz = compute_file_hashes(p)
    assert sz == len(b"hello canary tripwire")
    assert len(sha) == 64
