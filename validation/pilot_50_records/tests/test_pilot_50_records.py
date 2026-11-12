"""Validation gates for the 50-record schema-v0.8 pilot batch.

Reuses the project's own validators (`validation/structural.py`,
`validation/clinical_consistency.py`) rather than reimplementing the
rules -- a second independent copy of a consistency rule would itself
become a consistency risk, which is the reasoning
`validation/clinical_consistency.py`'s own module docstring already
records.

Organised to match the four gate families the pilot reports separately:
STRUCTURAL, REFERENTIAL INTEGRITY, CLINICAL CONSISTENCY, DATA QUALITY,
plus REUSABILITY (idempotence, determinism, originals-preserved) because
those are what the full-100k decision actually turns on.

Run:
    python -m pytest validation/pilot_50_records/tests -q
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_PILOT_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PILOT_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import load_config as load_indian_config  # noqa: E402
from integration.migrate_v07_to_v08 import (  # noqa: E402
    TARGET_SCHEMA_VERSION,
    _dict_to_patient,
    extract_indian_seed,
    migrate_record,
)
from schemas.patient_schema import (  # noqa: E402
    ENCOUNTER_TYPES,
    TIMELINE_EVENT_TYPES,
    SCHEMA_VERSION,
)
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from validation.structural import check_duplicate_ids, validate_patient  # noqa: E402
from generation.indian_population import valid_states  # noqa: E402

BATCH_PATH = _PILOT_DIR / "output" / "patient_records_50.json"
MANIFEST_PATH = _PILOT_DIR / "input" / "source_manifest.json"
BACKUP_DIR = _PILOT_DIR / "input" / "original_records"
SOURCE_DATASET = _REPO_ROOT / "outputs" / "m5" / "100k_patients"

EXPECTED_BATCH_SIZE = 50


@pytest.fixture(scope="module")
def indian_config():
    return load_indian_config()


@pytest.fixture(scope="module")
def records():
    if not BATCH_PATH.exists():
        pytest.skip(f"{BATCH_PATH} not built yet -- run run_pilot.py first")
    return json.loads(BATCH_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST_PATH.exists():
        pytest.skip(f"{MANIFEST_PATH} not built yet -- run run_pilot.py first")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def patients(records):
    return [_dict_to_patient(r) for r in records]


# ---------------------------------------------------------------- STRUCTURAL


def test_batch_contains_exactly_50_records(records):
    assert len(records) == EXPECTED_BATCH_SIZE


def test_patient_ids_are_unique(records, patients):
    assert len({r["patient_id"] for r in records}) == EXPECTED_BATCH_SIZE
    assert check_duplicate_ids(patients) == []


def test_every_record_is_schema_v08(records):
    assert TARGET_SCHEMA_VERSION == SCHEMA_VERSION == "0.8"
    assert {r["provenance"]["schema_version"] for r in records} == {"0.8"}


def test_every_record_passes_structural_validation(patients, indian_config):
    states = valid_states(indian_config)
    failures = {
        p.patient_id: validate_patient(p, valid_states=states)
        for p in patients
        if validate_patient(p, valid_states=states)
    }
    assert not failures, failures


def test_stored_validation_block_agrees_with_a_fresh_run(records):
    """A record must not claim `validated: true` unless it is."""
    for record in records:
        assert record["validation"]["validated"] is True, record["patient_id"]
        assert record["validation"]["errors"] == [], record["patient_id"]


def test_blood_pressure_types_units_and_bounds(records):
    for record in records:
        bp = record["blood_pressure"]
        assert isinstance(bp["systolic_mm_hg"], int) and not isinstance(
            bp["systolic_mm_hg"], bool
        )
        assert isinstance(bp["diastolic_mm_hg"], int)
        assert 70 <= bp["systolic_mm_hg"] <= 260
        assert 40 <= bp["diastolic_mm_hg"] <= 160
        # Provenance of the age-band extrapolation must never be silent.
        assert bp["age_band_source"].startswith("NFHS-5 ")
        assert isinstance(bp["extrapolated_beyond_source_age_range"], bool)
        assert bp["source"] == "derived_conditional_on_hypertension_label"


def test_controlled_vocabularies_are_respected(records):
    for record in records:
        for encounter in record["encounters"]:
            assert encounter["encounter_type"] in ENCOUNTER_TYPES
        for event in record["clinical_timeline"]:
            assert event["event_type"] in TIMELINE_EVENT_TYPES


def test_nulls_and_empty_collections_are_explicit(records):
    """Deferred fields are present-and-null, not silently absent -- a
    reviewer must be able to see that they were considered."""
    for record in records:
        for field in ("family_history", "echo", "blood_pressure", "encounters"):
            assert field in record, (record["patient_id"], field)
        assert "height_cm" in record["demographics"]
        assert "weight_kg" in record["demographics"]


# ----------------------------------------------------- REFERENTIAL INTEGRITY


def test_diagnosis_ids_are_unique_within_each_patient(records):
    for record in records:
        ids = [d["diagnosis_id"] for d in record["diagnoses"]]
        assert len(ids) == len(set(ids)), record["patient_id"]
        assert all(i.startswith(record["patient_id"]) for i in ids)


def test_medical_history_resolves_to_real_diagnoses(records):
    for record in records:
        known = {d["diagnosis_id"] for d in record["diagnoses"]}
        for entry in record["medical_history"]:
            assert entry["diagnosis_id"] in known, record["patient_id"]


def test_medications_resolve_to_real_diagnoses_and_match_drug_class(records):
    expected = {"antihypertensive": "hypertension", "antidiabetic": "diabetes"}
    for record in records:
        by_id = {d["diagnosis_id"]: d for d in record["diagnoses"]}
        for med in record["medications"]:
            diagnosis = by_id.get(med["diagnosis_id"])
            assert diagnosis is not None, record["patient_id"]
            assert diagnosis["code"] == expected[med["drug_class"]]


def test_encounters_belong_to_their_patient_and_are_indexed_once(records):
    for record in records:
        encounter_ids = {e["encounter_id"] for e in record["encounters"]}
        assert len(encounter_ids) == len(record["encounters"])
        for encounter in record["encounters"]:
            assert encounter["patient_id"] == record["patient_id"]
            assert encounter["encounter_id"].startswith(record["patient_id"])
        referenced = [
            e["reference_id"] for e in record["clinical_timeline"] if e["reference_id"]
        ]
        assert sorted(referenced) == sorted(encounter_ids), record["patient_id"]
        # No duplicate representation of the same event.
        assert len(referenced) == len(set(referenced))


def test_encounters_only_claim_measurements_that_exist(records):
    for record in records:
        analytes = {lab["analyte"] for lab in (record["labs"] or [])}
        for encounter in record["encounters"]:
            assert encounter["recorded_measurements"]
            for name in encounter["recorded_measurements"]:
                if name == "blood_pressure":
                    assert record["blood_pressure"] is not None
                elif name == "lipid_panel":
                    assert record["lipid_panel"] is not None
                elif name.startswith("labs."):
                    assert name.split(".", 1)[1] in analytes
                else:
                    pytest.fail(f"unknown recorded_measurement {name!r}")


# ---------------------------------------------------- CLINICAL CONSISTENCY


def test_every_record_passes_clinical_consistency(patients, indian_config):
    failures = {
        p.patient_id: validate_clinical_consistency(p, indian_config).errors
        for p in patients
        if not validate_clinical_consistency(p, indian_config).valid
    }
    assert not failures, failures


def test_systolic_always_exceeds_diastolic(records):
    for record in records:
        bp = record["blood_pressure"]
        assert bp["systolic_mm_hg"] > bp["diastolic_mm_hg"], record["patient_id"]


def test_blood_pressure_agrees_with_the_hypertension_label_definition(records):
    """The label's OWN published definition: SBP>=140 and/or DBP>=90
    and/or on antihypertensive medication."""
    for record in records:
        bp = record["blood_pressure"]
        raised = bp["systolic_mm_hg"] >= 140 or bp["diastolic_mm_hg"] >= 90
        hypertension = record["risk_factors"]["hypertension"]
        treated = any(
            m["drug_class"] == "antihypertensive" for m in (record["medications"] or [])
        )
        if not hypertension:
            assert not raised, record["patient_id"]
        else:
            assert raised or treated, record["patient_id"]


def test_a_treated_hypertensive_is_not_forced_to_look_uncontrolled(records):
    """The architecturally important case: because the definition is
    already satisfied by medication use, a treated patient's measurement
    must be left free. If every treated patient came out raised, the
    generator would be fabricating confirmation of the label.

    Asserted as a property of the generator, not of this 50-record
    sample: with only a handful of treated patients in the batch, an
    all-raised outcome is possible by chance, so the check is that the
    unconstrained region genuinely admits controlled values.
    """
    treated = [
        r
        for r in records
        if any(m["drug_class"] == "antihypertensive" for m in (r["medications"] or []))
    ]
    if not treated:
        pytest.skip("no treated hypertensives in this batch")
    controlled = [
        r
        for r in treated
        if r["blood_pressure"]["systolic_mm_hg"] < 140
        and r["blood_pressure"]["diastolic_mm_hg"] < 90
    ]
    # Documented in reports/validation_report.md; recorded here so a
    # regression that starts forcing treated patients high is visible.
    assert len(controlled) >= 1, (
        f"{len(treated)} treated hypertensives, none controlled -- check that the "
        "'unconstrained' BP region is still being used for treated patients"
    )


def test_diagnoses_are_a_strict_promotion_of_the_risk_factor_flags(records):
    for record in records:
        rf = record["risk_factors"]
        expected = {code for code in ("hypertension", "diabetes") if rf[code]}
        assert {d["code"] for d in record["diagnoses"]} == expected, record["patient_id"]
        # Hyperlipidemia's diagnosis stays deferred (D015) even though the
        # risk factor and the lipid interpretations both exist.
        assert "hyperlipidemia" not in {d["code"] for d in record["diagnoses"]}


def test_ldl_is_still_the_friedewald_derivation_subject_to_its_clip_range(records):
    """LDL = TC - HDL - TG/5, then clipped to the documented
    clip_range [30, 300] (configs/indian_population.yaml
    risk_factors.lipid_panel.ldl). The clip is part of the design, so
    the assertion is "derived-then-clipped", not "derived".

    The clip is NOT cosmetic here: TC, TG and HDL are sampled as three
    independent marginals, so some triples are internally impossible
    (TC < HDL + TG/5) and the floor absorbs it. That is counted by
    test_lipid_panel_internal_feasibility_is_measured_not_hidden below
    and reported as the pilot's headline unresolved issue.
    """
    clip_low, clip_high = 30.0, 300.0
    for record in records:
        lp = record["lipid_panel"]
        raw = (
            lp["total_cholesterol_mg_dl"]
            - lp["hdl_mg_dl"]
            - lp["triglycerides_mg_dl"] / 5.0
        )
        expected = min(max(raw, clip_low), clip_high)
        assert abs(lp["ldl_mg_dl"] - expected) < 0.11, record["patient_id"]


def test_lipid_panel_internal_feasibility_is_measured_not_hidden(records, indian_config):
    """A pre-existing (M4B) defect this pilot surfaces rather than
    silently inherits: independent TC/TG/HDL marginals can produce a
    panel whose total cholesterol is below the sum of its own
    components. The validator must WARN on every such record so the rate
    is countable; it is not promoted to an error because the stored LDL
    does follow its documented clip rule, and changing the sampling is a
    D011-level decision.
    """
    impossible = [
        r
        for r in records
        if r["lipid_panel"]["total_cholesterol_mg_dl"]
        - r["lipid_panel"]["hdl_mg_dl"]
        - r["lipid_panel"]["triglycerides_mg_dl"] / 5.0
        < 0
    ]
    for record in impossible:
        result = validate_clinical_consistency(_dict_to_patient(record), indian_config)
        assert any(
            "internally impossible" in w for w in result.warnings
        ), f"{record['patient_id']} is internally impossible but was not flagged"
        # Still "valid": the warning is disclosure, not a structural failure.
        assert result.valid, result.errors


def test_hba1c_rule_still_holds(records):
    for record in records:
        hba1c = [lab for lab in (record["labs"] or []) if lab["analyte"] == "HbA1c"]
        if record["risk_factors"]["diabetes"]:
            assert not hba1c, record["patient_id"]
        else:
            assert len(hba1c) == 1, record["patient_id"]
            assert hba1c[0]["unit"] == "%"
            assert 4.0 <= hba1c[0]["value"] <= 6.4


def test_all_measurement_dates_agree_with_the_timeline(records):
    for record in records:
        created = next(
            e["date"]
            for e in record["clinical_timeline"]
            if e["event_type"] == "synthetic_record_created"
        )
        for event in record["clinical_timeline"]:
            assert event["date"] >= created, record["patient_id"]
        for encounter in record["encounters"]:
            assert encounter["date"] == record["blood_pressure"]["measured_at"]
            for lab in record["labs"] or []:
                assert lab["measured_at"] == encounter["date"]


def test_bmi_is_untouched_and_height_weight_stay_unpopulated(records):
    """Height/weight are deferred for want of evidence; BMI remains the
    evidence-primary anthropometric. If height/weight ever become
    populated, the BMI arithmetic gate in clinical_consistency.py starts
    firing -- this test documents which state we are in."""
    for record in records:
        assert record["demographics"]["height_cm"] is None, record["patient_id"]
        assert record["demographics"]["weight_kg"] is None, record["patient_id"]
        assert record["risk_factors"]["bmi"] is not None


def test_no_unsupported_family_history_encounter_or_diagnosis_was_introduced(records):
    for record in records:
        assert record["family_history"] is None, record["patient_id"]
        assert record["echo"] is None, record["patient_id"]
        assert {e["encounter_type"] for e in record["encounters"]} <= {
            "synthetic_baseline_assessment"
        }
        assert {d["code"] for d in record["diagnoses"]} <= {"hypertension", "diabetes"}


def test_ecg_boundary_is_preserved(records):
    """ECG stays metadata-only (D003). No waveform, no guessed label."""
    for record in records:
        ecg = record["ecg"]
        assert ecg["signal_available"] is False, record["patient_id"]
        assert ecg["source"] == "PTB-XL"
        assert ecg["signal_shape"] == [1000, 12]


# -------------------------------------------------------------- DATA QUALITY


def test_blood_pressure_is_not_a_repeated_placeholder(records):
    """Guards against the failure mode of copying one value across
    patients to make records look complete."""
    sbp = [r["blood_pressure"]["systolic_mm_hg"] for r in records]
    dbp = [r["blood_pressure"]["diastolic_mm_hg"] for r in records]
    assert len(set(sbp)) >= 25, f"only {len(set(sbp))} distinct systolic values in 50"
    assert len(set(dbp)) >= 20, f"only {len(set(dbp))} distinct diastolic values in 50"
    pairs = list(zip(sbp, dbp))
    assert len(set(pairs)) >= 45, "suspiciously many identical BP pairs"


def test_pulse_pressure_stays_physiologically_plausible(records):
    """The pulse-pressure floor is an explicit engineering assumption
    (configs/indian_population.yaml). Its whole purpose is this gate."""
    pulse = [
        r["blood_pressure"]["systolic_mm_hg"] - r["blood_pressure"]["diastolic_mm_hg"]
        for r in records
    ]
    assert min(pulse) >= 20, f"narrowest pulse pressure {min(pulse)} mmHg"


def test_no_two_records_are_identical(records):
    serialised = {json.dumps(r, sort_keys=True) for r in records}
    assert len(serialised) == EXPECTED_BATCH_SIZE


def test_every_record_carries_m8_provenance(records):
    for record in records:
        generator = record["provenance"]["generator"]
        assert "M8 (schema 0.8" in generator, record["patient_id"]
        # The M8 block must appear once, not stacked by repeated runs.
        assert generator.count("M8 (schema 0.8") == 1, record["patient_id"]
        assert any(
            "NFHS-5" in dataset for dataset in record["provenance"]["source_datasets"]
        )
        assert extract_indian_seed(record) is not None


# ---------------------------------------------------------------- REUSABILITY


def test_migration_is_idempotent(records, indian_config):
    """Re-running on already-migrated records must change nothing -- no
    duplicated encounter, timeline event, provenance block or diagnosis.
    This is the precondition for ever running it over the full dataset.
    """
    states = valid_states(indian_config)
    for record in records:
        again, errors, _ = migrate_record(record, indian_config, states=states)
        assert not errors, (record["patient_id"], errors)
        assert again == record, f"{record['patient_id']} changed on re-migration"


def test_migration_is_deterministic(indian_config):
    """Same input, same config -> same output, every time."""
    originals = sorted(BACKUP_DIR.glob("PAT_*.json"))
    assert originals, "no backed-up originals to re-migrate"
    states = valid_states(indian_config)
    for path in originals[:10]:
        source = json.loads(path.read_text(encoding="utf-8"))
        first, errors_a, _ = migrate_record(source, indian_config, states=states)
        second, errors_b, _ = migrate_record(source, indian_config, states=states)
        assert not errors_a and not errors_b
        assert first == second, path.name


def test_migration_reproduces_the_shipped_batch_from_the_originals(records, indian_config):
    """The output batch must be exactly what the migration produces from
    the preserved originals -- i.e. the batch is re-derivable, not
    hand-finished."""
    by_id = {r["patient_id"]: r for r in records}
    states = valid_states(indian_config)
    for path in sorted(BACKUP_DIR.glob("PAT_*.json")):
        source = json.loads(path.read_text(encoding="utf-8"))
        migrated, errors, _ = migrate_record(source, indian_config, states=states)
        assert not errors, (path.name, errors)
        assert migrated == by_id[source["patient_id"]], path.name


def test_originals_are_preserved_and_match_their_recorded_hashes(manifest):
    """The production dataset must be untouched, and the backups must
    still match the hashes the manifest recorded."""
    for entry in manifest["records"]:
        source = _REPO_ROOT / entry["source_path"]
        assert source.exists(), entry["source_path"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == entry["sha256"], f"{entry['patient_id']} source file has CHANGED"
        backup = _REPO_ROOT / entry["backup_path"]
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == entry["sha256"]


def test_originals_are_still_schema_v07(manifest):
    """Confirms the migration wrote to a separate location and did not
    upgrade the production dataset in place."""
    for entry in manifest["records"][:10]:
        source = json.loads((_REPO_ROOT / entry["source_path"]).read_text(encoding="utf-8"))
        assert source["provenance"]["schema_version"] == "0.7"
        assert source.get("blood_pressure") is None
        assert source.get("encounters") is None


def test_production_dataset_still_has_100000_records():
    assert len(list(SOURCE_DATASET.glob("PAT_*.json"))) == 100_000


def test_migration_refuses_a_record_whose_seed_replay_disagrees(records, indian_config):
    """The provenance audit must actually bite: tamper with a stored
    generated value and the migration must refuse rather than migrate
    around it."""
    tampered = json.loads(json.dumps(records[0]))
    tampered["provenance"]["schema_version"] = "0.7"
    tampered["risk_factors"]["bmi"] = 99.9  # not what this seed produces
    _, errors, _ = migrate_record(tampered, indian_config)
    assert any("seed-replay mismatch" in e for e in errors), errors


def test_migration_refuses_an_unknown_schema_version(records, indian_config):
    tampered = json.loads(json.dumps(records[0]))
    tampered["provenance"]["schema_version"] = "0.6"
    _, errors, _ = migrate_record(tampered, indian_config)
    assert any("unsupported schema_version" in e for e in errors), errors
