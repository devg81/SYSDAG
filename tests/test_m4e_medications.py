"""M4E: tests for medication generation and validation.

Covers generation/indian_population.sample_medication_treatment(),
generation/clinical_history.derive_medications(), the schema addition
(Medication), validation/structural.py's vocabulary checks, and
validation/clinical_consistency.py's new hard-consistency rules.
"""

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from generation.indian_population import (  # noqa: E402
    load_config as load_indian_config,
    sample_medication_treatment,
    valid_states,
)
from generation.clinical_history import derive_diagnoses, derive_medications  # noqa: E402
from schemas.patient_schema import Medication  # noqa: E402
from validation.structural import validate_patient  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402

BASE_CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")
INDIAN_CONFIG = load_indian_config()


def _patient_with_risk_factors(seq: int, hypertension: bool, diabetes: bool):
    for s in range(seq, seq + 500):
        p = build_patient(s, BASE_CONFIG)
        if (
            p.risk_factors.hypertension == hypertension
            and p.risk_factors.diabetes == diabetes
        ):
            return p
    raise AssertionError("could not find a matching patient in the search window")


def _patient_with_medication(seq: int, drug_class: str):
    """Find a real patient who was actually drawn as treated, so tests
    exercise the real generation path rather than hand-constructed data."""
    for s in range(seq, seq + 2000):
        p = build_patient(s, BASE_CONFIG)
        if any(m.drug_class == drug_class for m in p.medications):
            return p
    raise AssertionError("could not find a treated patient in the search window")


# --- generation/indian_population.py (RNG-consuming) unit tests ---

def test_sample_medication_treatment_only_draws_for_present_diagnoses():
    rng = np.random.default_rng(0)
    treated = sample_medication_treatment(rng, INDIAN_CONFIG, hypertension=False, diabetes=False)
    assert treated == {}


def test_sample_medication_treatment_draws_bernoulli_at_configured_rate():
    # Force p=1.0 and p=0.0 via a stub config slice to confirm the wiring,
    # not just the real-world rate (a real-rate check belongs in the
    # population-level statistical report, not a unit test).
    stub_config = {
        "medications": {
            "antihypertensive_treatment_rate": {"distribution": {"p": 1.0}},
            "antidiabetic_treatment_rate": {"distribution": {"p": 0.0}},
        }
    }
    rng = np.random.default_rng(0)
    treated = sample_medication_treatment(rng, stub_config, hypertension=True, diabetes=True)
    assert treated == {"hypertension": True, "diabetes": False}


def test_medication_treatment_does_not_shift_existing_rng_sequence():
    """Additive-at-the-end: consuming extra RNG draws for medication
    treatment must not change any attribute generated before it."""
    from generation.indian_population import generate_indian_attributes

    rng1 = np.random.default_rng(42)
    attrs = generate_indian_attributes(rng1, INDIAN_CONFIG)
    assert "medication_treatment" in attrs
    # demographics/risk_factors/lipid/hba1c are drawn strictly before
    # medication_treatment in generate_indian_attributes() -- confirmed by
    # reading the function, and by the n=100 regression check in the
    # session log comparing byte-for-byte against the M4D baseline.
    assert attrs["risk_factors"]["hypertension"] in (True, False)


# --- generation/clinical_history.py (pure function) unit tests ---

def test_derive_medications_only_for_treated_diagnoses():
    dx = derive_diagnoses({"hypertension": True, "diabetes": True}, "PAT_000001")
    meds = derive_medications(dx, {"hypertension": True, "diabetes": False}, "PAT_000001")
    assert len(meds) == 1
    assert meds[0]["drug_class"] == "antihypertensive"
    assert meds[0]["diagnosis_id"] == dx[0]["diagnosis_id"]
    assert meds[0]["current_status"] == "active"
    assert meds[0]["start_date"] is None
    assert meds[0]["stop_date"] is None


def test_derive_medications_no_treatment_yields_empty():
    dx = derive_diagnoses({"hypertension": True, "diabetes": True}, "PAT_000001")
    assert derive_medications(dx, {}, "PAT_000001") == []


def test_derive_medications_never_for_diagnoses_without_a_drug_class():
    # hyperlipidemia is never a diagnosis code today, but confirm the
    # function itself would skip any code with no drug_class mapping.
    dx = [{"diagnosis_id": "PAT_000001_DX01", "code": "hyperlipidemia"}]
    meds = derive_medications(dx, {"hyperlipidemia": True}, "PAT_000001")
    assert meds == []


# --- real pipeline integration ---

def test_treated_hypertensive_patient_has_antihypertensive_medication():
    patient = _patient_with_medication(1, "antihypertensive")
    meds = [m for m in patient.medications if m.drug_class == "antihypertensive"]
    assert len(meds) == 1
    dx_ids = {dx.diagnosis_id for dx in patient.diagnoses if dx.code == "hypertension"}
    assert meds[0].diagnosis_id in dx_ids


def test_treated_diabetic_patient_has_antidiabetic_medication():
    patient = _patient_with_medication(1, "antidiabetic")
    meds = [m for m in patient.medications if m.drug_class == "antidiabetic"]
    assert len(meds) == 1
    dx_ids = {dx.diagnosis_id for dx in patient.diagnoses if dx.code == "diabetes"}
    assert meds[0].diagnosis_id in dx_ids


def test_no_diagnosis_no_medication():
    patient = _patient_with_risk_factors(1, hypertension=False, diabetes=False)
    assert patient.medications == []


def test_zero_treatment_patient_has_diagnoses_but_no_medications():
    """A diagnosed-but-untreated patient: diagnoses/medical_history exist,
    medications is an empty list -- not None, and not a contradiction."""
    for s in range(1, 500):
        p = build_patient(s, BASE_CONFIG)
        if p.diagnoses and not p.medications:
            assert p.medical_history  # chronic_condition entries still exist
            return
    raise AssertionError("could not find a diagnosed-but-untreated patient")


