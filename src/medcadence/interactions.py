# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Medication & supplement interaction safety engine.
"""

from .models import (
    HealthProfile,
    InteractionAlert,
    InteractionSeverity,
    MedicationItem,
)

# Clinical Interaction Rule Knowledge Base
INTERACTION_RULES: list[dict] = [
    {
        "pair": ("statin", "grapefruit"),
        "severity": InteractionSeverity.SEVERE,
        "mechanism": "CYP3A4 inhibition increases statin systemic bioavailability and risk of rhabdomyolysis.",
        "note": "Avoid concurrent grapefruit consumption with CYP3A4-metabolized statins (atorvastatin, simvastatin).",
    },
    {
        "pair": ("warfarin", "vitamin_k"),
        "severity": InteractionSeverity.SEVERE,
        "mechanism": "Vitamin K directly antagonizes vitamin K epoxide reductase, counteracting anticoagulant effect.",
        "note": "Maintain consistent daily dietary Vitamin K intake; avoid high-dose Vitamin K supplements while on warfarin.",
    },
    {
        "pair": ("ssri", "5-htp"),
        "severity": InteractionSeverity.CONTRAINDICATED,
        "mechanism": "Synergistic elevation of central serotonin levels carries risk of Serotonin Syndrome.",
        "note": "Do NOT combine 5-HTP or St. John's Wort with SSRI/SNRI antidepressant medications.",
    },
    {
        "pair": ("ssri", "st_johns_wort"),
        "severity": InteractionSeverity.CONTRAINDICATED,
        "mechanism": "Dual serotonergic agonism and CYP enzyme induction.",
        "note": "Severe risk of Serotonin Toxicity and reduced clearance of concurrent medications.",
    },
    {
        "pair": ("iron", "calcium"),
        "severity": InteractionSeverity.MILD_CAUTION,
        "mechanism": "Calcium competitively inhibits non-heme and heme iron intestinal absorption.",
        "note": "Separate ingestion of iron supplements and high-calcium dairy/supplements by at least 2 hours.",
    },
    {
        "pair": ("nsaid", "anticoagulant"),
        "severity": InteractionSeverity.SEVERE,
        "mechanism": "Additive platelet inhibition and gastric mucosal injury increases severe GI bleeding risk.",
        "note": "Avoid OTC NSAIDs (ibuprofen, naproxen) while on anticoagulants without prescribing physician oversight.",
    },
    {
        "pair": ("magnesium", "antibiotic"),
        "severity": InteractionSeverity.MODERATE,
        "mechanism": "Divalent cation chelation reduces fluoroquinolone and tetracycline antibiotic absorption.",
        "note": "Space magnesium supplements at least 2 to 4 hours away from oral antibiotics.",
    },
]

# Aliases mapping brand/generic names to interaction compound keys
COMPOUND_ALIASES: dict[str, str] = {
    "lipitor": "statin",
    "atorvastatin": "statin",
    "simvastatin": "statin",
    "zocor": "statin",
    "rosuvastatin": "statin",
    "crestor": "statin",
    "grapefruit": "grapefruit",
    "grapefruit juice": "grapefruit",
    "warfarin": "warfarin",
    "coumadin": "warfarin",
    "vitamin k": "vitamin_k",
    "vitamin k2": "vitamin_k",
    "5-htp": "5-htp",
    "5-hydroxytryptophan": "5-htp",
    "lexapro": "ssri",
    "escitalopram": "ssri",
    "zoloft": "ssri",
    "sertraline": "ssri",
    "prozac": "ssri",
    "fluoxetine": "ssri",
    "st john's wort": "st_johns_wort",
    "st. john's wort": "st_johns_wort",
    "iron": "iron",
    "ferrous sulfate": "iron",
    "calcium": "calcium",
    "calcium carbonate": "calcium",
    "calcium citrate": "calcium",
    "ibuprofen": "nsaid",
    "advil": "nsaid",
    "motrin": "nsaid",
    "naproxen": "nsaid",
    "aleve": "nsaid",
    "aspirin": "anticoagulant",
    "eliquis": "anticoagulant",
    "xarelto": "anticoagulant",
    "magnesium": "magnesium",
    "magnesium glycinate": "magnesium",
    "cipro": "antibiotic",
    "doxycycline": "antibiotic",
}


class InteractionSafetyEngine:
    """Audits current medication and supplement regimens for dangerous drug-drug & drug-supplement interactions."""

    @staticmethod
    def audit_profile(profile: HealthProfile) -> list[InteractionAlert]:
        return InteractionSafetyEngine.audit_items(profile.medications)

    @staticmethod
    def audit_items(items: list[MedicationItem]) -> list[InteractionAlert]:
        alerts: list[InteractionAlert] = []
        if len(items) < 2:
            return alerts

        # Normalize compounds
        normalized_items: list[tuple[MedicationItem, set[str]]] = []
        for item in items:
            name_lower = item.name.lower().strip()
            compounds = set()
            for alias, target in COMPOUND_ALIASES.items():
                if alias in name_lower:
                    compounds.add(target)
            for active in item.active_compounds:
                active_l = active.lower().strip()
                for alias, target in COMPOUND_ALIASES.items():
                    if alias in active_l:
                        compounds.add(target)
            normalized_items.append((item, compounds))

        # Check pairs
        for i in range(len(normalized_items)):
            for j in range(i + 1, len(normalized_items)):
                item_a, compounds_a = normalized_items[i]
                item_b, compounds_b = normalized_items[j]

                for rule in INTERACTION_RULES:
                    req_1, req_2 = rule["pair"]
                    match_forward = (req_1 in compounds_a and req_2 in compounds_b)
                    match_reverse = (req_2 in compounds_a and req_1 in compounds_b)

                    if match_forward or match_reverse:
                        alerts.append(
                            InteractionAlert(
                                item_a=item_a.name,
                                item_b=item_b.name,
                                severity=rule["severity"],
                                mechanism=rule["mechanism"],
                                clinical_note=rule["note"],
                            )
                        )

        return alerts
