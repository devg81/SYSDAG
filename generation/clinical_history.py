"""Diagnosis + medical-history + medication derivation (M4D/M4E,
docs/DECISIONS.md D015/D016).

All three functions are pure and deterministic -- no RNG draws (the one
random decision medications depend on, treatment status, is drawn earlier
by generation.indian_population.sample_medication_treatment() and passed
in already-resolved). Diagnoses are a 1:1 promotion of already-generated
risk_factors flags, never independently sampled (mirrors D011's rule for
lipid interpretations). medical_history entries and medications REFERENCE
diagnoses rather than re-deriving them, per
docs/CLINICAL_RECORD_DESIGN.md §D's "avoid duplicate independent
generation" principle.

hyperlipidemia is deliberately excluded from diagnosis generation -- see
docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md for why. Statin/antiplatelet
medications are deliberately excluded -- see
docs/M4E_MEDICATION_EVIDENCE.md for why.
"""

from __future__ import annotations

from typing import Any

# Order determines diagnosis_id suffix (DX01, DX02, ...) -- stable so
# output is deterministic given the same risk_factors.
_SUPPORTED_CODES = ("hypertension", "diabetes")

# Diagnosis code -> coarse therapeutic drug_class, the one controlled
# mapping this project's evidence actually supports (docs/
# M4E_MEDICATION_DESIGN.md M4E-2). Order determines medication_id suffix.
_DRUG_CLASS_BY_CODE = {
    "hypertension": "antihypertensive",
    "diabetes": "antidiabetic",
}


def derive_encounters(
    patient_id: str,
    assessment_date: str,
    has_blood_pressure: bool,
    has_lipid_panel: bool,
    lab_analytes: list[str],
) -> list[dict[str, Any]]:
    """One structural container for this record's single synthetic
    measurement cross-section (M8). Pure and deterministic -- no RNG, no
    new clinical facts.

    This is NOT a healthcare visit. Every measurement this project
    generates (blood pressure, lipid panel, HbA1c) already carries the
    same date, and until M8 that date had no identified owner, so the
    clinical_timeline had nothing to reference
    (docs/CLINICAL_RECORD_DESIGN.md section H's "Encounter
    --reference_id--> (nothing yet)"). This names that cross-section and
    lists which measurements belong to it; it invents no admission,
    appointment, physician, follow-up or care-seeking event. A real
    utilization-based encounter model stays deferred -- the only
    candidate source (NSS 75th Round) measures healthcare expenditure
    behaviour, not clinical encounters, and docs/
    INDIAN_GENERATION_STRATEGY.md classifies it "E -- Not Used".

    `recorded_measurements` REFERENCES field names rather than copying
    values, the same no-duplicate-representation rule
    derive_medical_history() follows for diagnoses.
    """
    recorded: list[str] = []
    if has_blood_pressure:
        recorded.append("blood_pressure")
    if has_lipid_panel:
        recorded.append("lipid_panel")
    recorded.extend(f"labs.{analyte}" for analyte in lab_analytes)
    if not recorded:
        # Nothing measured -> no cross-section to contain. Returning []
        # keeps "no encounter" honest rather than emitting an empty one.
        return []
    return [
        {
            "encounter_id": f"{patient_id}_ENC01",
            "encounter_type": "synthetic_baseline_assessment",
            "date": assessment_date,
            "patient_id": patient_id,
            "recorded_measurements": recorded,
            "source": "synthetic_structural_container",
        }
    ]


def derive_timeline(
    record_created_date: str, encounters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The clinical timeline as an INDEX over already-generated dated
    records (M8) -- never a source of new dates.

    Exactly two event types are emitted, both facts about the synthetic
    record itself: its creation, and the baseline assessment that owns
    the measurements. No diagnosis-onset, medication-start/stop or
    follow-up event is emitted: no evidence-backed per-patient date
    distribution exists for any of them (docs/M4_CLINICAL_EVIDENCE.md
    section 7), which is the same reason diagnosed_date/start_date are
    null throughout.

    One event per encounter, referencing it by id -- NOT one event per
    measurement. The measurements are already enumerated inside the
    encounter, so per-measurement events would be the duplicate
    representation this project's design rules forbid.

    Rebuilds the list from scratch every call rather than appending, so
    re-running it on an already-migrated record is idempotent.
    """
    timeline = [
        {
            "event_type": "synthetic_record_created",
            "date": record_created_date,
            "reference_id": None,
        }
    ]
    timeline.extend(
        {
            "event_type": enc["encounter_type"],
            "date": enc["date"],
            "reference_id": enc["encounter_id"],
        }
        for enc in encounters
    )
    return timeline


def derive_diagnoses(risk_factors: dict[str, Any], patient_id: str) -> list[dict[str, Any]]:
    """One Diagnosis-shaped dict per True flag in _SUPPORTED_CODES."""
    diagnoses = []
    for i, code in enumerate(_SUPPORTED_CODES, start=1):
        if risk_factors.get(code):
            diagnoses.append(
                {
                    "diagnosis_id": f"{patient_id}_DX{i:02d}",
                    "code": code,
                    "diagnosed_date": None,
                    "source": "derived_from_risk_factors",
                }
            )
    return diagnoses


def derive_medical_history(diagnoses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One chronic_condition entry per diagnosis, referencing it by id."""
    return [
        {
            "category": "chronic_condition",
            "description": dx["code"],
            "diagnosis_id": dx["diagnosis_id"],
            "event_date": dx["diagnosed_date"],
        }
        for dx in diagnoses
    ]


def derive_medications(
    diagnoses: list[dict[str, Any]], treated: dict[str, bool], patient_id: str
) -> list[dict[str, Any]]:
    """One Medication-shaped dict per diagnosis whose code was drawn
    `treated`, per generation.indian_population.sample_medication_treatment().
    Never resamples treatment status -- only constructs the record from an
    already-resolved outcome. `treated` may omit a code entirely (e.g. no
    diagnosis existed to draw treatment for) -- absent is equivalent to
    False."""
    medications = []
    i = 0
    for dx in diagnoses:
        drug_class = _DRUG_CLASS_BY_CODE.get(dx["code"])
        if drug_class is None or not treated.get(dx["code"], False):
            continue
        i += 1
        medications.append(
            {
                "medication_id": f"{patient_id}_MED{i:02d}",
                "drug_class": drug_class,
                "diagnosis_id": dx["diagnosis_id"],
                "current_status": "active",
                "start_date": None,
                "stop_date": None,
                "source": "derived_from_diagnosis_treatment_rate",
            }
        )
    return medications
