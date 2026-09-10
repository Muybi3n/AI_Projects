# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Clinical point extractor: Parses unstructured doctor notes into structured clinical milestones.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from .deid import ClinicalRedactor, RedactionResult
from .jargon import DecodedTerm, JargonTranslator


@dataclass
class ExtractedClinicalPoints:
    encounter_date: str
    original_raw_length: int
    chief_complaint: str = ""
    diagnoses_and_assessments: list[str] = field(default_factory=list)
    medication_changes: list[str] = field(default_factory=list)
    follow_up_orders_and_labs: list[str] = field(default_factory=list)
    decoded_jargon: list[DecodedTerm] = field(default_factory=list)
    redaction_summary: dict[str, Any] = field(default_factory=dict)
    sanitized_text_for_llm: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_date": self.encounter_date,
            "original_raw_length": self.original_raw_length,
            "chief_complaint": self.chief_complaint,
            "diagnoses_and_assessments": self.diagnoses_and_assessments,
            "medication_changes": self.medication_changes,
            "follow_up_orders_and_labs": self.follow_up_orders_and_labs,
            "decoded_jargon": [d.__dict__ for d in self.decoded_jargon],
            "redaction_summary": self.redaction_summary,
            "sanitized_text_for_llm": self.sanitized_text_for_llm,
        }


class NoteExtractor:
    """Extracts clinical points from raw clinical notes with de-identification."""

    @staticmethod
    def extract_from_note(
        note_text: str,
        encounter_date: str,
        patient_name_hint: str | None = None,
        redact_sensitive_findings: bool = True,
    ) -> ExtractedClinicalPoints:
        # Step 1: De-identify PHI and redact sensitive findings for LLM
        redaction: RedactionResult = ClinicalRedactor.deidentify(
            note_text,
            redact_sensitive_findings=redact_sensitive_findings,
            patient_name_hint=patient_name_hint,
        )

        # Step 2: Decode medical jargon & acronyms
        jargon = JargonTranslator.decode_text(note_text)

        # Step 3: Extract structured sections via clinical keyword heuristics
        lines = [line.strip() for line in note_text.split("\n") if line.strip()]

        chief_complaint = ""
        assessments = []
        med_changes = []
        orders = []

        current_section = None

        for line in lines:
            line_l = line.lower()
            if any(k in line_l for k in ["chief complaint:", "cc:", "reason for visit:", "presenting problem:"]):
                chief_complaint = re.sub(
                    r"^(chief complaint:|cc:|reason for visit:|presenting problem:)\s*", "", line, flags=re.IGNORECASE
                ).strip()
                current_section = "cc"
            elif any(k in line_l for k in ["assessment:", "impression:", "diagnoses:", "diagnosis:"]):
                current_section = "assessment"
                content = re.sub(
                    r"^(assessment:|impression:|diagnoses:|diagnosis:)\s*", "", line, flags=re.IGNORECASE
                ).strip()
                if content:
                    assessments.append(content)
            elif any(k in line_l for k in ["medication changes:", "med changes:", "prescriptions:", "rx:"]):
                current_section = "meds"
                content = re.sub(
                    r"^(medication changes:|med changes:|prescriptions:|rx:)\s*", "", line, flags=re.IGNORECASE
                ).strip()
                if content:
                    med_changes.append(content)
            elif any(k in line_l for k in ["plan:", "orders:", "follow up:", "follow-up:", "next steps:"]):
                current_section = "orders"
                content = re.sub(
                    r"^(plan:|orders:|follow up:|follow-up:|next steps:)\s*", "", line, flags=re.IGNORECASE
                ).strip()
                if content:
                    orders.append(content)
            else:
                # Add bullet items to current section
                if current_section == "assessment" and len(line) > 3:
                    assessments.append(line.lstrip("•-*123456789. "))
                elif current_section == "meds" and len(line) > 3:
                    med_changes.append(line.lstrip("•-*123456789. "))
                elif current_section == "orders" and len(line) > 3:
                    orders.append(line.lstrip("•-*123456789. "))

        if not chief_complaint and lines:
            chief_complaint = lines[0][:100]

        return ExtractedClinicalPoints(
            encounter_date=encounter_date,
            original_raw_length=len(note_text),
            chief_complaint=chief_complaint,
            diagnoses_and_assessments=assessments[:8],
            medication_changes=med_changes[:8],
            follow_up_orders_and_labs=orders[:8],
            decoded_jargon=jargon,
            redaction_summary={
                "phi_redacted_count": len(redaction.redacted_phi_items),
                "sensitive_findings_redacted_count": len(redaction.redacted_sensitive_findings),
                "redacted_phi_samples": redaction.redacted_phi_items[:5],
                "redacted_findings_samples": redaction.redacted_sensitive_findings[:5],
            },
            sanitized_text_for_llm=redaction.sanitized_text,
        )
