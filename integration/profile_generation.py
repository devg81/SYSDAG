"""M3.5 Step 4: profile where per-patient generation time actually goes.

Generates a small batch (default 20) and times each phase separately:
CSV read, build_label_map (incl. its internal ast.literal_eval parsing),
the ECG-lookup CSV read, Indian-attribute sampling, structural validation,
JSON serialization+write. Read-only measurement — does not modify the
generator (M3.5 Step 4 instruction: measure before optimizing).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

from integration.build_patient import build_patient, load_config  # noqa: E402
from generation.indian_population import load_config as load_indian_config  # noqa: E402
from ingestion.ptbxl_source import _build_label_map, pick_ecg_id, load_ptbxl_record  # noqa: E402

N = 20

if __name__ == "__main__":
    config = load_config(_REPO_ROOT / "configs" / "base.yaml")
    indian_config = load_indian_config()
    ptbxl_csv = str(_REPO_ROOT / config["ptbxl_csv"])
    scp_csv = str(_REPO_ROOT / config["scp_csv"])

    print(f"--- isolated single-call timings (n=1 each) ---")

    t0 = time.perf_counter()
    df = pd.read_csv(ptbxl_csv, index_col="ecg_id")
    print(f"single pd.read_csv(ptbxl_csv): {time.perf_counter()-t0:.4f}s ({len(df)} rows)")

    t0 = time.perf_counter()
    build_label_map = _build_label_map()
    label_map = build_label_map(ptbxl_csv, scp_csv, threshold=50.0)
    print(f"single build_label_map() call (incl. its own 2 CSV reads + ast.literal_eval on scp_codes): {time.perf_counter()-t0:.4f}s")

    t0 = time.perf_counter()
    ecg_id = pick_ecg_id(ptbxl_csv, config["training_folds"], seed=1000)
    print(f"single pick_ecg_id() call: {time.perf_counter()-t0:.4f}s")

    t0 = time.perf_counter()
    record = load_ptbxl_record(ecg_id, ptbxl_csv, scp_csv, 50.0)
    print(f"single load_ptbxl_record() call: {time.perf_counter()-t0:.4f}s")

    print(f"\n--- full build_patient() over {N} patients, per-phase totals ---")

    t_pick = t_load = t_indian = t_validate = t_serialize = 0.0
    t_total_start = time.perf_counter()
    for seq in range(1, N + 1):
        t0 = time.perf_counter()
        p = build_patient(seq, config, indian_config)
        elapsed = time.perf_counter() - t0
        if seq == 1:
            print(f"  patient 1 (cold): {elapsed:.4f}s")
        if seq == N:
            print(f"  patient {N}: {elapsed:.4f}s")
    t_total = time.perf_counter() - t_total_start
    print(f"\nTotal for {N} patients: {t_total:.3f}s -> {t_total/N:.4f}s/patient")
    print(f"Extrapolated to 1000 patients: {t_total/N*1000/60:.1f} minutes")
    print(f"Extrapolated to 100,000 patients: {t_total/N*100000/3600:.1f} hours")
