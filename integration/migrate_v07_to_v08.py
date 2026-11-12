"""Schema v0.7 -> v0.8 record migration (M8). Reusable, idempotent, dry-runnable.

WHAT IT ADDS
    demographics.height_cm / weight_kg  still null -- no evidence (see
                                        generation.indian_population.sample_height_cm)
    blood_pressure                      NEW: SBP/DBP conditional on the
                                        already-primary hypertension label
    encounters                          NEW: one synthetic_baseline_assessment,
                                        a structural container for this
                                        record's single measurement
                                        cross-section -- NOT a healthcare visit
    clinical_timeline                   rebuilt: gains `reference_id` and one
                                        event indexing the encounter
    provenance                          schema_version 0.7 -> 0.8, generator
                                        string and source_datasets extended
    validation                          re-run (structural + clinical)

WHAT IT NEVER TOUCHES
    patient_id, demographics.age/sex/state/urban_rural, risk_factors.*,
    lipid_panel, lipid_interpretations, labs, diagnoses, medical_history,
    medications, ecg, echo, family_history. All are asserted unchanged
    byte-for-byte (see `_UNCHANGED_FIELDS`), so a silent overwrite is a
    hard error rather than something a reviewer has to notice.

HOW IT STAYS CONSISTENT WITH FRESH GENERATION -- the central design choice.
    The migration does NOT invent a new random stream for blood pressure.
    It REPLAYS `generate_indian_attributes()` from the record's own
    recorded seed (`provenance.generator`'s `indian_random_seed=N`) and
    takes only the new field from that replay. Because blood pressure is
    drawn LAST in the generator's draw order, every pre-existing field
    comes off the replay identically -- which this module then VERIFIES
    against the stored record. Two consequences worth stating plainly:

      1. `migrate(record)` and a fresh `build_patient(sequence)` produce
         the same blood pressure for the same patient. There is one
         source of truth, not two.
      2. The replay doubles as a provenance audit. If a stored value
         disagrees with its own seed's replay, the record was not
         produced by the provenance it claims, and that is reported as
         an error instead of being quietly migrated.

IDEMPOTENCE
    Every derived field is REBUILT from the preserved base fields, never
    appended to. Re-running on an already-migrated v0.8 record therefore
    yields a byte-identical result -- no duplicated encounter, diagnosis
    or timeline event. Verified in
    `validation/pilot_50_records/tests/test_pilot_50_records.py`.

SCALE
    Designed for the full 100,000-record dataset, but deliberately does
    not reach for it: `--input-dir` plus `--ids-file` is how the pilot
    confines itself to 50 records. See `--help`.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.clinical_history import derive_encounters, derive_timeline  # noqa: E402
from generation.indian_population import (  # noqa: E402
    derive_weight_kg,
    generate_indian_attributes,
    load_config as load_indian_config,
    valid_states,
)
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from validation.structural import validate_patient  # noqa: E402

SOURCE_SCHEMA_VERSION = "0.7"
TARGET_SCHEMA_VERSION = "0.8"  # pinned: SCHEMA_VERSION moved on to 0.9 (D021)

# Fields the migration must leave byte-identical. Checked, not trusted:
# "no existing valid values were silently overwritten" is a validation
# requirement, so it is enforced in code rather than asserted in a report.
_UNCHANGED_FIELDS = (
    "patient_id",
    "risk_factors",
    "family_history",
    "medical_history",
    "diagnoses",
    "medications",
    "labs",
    "lipid_panel",
    "lipid_interpretations",
    "ecg",
    "echo",
)

# Demographics keys that must survive untouched (height_cm/weight_kg are
# the two the migration is allowed to write, and today it writes None to
# both).
_UNCHANGED_DEMOGRAPHICS = ("age", "sex", "state", "urban_rural")

_SEED_RE = re.compile(r"indian_random_seed=(\d+)")

# Appended to provenance.generator. Kept as one block so the migration's
# own additions are visually separable from M2C-M4E's history.
_M8_PROVENANCE = (
    "; M8 (schema 0.8, integration/migrate_v07_to_v08.py): blood_pressure "
    "SBP/DBP drawn from NFHS-5 age-band×sex bivariate normals (means: "
    "PLOS ONE 2025 doi:10.1371/journal.pone.0332226; per-band SDs DERIVED "
    "from that paper's mean/95%-CI/n and cross-validated to within 0.8% "
    "against the independently published NFHS-5 male overall SDs, "
    "PMC11068163; SBP/DBP correlation r=0.7255 DERIVED from that paper's "
    "SD(SBP)/SD(DBP)/SD(pulse-pressure) triple, not assumed), restricted "
    "to the region the hypertension label's OWN published definition "
    "implies (SBP≥140 and/or DBP≥90 and/or on antihypertensive) -- so BP "
    "is CONDITIONAL on that already-primary label and is NEVER used to "
    "re-derive it, and a TREATED hypertensive's BP is left unconstrained "
    "rather than forced high; a pulse-pressure floor of 20 mmHg is an "
    "EXPLICIT ENGINEERING ASSUMPTION (it removes a 2% tail of clinically "
    "absurd narrow-PP records a Gaussian copula produces), no upper cap; "
    "ages above source coverage (men>54, women>49) hold the oldest band "
    "constant, flagged per record via blood_pressure."
    "extrapolated_beyond_source_age_range; encounters contain ONE "
    "synthetic_baseline_assessment -- a structural container for this "
    "record's single measurement cross-section, NOT an observed healthcare "
    "contact (no visit/admission/appointment/follow-up is generated: no "
    "Indian utilization evidence exists); clinical_timeline gains "
    "reference_id and indexes that encounter, and still emits no "
    "diagnosis-onset, medication-start or follow-up event; height_cm/"
    "weight_kg STILL null after 6 failed research attempts for a national "
    "mean+SD of Indian adult height by sex (M4-0 ×3, M8 ×3), so BMI remains "
    "the evidence-primary anthropometric; family_history STILL null -- an "
    "open human scope decision, not an evidence gap; ECG unchanged and "
    "still metadata-only with signal_available=false (D003); echo "
    "unchanged. Full evidence and every limitation: "
    "configs/indian_population.yaml risk_factors.blood_pressure and "
    "validation/pilot_50_records/reports/evidence_and_assumptions.md"
)

_M8_SOURCE_DATASET = (
    "NFHS-5 2019-21 (blood pressure, via PLOS ONE 2025 "
    "doi:10.1371/journal.pone.0332226 and PMC11068163)"
)


def extract_indian_seed(record: dict[str, Any]) -> Optional[int]:
    """Read the record's OWN recorded Indian-conditioning seed.

    Taken from the record rather than recomputed from sequence so the
    replay below audits what the record claims about itself.
    """
    generator = (record.get("provenance") or {}).get("generator") or ""
    match = _SEED_RE.search(generator)
    return int(match.group(1)) if match else None


def _dict_to_patient(record: dict[str, Any]):
    """Rehydrate a record dict into the typed `Patient` the validators
    expect. Local import so `schemas` stays the only place the shapes
    are defined."""
    from schemas.patient_schema import (
        AirQuality,
        BloodPressure,
        Demographics,
        Diagnosis,
        ECGRecord,
        Encounter,
        Lab,
        LipidInterpretation,
        LipidPanel,
        MedicalHistoryEntry,
        Medication,
        Patient,
        Provenance,
        RiskFactors,
        TimelineEvent,
        ValidationMetadata,
    )

    def build(cls, value):
        return None if value is None else cls(**value)

    def build_list(cls, value):
        return None if value is None else [cls(**item) for item in value]

    return Patient(
        patient_id=record["patient_id"],
        demographics=Demographics(**record["demographics"]),
        provenance=Provenance(**record["provenance"]),
        risk_factors=build(RiskFactors, record.get("risk_factors")),
        family_history=record.get("family_history"),
        medical_history=build_list(MedicalHistoryEntry, record.get("medical_history")),
        diagnoses=build_list(Diagnosis, record.get("diagnoses")),
        medications=build_list(Medication, record.get("medications")),
        labs=build_list(Lab, record.get("labs")),
        blood_pressure=build(BloodPressure, record.get("blood_pressure")),
        air_quality=build(AirQuality, record.get("air_quality")),
        encounters=build_list(Encounter, record.get("encounters")),
        lipid_panel=build(LipidPanel, record.get("lipid_panel")),
        lipid_interpretations=build_list(
            LipidInterpretation, record.get("lipid_interpretations")
        ),
        ecg=build(ECGRecord, record.get("ecg")),
        echo=record.get("echo"),
        clinical_timeline=[TimelineEvent(**e) for e in record.get("clinical_timeline") or []],
        validation=ValidationMetadata(**record["validation"]),
    )


def _in_schema_field_order(record: dict[str, Any]) -> dict[str, Any]:
    """Reorder a record's top-level keys to the `Patient` dataclass's own
    field order. Keys the dataclass does not know about are preserved,
    appended after the known ones, so this can never lose data."""
    from dataclasses import fields

    from schemas.patient_schema import Patient

    order = [f.name for f in fields(Patient)]
    ordered = {name: record[name] for name in order if name in record}
    ordered.update({k: v for k, v in record.items() if k not in ordered})
    return ordered


def _verify_replay(
    record: dict[str, Any], attrs: dict[str, Any]
) -> list[str]:
    """Confirm the stored record really is what its own seed produces.

    Any disagreement means the record was not generated by the
    provenance it carries (a changed config, a different seed, a
    hand-edit). Reported, never migrated around.
    """
    problems: list[str] = []
    demo, replay_demo = record["demographics"], attrs["demographics"]
    for key in _UNCHANGED_DEMOGRAPHICS:
        if demo.get(key) != replay_demo.get(key):
            problems.append(
                f"demographics.{key}: stored {demo.get(key)!r} != seed replay "
                f"{replay_demo.get(key)!r}"
            )
    stored_rf = record.get("risk_factors") or {}
    for key, replayed in attrs["risk_factors"].items():
        if stored_rf.get(key) != replayed:
            problems.append(
                f"risk_factors.{key}: stored {stored_rf.get(key)!r} != seed replay {replayed!r}"
            )
    stored_lp = record.get("lipid_panel") or {}
    for key, replayed in attrs["lipid_panel"].items():
        if stored_lp.get(key) != replayed:
            problems.append(
                f"lipid_panel.{key}: stored {stored_lp.get(key)!r} != seed replay {replayed!r}"
            )
    stored_hba1c = next(
        (lab["value"] for lab in (record.get("labs") or []) if lab["analyte"] == "HbA1c"), None
    )
    if stored_hba1c != attrs["hba1c"]:
        problems.append(
            f"labs.HbA1c: stored {stored_hba1c!r} != seed replay {attrs['hba1c']!r}"
        )
    # Medication presence must agree with the replayed treatment draw --
    # this is the check that makes the new BP's `on_antihypertensive`
    # input trustworthy, since the BP region depends on it.
    stored_classes = {med["drug_class"] for med in (record.get("medications") or [])}
    replayed_treatment = attrs["medication_treatment"]
    expected_classes = set()
    if replayed_treatment.get("hypertension"):
        expected_classes.add("antihypertensive")
    if replayed_treatment.get("diabetes"):
        expected_classes.add("antidiabetic")
    if stored_classes != expected_classes:
        problems.append(
            f"medications drug_classes: stored {sorted(stored_classes)} != seed replay "
            f"{sorted(expected_classes)}"
        )
    return problems


def migrate_record(
    record: dict[str, Any],
    indian_config: dict[str, Any],
    *,
    states: Optional[set[str]] = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Migrate one record dict v0.7 (or already-v0.8) -> v0.8.

    Returns `(migrated, errors, notes)`. A non-empty `errors` means the
    record was NOT safely migratable and the caller must not write it.
    Pure: the input dict is never mutated.
    """
    errors: list[str] = []
    notes: list[str] = []
    original = copy.deepcopy(record)
    migrated = copy.deepcopy(record)

    stored_version = (migrated.get("provenance") or {}).get("schema_version")
    if stored_version == TARGET_SCHEMA_VERSION:
        notes.append("already at v0.8 -- rebuilding derived fields in place (idempotent re-run)")
    elif stored_version != SOURCE_SCHEMA_VERSION:
        errors.append(
            f"unsupported schema_version {stored_version!r}; this migration handles "
            f"{SOURCE_SCHEMA_VERSION!r} and {TARGET_SCHEMA_VERSION!r} only"
        )
        return migrated, errors, notes

    seed = extract_indian_seed(migrated)
    if seed is None:
        errors.append(
            "no indian_random_seed found in provenance.generator -- blood pressure "
            "cannot be generated reproducibly for this record"
        )
        return migrated, errors, notes

    attrs = generate_indian_attributes(np.random.default_rng(seed), indian_config)
    replay_problems = _verify_replay(migrated, attrs)
    if replay_problems:
        errors.extend(f"seed-replay mismatch: {p}" for p in replay_problems)
        return migrated, errors, notes
    notes.append(f"seed {seed} replay reproduced all pre-existing generated fields exactly")

    # --- The measurement cross-section's date. Taken from the record's
    # own existing dates, never invented: the labs' measured_at if
    # present, else the original synthetic_record_created event. ---
    lab_dates = {
        lab["measured_at"] for lab in (migrated.get("labs") or []) if lab.get("measured_at")
    }
    created_event = next(
        (
            e
            for e in (original.get("clinical_timeline") or [])
            if e.get("event_type") == "synthetic_record_created"
        ),
        None,
    )
    created_date = (created_event or {}).get("date")
    if created_date is None:
        errors.append("no synthetic_record_created event -- cannot anchor the timeline")
        return migrated, errors, notes
    if len(lab_dates) > 1:
        errors.append(f"labs carry conflicting measured_at dates {sorted(lab_dates)}")
        return migrated, errors, notes
    assessment_date = next(iter(lab_dates), created_date)
    if lab_dates and assessment_date != created_date:
        notes.append(
            f"labs measured_at {assessment_date} differs from record creation "
            f"{created_date}; using the measurement date for the assessment"
        )

    # --- NEW: blood pressure (last in the generator's draw order, so it
    # does not perturb anything above). ---
    bp = attrs["blood_pressure"]
    migrated["blood_pressure"] = {
        "systolic_mm_hg": bp["systolic_mm_hg"],
        "diastolic_mm_hg": bp["diastolic_mm_hg"],
        "measured_at": assessment_date,
        "age_band_source": bp["age_band_source"],
        "extrapolated_beyond_source_age_range": bp["extrapolated_beyond_source_age_range"],
        "source": "derived_conditional_on_hypertension_label",
    }

    # --- Anthropometrics: explicitly written as null rather than left
    # absent, so "not generated" is visible in the record itself. ---
    bmi = (migrated.get("risk_factors") or {}).get("bmi")
    height_cm = None  # no evidence -- see generation.indian_population.sample_height_cm
    migrated["demographics"]["height_cm"] = height_cm
    migrated["demographics"]["weight_kg"] = derive_weight_kg(bmi, height_cm)

    # --- NEW: encounters, then a timeline that indexes them. Both are
    # REBUILT from scratch, which is what makes a re-run idempotent. ---
    encounters = derive_encounters(
        migrated["patient_id"],
        assessment_date=assessment_date,
        has_blood_pressure=migrated.get("blood_pressure") is not None,
        has_lipid_panel=migrated.get("lipid_panel") is not None,
        lab_analytes=[lab["analyte"] for lab in (migrated.get("labs") or [])],
    )
    migrated["encounters"] = encounters
    migrated["clinical_timeline"] = derive_timeline(created_date, encounters)

    # --- Provenance. The generator string is extended, never replaced,
    # so M2C-M4E's trail survives; appended only once so a re-run does
    # not stack duplicates. ---
    provenance = migrated["provenance"]
    provenance["schema_version"] = TARGET_SCHEMA_VERSION
    if "M8 (schema 0.8" not in provenance["generator"]:
        provenance["generator"] = provenance["generator"] + _M8_PROVENANCE
    if _M8_SOURCE_DATASET not in provenance["source_datasets"]:
        provenance["source_datasets"] = list(provenance["source_datasets"]) + [_M8_SOURCE_DATASET]

    # --- Enforce the no-silent-overwrite contract. ---
    for field in _UNCHANGED_FIELDS:
        if migrated.get(field) != original.get(field):
            errors.append(f"migration changed {field!r}, which must be preserved unchanged")
    for key in _UNCHANGED_DEMOGRAPHICS:
        if migrated["demographics"].get(key) != original["demographics"].get(key):
            errors.append(f"migration changed demographics.{key!r}, which must be preserved")

    # --- Key order: match the `Patient` dataclass, so `blood_pressure`
    # sits where the schema puts it rather than trailing at the end just
    # because it was added last. Cosmetic, but it keeps a v0.7-vs-v0.8
    # diff readable for a reviewer. Any unexpected key is kept rather
    # than dropped. ---
    migrated = _in_schema_field_order(migrated)

    # --- Re-validate: structural and clinical, reported separately. ---
    patient = _dict_to_patient(migrated)
    structural_errors = validate_patient(
        patient, valid_states=states, expected_schema_version=TARGET_SCHEMA_VERSION
    )
    clinical = validate_clinical_consistency(patient, indian_config)
    migrated["validation"] = {
        "validated": not structural_errors and clinical.valid,
        "validation_version": "structural-0.3+clinical-0.2",
        "errors": list(structural_errors) + list(clinical.errors),
    }
    if structural_errors:
        errors.extend(f"structural: {e}" for e in structural_errors)
    if clinical.errors:
        errors.extend(f"clinical: {e}" for e in clinical.errors)
    notes.extend(f"clinical warning: {w}" for w in clinical.warnings)
    return migrated, errors, notes


