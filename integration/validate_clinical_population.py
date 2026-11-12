"""M4C (extended M8): run structural + clinical consistency validation
over an already-generated population's JSON output. Read-only analysis
— does not regenerate or modify anything.

M8 extension: `_patient_from_dict` (which predates `blood_pressure`/
`Encounter` and assigned `encounters` as a raw list of dicts rather than
`Encounter` instances) is replaced by
`integration.migrate_v07_to_v08._dict_to_patient`, the same v0.8-aware
reconstruction the migration itself uses — one deserializer, not two
independently-maintained ones. Structural validity is now RECOMPUTED via
`validation.structural.validate_patient` rather than trusted from the
record's own stored `validation.validated` flag (a record could claim
`validated: true` and be wrong; this script no longer takes that on
faith). Three new capabilities, each reusing existing code rather than
adding a parallel one: `--compare-source` (migration-integrity audit —
re-derives each record from its untouched v0.7 source via the same
`migrate_record()` the real migration used, and diffs the result against
what is actually on disk, so disk corruption/truncation and migration
drift are both caught), `--stats` (population-level distribution/
missingness/duplicate summary over whichever fields are present), and
`--json-out` (machine-readable report for `docs/PROJECT_STATE.md`-style
record-keeping).

SINGLE STREAMING PASS, on purpose: an earlier version of this script
loaded all 100,000 output records into one list, reconstructed all
100,000 into a second list of `Patient` objects, then did that again for
the source-comparison pass -- three full-population lists alive at once.
On this machine (~4GB free at the time) that got the process killed for
memory, not because any one record is large, but because holding
three live copies of a 100,000-record population at once was the
pattern, not any single record. This version visits each output file
exactly once, derives everything it needs from that one record
(reconstructing a `Patient`, running both validators, optionally loading
and migrating the matching source record), and keeps only small
aggregates (counts, `Counter`s, and per-record scalars needed for
`statistics.mean`/`stdev`) across the loop -- not the records themselves.
Only records that actually have an error are kept by id, so the error
dicts stay small regardless of population size unless something is
genuinely wrong.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import (  # noqa: E402
    load_config as load_indian_config,
    valid_states,
)
from integration.migrate_v07_to_v08 import _dict_to_patient, migrate_record  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from validation.structural import validate_patient  # noqa: E402

# Kept as a thin alias: existing imports of `_patient_from_dict` elsewhere
# (if any) keep working, but the real reconstruction now lives in exactly
# one place (the migration module), per this project's own
# no-duplicate-independent-generator discipline (docs/CLINICAL_RECORD_DESIGN.md §D).
_patient_from_dict = _dict_to_patient


def _load_one(path: Path) -> tuple[Optional[dict], Optional[str]]:
    """Returns (record, load_error) — exactly one of the two is set.
    A bad file (truncated write, invalid JSON) is reported, not raised,
    so it doesn't abort validation of the other 99,999."""
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return None, f"{path.name}: empty file"
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"{path.name}: invalid JSON ({e})"
    except OSError as e:
        return None, f"{path.name}: unreadable ({e})"


def _warning_kind(w: str) -> str:
    if "internally impossible" in w:
        return "lipid_panel internally impossible (TC < HDL + TG/5)"
    if "clip floor" in w:
        return "LDL clipped at floor (feasible but < 30)"
    if "Friedewald" in w:
        return "triglycerides > 400 (Friedewald invalid)"
    if "superclasses is empty" in w:
        return "ecg.superclasses empty (PTB-XL gap)"
    if "HbA1c value" in w and "SD" in w:
        return "HbA1c statistically far from age/sex-conditioned mean"
    return w.split(":")[0][:80]


class _RunningStat:
    """Mean/SD/min/max over a value stream without keeping every value.

    Welford's online algorithm -- exact, O(1) memory per stat, the
    standard reuse-first choice over `statistics.stdev` on a stored list
    (`CLAUDE.md` "stdlib before custom" applies to algorithms too; this
    is the textbook streaming variance formula, not a novel one)."""

    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.min = None
        self.max = None

    def add(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)
        self.min = x if self.min is None else min(self.min, x)
        self.max = x if self.max is None else max(self.max, x)

    def to_dict(self) -> dict[str, float]:
        sd = (self.m2 / (self.n - 1)) ** 0.5 if self.n > 1 else 0.0
        return {
            "n": self.n,
            "mean": round(self.mean, 3),
            "sd": round(sd, 3),
            "min": round(self.min, 3) if self.min is not None else None,
            "max": round(self.max, 3) if self.max is not None else None,
        }


