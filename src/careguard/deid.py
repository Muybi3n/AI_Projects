# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
HIPAA Safe Harbor PHI De-identification & Sensitive Clinical Findings Redaction Engine.
"""

import re
from dataclasses import dataclass, field


@dataclass
class RedactionResult:
    original_text: str
    sanitized_text: str
    redacted_phi_items: list[str] = field(default_factory=list)
    redacted_sensitive_findings: list[str] = field(default_factory=list)


# Regex patterns for HIPAA PHI Safe Harbor identifiers
PHONE_REGEX = re.compile(r"(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]\d{4}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
MRN_REGEX = re.compile(r"\b(MRN|MR#|RECORD|PATIENT\s*ID)[:\s#]*([A-Z0-9-]+)\b", re.IGNORECASE)
DOB_REGEX = re.compile(
    r"\b(DOB|BIRTHDATE|BORN)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},\s*\d{4})\b", re.IGNORECASE
)
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
NAME_TITLES_REGEX = re.compile(
    r"\b(Dr\.|Doctor|Physician|Patient|Nurse|NP|PA|MD|DO)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)

# Regex patterns for sensitive lab numbers & cancer/oncology findings
# E.g. "PSA: 14.2 ng/mL", "CEA: 8.4", "WBC: 18.5", "Stage IVb adenocarcinoma", "Gleason score 9"
LAB_VALUE_REGEX = re.compile(
    r"\b(PSA|CEA|CA-125|WBC|RBC|Platelets|Hemoglobin|Creatinine|BUN|eGFR|Troponin|BNP|AFP|HbA1c)[:\s=]*(\d+(?:\.\d+)?)\s*([a-zA-Z/%μ]+)?\b",
    re.IGNORECASE,
)
ONCOLOGY_STAGING_REGEX = re.compile(
    r"\b(Stage\s+(?:0|[I|V|X]+[a-c]?)|Gleason\s+score\s+\d+(?:\+\d+)?|T\d[a-c]?N\d[a-c]?M\d[a-c]?|biopsy\s+positive\s+for\s+[a-zA-Z\s]+|malignancy|carcinoma|metastasis\s+to\s+[a-zA-Z\s]+)\b",
    re.IGNORECASE,
)


class ClinicalRedactor:
    """Safely redacts PHI and sensitive clinical numbers before external LLM interaction."""

    @staticmethod
    def deidentify(
        text: str,
        redact_sensitive_findings: bool = True,
        patient_name_hint: str | None = None,
    ) -> RedactionResult:
        redacted_phi = []
        redacted_findings = []
        sanitized = text

        # 1. Custom Patient Name Masking
        if patient_name_hint and len(patient_name_hint) > 2:
            parts = patient_name_hint.split()
            for p in parts:
                if len(p) > 2:
                    pattern = re.compile(re.escape(p), re.IGNORECASE)
                    if pattern.search(sanitized):
                        redacted_phi.append(f"Name: {p}")
                        sanitized = pattern.sub("[PATIENT_NAME]", sanitized)

        # 2. Email, SSN, MRN, Phone
        for m in EMAIL_REGEX.finditer(sanitized):
            redacted_phi.append(f"Email: {m.group(0)}")
        sanitized = EMAIL_REGEX.sub("[EMAIL]", sanitized)

        for m in SSN_REGEX.finditer(sanitized):
            redacted_phi.append(f"SSN: {m.group(0)}")
        sanitized = SSN_REGEX.sub("[SSN]", sanitized)

        for m in MRN_REGEX.finditer(sanitized):
            redacted_phi.append(f"MRN: {m.group(0)}")
        sanitized = MRN_REGEX.sub("[MRN_REDACTED]", sanitized)

        for m in DOB_REGEX.finditer(sanitized):
            redacted_phi.append(f"DOB: {m.group(0)}")
        sanitized = DOB_REGEX.sub("[DOB_REDACTED]", sanitized)

        for m in PHONE_REGEX.finditer(sanitized):
            redacted_phi.append(f"Phone: {m.group(0)}")
        sanitized = PHONE_REGEX.sub("[PHONE]", sanitized)

        # 3. Doctor/Clinician Names
        for m in NAME_TITLES_REGEX.finditer(sanitized):
            redacted_phi.append(f"Clinician: {m.group(0)}")
        sanitized = NAME_TITLES_REGEX.sub(r"\1 [CLINICIAN_NAME]", sanitized)

        # 4. Sensitive Findings Redaction (if enabled)
        if redact_sensitive_findings:
            # Mask raw lab metrics
            for m in LAB_VALUE_REGEX.finditer(sanitized):
                redacted_findings.append(f"Lab Value: {m.group(0)}")
            sanitized = LAB_VALUE_REGEX.sub(r"\1: [LAB_VALUE_REDACTED]", sanitized)

            # Mask oncology staging and biopsy details
            for m in ONCOLOGY_STAGING_REGEX.finditer(sanitized):
                redacted_findings.append(f"Clinical Staging/Finding: {m.group(0)}")
            sanitized = ONCOLOGY_STAGING_REGEX.sub("[SENSITIVE_DIAGNOSTIC_REDACTED]", sanitized)

        return RedactionResult(
            original_text=text,
            sanitized_text=sanitized,
            redacted_phi_items=redacted_phi,
            redacted_sensitive_findings=redacted_findings,
        )
