"""M2C milestone checks: Indian-conditioned demographics + risk factors.

Maps to the 11 tests specified for M2C (session log has the full mapping).
Tests 10 (M1 regression) and 11 (ECG regression) live in
tests/test_stage2_foundation.py and are unaffected by this file.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from schemas.patient_schema import SMOKING_STATUSES  # noqa: E402
from generation.indian_population import (  # noqa: E402
    load_config as load_indian_config,
    valid_states,
    validate_config,
)

BASE_CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")
INDIAN_CONFIG = load_indian_config()
STATES = valid_states(INDIAN_CONFIG)


def _build(sequence: int):
    return build_patient(sequence, BASE_CONFIG, INDIAN_CONFIG)


# Test 1 — a valid Indian-conditioned patient can be generated
def test_single_patient_generates_and_validates():
    patient = _build(1)
    assert patient.validation.validated, patient.validation.errors


# Test 2 — required demographic fields
def test_required_demographic_fields_present():
    patient = _build(1)
    d = patient.demographics
    assert d.age is not None
    assert d.sex in (0, 1)
    assert d.state is not None
    assert d.urban_rural is not None


# Test 3 — required risk factors
def test_required_risk_factors_present():
    patient = _build(1)
    rf = patient.risk_factors
    assert rf is not None
    assert rf.bmi is not None
    assert rf.smoking_status is not None
    assert rf.hypertension is not None
    assert rf.diabetes is not None
    assert rf.hyperlipidemia is not None


# Test 4 — state validation
def test_state_is_from_canonical_list():
    for seq in range(1, 21):
        patient = _build(seq)
        assert patient.demographics.state in STATES


# Test 5 — urban/rural validation
def test_urban_rural_is_controlled_value():
    for seq in range(1, 21):
        patient = _build(seq)
        assert patient.demographics.urban_rural in ("urban", "rural")


# Test 6 — age constraints
def test_age_within_configured_bounds():
    dist = INDIAN_CONFIG["demographics"]["age"]["distribution"]
    for seq in range(1, 21):
        patient = _build(seq)
        assert dist["min"] <= patient.demographics.age <= dist["max"]


# Test 7 — BMI constraints
def test_bmi_within_plausible_range():
    for seq in range(1, 21):
        patient = _build(seq)
        bmi = patient.risk_factors.bmi
        assert 10.0 <= bmi <= 80.0  # matches validation/structural.py's bound


# Test 8 — probability validation
def test_config_probabilities_are_valid():
    errors = validate_config(INDIAN_CONFIG)
    assert errors == []


def test_smoking_status_is_controlled_value():
    for seq in range(1, 21):
        patient = _build(seq)
        assert patient.risk_factors.smoking_status in SMOKING_STATUSES


# Test 9 — reproducibility
def test_reproducibility_same_config_same_seed_same_output():
    p1 = _build(5)
    p2 = _build(5)
    assert p1.demographics.age == p2.demographics.age
    assert p1.demographics.sex == p2.demographics.sex
    assert p1.demographics.state == p2.demographics.state
    assert p1.demographics.urban_rural == p2.demographics.urban_rural
    assert p1.risk_factors.bmi == p2.risk_factors.bmi
    assert p1.risk_factors.smoking_status == p2.risk_factors.smoking_status
    assert p1.risk_factors.hypertension == p2.risk_factors.hypertension
    assert p1.risk_factors.diabetes == p2.risk_factors.diabetes
    assert p1.risk_factors.hyperlipidemia == p2.risk_factors.hyperlipidemia


def test_family_history_is_populated_with_a_derivation_tag():
    # D020 superseded D004's "leave null" for family history.
    patient = _build(1)
    assert set(patient.family_history) == {"diabetes", "cardiovascular_disease", "derivation"}
