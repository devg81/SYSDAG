"""M8 — blood pressure, encounters, timeline references (schema v0.8).

Tests the REUSABLE generation/validation layer, not the 50-record pilot
batch (that is `validation/pilot_50_records/tests/`). These are the
properties that must hold for all 100,000 records, so most are checked
as properties over many draws rather than on one example.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.clinical_history import derive_encounters, derive_timeline
from generation.indian_population import (
    _bp_band,
    _bp_region,
    derive_weight_kg,
    generate_indian_attributes,
    load_config as load_indian_config,
    sample_blood_pressure,
    sample_height_cm,
    validate_config,
)
from schemas.patient_schema import (
    SCHEMA_VERSION,
    BloodPressure,
    Encounter,
    Patient,
    TimelineEvent,
)
from validation.structural import validate_patient

INDIAN_CONFIG = load_indian_config()
SBP_THRESHOLD = 140
DBP_THRESHOLD = 90
PRODUCTION_DATASET = _REPO_ROOT / "outputs" / "m5" / "100k_patients"


def _bp(seed: int, age: float, sex: int, hypertension: bool, treated: bool):
    return sample_blood_pressure(
        np.random.default_rng(seed), INDIAN_CONFIG, age, sex, hypertension, treated
    )


# ------------------------------------------------------------------ schema


def test_schema_version_is_010():
    assert SCHEMA_VERSION == "0.12"


def test_config_validates():
    assert validate_config(INDIAN_CONFIG) == []


def test_config_rejects_a_broken_bp_band():
    broken = copy.deepcopy(INDIAN_CONFIG)
    bands = broken["risk_factors"]["blood_pressure"]["distribution"]["age_bands_by_sex"]
    bands["male"][2] = [25, 29, 80.0, 11.08, 120.0, 8.53]  # mean SBP below mean DBP
    errors = validate_config(broken)
    assert any("mean SBP" in e for e in errors), errors


def test_config_rejects_an_age_band_gap():
    broken = copy.deepcopy(INDIAN_CONFIG)
    bands = broken["risk_factors"]["blood_pressure"]["distribution"]["age_bands_by_sex"]
    del bands["male"][3]  # leaves a 30-34 hole
    assert any("gap/overlap" in e for e in validate_config(broken))


# --------------------------------------------------- blood-pressure regions


def test_region_mapping_matches_the_published_label_definition():
    assert _bp_region(False, False) == "normotensive"
    assert _bp_region(True, False) == "raised"
    # Already satisfied by medication use -> the measurement is free.
    assert _bp_region(True, True) == "unconstrained"
    assert _bp_region(False, True) == "normotensive"


@pytest.mark.parametrize("sex", [0, 1])
def test_normotensive_bp_is_always_below_both_thresholds(sex):
    for seed in range(300):
        bp = _bp(seed, 20.0 + (seed % 70), sex, hypertension=False, treated=False)
        assert bp["systolic_mm_hg"] < SBP_THRESHOLD
        assert bp["diastolic_mm_hg"] < DBP_THRESHOLD


@pytest.mark.parametrize("sex", [0, 1])
def test_untreated_hypertensive_bp_always_meets_the_definition(sex):
    for seed in range(300):
        bp = _bp(seed, 20.0 + (seed % 70), sex, hypertension=True, treated=False)
        assert (
            bp["systolic_mm_hg"] >= SBP_THRESHOLD or bp["diastolic_mm_hg"] >= DBP_THRESHOLD
        )


def test_untreated_hypertensive_region_is_reachable_for_the_youngest_patients():
    """The raised region sits ~2.6 SD out for women aged 20-24. The grid
    sampler must still produce valid values there -- this is the case a
    rejection sampler would have had to bail out of."""
    for seed in range(200):
        bp = _bp(seed, 21.0, 1, hypertension=True, treated=False)
        assert (
            bp["systolic_mm_hg"] >= SBP_THRESHOLD or bp["diastolic_mm_hg"] >= DBP_THRESHOLD
        )


def test_treated_hypertensive_bp_is_not_forced_high():
    """The architecturally important property: a treated patient already
    satisfies the definition through medication, so controlled readings
    must be possible. If this ever becomes all-raised, the generator is
    fabricating confirmation of the label."""
    controlled = sum(
        1
        for seed in range(500)
        if _bp(seed, 55.0, 0, hypertension=True, treated=True)["systolic_mm_hg"]
        < SBP_THRESHOLD
        and _bp(seed, 55.0, 0, hypertension=True, treated=True)["diastolic_mm_hg"]
        < DBP_THRESHOLD
    )
    assert controlled > 100, f"only {controlled}/500 treated patients came out controlled"


# ------------------------------------------------- physiological invariants


@pytest.mark.parametrize("hypertension,treated", [(False, False), (True, False), (True, True)])
def test_systolic_always_exceeds_diastolic_and_pulse_pressure_floor_holds(
    hypertension, treated
):
    floor = INDIAN_CONFIG["risk_factors"]["blood_pressure"]["distribution"][
        "min_pulse_pressure_mm_hg"
    ]
    for seed in range(400):
        for sex in (0, 1):
            bp = _bp(seed, 20.0 + (seed % 70), sex, hypertension, treated)
            s, d = bp["systolic_mm_hg"], bp["diastolic_mm_hg"]
            assert s > d
            assert s - d >= floor


def test_values_are_whole_mmhg_integers():
    for seed in range(100):
        bp = _bp(seed, 45.0, 0, True, False)
        assert isinstance(bp["systolic_mm_hg"], int)
        assert isinstance(bp["diastolic_mm_hg"], int)


# ------------------------------------------------------- age-band selection


def test_continuous_age_never_falls_between_bands():
    """Bands are stated in whole years; ages are continuous. A patient
    aged 24.6 belongs to the 20-24 band, not to a gap."""
    for sex in (0, 1):
        for tenth in range(200, 900):
            age = tenth / 10.0
            band, label, _ = _bp_band(INDIAN_CONFIG, age, sex)
            assert band is not None
            assert label.startswith("NFHS-5 ")


def test_extrapolation_flag_matches_source_coverage():
    coverage = INDIAN_CONFIG["risk_factors"]["blood_pressure"]["distribution"][
        "source_age_coverage_max_by_sex"
    ]
    for sex, key in ((0, "male"), (1, "female")):
        limit = coverage[key]
        # Still inside coverage: a patient aged limit+0.9 is `limit` years old.
        _, _, extrapolated = _bp_band(INDIAN_CONFIG, limit + 0.9, sex)
        assert extrapolated is False
        _, label, extrapolated = _bp_band(INDIAN_CONFIG, limit + 1.0, sex)
        assert extrapolated is True
        # v0.10: beyond coverage the oldest band's DBP/SDs are kept and
        # mean SBP follows the fitted NFHS-5 trend, so it RISES with age
        # while mean DBP stays flat (pulse pressure widens).
        last = INDIAN_CONFIG["risk_factors"]["blood_pressure"]["distribution"][
            "age_bands_by_sex"
        ][key][-1]
        band_edge, _, _ = _bp_band(INDIAN_CONFIG, limit + 1.0, sex)
        band_89, label_89, _ = _bp_band(INDIAN_CONFIG, 89.0, sex)
        assert label.startswith(f"NFHS-5 {key} {int(last[0])}-{int(last[1])}") and "extrapolated" in label
        assert band_89[2] > band_edge[2] > last[2] - 1.0
        assert band_89[4] == band_edge[4] == last[4]
        assert band_89[3] == last[3] and band_89[5] == last[5]


# ------------------------------------------------- determinism / no drift


def test_same_seed_gives_identical_blood_pressure():
    a = _bp(12345, 61.3, 1, True, False)
    b = _bp(12345, 61.3, 1, True, False)
    assert a == b


def test_different_seeds_give_varied_blood_pressure():
    values = {
        (bp["systolic_mm_hg"], bp["diastolic_mm_hg"])
        for bp in (_bp(seed, 50.0, 0, False, False) for seed in range(100))
    }
    assert len(values) > 50, "blood pressure is suspiciously repetitive across seeds"


@pytest.mark.parametrize(
    "patient_id", ["PAT_000001", "PAT_000007", "PAT_033333", "PAT_099999"]
)
def test_adding_blood_pressure_did_not_perturb_any_pre_existing_field(patient_id):
    """Every field drawn BEFORE the lipid panel must come off the same seed
    identically to the stored v0.8 dataset (age now rounded to 2 dp).
    v0.10 (D022) deliberately changed lipids/HbA1c, so those are no longer
    compared -- see tests/test_v010_review_fixes.py for their new contract.
    """
    path = PRODUCTION_DATASET / f"{patient_id}.json"
    if not path.exists():
        pytest.skip(f"{path} not present")
    stored = json.loads(path.read_text(encoding="utf-8"))
    seed = int(re.search(r"indian_random_seed=(\d+)", stored["provenance"]["generator"]).group(1))
    attrs = generate_indian_attributes(np.random.default_rng(seed), INDIAN_CONFIG)

    assert attrs["demographics"]["age"] == round(stored["demographics"]["age"], 2)
    for key in ("sex", "state", "urban_rural"):
        assert attrs["demographics"][key] == stored["demographics"][key], key
    for key, value in attrs["risk_factors"].items():
        assert value == stored["risk_factors"][key], key


# ------------------------------------------------- anthropometrics deferral


def test_height_is_not_generated_and_says_so():
    assert sample_height_cm(np.random.default_rng(1), INDIAN_CONFIG, 0) is None
    assert sample_height_cm(np.random.default_rng(1), INDIAN_CONFIG, 1) is None


def test_height_hook_refuses_to_stay_a_no_op_once_evidence_arrives():
    """Guards against the config gaining a height distribution while the
    generator silently keeps returning None."""
    with_evidence = copy.deepcopy(INDIAN_CONFIG)
    with_evidence["risk_factors"]["anthropometrics_height_weight"]["status"] = "SUPPORTED"
    with pytest.raises(NotImplementedError):
        sample_height_cm(np.random.default_rng(1), with_evidence, 0)


def test_weight_is_derived_from_bmi_and_height_never_sampled():
    assert derive_weight_kg(24.0, None) is None
    assert derive_weight_kg(None, 170.0) is None
    # 24.0 * 1.70^2 = 69.36
    assert derive_weight_kg(24.0, 170.0) == 69.4
    # The derivation must round-trip back to the BMI it came from.
    weight = derive_weight_kg(27.5, 162.0)
    assert abs(weight / (1.62**2) - 27.5) < 0.15


# --------------------------------------------------- encounters / timeline


def test_encounter_contains_the_measurements_that_exist():
    encounters = derive_encounters(
        "PAT_000001", "2026-10-20", True, True, ["HbA1c"]
    )
    assert len(encounters) == 1
    encounter = encounters[0]
    assert encounter["encounter_id"] == "PAT_000001_ENC01"
    assert encounter["encounter_type"] == "synthetic_baseline_assessment"
    assert encounter["patient_id"] == "PAT_000001"
    assert encounter["recorded_measurements"] == ["blood_pressure", "lipid_panel", "labs.HbA1c"]
    assert encounter["source"] == "synthetic_structural_container"


def test_no_encounter_is_emitted_when_nothing_was_measured():
    """An empty container would be a null dressed up as a record."""
    assert derive_encounters("PAT_000001", "2026-10-20", False, False, []) == []


def test_diabetic_patient_encounter_omits_hba1c():
    encounters = derive_encounters("PAT_000002", "2026-10-20", True, True, [])
    assert encounters[0]["recorded_measurements"] == ["blood_pressure", "lipid_panel"]


def test_timeline_indexes_the_encounter_without_duplicating_measurements():
    encounters = derive_encounters("PAT_000001", "2026-10-20", True, True, ["HbA1c"])
    timeline = derive_timeline("2026-10-20", encounters)
    assert [e["event_type"] for e in timeline] == [
        "synthetic_record_created",
        "synthetic_baseline_assessment",
    ]
    assert timeline[0]["reference_id"] is None
    assert timeline[1]["reference_id"] == "PAT_000001_ENC01"
    # One event per encounter, NOT one per measurement.
    assert len(timeline) == 1 + len(encounters)


def test_timeline_is_rebuilt_not_appended():
    """Idempotence at its source: calling twice must not stack events."""
    encounters = derive_encounters("PAT_000001", "2026-10-20", True, True, ["HbA1c"])
    assert derive_timeline("2026-10-20", encounters) == derive_timeline(
        "2026-10-20", encounters
    )


def test_timeline_has_only_the_record_s_own_events():
    """No diagnosis-onset, medication-start or follow-up date is ever
    invented -- no evidence-backed per-patient date distribution exists."""
    encounters = derive_encounters("PAT_000001", "2026-10-20", True, True, ["HbA1c"])
    types = {e["event_type"] for e in derive_timeline("2026-10-20", encounters)}
    assert not any(
        word in t for t in types for word in ("onset", "diagnos", "follow", "medication")
    )


# ------------------------------------------- structural validator coverage


def _patient_with_bp(**overrides) -> Patient:
    from schemas.patient_schema import Demographics, Provenance, ValidationMetadata

    defaults = dict(
        systolic_mm_hg=132,
        diastolic_mm_hg=84,
        measured_at="2026-10-20",
        age_band_source="NFHS-5 male 45-49",
        extrapolated_beyond_source_age_range=False,
    )
    defaults.update(overrides)
    return Patient(
        patient_id="PAT_000001",
        demographics=Demographics(age=47.0, sex=0),
        provenance=Provenance(
            schema_version=SCHEMA_VERSION,
            generated_at="2026-10-20T00:00:00+00:00",
            generator="test",
            random_seed=1,
            source_datasets=[],
        ),
        blood_pressure=BloodPressure(**defaults),
        clinical_timeline=[TimelineEvent(event_type="synthetic_record_created", date="2026-10-20")],
        validation=ValidationMetadata(),
    )


def test_validator_rejects_diastolic_at_or_above_systolic():
    errors = validate_patient(_patient_with_bp(systolic_mm_hg=84, diastolic_mm_hg=84))
    assert any("must exceed" in e for e in errors), errors


def test_validator_rejects_out_of_range_blood_pressure():
    assert any(
        "out of plausible range" in e
        for e in validate_patient(_patient_with_bp(systolic_mm_hg=400))
    )


def test_validator_rejects_missing_bp_provenance():
    assert any(
        "age_band_source" in e for e in validate_patient(_patient_with_bp(age_band_source=None))
    )
    assert any(
        "extrapolated_beyond_source_age_range" in e
        for e in validate_patient(_patient_with_bp(extrapolated_beyond_source_age_range=None))
    )


def test_validator_rejects_an_unknown_encounter_type():
    patient = _patient_with_bp()
    patient.encounters = [
        Encounter(
            encounter_id="PAT_000001_ENC01",
            encounter_type="outpatient_visit",  # not an evidence-backed type
            date="2026-10-20",
            patient_id="PAT_000001",
            recorded_measurements=["blood_pressure"],
        )
    ]
    assert any("unsupported encounter_type" in e for e in validate_patient(patient))


def test_validator_rejects_an_encounter_owned_by_another_patient():
    patient = _patient_with_bp()
    patient.encounters = [
        Encounter(
            encounter_id="PAT_000001_ENC01",
            encounter_type="synthetic_baseline_assessment",
            date="2026-10-20",
            patient_id="PAT_000999",
            recorded_measurements=["blood_pressure"],
        )
    ]
    assert any("does not match" in e for e in validate_patient(patient))


def test_validator_rejects_an_unknown_timeline_event_type():
    patient = _patient_with_bp()
    patient.clinical_timeline = [
        TimelineEvent(event_type="hospital_admission", date="2026-10-20")
    ]
    assert any("unsupported event_type" in e for e in validate_patient(patient))
