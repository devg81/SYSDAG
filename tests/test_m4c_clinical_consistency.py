"""M4C: tests for validation/clinical_consistency.py.

Uses build_patient() for real integrated patients, plus small synthetic
fixtures (direct object mutation) for deliberately-broken cases, per this
milestone's TDD instruction.
"""

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from generation.indian_population import load_config as load_indian_config  # noqa: E402
from schemas.patient_schema import Lab, LipidInterpretation  # noqa: E402
from validation.clinical_consistency import (  # noqa: E402
    validate_clinical_consistency,
    validate_population_clinical_consistency,
)

BASE_CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")
INDIAN_CONFIG = load_indian_config()


def _patient_with_sex(seq: int, target_diabetes: bool | None = None):
    """Find a patient matching a target diabetes status within a small
    search window, for tests that need a specific branch."""
    for s in range(seq, seq + 200):
        p = build_patient(s, BASE_CONFIG)
        if target_diabetes is None or p.risk_factors.diabetes == target_diabetes:
            return p
    raise AssertionError("could not find a matching patient in the search window")


def _patient_with_interpretation(seq: int, target_dyslipidemia: bool):
    """Find a patient whose NCEP interpretation already naturally has the
    target value, WITHOUT mutating lipid_interpretations -- keeps the
    lipid_panel<->interpretation hard-consistency check untouched so these
    tests isolate only the hyperlipidemia<->interpretation relationship."""
    for s in range(seq, seq + 500):
        p = build_patient(s, BASE_CONFIG)
        ncep = next(i for i in p.lipid_interpretations if i.definition == "NCEP_ATP_III")
        if ncep.dyslipidemia == target_dyslipidemia:
            return p
    raise AssertionError("could not find a matching patient in the search window")


# Test 1 — valid integrated patient passes
def test_valid_integrated_patient_passes():
    patient = build_patient(1, BASE_CONFIG)
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert result.valid, result.errors
    assert "lipid_panel_interpretation_consistency" in result.checks_performed
    assert "diabetes_hba1c_consistency" in result.checks_performed


# Test 2 — invalid lipid interpretation is detected
def test_tampered_lipid_interpretation_is_detected():
    patient = build_patient(1, BASE_CONFIG)
    # Flip the stored interpretation without touching the raw values --
    # exactly the "LDL=85, hyperlipidemia=true under a definition where 85
    # doesn't qualify" failure mode this milestone is designed to catch.
    patient.lipid_interpretations[0].dyslipidemia = not patient.lipid_interpretations[0].dyslipidemia
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("does not match recomputation" in e for e in result.errors)


# Test 3 — missing raw lipid values are handled correctly (warning, not a crash/false-pass)
def test_missing_raw_lipid_values_handled():
    patient = build_patient(1, BASE_CONFIG)
    patient.lipid_panel.ldl_mg_dl = None
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert any("missing raw values" in w for w in result.warnings)
    # Not treated as a hard error -- we can't re-verify, but that's not
    # itself proof of a contradiction.
    assert not any("does not match recomputation" in e for e in result.errors)


# Test 4 — v0.10: a diabetic patient MISSING HbA1c is detected, and a
# non-diabetic HbA1c above the NGT range is rejected.
def test_diabetic_patient_missing_hba1c_is_detected():
    patient = _patient_with_sex(1, target_diabetes=True)
    patient.labs = []
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("missing the expected HbA1c" in e for e in result.errors)


def test_non_diabetic_hba1c_in_diabetic_range_is_detected():
    patient = _patient_with_sex(1, target_diabetes=False)
    patient.labs[0].value = 8.5
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid


def test_non_diabetic_patient_missing_hba1c_is_detected():
    patient = _patient_with_sex(1, target_diabetes=False)
    patient.labs = None
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("missing the expected HbA1c" in e for e in result.errors)


# Test 5 — invalid medication/diagnosis relationship: not implemented, so
# the validator must neither error on their expected absence nor invent a
# relationship -- but MUST warn if one is unexpectedly populated.
def test_unimplemented_domains_absent_is_not_an_error():
    # M4D implemented diagnoses/medical_history, M4E implemented
    # medications, and M8 implemented encounters (as a structural
    # baseline-assessment container -- see ENCOUNTER_TYPES); D020
    # implemented family_history. The domain still legitimately absent is
    # echo (scope entirely open); its absence must not error.
    patient = build_patient(1, BASE_CONFIG)
    assert patient.echo is None
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not any("echo" in e for e in result.errors)
    assert not any("family_history" in e for e in result.errors)


def test_unexpectedly_populated_unimplemented_domain_warns():
    patient = build_patient(1, BASE_CONFIG)
    # echo is Optional[dict] in the schema, so a dict is a structurally
    # legal value -- which is exactly why an unexpected one must warn.
    patient.echo = {"lvef": 55}  # should never happen today
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert any("echo is populated" in w for w in result.warnings)


