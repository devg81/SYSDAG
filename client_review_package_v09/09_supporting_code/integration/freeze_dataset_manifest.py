"""Freeze a validated dataset version: write a manifest in the SAME
format `outputs/m5/dataset_manifest.json` established (M5) — reused, not
reinvented, per this project's own versioning convention.

Only run this after the corresponding validation report shows a clean
pass; it records the validation result, it does not perform validation
itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def _sha256_of_directory_listing(directory: Path) -> str:
    """A single checksum over (filename, per-file sha256) pairs, sorted —
    cheap to verify, and any added/removed/modified/truncated file
    changes it. Not a per-file manifest (100,000 entries would dwarf this
    file) but a reproducible digest of the whole directory's content."""
    hasher = hashlib.sha256()
    for path in sorted(directory.glob("PAT_*.json")):
        hasher.update(path.name.encode("utf-8"))
        hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return hasher.hexdigest()


def build_manifest(
    output_dir: Path,
    source_dir: Path | None,
    validation_report_path: Path,
    schema_version: str,
    dataset_name: str,
    dataset_version: str,
) -> dict[str, Any]:
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    sc = validation_report["structural_and_clinical"]
    mi = validation_report.get("migration_integrity")

    files = sorted(output_dir.glob("PAT_*.json"))
    # Filename IS the canonical patient_id (integration/patient_id.py's
    # own convention) -- cheap uniqueness check without re-parsing
    # 100,000 JSON bodies a second time; the validator pass already did
    # the real duplicate-ID check (which compares the records' OWN
    # patient_id field, catching a file renamed to not match its content).
    patient_ids = [p.stem for p in files]
    manifest: dict[str, Any] = {
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "patient_count": len(files),
        "schema_version": schema_version,
        "source_dataset": (
            {
                "path": str(source_dir.relative_to(_REPO_ROOT)).replace("\\", "/"),
                "schema_version": "0.7",
                "record_count": len(list(source_dir.glob("PAT_*.json"))),
                "immutability": "source dataset is read-only input to the migration; never modified in place",
            }
            if source_dir is not None
            else "none -- generated fresh via integration/generate_population.py (seed = random_seed + sequence)"
        ),
        "migration_entry_point": (
            "integration.migrate_v07_to_v08.migrate_record" if source_dir is not None else None
        ),
        "code_state": {
            "git_head_commit": _git_head(),
            "note": (
                "this project does not commit per-milestone by standing convention "
                "(see docs/PROJECT_STATE.md); the schema/generation/validation code "
                "at the time of this freeze is the working tree, not necessarily this "
                "commit alone"
            ),
        },
        "validation_status": {
            "structural": "PASS" if sc["structurally_valid"] == sc["n"] else "FAIL",
            "structurally_valid_count": sc["structurally_valid"],
            "structurally_invalid_count": sc["n"] - sc["structurally_valid"],
            "unique_patient_ids": len(set(patient_ids)),
            "duplicate_patient_id_errors": len(sc["duplicate_patient_id_errors"]),
        },
        "clinical_validation_status": {
            "status": "PASS" if sc["clinically_consistent"] == sc["n"] else "FAIL",
            "clinically_consistent_count": sc["clinically_consistent"],
            "clinical_errors": sum(len(v) for v in sc["clinical_error_records"].values()),
            "clinical_warnings": sc["total_clinical_warnings"],
            "warnings_by_kind": sc["warnings_by_kind"],
            "checks_performed": sorted(sc["checks_performed_counts"].keys()),
        },
        "accepted_limitations": {
            "lipid_panel_internal_feasibility": (
                "Infeasible TC/TG/HDL triples are rejected and redrawn (D019); LDL "
                "can still sit at the documented 30 mg/dL clip floor (validator WARNING)."
            ),
            "blood_pressure_age_extrapolation": (
                "NFHS-5 source coverage is men<=54, women<=49; older patients use the "
                "oldest band held constant (conservative, not invented). Flagged per "
                "record via blood_pressure.extrapolated_beyond_source_age_range."
            ),
            "family_history": (
                "LASI observed for 45+; MODEL-DERIVED (calibrated parent simulation) "
                "for 20-44, tagged per record via family_history.derivation (D020)."
            ),
            "air_quality": (
                "2023 CPCB state annual mean, urban-station-weighted and applied "
                "unadjusted to rural patients (flagged per record); null with a reason "
                "for 9 unmonitored states/UTs (D021)."
            ),
            "height_weight": "not generated -- no national mean+SD of Indian adult height located",
            "echo": "not generated -- scope entirely open",
            "hyperlipidemia_diagnosis": "deliberately deferred (D015) -- unchanged by this freeze",
            "ecg_waveform": "NOT GENERATED -- metadata-only (Stage 4 explicitly deferred, out of scope)",
        },
        "migration_integrity": (
            {
                "source_records_checked": mi["source_records_checked"],
                "records_matching_recomputation_exactly": mi["records_matching_recomputation_exactly"],
                "records_differing_from_recomputation": len(mi["records_differing_from_recomputation"]),
                "records_migrate_errors": len(mi["records_migrate_errors"]),
            }
            if mi is not None
            else "not checked in this run"
        ),
        "directory_checksum_sha256": _sha256_of_directory_listing(output_dir),
        "full_validation_report": str(validation_report_path.relative_to(_REPO_ROOT)).replace("\\", "/"),
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-dir", help="v0.7 source of a migrated dataset; omit for a fresh generation")
    parser.add_argument("--validation-report", required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    manifest = build_manifest(
        _REPO_ROOT / args.output_dir,
        _REPO_ROOT / args.source_dir if args.source_dir else None,
        _REPO_ROOT / args.validation_report,
        args.schema_version,
        args.dataset_name,
        args.dataset_version,
    )
    out_path = _REPO_ROOT / args.out
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"manifest -> {args.out}")
    print(json.dumps({k: v for k, v in manifest.items() if k != "directory_checksum_sha256"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
