"""v0.10 (D022) -- regression tests for the 9 behaviours the 2026-11-12
review asked to protect, plus the contract of each review fix."""

from __future__ import annotations

import math

import numpy as np
import pytest

from generation.indian_population import (
    derive_air_quality,
    derive_lipid_interpretations,
    generate_indian_attributes,
    load_config,
    sample_blood_pressure,
    sample_lipid_panel,
)
from integration.build_patient import build_patient, load_config as load_base_config
from validation.clinical_consistency import validate_clinical_consistency
from pathlib import Path

CFG = load_config()
BASE = load_base_config(Path(__file__).resolve().parents[1] / "configs" / "base.yaml")
ATTRS = [generate_indian_attributes(np.random.default_rng(42 + i), CFG) for i in range(1, 3001)]
PATIENTS = [build_patient(seq, BASE, CFG) for seq in (1, 11, 13, 15, 95, 19321, 33933, 78682)]


# ---- protected 1: LDL is Friedewald, exactly, with no clamp/floor ---------
def test_ldl_is_exact_friedewald_and_never_clamped():
    ldls = []
    for a in ATTRS:
        lp = a["lipid_panel"]
        implied = lp["total_cholesterol_mg_dl"] - lp["hdl_mg_dl"] - lp["triglycerides_mg_dl"] / 5
        assert abs(lp["ldl_mg_dl"] - implied) <= 0.11
        assert lp["ldl_mg_dl"] >= 30.0 and lp["triglycerides_mg_dl"] <= 400.0
        ldls.append(lp["ldl_mg_dl"])
    # v0.9 piled 7.7% exactly at 30.0; a continuous draw puts ~0 on any value.
    assert ldls.count(30.0) <= 3
    assert max(ldls.count(v) for v in set(ldls)) <= 10


def test_tg_hdl_are_negatively_correlated():
    tg = np.log([a["lipid_panel"]["triglycerides_mg_dl"] for a in ATTRS])
    hdl = np.array([a["lipid_panel"]["hdl_mg_dl"] for a in ATTRS])
    assert np.corrcoef(tg, hdl)[0, 1] < -0.2


# ---- protected 2: BP conditional on the label, treated left free ----------
def test_bp_respects_hypertension_label():
    rng = np.random.default_rng(7)
    treated_controlled = 0
    for _ in range(400):
        n = sample_blood_pressure(rng, CFG, 60.0, 0, False, False)
        assert n["systolic_mm_hg"] < 140 and n["diastolic_mm_hg"] < 90
        r = sample_blood_pressure(rng, CFG, 60.0, 0, True, False)
        assert r["systolic_mm_hg"] >= 140 or r["diastolic_mm_hg"] >= 90
        t = sample_blood_pressure(rng, CFG, 60.0, 0, True, True)
        treated_controlled += t["systolic_mm_hg"] < 140 and t["diastolic_mm_hg"] < 90
    assert treated_controlled > 0  # unconstrained, not forced high


# ---- protected 3: honest flags --------------------------------------------
def test_extrapolation_flag_and_confidence():
    for a in ATTRS:
        bp, d = a["blood_pressure"], a["demographics"]
        limit = 54 if d["sex"] == 0 else 49
        assert bp["extrapolated_beyond_source_age_range"] == (d["age"] >= limit + 1)
        assert bp["confidence"] == ("low" if bp["extrapolated_beyond_source_age_range"] else "moderate")
        aq = a["air_quality"]
        assert (aq["aqi"] is None) == (aq["unavailable_reason"] is not None)


# ---- protected 4: cross references valid (diagnosis->med->encounter) ------
def test_built_patients_pass_clinical_consistency():
    for p in PATIENTS:
        result = validate_clinical_consistency(p, CFG)
        assert p.validation.validated, p.validation.errors
        assert result.valid, (p.patient_id, result.errors)
        dx_ids = {dx.diagnosis_id for dx in p.diagnoses}
        assert all(m.diagnosis_id in dx_ids for m in p.medications)
        assert "labs.HbA1c" in p.encounters[0].recorded_measurements


# ---- protected 5: provenance ----------------------------------------------
def test_provenance_lists_sources():
    prov = PATIENTS[0].provenance
    assert prov.schema_version == "0.11"
    assert any("INDIAB-13" in s for s in prov.source_datasets)
    assert "never clamped" in prov.generator


# ---- protected 6: deterministic AQI ---------------------------------------
def test_aqi_is_deterministic_by_state():
    for state in ("Delhi", "Kerala", "Uttar Pradesh"):
        assert derive_air_quality(CFG, state) == derive_air_quality(CFG, state)


# ---- protected 7: family history derivation by age band -------------------
def test_family_history_derivation_tag():
    for a in ATTRS:
        expected = "lasi_observed_45_plus" if a["demographics"]["age"] >= 45 else "parent_simulation_calibrated"
        assert a["family_history"]["derivation"] == expected


# ---- protected 8 + issue 6: thresholds, sex-specific HDL, LAI vs NCEP -----
def test_lipid_flags_follow_thresholds_and_lai_differs_from_ncep():
    panel = {"total_cholesterol_mg_dl": 180.0, "triglycerides_mg_dl": 100.0, "hdl_mg_dl": 45.0, "ldl_mg_dl": 115.0}
    by_def = {i["definition"]: i for i in derive_lipid_interpretations(CFG, panel, sex=0)}
    assert by_def["NCEP_ATP_III"]["dyslipidemia"] is False
    assert by_def["LAI_2020"]["dyslipidemia"] is True and by_def["LAI_2020"]["components_abnormal"] == ["LDL"]
    female = {i["definition"]: i for i in derive_lipid_interpretations(CFG, panel, sex=1)}
    assert "HDL" in female["NCEP_ATP_III"]["components_abnormal"]  # 45 < 50 for women only


# ---- protected 9: sex coding ----------------------------------------------
def test_sex_coding():
    assert {a["demographics"]["sex"] for a in ATTRS} == {0, 1}


# ---- issues 3, 4, 7 --------------------------------------------------------
def test_everyone_has_hba1c_and_onset_is_modeled_and_bounded():
    for a in ATTRS:
        assert a["hba1c"]["value"] is not None
        age = a["demographics"]["age"]
        assert age == round(age, 2)
        for cond in ("hypertension", "diabetes"):
            present = a["risk_factors"][cond]
            assert (cond in a["onset"]) == present
            if present:
                o = a["onset"][cond]
                assert 15.0 <= o["age_at_onset_years"] <= age
                assert o["onset_derivation"].startswith("modeled")


def test_lipid_sampler_raises_instead_of_clamping():
    cfg = load_config()
    cfg["risk_factors"]["lipid_panel"]["joint_model"]["rejection_bounds"]["ldl_min"] = 10_000.0
    with pytest.raises(RuntimeError):
        sample_lipid_panel(np.random.default_rng(1), cfg, 0)
