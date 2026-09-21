"""Tests for duplicate detection algorithms."""

from drivemesh.duplicates import DuplicateDetector, normalize_filename
from drivemesh.models import DriveFile, DuplicateType


def test_normalize_filename():
    assert normalize_filename("Report_Final_v2.docx") == "report.docx"
    assert normalize_filename("Copy of 2024_W2_Form.pdf") == "2024_w2_form.pdf"
    assert normalize_filename("Presentation (1).pptx") == "presentation.pptx"
    assert normalize_filename("data_backup_2024_01_15.csv") == "data.csv"


def test_exact_checksum_duplicates():
    f1 = DriveFile(
        id="f1",
        name="Doc.pdf",
        size_bytes=1000,
        md5_checksum="abc",
        path_hierarchy="/Organized/Doc.pdf",
    )
    f2 = DriveFile(
        id="f2",
        name="Copy of Doc.pdf",
        size_bytes=1000,
        md5_checksum="abc",
        path_hierarchy="/Doc (1).pdf",
    )
    detector = DuplicateDetector([f1, f2])
    dups = detector.find_exact_checksum_duplicates()

    assert len(dups) == 1
    assert dups[0].duplicate_type == DuplicateType.EXACT_CHECKSUM
    assert dups[0].canonical_file_id == "f1"
    assert dups[0].duplicate_file_ids == ["f2"]
    assert dups[0].wasted_bytes == 1000


def test_name_and_size_duplicates():
    f1 = DriveFile(id="f1", name="Photo.png", size_bytes=50000, md5_checksum="", path_hierarchy="/Photos/Photo.png")
    f2 = DriveFile(id="f2", name="photo.png", size_bytes=50000, md5_checksum="", path_hierarchy="/Unsorted/photo.png")

    detector = DuplicateDetector([f1, f2])
    dups = detector.find_name_and_size_duplicates()

    assert len(dups) == 1
    assert dups[0].duplicate_type == DuplicateType.NAME_AND_SIZE
    assert dups[0].wasted_bytes == 50000


def test_fuzzy_version_duplicates():
    f1 = DriveFile(
        id="f1",
        name="Proposal_v1.docx",
        size_bytes=20000,
        path_hierarchy="/Proposal_v1.docx",
        modified_time="2024-01-01",
    )
    f2 = DriveFile(
        id="f2",
        name="Proposal_v2_final.docx",
        size_bytes=22000,
        path_hierarchy="/Projects/Proposal_v2_final.docx",
        modified_time="2024-01-05",
    )

    detector = DuplicateDetector([f1, f2])
    dups = detector.find_fuzzy_version_duplicates()

    assert len(dups) == 1
    assert dups[0].duplicate_type == DuplicateType.FUZZY_VERSION
    assert dups[0].canonical_file_id == "f2"


def test_zero_byte_ghosts():
    f1 = DriveFile(id="f1", name="empty.txt", size_bytes=0)
    f2 = DriveFile(id="f2", name="normal.txt", size_bytes=100)

    detector = DuplicateDetector([f1, f2])
    ghosts = detector.find_zero_byte_ghosts()

    assert len(ghosts) == 1
    assert ghosts[0].duplicate_file_ids == ["f1"]


def test_run_all_pipeline():
    f1 = DriveFile(id="f1", name="Tax.pdf", size_bytes=1000, md5_checksum="hash1")
    f2 = DriveFile(id="f2", name="Tax_copy.pdf", size_bytes=1000, md5_checksum="hash1")
    f3 = DriveFile(id="f3", name="empty.doc", size_bytes=0)

    detector = DuplicateDetector([f1, f2, f3])
    all_groups = detector.run_all()
    assert len(all_groups) == 2
