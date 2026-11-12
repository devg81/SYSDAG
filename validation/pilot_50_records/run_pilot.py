"""Pilot driver: select 50 records, back them up, migrate v0.7 -> v0.8, validate.

Deliberately thin. All reusable logic lives in the project's existing
modules -- `integration/migrate_v07_to_v08.py` (migration),
`generation/` (sampling/derivation), `validation/structural.py` and
`validation/clinical_consistency.py` (checks). This file only decides
WHICH 50 records the pilot uses, records that choice so it is
reproducible, and collects the numbers the reports quote. Nothing here
should be needed to apply the migration to the remaining 99,950 records.

Run:
    python validation/pilot_50_records/run_pilot.py --dry-run
    python validation/pilot_50_records/run_pilot.py
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_PILOT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PILOT_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402

from generation.indian_population import load_config as load_indian_config  # noqa: E402
from integration.migrate_v07_to_v08 import migrate_paths  # noqa: E402

# The production dataset. Read-only here -- the pilot never writes into it.
SOURCE_DATASET = _REPO_ROOT / "outputs" / "m5" / "100k_patients"
DATASET_SIZE = 100_000
BATCH_SIZE = 50

# Selection seed. Fixed so the same 50 patients are chosen on every run;
# a plain uniform sample without replacement across all 100,000 records,
# NOT a purposive pick. Coverage of rarer cases (treated hypertensives,
# diabetics, age-extrapolated patients) is therefore whatever chance
# gives, and is REPORTED rather than engineered -- a hand-picked batch
# would look complete while telling a reviewer nothing about the
# population.
SELECTION_SEED = 8

INPUT_DIR = _PILOT_DIR / "input"
OUTPUT_DIR = _PILOT_DIR / "output"
REPORTS_DIR = _PILOT_DIR / "reports"
BACKUP_DIR = INPUT_DIR / "original_records"


def select_patient_ids() -> list[str]:
    """Deterministic uniform sample of 50 of the 100,000 patient ids."""
    rng = np.random.default_rng(SELECTION_SEED)
    indices = rng.choice(DATASET_SIZE, size=BATCH_SIZE, replace=False)
    return [f"PAT_{i + 1:06d}" for i in sorted(int(i) for i in indices)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def back_up_originals(patient_ids: list[str]) -> list[dict[str, str]]:
    """Copy the 50 source records aside, with hashes, so the batch stays
    traceable to -- and verifiable against -- the untouched originals."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for pid in patient_ids:
        source = SOURCE_DATASET / f"{pid}.json"
        digest = sha256(source)
        shutil.copy2(source, BACKUP_DIR / f"{pid}.json")
        entries.append(
            {
                "patient_id": pid,
                "source_path": str(source.relative_to(_REPO_ROOT)).replace("\\", "/"),
                "backup_path": str((BACKUP_DIR / f"{pid}.json").relative_to(_REPO_ROOT)).replace(
                    "\\", "/"
                ),
                "sha256": digest,
            }
        )
    return entries


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The distribution/missingness numbers the reports quote. Computed
    from the migrated records themselves, never hand-copied."""
    sbp = [r["blood_pressure"]["systolic_mm_hg"] for r in records]
    dbp = [r["blood_pressure"]["diastolic_mm_hg"] for r in records]
    pulse = [s - d for s, d in zip(sbp, dbp)]
    ages = [r["demographics"]["age"] for r in records]

    def stats(values: list[float]) -> dict[str, float]:
        return {
            "n": len(values),
            "mean": round(statistics.mean(values), 2),
            "sd": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
            "min": round(min(values), 2),
            "median": round(statistics.median(values), 2),
            "max": round(max(values), 2),
        }

    hypertensive = [r for r in records if r["risk_factors"]["hypertension"]]
    treated = [
        r
        for r in records
        if any(m["drug_class"] == "antihypertensive" for m in (r["medications"] or []))
    ]
    diabetic = [r for r in records if r["risk_factors"]["diabetes"]]
    extrapolated = [
        r for r in records if r["blood_pressure"]["extrapolated_beyond_source_age_range"]
    ]

    # Field-level missingness, with the reason each absence is expected.
    def missing(field: str) -> int:
        return sum(1 for r in records if r.get(field) in (None, [], {}))

    return {
        "batch_size": len(records),
        "unique_patient_ids": len({r["patient_id"] for r in records}),
        "schema_versions": dict(Counter(r["provenance"]["schema_version"] for r in records)),
        "age": stats(ages),
        "sex": {
            "male": sum(1 for r in records if r["demographics"]["sex"] == 0),
            "female": sum(1 for r in records if r["demographics"]["sex"] == 1),
        },
        "blood_pressure": {
            "systolic_mm_hg": stats(sbp),
            "diastolic_mm_hg": stats(dbp),
            "pulse_pressure_mm_hg": stats(pulse),
            "sbp_gt_dbp_all": all(s > d for s, d in zip(sbp, dbp)),
            "pulse_pressure_below_20": sum(1 for p in pulse if p < 20),
            "raised_bp_count": sum(1 for s, d in zip(sbp, dbp) if s >= 140 or d >= 90),
            "age_extrapolated_count": len(extrapolated),
            "distinct_values": {
                "systolic": len(set(sbp)),
                "diastolic": len(set(dbp)),
            },
        },
        "cohort_coverage": {
            "hypertension_label_true": len(hypertensive),
            "on_antihypertensive": len(treated),
            "treated_and_controlled": sum(
                1
                for r in treated
                if r["blood_pressure"]["systolic_mm_hg"] < 140
                and r["blood_pressure"]["diastolic_mm_hg"] < 90
            ),
            "diabetes_label_true": len(diabetic),
            "diabetic_without_hba1c": sum(1 for r in diabetic if not r["labs"]),
            "age_band_sources": dict(
                Counter(r["blood_pressure"]["age_band_source"] for r in records)
            ),
        },
        "missingness": {
            "demographics.height_cm": sum(
                1 for r in records if r["demographics"]["height_cm"] is None
            ),
            "demographics.weight_kg": sum(
                1 for r in records if r["demographics"]["weight_kg"] is None
            ),
            "family_history": missing("family_history"),
            "echo": missing("echo"),
            "labs": missing("labs"),
            "medications": missing("medications"),
            "diagnoses": missing("diagnoses"),
            "blood_pressure": missing("blood_pressure"),
            "encounters": missing("encounters"),
        },
        "encounters": {
            "records_with_exactly_one": sum(1 for r in records if len(r["encounters"]) == 1),
            "types": dict(
                Counter(e["encounter_type"] for r in records for e in r["encounters"])
            ),
            "recorded_measurement_sets": dict(
                Counter(
                    ",".join(e["recorded_measurements"])
                    for r in records
                    for e in r["encounters"]
                )
            ),
        },
        "clinical_timeline": {
            "event_counts": dict(Counter(len(r["clinical_timeline"]) for r in records)),
            "event_types": dict(
                Counter(e["event_type"] for r in records for e in r["clinical_timeline"])
            ),
        },
        "ecg": {
            "signal_available_true": sum(
                1 for r in records if r.get("ecg") and r["ecg"]["signal_available"]
            ),
            "missing_superclasses": sum(
                1 for r in records if r.get("ecg") and not r["ecg"]["superclasses"]
            ),
        },
        "validation": {
            "validated_true": sum(1 for r in records if r["validation"]["validated"]),
            "total_errors": sum(len(r["validation"]["errors"]) for r in records),
        },
        "lipid_feasibility": lipid_feasibility(records),
    }


def lipid_feasibility(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts the pre-existing (M4B) lipid defect this pilot surfaces.

    TC, TG and HDL are sampled as three INDEPENDENT marginals, so some
    triples are internally impossible (TC < HDL + TG/5) and the LDL
    clip_range floor of 30 mg/dL silently absorbs it. Counted here so
    the rate is a number in a report rather than a surprise in review.
    """
    impossible, clipped, high_tg = [], [], []
    for record in records:
        lp = record["lipid_panel"]
        implied = (
            lp["total_cholesterol_mg_dl"]
            - lp["hdl_mg_dl"]
            - lp["triglycerides_mg_dl"] / 5.0
        )
        if implied < 0:
            impossible.append(record["patient_id"])
        elif implied < 30.0:
            clipped.append(record["patient_id"])
        if lp["triglycerides_mg_dl"] > 400.0:
            high_tg.append(record["patient_id"])
    return {
        "internally_impossible_tc_below_components": {
            "count": len(impossible),
            "patient_ids": impossible,
        },
        "ldl_clipped_at_floor_but_feasible": {"count": len(clipped), "patient_ids": clipped},
        "triglycerides_above_friedewald_validity_400": {
            "count": len(high_tg),
            "patient_ids": high_tg,
        },
        "note": (
            "Pre-existing M4B artefact, NOT introduced by M8. The stored LDL still "
            "follows its documented clip rule, so these are warnings rather than "
            "validation errors -- but see reports/validation_report.md: this is the "
            "pilot's headline unresolved issue for the full 100,000-record dataset."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="audit only; write nothing anywhere"
    )
    args = parser.parse_args(argv)

    if not SOURCE_DATASET.is_dir():
        print(f"ERROR: source dataset not found at {SOURCE_DATASET}")
        return 2

    patient_ids = select_patient_ids()
    source_paths = [SOURCE_DATASET / f"{pid}.json" for pid in patient_ids]
    missing = [p for p in source_paths if not p.exists()]
    if missing:
        print(f"ERROR: {len(missing)} selected record(s) missing, e.g. {missing[0]}")
        return 2

    indian_config = load_indian_config()
    started = datetime.datetime.now(datetime.timezone.utc)
    # output_dir=None: the pilot writes ONE combined batch file, not a
    # second per-record copy of its own output. The full-dataset run uses
    # the migration's CLI with a real --output-dir instead.
    summary = migrate_paths(source_paths, None, indian_config, dry_run=args.dry_run)
    elapsed = (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()

    print(f"selected {len(patient_ids)} records (seed {SELECTION_SEED})")
    print(f"clean: {summary['records_clean']}   failed: {summary['records_failed']}")
    print(f"elapsed: {elapsed:.2f}s  ({1000 * elapsed / len(patient_ids):.1f} ms/record)")
    for result in summary["results"]:
        for error in result["errors"]:
            print(f"  FAIL {result['patient_id']}: {error}")

    if summary["records_failed"]:
        print("\nNo output written -- a partial batch is worse than none.")
        return 1
    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0

    records = summary["records"]
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    backups = back_up_originals(patient_ids)
    batch_path = OUTPUT_DIR / "patient_records_50.json"
    batch_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    manifest = {
        "created_at": started.isoformat(),
        "purpose": (
            "Traceability manifest for the 50-record schema-v0.8 validation pilot. "
            "Every selected record is listed with the SHA-256 of its UNMODIFIED "
            "source file, so the batch can be re-derived and the originals "
            "re-verified at any time."
        ),
        "source_dataset": str(SOURCE_DATASET.relative_to(_REPO_ROOT)).replace("\\", "/"),
        "source_dataset_record_count": DATASET_SIZE,
        "source_schema_version": summary["source_schema_version"],
        "target_schema_version": summary["target_schema_version"],
        "selection_method": (
            f"numpy.random.default_rng({SELECTION_SEED}).choice({DATASET_SIZE}, "
            f"size={BATCH_SIZE}, replace=False), mapped to PAT_%06d of index+1, sorted. "
            "Uniform without replacement over the whole dataset -- not purposive, "
            "not stratified, not hand-picked."
        ),
        "selection_seed": SELECTION_SEED,
        "batch_size": BATCH_SIZE,
        "migration_entry_point": "integration/migrate_v07_to_v08.py",
        "config": {
            "indian_population": "configs/indian_population.yaml",
            "indian_population_random_seed": indian_config["random_seed"],
            "per_record_seed_rule": (
                "each record's blood pressure is generated by replaying "
                "generation.indian_population.generate_indian_attributes() from the "
                "seed recorded in that record's own provenance.generator "
                "(indian_random_seed=N); the replay is verified to reproduce every "
                "pre-existing field before the new field is accepted"
            ),
        },
        "originals_preserved": (
            "The source dataset was opened read-only. Verified copies are kept at "
            "input/original_records/ and hashed below."
        ),
        "patient_ids": patient_ids,
        "records": backups,
        "timing": {
            "elapsed_seconds": round(elapsed, 3),
            "ms_per_record": round(1000 * elapsed / len(patient_ids), 2),
            "projected_full_dataset_minutes": round(
                elapsed / len(patient_ids) * DATASET_SIZE / 60, 1
            ),
        },
    }
    (INPUT_DIR / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    stats = summarise(records)
    stats["migration_run"] = {
        k: v for k, v in summary.items() if k not in ("records", "results")
    }
    stats["per_record_notes"] = summary["results"]
    # Every clinical warning raised across the batch, tallied by kind.
    # Warnings are disclosure, not failure -- but an untallied warning is
    # indistinguishable from a hidden one.
    warning_counts: Counter[str] = Counter()
    for result in summary["results"]:
        for note in result["notes"]:
            if note.startswith("clinical warning: "):
                text = note[len("clinical warning: ") :]
                # Collapse to the warning's kind, dropping per-record numbers.
                kind = text.split(":")[0].split(" -- ")[0][:90]
                warning_counts[kind] += 1
    stats["clinical_warnings_by_kind"] = dict(warning_counts)
    stats["clinical_warning_total"] = sum(warning_counts.values())
    (REPORTS_DIR / "validation_metrics.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nbatch     -> {batch_path.relative_to(_REPO_ROOT)}")
    print(f"manifest  -> {(INPUT_DIR / 'source_manifest.json').relative_to(_REPO_ROOT)}")
    print(f"metrics   -> {(REPORTS_DIR / 'validation_metrics.json').relative_to(_REPO_ROOT)}")
    print(f"\nvalidated: {stats['validation']['validated_true']}/{len(records)}")
    print(json.dumps(stats["blood_pressure"], indent=2))
    print(json.dumps(stats["cohort_coverage"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
