# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh package initialization."""

from canarymesh.advisor import CanaryMeshAdvisor
from canarymesh.generator import deploy_decoy_file
from canarymesh.models import DecoyArtifact, DecoyCategory, TripwireAlert
from canarymesh.storage import DecoyStore
from canarymesh.tripwire import TripwireEngine

__version__ = "0.1.0"
__all__ = [
    "CanaryMeshAdvisor",
    "DecoyArtifact",
    "DecoyCategory",
    "DecoyStore",
    "TripwireAlert",
    "TripwireEngine",
    "deploy_decoy_file",
]
