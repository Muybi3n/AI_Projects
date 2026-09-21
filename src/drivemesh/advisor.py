"""Heuristic AI advisor and pluggable LLM adapter for drive organization and storage hygiene."""

from __future__ import annotations

from collections.abc import Callable

from drivemesh.models import DriveAuditReport, DriveFile, FileCluster


class DriveMeshAdvisor:
    """Provides storage optimization recommendations and interactive query responses."""

    def __init__(
        self,
        files: list[DriveFile] | None = None,
        clusters: list[FileCluster] | None = None,
        audit_report: DriveAuditReport | None = None,
        custom_llm_callable: Callable[[str], str] | None = None,
    ) -> None:
        self.files = files or []
        self.clusters = clusters or []
        self.audit_report = audit_report
        self.custom_llm_callable = custom_llm_callable

    def ask(self, question: str) -> str:
        """Answer queries using custom LLM if registered, or deterministic heuristics."""
        if self.custom_llm_callable:
            context = self._generate_context_prompt()
            full_prompt = (
                f"Context:\n{context}\n\nQuestion: {question}\nProvide actionable storage engineering recommendations:"
            )
            return self.custom_llm_callable(full_prompt)

        return self._heuristic_answer(question)

    def _generate_context_prompt(self) -> str:
        """Assemble structured context summary for external LLM ingestion."""
        total_files = len(self.files)
        total_size_mb = sum(f.size_bytes for f in self.files) / (1024 * 1024)
        reclaimable_mb = (self.audit_report.reclaimable_bytes if self.audit_report else 0) / (1024 * 1024)
        clusters_desc = ", ".join(f"{c.category.value} ({len(c.file_ids)} files)" for c in self.clusters[:5])

        return (
            f"Total Files: {total_files}\n"
            f"Total Storage: {total_size_mb:.2f} MB\n"
            f"Reclaimable Duplicate Storage: {reclaimable_mb:.2f} MB\n"
            f"Discovered Clusters: {clusters_desc}\n"
        )

    def _heuristic_answer(self, question: str) -> str:
        """Deterministic heuristic advisor responding to storage questions."""
        q = question.lower()

        # 1. Duplicates and wasted space queries
        if any(w in q for w in ["duplicate", "waste", "reclaim", "save space", "clean"]):
            if not self.audit_report or self.audit_report.reclaimable_bytes == 0:
                return (
                    "🔍 **Storage Hygiene Check**: No duplicate bloat detected in your scanned files. "
                    "All files appear to be unique binary artifacts."
                )
            reclaim_mb = self.audit_report.reclaimable_bytes / (1024 * 1024)
            dup_count = len(self.audit_report.duplicate_groups)
            return (
                f"🧹 **Duplicate Resolution Advisory**:\n"
                f"- Found **{dup_count} duplicate groups** with **{reclaim_mb:.2f} MB** of reclaimable space.\n"
                f"- Recommended Strategy: Keep canonical files in structured directories (`/Tax`, `/Finance`) and "
                f"purge numbered copies (e.g. `(1)`, `Copy of...`) or older draft versions using `drivemesh plan`."
            )

        # 2. Structure / taxonomy / organization questions
        if any(w in q for w in ["structure", "organize", "taxonomy", "folder", "mesh", "where"]):
            if not self.clusters:
                return (
                    "📁 **Taxonomy Advice**: A clean drive should follow domain-driven partitioning:\n"
                    "  ├── `/Financial_Tax/<Year>/` (W2s, 1099s, Invoices)\n"
                    "  ├── `/Legal_Contracts/` (NDAs, Deeds, Terms)\n"
                    "  ├── `/Health_Medical/` (Lab work, Immunization)\n"
                    "  ├── `/Engineering_Dev/` (Manifests, Backups, Code)\n"
                    "  └── `/Work_Projects/<Year_Quarter>/` (Presentations, Decks)\n"
                    "Run `drivemesh cluster` to automatically sort your files into this taxonomy."
                )
            top_clusters = self.clusters[:4]
            cluster_lines = "\n".join(
                f"  - **{c.category.value}** -> Suggested Path: `{c.suggested_target_path}` ({len(c.file_ids)} files, {c.total_size_bytes / (1024 * 1024):.1f} MB)"
                for c in top_clusters
            )
            return (
                f"🗂️ **Recommended Drive Mesh Structure**:\n"
                f"Based on your metadata, your files naturally group into:\n{cluster_lines}\n\n"
                f"Use `drivemesh plan` to review and export atomic migration instructions."
            )

        # 3. Health & overall score
        if any(w in q for w in ["health", "score", "audit", "status", "summary"]):
            if self.audit_report:
                return (
                    f"📊 **Drive Health Audit**:\n"
                    f"- Overall Health Score: **{self.audit_report.health_score}/100**\n"
                    f"- Total Files: {self.audit_report.total_files} ({self.audit_report.total_storage_bytes / (1024 * 1024):.2f} MB)\n"
                    f"- Clutter in Root: {self.audit_report.orphaned_root_files_count} files\n"
                    f"- Key Next Step: {self.audit_report.recommendations[0] if self.audit_report.recommendations else 'Maintain current organization.'}"
                )
            return "Run `drivemesh audit` to compute your drive health score."

        # Default fallback guidance
        return (
            "🤖 **DriveMesh Advisor**: I analyze cloud drive metadata to eliminate duplicates, "
            "cluster messy documents into clean taxonomy trees, and identify storage waste.\n"
            "Try asking:\n"
            "- 'How much space can I reclaim from duplicates?'\n"
            "- 'How should I structure my folder taxonomy?'\n"
            "- 'What is my current drive health score?'"
        )
