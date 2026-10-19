from canarymesh.models import DecoyArtifact, DecoyCategory, utc_now_iso
from canarymesh.storage import DecoyStore


def test_decoy_store(tmp_path):
    store = DecoyStore(data_dir=tmp_path)
    assert store.list_decoys() == []
    assert store.list_alerts() == []

    art = DecoyArtifact(
        token_id="CANARY-STORE1",
        name="store-decoy",
        category=DecoyCategory.DATABASE_CONFIG,
        file_path="/tmp/db.yml",
        expected_sha256="123456",
        expected_blake2b="789012",
        file_size_bytes=100,
        created_at=utc_now_iso(),
        last_checked_at=utc_now_iso(),
        canary_identifier="CANARY-STORE1",
    )
    store.add_decoy(art)
    assert len(store.list_decoys()) == 1

    fetched = store.get_decoy("store-decoy")
    assert fetched is not None
    assert fetched.token_id == "CANARY-STORE1"

    # Remove
    assert store.remove_decoy("store-decoy") is True
    assert len(store.list_decoys()) == 0
