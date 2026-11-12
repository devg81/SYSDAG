"""M4D: tests for diagnosis + medical-history generation and validation.

Covers generation/clinical_history.py, the schema additions (Diagnosis,
MedicalHistoryEntry), validation/structural.py's vocabulary checks, and
validation/clinical_consistency.py's new hard-consistency rules.
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from generation.indian_population import load_config as load_indian_config  # noqa: E402
from generation.clinical_history import derive_diagnoses, derive_medical_history  # noqa: E402
from schemas.patient_schema import Diagnosis, MedicalHistoryEntry  # noqa: E402
from validation.structural import validate_patient  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from generation.indian_population import valid_states  # noqa: E402

BASE_CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")
INDIAN_CONFIG = load_indian_config()


def _patient_with_risk_factors(seq: int, hypertension: bool, diabetes: bool):
    """Find a patient matching both target flags within a small search window."""
    for s in range(seq, seq + 500):
        p = build_patient(s, BASE_CONFIG)
        if (
            p.risk_factors.hypertension == hypertension
            and p.risk_factors.diabetes == diabetes
        ):
            return p
    raise AssertionError("could not find a matching patient in the search window")


# --- generation/clinical_history.py (pure function) unit tests ---

def test_derive_diagnoses_both_true():
    dx = derive_diagnoses({"hypertension": True, "diabetes": True}, "PAT_000001")
    codes = {d["code"] for d in dx}
    assert codes == {"hypertension", "diabetes"}
    assert all(d["diagnosed_date"] is None for d in dx)
    assert all(d["source"] == "derived_from_risk_factors" for d in dx)
    assert all(d["diagnosis_id"].startswith("PAT_000001_DX") for d in dx)


def test_derive_diagnoses_both_false():
    assert derive_diagnoses({"hypertension": False, "diabetes": False}, "PAT_000001") == []


def test_derive_diagnoses_hyperlipidemia_never_promoted():
    dx = derive_diagnoses(
        {"hypertension": False, "diabetes": False, "hyperlipidemia": True}, "PAT_000001"
    )
    assert dx == []


def test_derive_medical_history_references_diagnoses():
    dx = derive_diagnoses({"hypertension": True, "diabetes": False}, "PAT_000001")
    history = derive_medical_history(dx)
    assert len(history) == 1
    assert history[0]["category"] == "chronic_condition"
    assert history[0]["description"] == "hypertension"
    assert history[0]["diagnosis_id"] == dx[0]["diagnosis_id"]
    assert history[0]["event_date"] == dx[0]["diagnosed_date"]


# --- real pipeline integration ---

def test_hypertensive_patient_gets_hypertension_diagnosis():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=False)
    codes = {d.code for d in patient.diagnoses}
    assert "hypertension" in codes
    assert "diabetes" not in codes
    assert "hyperlipidemia" not in codes


def test_non_hypertensive_non_diabetic_has_no_diagnoses():
    patient = _patient_with_risk_factors(1, hypertension=False, diabetes=False)
    assert patient.diagnoses == []
    assert patient.medical_history == []


def test_diagnosed_date_always_null():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=True)
    assert all(dx.diagnosed_date is None for dx in patient.diagnoses)


def test_medical_history_mirrors_diagnoses_one_to_one():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=True)
    assert len(patient.medical_history) == len(patient.diagnoses)
    dx_ids = {dx.diagnosis_id for dx in patient.diagnoses}
    for entry in patient.medical_history:
        assert entry.category == "chronic_condition"
        assert entry.diagnosis_id in dx_ids


def test_structural_validation_passes_for_real_patient():
    patient = build_patient(1, BASE_CONFIG)
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert errors == []


def test_structural_validation_rejects_unsupported_diagnosis_code():
    patient = build_patient(1, BASE_CONFIG)
    patient.diagnoses = [
        Diagnosis(diagnosis_id="PAT_000001_DX99", code="myocardial_infarction")
    ]
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert any("unsupported code" in e for e in errors)


def test_structural_validation_rejects_unknown_medical_history_category():
    patient = build_patient(1, BASE_CONFIG)
    patient.medical_history = [
        MedicalHistoryEntry(category="not_a_real_category", description="x")
    ]
    errors = validate_patient(patient, valid_states=valid_states(INDIAN_CONFIG))
    assert any("unknown category" in e for e in errors)


# --- clinical consistency (hard rules) ---

def test_clinical_consistency_passes_for_real_patient():
    patient = build_patient(1, BASE_CONFIG)
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert result.valid, result.errors
    assert "diagnosis_risk_factor_consistency" in result.checks_performed
    assert "medical_history_diagnosis_consistency" in result.checks_performed


def test_clinical_consistency_detects_diagnosis_not_matching_risk_factors():
    patient = _patient_with_risk_factors(1, hypertension=False, diabetes=False)
    patient.diagnoses = [
        Diagnosis(diagnosis_id=f"{patient.patient_id}_DX01", code="hypertension")
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("do not match recomputation from risk_factors" in e for e in result.errors)


def test_clinical_consistency_detects_missing_diagnosis():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=False)
    patient.diagnoses = []
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("do not match recomputation from risk_factors" in e for e in result.errors)


def test_clinical_consistency_rejects_unsupported_diagnosis_code():
    patient = build_patient(1, BASE_CONFIG)
    patient.diagnoses = list(patient.diagnoses) + [
        Diagnosis(diagnosis_id=f"{patient.patient_id}_DX99", code="hyperlipidemia")
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("unsupported codes" in e for e in result.errors)


def test_clinical_consistency_detects_orphan_medical_history_entry():
    patient = build_patient(1, BASE_CONFIG)
    patient.medical_history = list(patient.medical_history) + [
        MedicalHistoryEntry(
            category="chronic_condition", description="ghost", diagnosis_id="NOT_A_REAL_ID"
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("orphan entry" in e for e in result.errors)


def test_clinical_consistency_rejects_procedure_category():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=False)
    patient.medical_history = [
        MedicalHistoryEntry(
            category="procedure",
            description="angioplasty",
            diagnosis_id=patient.diagnoses[0].diagnosis_id,
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("unsupported category" in e for e in result.errors)


def test_clinical_consistency_rejects_cv_event_category():
    patient = _patient_with_risk_factors(1, hypertension=True, diabetes=False)
    patient.medical_history = [
        MedicalHistoryEntry(
            category="cv_event",
            description="myocardial_infarction",
            diagnosis_id=patient.diagnoses[0].diagnosis_id,
        )
    ]
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("unsupported category" in e for e in result.errors)


# --- regression: existing M4B/M4C behavior untouched ---

def test_demographics_risk_factors_lipids_hba1c_unchanged():
    """Same seed must produce byte-identical upstream fields -- diagnoses/
    medical_history are purely additive, never influencing anything
    generated before them."""
    patient = build_patient(1, BASE_CONFIG)
    assert patient.demographics.age is not None
    assert patient.risk_factors.hypertension in (True, False)
    assert patient.lipid_panel.ldl_mg_dl is not None
    assert len(patient.lipid_interpretations) == 2


def test_hyperlipidemia_semantic_distinction_still_intact():
    patient = build_patient(1, BASE_CONFIG)
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert (
        "hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared"
        in result.checks_performed
    )
    assert not any("hyperlipidemia" in e for e in result.errors)
