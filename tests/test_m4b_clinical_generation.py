"""M4B: generation-level tests for lipid panel / interpretations / HbA1c.

Complements tests/test_m4a_clinical_schema.py (schema-level) — these
tests exercise the actual generation functions in
generation/indian_population.py and the integrated build_patient()
pipeline.
"""

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from generation.indian_population import (  # noqa: E402
    derive_lipid_interpretations,
    load_config as load_indian_config,
    sample_hba1c,
    sample_lipid_panel,
)

BASE_CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")
INDIAN_CONFIG = load_indian_config()


# Test 1 — same seed -> same generated values
def test_same_seed_same_lipid_values():
    rng1 = np.random.default_rng(123)
    rng2 = np.random.default_rng(123)
    v1 = sample_lipid_panel(rng1, INDIAN_CONFIG, sex=0)
    v2 = sample_lipid_panel(rng2, INDIAN_CONFIG, sex=0)
    assert v1 == v2


# Test 2 — different seed -> valid (structurally sane) but different samples
def test_different_seed_gives_different_but_valid_samples():
    rng1 = np.random.default_rng(1)
    rng2 = np.random.default_rng(2)
    v1 = sample_lipid_panel(rng1, INDIAN_CONFIG, sex=0)
    v2 = sample_lipid_panel(rng2, INDIAN_CONFIG, sex=0)
    assert v1 != v2
    for v in (v1, v2):
        assert 30.0 <= v["ldl_mg_dl"] <= 300.0


# Test 3 — lipid values fall within configured/approved ranges
def test_lipid_values_within_approved_ranges():
    rng = np.random.default_rng(7)
    for sex in (0, 1):
        v = sample_lipid_panel(rng, INDIAN_CONFIG, sex)
        assert 100.0 <= v["total_cholesterol_mg_dl"] <= 320.0
        assert 50.0 <= v["triglycerides_mg_dl"] <= 400.0
        assert 20.0 <= v["hdl_mg_dl"] <= 90.0
        assert 30.0 <= v["ldl_mg_dl"] <= 300.0


# Test 3b — D019: no TC/HDL/TG triple is Friedewald-infeasible (TC < HDL + TG/5)
def test_no_infeasible_lipid_triples_at_scale():
    rng = np.random.default_rng(2024)
    infeasible = 0
    n = 20000
    for i in range(n):
        v = sample_lipid_panel(rng, INDIAN_CONFIG, sex=i % 2)
        raw = v["total_cholesterol_mg_dl"] - v["hdl_mg_dl"] - v["triglycerides_mg_dl"] / 5.0
        if raw < 0:
            infeasible += 1
    assert infeasible == 0


# Test 4 — lipid interpretations are derived from (recomputable from) raw values
def test_interpretations_are_recomputable_from_raw_values():
    rng = np.random.default_rng(99)
    v = sample_lipid_panel(rng, INDIAN_CONFIG, sex=1)
    interps = derive_lipid_interpretations(INDIAN_CONFIG, v, sex=1)
    recomputed = derive_lipid_interpretations(INDIAN_CONFIG, v, sex=1)
    assert interps == recomputed  # pure function: same input -> same output, always


# Test 5 — lipid_interpretations.dyslipidemia is a *computed* value with no
# independent randomness of its own (since D023, risk_factors.hyperlipidemia
# is derived from it too).
def test_lipid_interpretation_has_no_independent_randomness():
    v = {
        "total_cholesterol_mg_dl": 250.0,
        "triglycerides_mg_dl": 100.0,
        "hdl_mg_dl": 35.0,
        "ldl_mg_dl": 150.0,
    }
    results = [derive_lipid_interpretations(INDIAN_CONFIG, v, sex=0) for _ in range(5)]
    assert all(r == results[0] for r in results)  # identical every time, no RNG involved