def test_family_history_derivation_must_match_age_tier():
    patient = build_patient(1, BASE_CONFIG)
    wrong = (
        "parent_simulation_calibrated" if patient.demographics.age >= 45
        else "lasi_observed_45_plus"
    )
    patient.family_history = dict(patient.family_history, derivation=wrong)
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert any("family_history.derivation" in e for e in result.errors)


def test_encounters_are_now_generated_and_indexed_by_the_timeline():
    """M8's counterpart to the test above: encounters left the
    unimplemented list, so the pilot's referential-integrity rules must
    actually hold on a freshly built patient."""
    patient = build_patient(1, BASE_CONFIG)
    assert patient.encounters is not None and len(patient.encounters) == 1
    encounter = patient.encounters[0]
    assert encounter.encounter_type == "synthetic_baseline_assessment"
    assert encounter.patient_id == patient.patient_id
    assert encounter.recorded_measurements  # never an empty container
    referenced = {
        e.reference_id
        for e in patient.clinical_timeline
        if e.reference_id and e.event_type != "condition_onset_modeled"
    }
    assert referenced == {encounter.encounter_id}
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert result.valid, result.errors


# Test 6/7/8 — invalid timeline reference / temporal ordering / invalid
# date: the only real dated relationship that exists today is
# clinical_timeline vs. labs.measured_at (see docs/M4C_CONSISTENCY_AUDIT.md
# -- no diagnosis/medication dates exist yet to test ordering against).
def test_mismatched_lab_measured_at_is_detected():
    patient = _patient_with_sex(1, target_diabetes=False)
    patient.labs[0].measured_at = "1999-01-01"  # deliberately wrong
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("does not match" in e and "clinical_timeline" in e for e in result.errors)


# Test 9 — existing valid M1-M4B patient remains valid
def test_existing_patient_remains_valid():
    patient = build_patient(1, BASE_CONFIG)
    assert patient.validation.validated  # structural, from build_patient() itself
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert result.valid, result.errors


# Test 10 — ECG metadata remains structurally compatible (delegated to
# validation/structural.py, not reimplemented -- this test confirms the
# delegation assumption holds, not a new ECG rule)
def test_ecg_untouched_and_still_structurally_valid():
    patient = build_patient(1, BASE_CONFIG)
    assert patient.ecg is not None
    assert patient.ecg.signal_shape == [1000, 12]
    assert patient.validation.validated


# Test 11 — missingness rules behave correctly across the population
def test_missingness_rules_correct_across_population():
    patients = [build_patient(seq, BASE_CONFIG) for seq in range(1, 21)]
    for p in patients:
        assert p.lipid_panel is not None  # always populated
        # v0.10: HbA1c for everyone; [] / None are never produced for labs.
        assert p.labs is not None and p.labs[0].analyte == "HbA1c"


# Test 12 — D023 (v0.11, reverses D014): risk_factors.hyperlipidemia is
# DERIVED from the NCEP_ATP_III interpretation, so the generator always
# agrees and the validator rejects a disagreement in either direction.
def test_generated_hyperlipidemia_equals_ncep_interpretation():
    for interp_target in (True, False):
        patient = _patient_with_interpretation(1, target_dyslipidemia=interp_target)
        assert patient.risk_factors.hyperlipidemia is interp_target
        result = validate_clinical_consistency(patient, INDIAN_CONFIG)
        assert result.valid, result.errors
        assert "hyperlipidemia_derived_from_lipid_interpretations" in result.checks_performed


def test_hyperlipidemia_true_with_normal_panel_is_rejected():
    patient = _patient_with_interpretation(1, target_dyslipidemia=False)
    patient.risk_factors.hyperlipidemia = True  # the old PAT_000095 pattern
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("risk_factors.hyperlipidemia=True does not match" in e for e in result.errors)


def test_hyperlipidemia_false_with_abnormal_panel_is_rejected():
    patient = _patient_with_interpretation(1, target_dyslipidemia=True)
    patient.risk_factors.hyperlipidemia = False
    result = validate_clinical_consistency(patient, INDIAN_CONFIG)
    assert not result.valid
    assert any("risk_factors.hyperlipidemia=False does not match" in e for e in result.errors)


def test_hyperlipidemia_follows_ncep_not_lai():
    # LAI and NCEP differ only for 100 <= LDL < 130; the flag must follow NCEP.
    for s in range(1, 2000):
        p = build_patient(s, BASE_CONFIG)
        by_def = {i.definition: i.dyslipidemia for i in p.lipid_interpretations}
        if by_def["LAI_2020"] and not by_def["NCEP_ATP_III"]:
            assert p.risk_factors.hyperlipidemia is False
            return
    raise AssertionError("no LAI-only dyslipidemia patient in the search window")


def test_batch_validation_is_linear_not_quadratic_in_call_count():
    patients = [build_patient(seq, BASE_CONFIG) for seq in range(1, 11)]
    results = validate_population_clinical_consistency(patients, INDIAN_CONFIG)
    assert len(results) == 10
    assert all(r.valid for r in results)