def validate_population(
    in_dir: Path,
    indian_config: dict[str, Any],
    *,
    compare_source: Optional[Path] = None,
    want_stats: bool = False,
    sample: Optional[int] = None,
) -> dict[str, Any]:
    """The one streaming pass. Every per-record object (dict, Patient,
    ClinicalValidationResult, migrate_record() output) is scoped to a
    single loop iteration and discarded before the next -- only small
    aggregates survive the loop."""
    states = valid_states(indian_config)
    paths = sorted(Path(in_dir).glob("PAT_*.json"))
    if sample:
        paths = paths[:sample]

    load_errors: list[str] = []
    seen_ids: Counter = Counter()  # cheap: short strings, not full records
    structural_error_records: dict[str, list[str]] = {}
    clinical_error_records: dict[str, list[str]] = {}
    total_warnings = 0
    warning_kind_counts: Counter = Counter()
    check_counts: Counter = Counter()
    n_ok = 0

    mi_source_ids: set[str] = set()
    mi_mismatches: dict[str, list[str]] = {}
    mi_migrate_errors: dict[str, list[str]] = {}
    mi_checked = 0
    if compare_source:
        mi_source_ids = {p.stem for p in Path(compare_source).glob("PAT_*.json")}

    schema_versions: Counter = Counter()
    distinct_hashes: Counter = Counter()  # sha256 digest, not the full string -- fixed 32 bytes/record
    sbp_stat, dbp_stat, pp_stat = _RunningStat(), _RunningStat(), _RunningStat()
    distinct_sbp: set[int] = set()
    distinct_dbp: set[int] = set()
    bp_present = bp_sbp_gt_dbp_violations = bp_pp_below_20 = bp_raised = bp_extrapolated = 0
    lipid_present = lipid_impossible = lipid_clipped = lipid_high_tg = 0
    missingness: Counter = Counter()
    ecg_missing_superclass = ecg_signal_available = 0

    for path in paths:
        record, load_error = _load_one(path)
        if load_error:
            load_errors.append(load_error)
            continue

        patient_id = record.get("patient_id", path.stem)
        seen_ids[patient_id] += 1

        patient = _dict_to_patient(record)
        structural_errors = validate_patient(patient, valid_states=states)
        if structural_errors:
            structural_error_records[patient_id] = structural_errors
        else:
            n_ok += 1

        clinical = validate_clinical_consistency(patient, indian_config)
        if clinical.errors:
            clinical_error_records[patient_id] = clinical.errors
        total_warnings += len(clinical.warnings)
        for w in clinical.warnings:
            warning_kind_counts[_warning_kind(w)] += 1
        for c in clinical.checks_performed:
            check_counts[c] += 1
        del patient, clinical  # explicit: don't let these outlive the iteration

        if compare_source and patient_id in mi_source_ids:
            # The reverse case (a source record with no matching output)
            # is a set difference computed once after the loop, not
            # tracked per-record here.
            source, source_load_error = _load_one(Path(compare_source) / f"{patient_id}.json")
            if source_load_error:
                mi_migrate_errors[patient_id] = [source_load_error]
            else:
                recomputed, errors, _ = migrate_record(source, indian_config, states=states)
                mi_checked += 1
                if errors:
                    mi_migrate_errors[patient_id] = errors
                elif recomputed != record:
                    mi_mismatches[patient_id] = sorted(
                        k
                        for k in set(recomputed) | set(record)
                        if recomputed.get(k) != record.get(k)
                    )
                del recomputed
            del source

        if want_stats:
            schema_versions[record.get("provenance", {}).get("schema_version")] += 1
            distinct_hashes[
                hashlib.sha256(
                    json.dumps(record, sort_keys=True).encode("utf-8")
                ).digest()
            ] += 1

            bp = record.get("blood_pressure")
            if bp is not None:
                bp_present += 1
                s, d = bp["systolic_mm_hg"], bp["diastolic_mm_hg"]
                sbp_stat.add(s)
                dbp_stat.add(d)
                pp_stat.add(s - d)
                distinct_sbp.add(s)
                distinct_dbp.add(d)
                if s <= d:
                    bp_sbp_gt_dbp_violations += 1
                if s - d < 20:
                    bp_pp_below_20 += 1
                if s >= 140 or d >= 90:
                    bp_raised += 1
                if bp["extrapolated_beyond_source_age_range"]:
                    bp_extrapolated += 1

            lp = record.get("lipid_panel")
            if lp is not None:
                lipid_present += 1
                implied = lp["total_cholesterol_mg_dl"] - lp["hdl_mg_dl"] - lp["triglycerides_mg_dl"] / 5.0
                if implied < 0:
                    lipid_impossible += 1
                elif implied < 30.0:
                    lipid_clipped += 1
                if lp["triglycerides_mg_dl"] > 400.0:
                    lipid_high_tg += 1

            for field_name in (
                "family_history", "echo", "labs", "medications", "diagnoses",
                "medical_history", "encounters",
            ):
                if record.get(field_name) in (None, [], {}):
                    missingness[field_name] += 1

            ecg = record.get("ecg")
            if ecg:
                if not ecg["superclasses"]:
                    ecg_missing_superclass += 1
                if ecg["signal_available"]:
                    ecg_signal_available += 1

        del record  # last reference dropped before the next loop iteration

    n = len(paths) - len(load_errors)
    duplicate_patient_id_errors = [
        f"duplicate patient_id: {pid} (x{count})" for pid, count in seen_ids.items() if count > 1
    ]

    report: dict[str, Any] = {
        "source_dir": str(in_dir),
        "load_errors": load_errors,
        "structural_and_clinical": {
            "n": n,
            "duplicate_patient_id_errors": duplicate_patient_id_errors,
            "structurally_valid": n_ok,
            "structural_error_records": structural_error_records,
            "clinically_consistent": n - len(clinical_error_records),
            "clinical_error_records": clinical_error_records,
            "total_clinical_warnings": total_warnings,
            "warnings_by_kind": dict(warning_kind_counts),
            "checks_performed_counts": dict(check_counts),
        },
    }

    if compare_source:
        output_ids = set(seen_ids.keys())
        report["migration_integrity"] = {
            "source_records_checked": mi_checked,
            "output_records_with_no_matching_source": sorted(output_ids - mi_source_ids),
            "source_records_with_no_matching_output": sorted(mi_source_ids - output_ids),
            "records_matching_recomputation_exactly": (
                mi_checked - len(mi_mismatches) - len(mi_migrate_errors)
            ),
            "records_differing_from_recomputation": mi_mismatches,
            "records_migrate_errors": mi_migrate_errors,
        }

    if want_stats:
        stats: dict[str, Any] = {"n": n}
        stats["blood_pressure"] = {"present": bp_present, "missing": n - bp_present}
        if bp_present:
            stats["blood_pressure"].update(
                {
                    "systolic_mm_hg": sbp_stat.to_dict(),
                    "diastolic_mm_hg": dbp_stat.to_dict(),
                    "pulse_pressure_mm_hg": pp_stat.to_dict(),
                    "sbp_gt_dbp_violations": bp_sbp_gt_dbp_violations,
                    "pulse_pressure_below_20": bp_pp_below_20,
                    "raised_bp_count": bp_raised,
                    "age_extrapolated_count": bp_extrapolated,
                    "distinct_sbp_values": len(distinct_sbp),
                    "distinct_dbp_values": len(distinct_dbp),
                }
            )
        if lipid_present:
            stats["lipid_feasibility"] = {
                "n": lipid_present,
                "internally_impossible_tc_below_components": {
                    "count": lipid_impossible,
                    "pct": round(100 * lipid_impossible / lipid_present, 2),
                },
                "ldl_clipped_at_floor_but_feasible": {
                    "count": lipid_clipped,
                    "pct": round(100 * lipid_clipped / lipid_present, 2),
                },
                "triglycerides_above_friedewald_validity_400": {
                    "count": lipid_high_tg,
                    "pct": round(100 * lipid_high_tg / lipid_present, 2),
                },
            }
        stats["missingness"] = {
            field_name: {
                "empty_or_null": missingness[field_name],
                "pct": round(100 * missingness[field_name] / n, 2) if n else 0.0,
            }
            for field_name in (
                "family_history", "echo", "labs", "medications", "diagnoses",
                "medical_history", "encounters",
            )
        }
        stats["schema_versions"] = {k: v for k, v in schema_versions.items() if k is not None}
        stats["exact_duplicate_records"] = sum(c for c in distinct_hashes.values() if c > 1)
        stats["unique_patient_ids"] = len(seen_ids)
        stats["ecg"] = {
            "superclasses_empty": ecg_missing_superclass,
            "signal_available_true": ecg_signal_available,
        }
        report["statistics"] = stats

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("in_dir", nargs="?", default="outputs/m4c/10_patients")
    parser.add_argument(
        "--compare-source",
        help="v0.7 source directory to re-derive each record from and diff against disk",
    )
    parser.add_argument("--stats", action="store_true", help="also print the statistical summary")
    parser.add_argument("--json-out", help="write the full machine-readable report here")
    parser.add_argument("--sample", type=int, help="validate only the first N records (fast dev loop)")
    args = parser.parse_args(argv)

    indian_config = load_indian_config()
    report = validate_population(
        _REPO_ROOT / args.in_dir,
        indian_config,
        compare_source=(_REPO_ROOT / args.compare_source) if args.compare_source else None,
        want_stats=args.stats,
        sample=args.sample,
    )

    sc = report["structural_and_clinical"]
    print(f"n={sc['n']}  (load errors: {len(report['load_errors'])})")
    print(f"structurally valid (recomputed): {sc['structurally_valid']}/{sc['n']}")
    print(f"clinically consistent: {sc['clinically_consistent']}/{sc['n']}")
    print(f"duplicate patient_id errors: {len(sc['duplicate_patient_id_errors'])}")
    print(f"total clinical warnings: {sc['total_clinical_warnings']}")
    if sc["warnings_by_kind"]:
        print("warnings by kind:")
        for kind, count in sorted(sc["warnings_by_kind"].items(), key=lambda kv: -kv[1]):
            print(f"  {count:7d}  {kind}")
    if sc["structural_error_records"]:
        print(f"structural errors in {len(sc['structural_error_records'])} record(s), e.g.:")
        for pid, errs in list(sc["structural_error_records"].items())[:10]:
            print(f"  {pid}: {errs[:2]}")
    if sc["clinical_error_records"]:
        print(f"clinical errors in {len(sc['clinical_error_records'])} record(s), e.g.:")
        for pid, errs in list(sc["clinical_error_records"].items())[:10]:
            print(f"  {pid}: {errs[:2]}")

    if args.compare_source:
        mi = report["migration_integrity"]
        print()
        print(f"migration integrity: {mi['source_records_checked']} source records checked")
        print(f"  matching recomputation exactly: {mi['records_matching_recomputation_exactly']}")
        print(f"  differing from recomputation: {len(mi['records_differing_from_recomputation'])}")
        print(f"  migrate_record() errors: {len(mi['records_migrate_errors'])}")
        print(f"  output records with no source: {len(mi['output_records_with_no_matching_source'])}")
        print(f"  source records with no output: {len(mi['source_records_with_no_matching_output'])}")

    if args.stats:
        print()
        print(json.dumps(report["statistics"], indent=2))

    if args.json_out:
        Path(_REPO_ROOT / args.json_out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nfull report -> {args.json_out}")

    ok = (
        not report["load_errors"]
        and not sc["duplicate_patient_id_errors"]
        and sc["structurally_valid"] == sc["n"]
        and sc["clinically_consistent"] == sc["n"]
        and (not args.compare_source or (
            not report["migration_integrity"]["records_differing_from_recomputation"]
            and not report["migration_integrity"]["records_migrate_errors"]
        ))
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
