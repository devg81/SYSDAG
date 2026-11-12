"""D024 (v0.12; -jatin): rule-based LAI risk tier on the LAI_2020 interpretation.

Deliberately avoids build_patient() (needs PTB-XL + pandas): it tests the pure
derivation function, the generator's attribute output, and the validator on a
committed v0.12 review sample, so it runs on any machine with numpy + PyYAML.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generation.indian_population import (  # noqa: E402
    derive_lai_risk,
    generate_indian_attributes,
    load_config,
)
from integration.migrate_v07_to_v08 import _dict_to_patient  # noqa: E402
from schemas.patient_schema import LAI_RISK_CATEGORIES  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402

CFG = load_config()
SAMPLE = REPO_ROOT / "review_samples_v012" / "urban_UP_age65_PAT_000001.json"
GOOD_LIPIDS = {"hdl_mg_dl": 60.0, "ldl_mg_dl": 90.0}


def _risk(age=30.0, sex=0, smoking="never", htn=False, dm=False, lipids=GOOD_LIPIDS):
    return derive_lai_risk(CFG, age, sex, smoking, htn, dm, lipids)


def test_no_risk_factors_is_low_with_goal_100():
    r = _risk()
    assert r["risk_category"] == "low" and r["ldl_goal_mg_dl"] == 100.0
    assert r["risk_factors_counted"] == [] and r["ldl_above_goal"] is False


def test_age_threshold_is_sex_specific():
    assert _risk(age=45.0, sex=0)["risk_factors_counted"] == ["age"]  # man 45 counts
    assert _risk(age=50.0, sex=1)["risk_factors_counted"] == []  # woman 50 does not
    assert _risk(age=55.0, sex=1)["risk_factors_counted"] == ["age"]


def test_low_hdl_threshold_is_sex_specific():
    lipids = {"hdl_mg_dl": 45.0, "ldl_mg_dl": 90.0}
    assert "low_hdl" not in _risk(sex=0, lipids=lipids)["risk_factors_counted"]  # men < 40
    assert "low_hdl" in _risk(sex=1, lipids=lipids)["risk_factors_counted"]  # women < 50


def test_only_current_smoking_counts():
    assert _risk(smoking="former")["risk_factors_counted"] == []
    assert _risk(smoking="current")["risk_factors_counted"] == ["current_smoking"]


def test_non_diabetic_tiers_by_count():
    assert _risk(htn=True)["risk_category"] == "low"  # 1 RF
    assert _risk(htn=True, smoking="current")["risk_category"] == "moderate"  # 2 RF
    three = _risk(age=50.0, htn=True, smoking="current")
    assert three["risk_category"] == "high" and three["ldl_goal_mg_dl"] == 70.0  # 3 RF


def test_diabetes_tiers():
    assert _risk(dm=True)["risk_category"] == "high"  # diabetes + 0 RF
    assert _risk(dm=True, htn=True)["risk_category"] == "high"  # diabetes + 1 RF
    vh = _risk(dm=True, htn=True, smoking="current")
    assert vh["risk_category"] == "very_high" and vh["ldl_goal_mg_dl"] == 50.0  # diabetes + 2 RF


def test_ldl_above_goal_is_inclusive():
    at_goal = {"hdl_mg_dl": 60.0, "ldl_mg_dl": 100.0}
    assert _risk(lipids=at_goal)["ldl_above_goal"] is True


def test_generator_attaches_tier_to_lai_only_and_uses_no_rng():
    for seed in range(43, 143):
        a = generate_indian_attributes(np.random.default_rng(seed), CFG)
        by_def = {i["definition"]: i for i in a["lipid_interpretations"]}
        assert by_def["LAI_2020"]["risk_category"] in LAI_RISK_CATEGORIES
        assert "risk_category" not in by_def["NCEP_ATP_III"]
    # Same seed -> identical output (the tier is a pure function of the record).
    a1 = generate_indian_attributes(np.random.default_rng(99), CFG)
    a2 = generate_indian_attributes(np.random.default_rng(99), CFG)
    assert a1 == a2


def _sample_patient():
    record = json.loads(SAMPLE.read_text(encoding="utf-8"))
    record["validation"].pop("clinical_consistency", None)
    return _dict_to_patient(record)


def test_v012_sample_passes_lai_check():
    result = validate_clinical_consistency(_sample_patient(), CFG)
    assert result.valid, result.errors
    assert "lai_risk_tier_consistency" in result.checks_performed


def test_tampered_risk_category_is_rejected():
    patient = _sample_patient()
    lai = next(i for i in patient.lipid_interpretations if i.definition == "LAI_2020")
    lai.risk_category = "low" if lai.risk_category != "low" else "high"
    result = validate_clinical_consistency(patient, CFG)
    assert not result.valid
    assert any("risk_category" in e and "D024" in e for e in result.errors)


def test_risk_fields_on_ncep_are_rejected():
    patient = _sample_patient()
    ncep = next(i for i in patient.lipid_interpretations if i.definition == "NCEP_ATP_III")
    ncep.risk_category = "high"
    result = validate_clinical_consistency(patient, CFG)
    assert not result.valid
    assert any("non-LAI definition" in e for e in result.errors)


def test_v011_record_without_tier_is_still_accepted():
    # Older records simply lack the optional fields: the check does not fire.
    record = json.loads((REPO_ROOT / "review_samples_v011" / SAMPLE.name).read_text(encoding="utf-8"))
    record["validation"].pop("clinical_consistency", None)
    record = copy.deepcopy(record)
    result = validate_clinical_consistency(_dict_to_patient(record), CFG)
    assert not any("D024" in e for e in result.errors)
