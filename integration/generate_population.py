"""Generate an N-patient population via build_patient(), with structural
validation and duplicate-ID checking across the population.

Used for M2C's 10-patient and 100-patient development runs
(`docs/session_logs/2026-09-25_M2C-indian-conditioning.md`). No new
generation logic here — pure orchestration over the existing
`integration.build_patient.build_patient()`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from generation.indian_population import load_config as load_indian_config  # noqa: E402
from validation.structural import check_duplicate_ids  # noqa: E402
from schemas.patient_schema import Patient  # noqa: E402


def generate_population(
    n: int, config: dict[str, Any], indian_config: dict[str, Any]
) -> list[Patient]:
    return [build_patient(seq, config, indian_config) for seq in range(1, n + 1)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate N synthetic patients")
    parser.add_argument("n", type=int)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    config = load_config(_REPO_ROOT / "configs" / "base.yaml")
    indian_config = load_indian_config()

    patients = generate_population(args.n, config, indian_config)

    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else _REPO_ROOT / "outputs" / "m2c" / f"{args.n}_patients"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in patients:
        (out_dir / f"{p.patient_id}.json").write_text(
            json.dumps(p.to_dict(), indent=2), encoding="utf-8"
        )

    dup_errors = check_duplicate_ids(patients)
    n_valid = sum(1 for p in patients if p.validation.validated)
    print(f"Generated {len(patients)} patients -> {out_dir}")
    print(f"Structurally valid: {n_valid}/{len(patients)}")
    if dup_errors:
        print("Duplicate ID errors:", dup_errors)
    invalid = [p.patient_id for p in patients if not p.validation.validated]
    if invalid:
        print("Invalid patient IDs:", invalid)
