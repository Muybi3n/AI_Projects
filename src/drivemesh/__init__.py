"""drivemesh-core: Local-first Google Drive & cloud storage metadata clustering, subject grouping, and fuzzy duplicate detection engine."""

from drivemesh.advisor import DriveMeshAdvisor
from drivemesh.cluster import SubjectClusterer
from drivemesh.duplicates import DuplicateDetector
from drivemesh.importer import DriveImporter
from drivemesh.models import (
    ClusterCategory,
    DriveAuditReport,
    DriveFile,
    DriveFolder,
    DuplicateGroup,
    DuplicateType,
    FileCluster,
    MeshMoveOperation,
    MeshPlan,
    ResolutionAction,
)
from drivemesh.storage import DriveStorage

__version__ = "0.1.0"
__all__ = [
    "ClusterCategory",
    "DriveAuditReport",
    "DriveFile",
    "DriveFolder",
    "DriveImporter",
    "DriveMeshAdvisor",
    "DriveStorage",
    "DuplicateDetector",
    "DuplicateGroup",
    "DuplicateType",
    "FileCluster",
    "MeshMoveOperation",
    "MeshPlan",
    "ResolutionAction",
    "SubjectClusterer",
    "__version__",
]