def migrate_paths(
    input_paths: list[Path],
    output_dir: Optional[Path],
    indian_config: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Migrate a list of record files. Writes nothing when `dry_run`.

    Nothing is written unless EVERY record migrated cleanly -- a partial
    batch is worse than no batch, because it looks complete.
    """
    states = valid_states(indian_config)
    results: list[dict[str, Any]] = []
    migrated_records: list[dict[str, Any]] = []
    for path in input_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        migrated, errors, notes = migrate_record(record, indian_config, states=states)
        results.append(
            {
                "patient_id": record.get("patient_id"),
                "source_path": str(path),
                "errors": errors,
                "notes": notes,
            }
        )
        migrated_records.append(migrated)

    failed = [r for r in results if r["errors"]]
    summary = {
        "migrated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "target_schema_version": TARGET_SCHEMA_VERSION,
        "records_in": len(input_paths),
        "records_clean": len(results) - len(failed),
        "records_failed": len(failed),
        "dry_run": dry_run,
        "results": results,
    }

    if dry_run or failed:
        summary["written"] = 0
        return summary

    # `output_dir=None` means "migrate and hand the records back without
    # writing per-record files" -- how the pilot avoids keeping a second
    # copy of its own batch on disk. The full-dataset CLI run passes a
    # real directory and gets the one-file-per-patient layout that
    # matches the production dataset.
    written = 0
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for migrated in migrated_records:
            (output_dir / f"{migrated['patient_id']}.json").write_text(
                json.dumps(migrated, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        written = len(migrated_records)
    summary["written"] = written
    summary["records"] = migrated_records
    return summary


def _resolve_inputs(args: argparse.Namespace) -> list[Path]:
    input_dir = Path(args.input_dir)
    if args.ids_file:
        ids = [
            line.strip()
            for line in Path(args.ids_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return [input_dir / f"{pid}.json" for pid in ids]
    paths = sorted(input_dir.glob("PAT_*.json"))
    return paths[: args.limit] if args.limit else paths


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate synthetic patient records from schema v0.7 to v0.8 "
            "(adds blood_pressure, encounters, timeline references). "
            "Idempotent; use --dry-run to audit without writing."
        )
    )
    parser.add_argument("--input-dir", required=True, help="directory of PAT_*.json records")
    parser.add_argument("--output-dir", help="where to write migrated records (omit with --dry-run)")
    parser.add_argument(
        "--ids-file", help="file of patient_ids, one per line -- how the pilot scopes to 50"
    )
    parser.add_argument("--limit", type=int, help="migrate only the first N records found")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="audit and report without writing anything (always safe to run)",
    )
    parser.add_argument("--summary-out", help="write the JSON run summary here")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.output_dir:
        parser.error("--output-dir is required unless --dry-run is given")

    indian_config = load_indian_config()
    input_paths = _resolve_inputs(args)
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        print(f"ERROR: {len(missing)} input file(s) not found, e.g. {missing[0]}")
        return 2

    summary = migrate_paths(
        input_paths,
        Path(args.output_dir) if args.output_dir else None,
        indian_config,
        dry_run=args.dry_run,
    )

    print(f"records in:     {summary['records_in']}")
    print(f"records clean:  {summary['records_clean']}")
    print(f"records failed: {summary['records_failed']}")
    print(f"records written:{summary['written']}")
    for result in summary["results"]:
        for error in result["errors"]:
            print(f"  FAIL {result['patient_id']}: {error}")

    if args.summary_out:
        # Drop the full records from the summary file -- the migrated
        # records are the output directory's job, not the summary's.
        lean = {k: v for k, v in summary.items() if k != "records"}
        Path(args.summary_out).write_text(
            json.dumps(lean, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"summary -> {args.summary_out}")

    return 1 if summary["records_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
