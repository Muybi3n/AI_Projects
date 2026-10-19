from canarymesh.generator import deploy_decoy_file
from canarymesh.models import DecoyArtifact, DecoyCategory, TripwireTriggerType, utc_now_iso
from canarymesh.tripwire import TripwireEngine


def test_tripwire_engine_intact(tmp_path):
    target = tmp_path / "credentials"
    sha, blake, size, meta = deploy_decoy_file(target, DecoyCategory.AWS_CREDENTIALS, "CANARY-1111")
    now_str = utc_now_iso()

    art = DecoyArtifact(
        token_id="CANARY-1111",
        name="test-aws",
        category=DecoyCategory.AWS_CREDENTIALS,
        file_path=str(target),
        expected_sha256=sha,
        expected_blake2b=blake,
        file_size_bytes=size,
        created_at=now_str,
        last_checked_at=now_str,
        canary_identifier="CANARY-1111",
    )

    engine = TripwireEngine()
    is_intact, alerts = engine.check_artifact(art)
    assert is_intact is True
    assert len(alerts) == 0

    summary = engine.run_fleet_audit([art])
    assert summary.overall_health == "ALL_DECOYS_INTACT"
    assert summary.intact_decoys == 1
    assert summary.tampered_decoys == 0


def test_tripwire_engine_tampered(tmp_path):
    target = tmp_path / "creds"
    sha, blake, size, meta = deploy_decoy_file(target, DecoyCategory.AWS_CREDENTIALS, "CANARY-2222")
    now_str = utc_now_iso()

    art = DecoyArtifact(
        token_id="CANARY-2222",
        name="test-aws",
        category=DecoyCategory.AWS_CREDENTIALS,
        file_path=str(target),
        expected_sha256=sha,
        expected_blake2b=blake,
        file_size_bytes=size,
        created_at=now_str,
        last_checked_at=now_str,
        canary_identifier="CANARY-2222",
    )

    # Tamper with file
    target.write_text("TAMPERED ADVERSARY MODIFICATION", encoding="utf-8")

    engine = TripwireEngine()
    is_intact, alerts = engine.check_artifact(art)
    assert is_intact is False
    assert len(alerts) == 1
    assert alerts[0].trigger_type == TripwireTriggerType.TAMPERED

    summary = engine.run_fleet_audit([art])
    assert summary.overall_health == "BREACH_OR_TAMPER_DETECTED"
    assert summary.tampered_decoys == 1


def test_tripwire_engine_missing(tmp_path):
    target = tmp_path / "deleted_file"
    sha, blake, size, meta = deploy_decoy_file(target, DecoyCategory.SSH_KEY, "CANARY-3333")
    target.unlink()

    art = DecoyArtifact(
        token_id="CANARY-3333",
        name="test-ssh",
        category=DecoyCategory.SSH_KEY,
        file_path=str(target),
        expected_sha256=sha,
        expected_blake2b=blake,
        file_size_bytes=size,
        created_at=utc_now_iso(),
        last_checked_at=utc_now_iso(),
        canary_identifier="CANARY-3333",
    )

    engine = TripwireEngine()
    is_intact, alerts = engine.check_artifact(art)
    assert is_intact is False
    assert len(alerts) == 1
    assert alerts[0].trigger_type == TripwireTriggerType.MISSING