# Test 6 — multiple lipid definitions remain internally consistent
def test_multiple_definitions_consistent_with_their_own_thresholds():
    v = {
        "total_cholesterol_mg_dl": 150.0,  # below both TC thresholds
        "triglycerides_mg_dl": 100.0,  # below both TG thresholds
        "hdl_mg_dl": 45.0,  # below male 40? no (45>=40, normal); irrelevant here, use male
        "ldl_mg_dl": 115.0,  # between LAI's 100 and NCEP's 130
    }
    interps = {i["definition"]: i for i in derive_lipid_interpretations(INDIAN_CONFIG, v, sex=0)}
    assert interps["NCEP_ATP_III"]["dyslipidemia"] is False  # LDL 115 < 130
    assert interps["LAI_2020"]["dyslipidemia"] is True  # LDL 115 >= 100
    assert "LDL" in interps["LAI_2020"]["components_abnormal"]
    assert "LDL" not in interps["NCEP_ATP_III"]["components_abnormal"]


# Test 7 — HbA1c generated correctly (range, unit handled at schema level)
def test_hba1c_generated_within_range_for_non_diabetic():
    rng = np.random.default_rng(55)
    for _ in range(20):
        h = sample_hba1c(rng, INDIAN_CONFIG, age=50.0, sex=0, diabetes=False)
        assert 4.0 <= h["value"] <= 6.4
        assert h["derivation"] == "observed_distribution_indiab12_ngt"


# Test 8 — v0.10 (D022): diabetics now get HbA1c from the diabetic
# distribution, tagged by treatment status (still conditional on the label).
def test_hba1c_for_diabetic_is_tagged_by_treatment():
    rng = np.random.default_rng(55)
    treated = sample_hba1c(rng, INDIAN_CONFIG, age=50.0, sex=0, diabetes=True, on_antidiabetic=True)
    untreated = sample_hba1c(rng, INDIAN_CONFIG, age=50.0, sex=0, diabetes=True, on_antidiabetic=False)
    assert 4.0 <= treated["value"] <= 18.0 and 4.0 <= untreated["value"] <= 18.0
    assert treated["confidence"] == "moderate" and untreated["confidence"] == "low"
    assert untreated["derivation"].startswith("borrowed")


# Test 9 — existing patient fields (demographics/risk_factors/ECG) remain
# unchanged by M4B, matching the pre-M4B reference values already
# established for PAT_000001 (seed 42, sequence 1) in M2C/M3/M3.5/M4A.
def test_existing_fields_unchanged_for_reference_patient():
    patient = build_patient(1, BASE_CONFIG)
    assert patient.patient_id == "PAT_000001"
    assert patient.demographics.age == 65.01  # v0.10: rounded to 2 dp, same draw
    assert patient.demographics.state == "Uttar Pradesh"
    assert patient.demographics.urban_rural == "urban"
    assert patient.risk_factors.bmi == 18.0
    assert patient.ecg.ecg_id == 11314


# Test 10 — missingness behavior matches M4B-0 design
def test_missingness_matches_design():
    diabetic_patient = None
    non_diabetic_patient = None
    for seq in range(1, 50):
        p = build_patient(seq, BASE_CONFIG)
        if p.risk_factors.diabetes and diabetic_patient is None:
            diabetic_patient = p
        if not p.risk_factors.diabetes and non_diabetic_patient is None:
            non_diabetic_patient = p
        if diabetic_patient and non_diabetic_patient:
            break

    assert non_diabetic_patient is not None
    assert non_diabetic_patient.lipid_panel is not None  # always populated
    assert non_diabetic_patient.labs is not None
    assert non_diabetic_patient.labs[0].analyte == "HbA1c"
    assert non_diabetic_patient.labs[0].value is not None

    if diabetic_patient is not None:
        assert diabetic_patient.lipid_panel is not None  # always populated regardless of diabetes
        assert diabetic_patient.labs[0].analyte == "HbA1c"  # v0.10: everyone has HbA1c


# Test 11 — serialization of a real generated patient remains valid
def test_generated_patient_serializes_and_round_trips():
    patient = build_patient(2, BASE_CONFIG)
    d = patient.to_dict()
    assert d["lipid_panel"]["ldl_mg_dl"] is not None
    assert len(d["lipid_interpretations"]) == 2
    round_tripped = json.loads(json.dumps(d))
    assert round_tripped == d


# Test 12 (existing suite passing) is verified by running the full suite,
# not a test within this file.
