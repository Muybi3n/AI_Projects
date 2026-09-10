# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Medical acronym & clinical shorthand lexicon dictionary.
"""

import re
from dataclasses import dataclass

CLINICAL_LEXICON: dict[str, str] = {
    # Symptoms & General
    "sob": "Shortness of breath (dyspnea)",
    "cp": "Chest pain",
    "doe": "Dyspnea on exertion (shortness of breath during activity)",
    "n/v": "Nausea and vomiting",
    "wnl": "Within normal limits (normal result)",
    "nkda": "No known drug allergies",
    "prn": "Pro re nata (take as needed)",
    "bid": "Bis in die (twice a day)",
    "tid": "Ter in die (three times a day)",
    "qid": "Quater in die (four times a day)",
    "qd": "Quaque die (once daily)",
    "po": "Per os (orally / by mouth)",
    "npo": "Nil per os (nothing by mouth)",
    "qhs": "Every night at bedtime",
    "ac": "Before meals",
    "pc": "After meals",
    "stat": "Immediately / urgently",
    "ad lib": "As desired / freely",
    "yo": "Year old",
    "c/o": "Complains of",
    "s/p": "Status post (after a procedure or event)",
    "r/o": "Rule out (suspected condition being tested)",
    "hx": "Medical history",
    "tx": "Treatment",
    "dx": "Diagnosis",
    "rx": "Prescription",
    "fx": "Bone fracture",
    "sx": "Symptoms",
    # Cardiovascular & Vitals
    "htn": "Hypertension (high blood pressure)",
    "chf": "Congestive heart failure",
    "cad": "Coronary artery disease",
    "mi": "Myocardial infarction (heart attack)",
    "afib": "Atrial fibrillation (irregular heartbeat)",
    "a-fib": "Atrial fibrillation (irregular heartbeat)",
    "lvef": "Left ventricular ejection fraction (heart pumping efficiency)",
    "ef": "Ejection fraction",
    "bp": "Blood pressure",
    "hr": "Heart rate",
    "rr": "Respiratory rate",
    "spo2": "Blood oxygen saturation percentage",
    "ed": "Edema (fluid swelling) or Emergency Department",
    # Metabolic & Endocrine
    "t2dm": "Type 2 diabetes mellitus",
    "dm2": "Type 2 diabetes mellitus",
    "dm": "Diabetes mellitus",
    "hba1c": "Glycated hemoglobin (3-month average blood sugar)",
    "a1c": "Hemoglobin A1c (average blood sugar)",
    "fbg": "Fasting blood glucose",
    "tsh": "Thyroid stimulating hormone",
    # Renal & GI
    "ckd": "Chronic kidney disease",
    "esrd": "End-stage renal disease",
    "egfr": "Estimated glomerular filtration rate (kidney filter efficiency)",
    "bun": "Blood urea nitrogen (kidney metabolic waste marker)",
    "cr": "Serum creatinine (kidney function marker)",
    "gerd": "Gastroesophageal reflux disease (acid reflux)",
    "uti": "Urinary tract infection",
    # Neurological & Musculoskeletal
    "cva": "Cerebrovascular accident (stroke)",
    "tia": "Transient ischemic attack (mini-stroke)",
    "oa": "Osteoarthritis (joint wear and tear)",
    "ra": "Rheumatoid arthritis (inflammatory joint disease)",
    "ams": "Altered mental status (confusion/delirium)",
    "loc": "Loss of consciousness",
    "pvd": "Peripheral vascular disease",
    "pad": "Peripheral artery disease",
    # Pulmonary
    "copd": "Chronic obstructive pulmonary disease",
    "osa": "Obstructive sleep apnea",
    "uri": "Upper respiratory infection (common cold)",
}


@dataclass
class DecodedTerm:
    acronym: str
    plain_english: str


class JargonTranslator:
    """Translates medical shorthand and acronyms into patient-friendly English."""

    @staticmethod
    def decode_text(text: str) -> list[DecodedTerm]:
        words = re.findall(r"\b[A-Za-z0-9/-]+\b", text)
        decoded = []
        seen = set()

        for w in words:
            w_lower = w.lower().strip()
            if w_lower in CLINICAL_LEXICON and w_lower not in seen:
                seen.add(w_lower)
                decoded.append(
                    DecodedTerm(
                        acronym=w.upper(),
                        plain_english=CLINICAL_LEXICON[w_lower],
                    )
                )

        return decoded
