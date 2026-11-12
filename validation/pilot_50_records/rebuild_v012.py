"""Rebuild the 50-record pilot at the CURRENT schema (v0.12) -- -jatin, 2026-11-12.

Human decision (2026-11-12, open question 9): rebuild the stale v0.8 pilot
rather than retire it. The v0.8 pilot was a v0.7 -> v0.8 MIGRATION of 50
records from the M5 dataset; that migration path no longer applies. This
script regenerates the SAME 50 patient IDs (from input/source_manifest.json)
fresh with `build_patient()`, runs the structural and clinical-consistency
validators, and writes:

    output_v012/patient_records_50_v012.json   the 50 records
    reports/validation_metrics_v012.json       pass rates, checks, timing

It does not touch the v0.8 files (they remain as the historical artifact).

Needs PTB-XL CSVs + a working pandas (build_patient), so it is meant to run
on the AWS/teammate machine:

    python validation/pilot_50_records/rebuild_v012.py

Exit code 1 if any record fails structural or clinical validation.
"""

from __future__ import annotations

import datetime
import json
import sys
import time
from collections import Counter
from pathlib import Path

_PILOT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PILOT_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import load_config as load_indian_config  # noqa: E402
from integration.build_patient import build_patient, load_config  # noqa: E402
from schemas.patient_schema import SCHEMA_VERSION  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from validation.structural import check_duplicate_ids  # noqa: E402

OUT_RECORDS = _PILOT_DIR / "output_v012" / "patient_records_50_v012.json"
OUT_METRICS = _PILOT_DIR / "reports" / "validation_metrics_v012.json"


def main() -> int:
    manifest = json.loads((_PILOT_DIR / "input" / "source_manifest.json").read_text(encoding="utf-8"))
    ids = manifest["patient_ids"]
    config = load_config(_REPO_ROOT / "configs" / "base.yaml")
    indian_config = load_indian_config()

    t0 = time.perf_counter()
    patients = [build_patient(int(pid.split("_")[1]), config, indian_config) for pid in ids]
    clinical = [validate_clinical_consistency(p, indian_config) for p in patients]
    elapsed = time.perf_counter() - t0

    records = []
    for p, c in zip(patients, clinical):
        d = p.to_dict()
        d["validation"]["clinical_consistency"] = {"valid": c.valid, "errors": c.errors, "warnings": c.warnings}
        records.append(d)
    OUT_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    OUT_RECORDS.write_text(json.dumps(records, indent=2), encoding="utf-8")

    lai = Counter(
        next(i.risk_category for i in p.lipid_interpretations if i.definition == "LAI_2020") for p in patients
    )
    metrics = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "author": "-jatin (script); run by whoever executes it",
        "schema_version": SCHEMA_VERSION,
        "patient_ids_source": "input/source_manifest.json (same 50 IDs as the v0.8 pilot)",
        "n": len(patients),
        "structurally_valid": sum(p.validation.validated for p in patients),
        "clinically_consistent": sum(c.valid for c in clinical),
        "clinical_warnings": sum(len(c.warnings) for c in clinical),
        "duplicate_id_errors": check_duplicate_ids(patients),
        "hyperlipidemia_true": sum(bool(p.risk_factors.hyperlipidemia) for p in patients),
        "lai_risk_categories": dict(lai),
        "checks_performed": sorted(set().union(*(c.checks_performed for c in clinical))),
        "seconds": round(elapsed, 2),
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    ok = metrics["structurally_valid"] == metrics["clinically_consistent"] == len(ids) and not metrics["duplicate_id_errors"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