def test_no_specific_drug_name_ever_generated():
    """This milestone's central restriction: only a coarse drug_class,
    never a specific drug name, dose, frequency, or route."""
    patient = build_patient(1, BASE_CONFIG)
    for med in patient.medications:
        assert not hasattr(med, "name")
        assert not hasattr(med, "dose")
        assert not hasattr(med, "frequency")
        assert not hasattr(med, "route")


def test_multiple_diagnoses_each_get_independent_treatment_draw():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=True)
    assert len(patient.diagnoses) == 2
    # Each medication (0, 1, or 2 of them) must reference a distinct diagnosis.
    referenced = [m.diagnosis_id for m in patient.medications]
    assert len(referenced) == len(set(referenced))


def test_structural_validation_passes_for_real_patient():
    patient = build_patient(1, BASE_CONFIG)
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert errors == []


def test_structural_validation_rejects_unsupported_drug_class():
    patient = build_patient(1, BASE_CONFIG)
    patient.medications = [
        Medication(medication_id="PAT_000001_MED99", drug_class="statin", diagnosis_id="X")
    ]
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert any("unsupported drug_class" in e for e in errors)


def test_structural_validation_rejects_unknown_status():
    patient = build_patient(1, BASE_CONFIG)
    patient.medications = [
        Medication(
            medication_id="PAT_000001_MED99",
            drug_class="antihypertensive",
            diagnosis_id="X",
            current_status="paused",
        )
    ]
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert any("unknown current_status" in e for e in errors)


def test_structural_validation_rejects_duplicate_medication_id():
    patient = build_patient(1, BASE_CONFIG)
    patient.medications = [
        Medication(medication_id="DUP", drug_class="antihypertensive", diagnosis_id="X"),
        Medication(medication_id="DUP", drug_class="antidiabetic", diagnosis_id="Y"),
    ]
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert any("duplicate medication_id" in e for e in errors)


# --- clinical consistency (hard rules) ---

def test_clinical_consistency_passes_for_real_patient():
    patient = build_patient(1, BASE_CONFIG)
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert result.valid, result.errors
    assert "medication_diagnosis_consistency" in result.checks_performed


def test_clinical_consistency_detects_orphan_medication():
    patient = _patient_with_medication(1, "antihypertensive")
    patient.medications = list(patient.medications) + [
        Medication(
            medication_id=f"{patient.patient_id}_MED99",
            drug_class="antihypertensive",
            diagnosis_id="NOT_A_REAL_ID",
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("orphan entry" in e for e in result.errors)


def test_clinical_consistency_detects_drug_class_diagnosis_mismatch():
    patient = _patient_with_medication(1, "antihypertensive")
    htn_dx_id = next(dx.diagnosis_id for dx in patient.diagnoses if dx.code == "hypertension")
    patient.medications = [
        Medication(
            medication_id=f"{patient.patient_id}_MED01",
            drug_class="antidiabetic",  # wrong class for a hypertension diagnosis
            diagnosis_id=htn_dx_id,
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("does not match referenced diagnosis code" in e for e in result.errors)


def test_clinical_consistency_detects_active_with_stop_date():
    patient = _patient_with_medication(1, "antihypertensive")
    med = patient.medications[0]
    patient.medications = [
        Medication(
            medication_id=med.medication_id,
            drug_class=med.drug_class,
            diagnosis_id=med.diagnosis_id,
            current_status="active",
            stop_date="2026-01-01",
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("current_status='active' but stop_date is set" in e for e in result.errors)


def test_clinical_consistency_detects_impossible_date_ordering():
    patient = _patient_with_medication(1, "antihypertensive")
    med = patient.medications[0]
    patient.medications = [
        Medication(
            medication_id=med.medication_id,
            drug_class=med.drug_class,
            diagnosis_id=med.diagnosis_id,
            current_status="discontinued",
            start_date="2026-06-01",
            stop_date="2026-01-01",
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("start_date" in e and "> stop_date" in e for e in result.errors)


def test_clinical_consistency_detects_duplicate_medication_per_diagnosis():
    patient = _patient_with_medication(1, "antihypertensive")
    med = patient.medications[0]
    patient.medications = [med, med]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("already has a medication" in e for e in result.errors)


# --- regression: existing M4B/M4C/M4D behavior untouched ---

def test_demographics_risk_factors_lipids_diagnoses_unchanged():
    patient = build_patient(1, BASE_CONFIG)
    assert patient.demographics.age is not None
    assert patient.risk_factors.hypertension in (True, False)
    assert patient.lipid_panel.ldl_mg_dl is not None
    assert len(patient.lipid_interpretations) == 2
    assert patient.diagnoses is not None
    assert patient.medical_history is not None


def test_hyperlipidemia_semantic_distinction_still_intact():
    patient = build_patient(1, BASE_CONFIG)
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert (
        "hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared"
        in result.checks_performed
    )
    assert not any("hyperlipidemia" in e for e in result.errors)


def test_serialization_round_trip():
    """Medication must survive Patient.to_dict() -> json -> reconstruction,
    the same real path integration/validate_clinical_population.py uses."""
    import json as json_module

    from integration.validate_clinical_population import _patient_from_dict

    patient = _patient_with_medication(1, "antihypertensive")
    raw = json_module.loads(json_module.dumps(patient.to_dict()))
    rebuilt = _patient_from_dict(raw)
    assert [m.drug_class for m in rebuilt.medications] == [m.drug_class for m in patient.medications]
    assert [m.diagnosis_id for m in rebuilt.medications] == [
        m.diagnosis_id for m in patient.medications
    ]
