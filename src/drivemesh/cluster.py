"""Subject clustering, taxonomy classification, and mesh structure generator."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from drivemesh.models import ClusterCategory, DriveFile, FileCluster, MeshMoveOperation, MeshPlan

# Category rule definitions with weighted keyword patterns
CATEGORY_RULES: dict[ClusterCategory, dict[str, Any]] = {
    ClusterCategory.FINANCIAL_TAX: {
        "keywords": [
            "tax",
            "w2",
            "1099",
            "w-2",
            "1040",
            "invoice",
            "receipt",
            "forecast",
            "budget",
            "revenue",
            "expense",
            "statement",
            "payroll",
            "banking",
            "schwab",
            "vanguard",
            "fidelity",
            "dividend",
            "crypto",
            "balance_sheet",
        ],
        "extensions": [".xlsx", ".xls", ".csv", ".tsv"],
        "weight": 1.2,
    },
    ClusterCategory.LEGAL_CONTRACTS: {
        "keywords": [
            "nda",
            "agreement",
            "contract",
            "lease",
            "deed",
            "bylaws",
            "incorporation",
            "trademark",
            "patent",
            "license",
            "settlement",
            "terms",
            "amendment",
            "power_of_attorney",
            "will",
            "trust",
            "affidavit",
        ],
        "extensions": [".pdf", ".docx", ".doc"],
        "weight": 1.3,
    },
    ClusterCategory.HEALTH_MEDICAL: {
        "keywords": [
            "health",
            "medical",
            "lab",
            "bloodwork",
            "panel",
            "vaccine",
            "immunization",
            "prescription",
            "doctor",
            "hospital",
            "clinic",
            "biomarker",
            "radiology",
            "mri",
            "ct_scan",
            "dental",
            "vision",
            "diagnosis",
        ],
        "extensions": [".pdf"],
        "weight": 1.4,
    },
    ClusterCategory.ENGINEERING_DEV: {
        "keywords": [
            "k8s",
            "kubernetes",
            "docker",
            "compose",
            "manifest",
            "github",
            "gitlab",
            "ansible",
            "terraform",
            "homelab",
            "linux",
            "config",
            "backup",
            "schema",
            "sql",
            "python",
            "rust",
            "api",
            "repo",
            "patch",
        ],
        "extensions": [".yml", ".yaml", ".json", ".py", ".rs", ".go", ".sh", ".tar.gz", ".zip", ".tf"],
        "weight": 1.2,
    },
    ClusterCategory.WORK_PROJECTS: {
        "keywords": [
            "roadmap",
            "okr",
            "sprint",
            "presentation",
            "deck",
            "meeting_notes",
            "status",
            "project",
            "brief",
            "strategy",
            "proposal",
            "client",
            "deliverable",
            "q1",
            "q2",
            "q3",
            "q4",
        ],
        "extensions": [".pptx", ".ppt", ".key", ".gslides", ".gdoc"],
        "weight": 1.0,
    },
    ClusterCategory.ACADEMIC_RESEARCH: {
        "keywords": [
            "paper",
            "thesis",
            "dissertation",
            "arxiv",
            "journal",
            "publication",
            "abstract",
            "literature",
            "study",
            "benchmark",
            "dataset",
            "survey",
        ],
        "extensions": [".pdf", ".tex", ".bib"],
        "weight": 1.2,
    },
    ClusterCategory.MEDIA_ASSETS: {
        "keywords": [
            "video",
            "demo",
            "screen_recording",
            "recording",
            "audio",
            "podcast",
            "raw",
            "photo",
            "b-roll",
            "render",
            "clip",
        ],
        "extensions": [".mp4", ".mov", ".mkv", ".wav", ".mp3", ".flac", ".raw", ".png", ".jpg", ".jpeg"],
        "weight": 1.1,
    },
    ClusterCategory.PERSONAL_ADMIN: {
        "keywords": [
            "passport",
            "driver_license",
            "utility",
            "insurance",
            "vehicle",
            "registration",
            "id_card",
            "rent",
        ],
        "extensions": [".pdf", ".jpg", ".png"],
        "weight": 1.1,
    },
}

YEAR_REGEX = re.compile(r"(?:^|\D)(20[12]\d)(?:\D|$)")


def tokenize_name(text: str) -> list[str]:
    """Tokenize a string into lowercase alphanumeric components."""
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1 and not t.isdigit()]


class SubjectClusterer:
    """Classifies files into taxonomy categories and groups into subject meshes."""

    def __init__(self, files: list[DriveFile]) -> None:
        self.files = files

    def classify_file(self, f: DriveFile) -> tuple[ClusterCategory, str, float]:
        """Classify a single file into category, discovered subject label, and confidence score."""
        combined_text = f"{f.name} {f.path_hierarchy}".lower()
        ext = Path(f.name).suffix.lower()

        scores: Counter[ClusterCategory] = Counter()

        for cat, config in CATEGORY_RULES.items():
            cat_score = 0.0
            for kw in config["keywords"]:
                if kw in combined_text:
                    cat_score += 2.0
            if ext in config["extensions"]:
                cat_score += 1.0

            if cat_score > 0:
                scores[cat] = cat_score * config["weight"]

        if not scores:
            return ClusterCategory.UNCATEGORIZED, "General", 0.3

        top_cat, top_score = scores.most_common(1)[0]
        # Calculate confidence normalized roughly 0.5 to 0.99
        confidence = min(0.99, round(1.0 - math.exp(-top_score / 4.0), 2))

        # Extract subject label (topic name from common tokens)
        tokens = tokenize_name(f.name)
        year_match = YEAR_REGEX.search(combined_text)
        year_str = year_match.group(1) if year_match else ""

        label_parts: list[str] = []
        if year_str:
            label_parts.append(year_str)
        if tokens:
            label_parts.append(tokens[0].capitalize())

        label = " ".join(label_parts) if label_parts else top_cat.value.split("&")[0].strip()

        return top_cat, label, confidence

    def cluster_all(self) -> list[FileCluster]:
        """Run classification on all files and aggregate into FileCluster groups."""
        grouped: dict[tuple[ClusterCategory, str], list[DriveFile]] = defaultdict(list)

        for f in self.files:
            cat, label, conf = self.classify_file(f)
            f.assigned_category = cat
            f.cluster_label = label
            f.confidence = conf
            grouped[(cat, label)].append(f)

        clusters: list[FileCluster] = []
        for (cat, label), flist in grouped.items():
            total_size = sum(x.size_bytes for x in flist)
            avg_conf = round(sum(x.confidence for x in flist) / len(flist), 2)

            # Generate target mesh path
            target_path = self._generate_mesh_path(cat, label)
            cluster_id = f"cluster_{cat.name.lower()}_{abs(hash(label)) & 0xFFFFFF:06x}"

            clusters.append(
                FileCluster(
                    cluster_id=cluster_id,
                    category=cat,
                    label=label,
                    file_ids=[x.id for x in flist],
                    total_size_bytes=total_size,
                    suggested_target_path=target_path,
                    confidence_score=avg_conf,
                )
            )

        # Sort clusters by total size descending
        clusters.sort(key=lambda c: c.total_size_bytes, reverse=True)
        return clusters

    def _generate_mesh_path(self, category: ClusterCategory, label: str) -> str:
        """Create clean canonical folder path suggestion for a cluster."""
        cat_folder = category.value.replace(" & ", "_").replace(" / ", "_").replace(" ", "_")
        sub_folder = label.replace(" ", "_")
        return f"/{cat_folder}/{sub_folder}"

    def build_mesh_plan(self, duplicate_deletions: list[str] | None = None) -> MeshPlan:
        """Generate structured move and reorganization plan for unorganized files."""
        clusters = self.cluster_all()
        cluster_map = {}
        for c in clusters:
            for fid in c.file_ids:
                cluster_map[fid] = c

        moves: list[MeshMoveOperation] = []
        files_by_id = {f.id: f for f in self.files}
        deletion_set = set(duplicate_deletions or [])

        for f in self.files:
            if f.id in deletion_set:
                continue

            c = cluster_map.get(f.id)
            if not c or c.category == ClusterCategory.UNCATEGORIZED:
                continue

            current_dir = str(Path(f.path_hierarchy).parent).replace("\\", "/")
            if current_dir == ".":
                current_dir = "/"

            target_dir = c.suggested_target_path
            # Check if relocation needed
            if current_dir != target_dir:
                proposed_full = f"{target_dir.rstrip('/')}/{f.name}"
                moves.append(
                    MeshMoveOperation(
                        file_id=f.id,
                        file_name=f.name,
                        current_path=f.path_hierarchy,
                        proposed_path=proposed_full,
                        reason=f"Categorized under {c.category.value} ({c.label})",
                    )
                )

        import datetime

        return MeshPlan(
            plan_id=f"plan_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            proposed_moves=moves,
            proposed_deletions=list(deletion_set),
            total_reclaimable_bytes=sum(files_by_id[fid].size_bytes for fid in deletion_set if fid in files_by_id),
        )
