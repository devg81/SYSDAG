"""M4A: schema-level tests for LipidPanel/LipidInterpretation/Lab.

Schema-only milestone — no generation logic exists yet for any of these
fields, so tests construct Patient/LipidPanel/LipidInterpretation/Lab
objects directly rather than via build_patient(). Test 1 and test 8 use
the real build_patient() pipeline to confirm backward compatibility.
"""

import copy
import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from schemas.patient_schema import (  # noqa: E402
    Lab,
    LipidInterpretation,
    LipidPanel,
    SCHEMA_VERSION,
)
from validation.structural import validate_patient  # noqa: E402

BASE_CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")


def _minimal_patient():
    return build_patient(1, BASE_CONFIG)


# Test 1 — minimal patient still works. As of M4B, build_patient() itself
# populates lipid_panel/lipid_interpretations/labs (generation logic now
# exists) — this test only confirms the pipeline runs end-to-end and
# validates; schema-level "fields default to None on a bare dataclass
# construction" is covered separately by test_lipid_panel_with_all_missing_values_validates.
def test_minimal_patient_still_works():
    patient = _minimal_patient()
    assert patient.validation.validated, patient.validation.errors
    # Bumped 0.7 -> 0.8 by M8 (blood_pressure, encounters,
    # TimelineEvent.reference_id), 0.8 -> 0.9 by D020/D021.
    assert patient.provenance.schema_version == SCHEMA_VERSION == "0.13"


# Test 2 — patient with LipidPanel works
def test_patient_with_lipid_panel_validates():
    patient = _minimal_patient()
    patient.lipid_panel = LipidPanel(
        ldl_mg_dl=132.0, hdl_mg_dl=38.0, triglycerides_mg_dl=160.0, total_cholesterol_mg_dl=210.0
    )
    errors = validate_patient(patient)
    assert errors == []


# Test 3 — multiple LipidInterpretations coexist
def test_patient_with_multiple_lipid_interpretations_validates():
    patient = _minimal_patient()
    patient.lipid_panel = LipidPanel(ldl_mg_dl=110.0, hdl_mg_dl=38.0)
    patient.lipid_interpretations = [
        LipidInterpretation(
            definition="NCEP_ATP_III",
            dyslipidemia=False,
            components_abnormal=["HDL"],
            source_citation="ICMR-INDIAB-17 (Anjana et al., Lancet Diabetes Endocrinol 2023)",
        ),
        LipidInterpretation(
            definition="LAI_2020",
            dyslipidemia=True,
            components_abnormal=["LDL", "HDL"],
            source_citation="ICMR-INDIAB-25 (J Clin Lipidology 2026)",
        ),
    ]
    errors = validate_patient(patient)
    assert errors == []
    assert len(patient.lipid_interpretations) == 2
    assert {i.definition for i in patient.lipid_interpretations} == {"NCEP_ATP_III", "LAI_2020"}


# Test 4 — missing lipid values (all-None LipidPanel) still validates
def test_lipid_panel_with_all_missing_values_validates():
    patient = _minimal_patient()
    patient.lipid_panel = LipidPanel()  # all fields None
    errors = validate_patient(patient)
    assert errors == []


# Test 5 — HbA1c representable via the generic Lab structure
def test_hba1c_represented_via_generic_lab():
    patient = _minimal_patient()
    patient.labs = [Lab(analyte="HbA1c", unit="%", value=5.4, measured_at="2026-09-26")]
    errors = validate_patient(patient)
    assert errors == []


# Test 6 — invalid lipid/lab units fail validation
def test_invalid_analyte_unit_fails():
    patient = _minimal_patient()
    patient.labs = [Lab(analyte="HbA1c", unit="mg/dL", value=5.4)]  # wrong unit for HbA1c
    errors = validate_patient(patient)
    assert any("expects unit" in e for e in errors)


# Test 7 — malformed lipid interpretations fail validation
def test_malformed_lipid_interpretation_fails():
    patient = _minimal_patient()
    patient.lipid_interpretations = [LipidInterpretation(definition="")]  # missing definition
    errors = validate_patient(patient)
    assert any("missing definition" in e for e in errors)

    patient2 = _minimal_patient()
    patient2.lipid_interpretations = [
        LipidInterpretation(definition="NCEP_ATP_III", components_abnormal=["not_a_real_component"])
    ]
    errors2 = validate_patient(patient2)
    assert any("unknown components_abnormal" in e for e in errors2)


# Test 8 — existing M1-M3 behavior unchanged (structural validity of the
# base pipeline, independent of any new fields)
def test_existing_pipeline_behavior_unchanged():
    patient = _minimal_patient()
    assert patient.demographics.age is not None
    assert patient.risk_factors is not None
    assert patient.ecg is not None
    assert patient.ecg.signal_shape == [1000, 12]
    assert patient.validation.validated


# Test 9 — serialization includes the new fields
def test_serialization_includes_new_fields():
    patient = _minimal_patient()
    patient.lipid_panel = LipidPanel(ldl_mg_dl=132.0)
    patient.lipid_interpretations = [LipidInterpretation(definition="NCEP_ATP_III", dyslipidemia=True)]
    patient.labs = [Lab(analyte="HbA1c", unit="%", value=5.4)]

    d = patient.to_dict()
    assert d["lipid_panel"]["ldl_mg_dl"] == 132.0
    assert d["lipid_interpretations"][0]["definition"] == "NCEP_ATP_III"
    assert d["labs"][0]["analyte"] == "HbA1c"


# Test 10 — dict/JSON round-trip is stable (the level of round-trip this
# repo actually supports — no Patient-object deserialization exists
# anywhere in the codebase, confirmed before this milestone's changes)
def test_json_round_trip_is_stable():
    patient = _minimal_patient()
    patient.lipid_panel = LipidPanel(
        ldl_mg_dl=132.0, hdl_mg_dl=38.0, triglycerides_mg_dl=None, total_cholesterol_mg_dl=210.0
    )
    patient.lipid_interpretations = [
        LipidInterpretation(definition="NCEP_ATP_III", dyslipidemia=True, components_abnormal=["LDL"])
    ]
    patient.labs = [Lab(analyte="HbA1c", unit="%", value=5.4, measured_at="2026-09-26")]

    original = patient.to_dict()
    round_tripped = json.loads(json.dumps(original))
    assert round_tripped == original


# Backward compatibility: an old-shape dict (missing the new keys
# entirely, as every M1-M3 JSON file on disk is) is still valid JSON and
# unaffected by the new schema — nothing in this repo tries to strictly
# reconstruct a Patient object from it, so there's nothing to break.
def test_old_shape_json_is_still_valid_json_and_unaffected():
    patient = _minimal_patient()
    d = patient.to_dict()
    old_style = copy.deepcopy(d)
    del old_style["lipid_panel"], old_style["lipid_interpretations"], old_style["labs"]
    # Just confirms this reduced dict round-trips as plain JSON -- the
    # repo has no code path that would choke on it (see integration/
    # {analyze_m3_population,plot_m3_validation,validate_population}.py,
    # all of which read patient JSON as plain dicts, never as typed objects).
    assert json.loads(json.dumps(old_style)) == old_style
