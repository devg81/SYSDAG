"""Adapter onto the existing PTB-XL / syngen ECG code.

Reuses `syngen/SynGen/SynGen/gan_pytorch.py`'s `build_label_map()` for the
SCP-code -> diagnostic-superclass mapping (see `docs/DECISIONS.md` D002/D003)
instead of re-implementing it. Only metadata is pulled here — actual
waveform loading (`wfdb.rdrecord`) and GAN-based synthesis are Stage 4 work,
not M1 (`docs/DECISIONS.md` D003).

Real PTB-XL `patient_id` values are never read into the returned dict —
only clinical field values (age/sex/height/weight), per `CLAUDE.md` §10/§31.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SYNGEN_DIR = _REPO_ROOT / "syngen" / "SynGen" / "SynGen"

# PTB-XL's documented anonymization-age encoding — ages above 89 are capped.
# Carried forward from CLAUDE.md §2's "known findings to carry forward".
_MAX_AGE = 89.0


def _build_label_map():
    """Import and return syngen's build_label_map function (lazy, path-injected)."""
    syngen_dir = str(_SYNGEN_DIR)
    if syngen_dir not in sys.path:
        sys.path.insert(0, syngen_dir)
    from gan_pytorch import build_label_map  # reused, not reimplemented

    return build_label_map


@functools.lru_cache(maxsize=4)
def _cached_ptbxl_df(ptbxl_csv: str) -> pd.DataFrame:
    """Process-level cache: `pd.read_csv` on its own is cheap (~0.26s for
    21,837 rows), but was being called 2x per patient across
    pick_ecg_id/load_ptbxl_record — this makes repeated calls free. Read-only
    downstream (only `.loc[...]` and `.isin(...)`), never mutated, so
    sharing one cached DataFrame across calls is safe (M3.5 Step 4 — this
    does not change any generated value, only how many times the same file
    is parsed)."""
    return pd.read_csv(ptbxl_csv, index_col="ecg_id")


@functools.lru_cache(maxsize=4)
def _cached_label_map(ptbxl_csv: str, scp_csv: str, threshold: float) -> dict:
    """Process-level cache for the real bottleneck: `build_label_map()`
    re-runs `ast.literal_eval` over all ~21,837 `scp_codes` values on every
    call (measured at ~4.9s/call, M3.5 Step 4 profiling) — this was being
    paid once PER PATIENT. Caching it here is a pure performance fix: same
    inputs always produce the same label map, so reusing it changes
    nothing about generated content, only how often the parse runs."""
    build_label_map = _build_label_map()
    return build_label_map(ptbxl_csv, scp_csv, threshold=threshold)


def load_ptbxl_record(
    ecg_id: int, ptbxl_csv: str, scp_csv: str, scp_threshold: float = 50.0
) -> dict[str, Any]:
    """Return ECG metadata + demographic field values for one PTB-XL record.

    Raises KeyError if `ecg_id` is not present in the label map.
    """
    label_map = _cached_label_map(ptbxl_csv, scp_csv, scp_threshold)
    if ecg_id not in label_map:
        raise KeyError(f"ecg_id {ecg_id} not found in PTB-XL label map")
    meta = label_map[ecg_id]

    df = _cached_ptbxl_df(ptbxl_csv)
    row = df.loc[ecg_id]

    age = float(row["age"])
    if age > _MAX_AGE:
        age = _MAX_AGE

    return {
        "ecg_id": ecg_id,
        "superclasses": meta["superclasses"],
        "strat_fold": meta["strat_fold"],
        "filename_lr": meta["filename_lr"],
        "sampling_hz": 100,
        "signal_shape": [1000, 12],
        "age": age,
        "sex": int(row["sex"]),
        "height": None if pd.isna(row["height"]) else float(row["height"]),
        "weight": None if pd.isna(row["weight"]) else float(row["weight"]),
    }


def pick_ecg_id(ptbxl_csv: str, folds: list[int], seed: int) -> int:
    """Deterministically pick one ecg_id restricted to `folds` (patient-level
    fold discipline — CLAUDE.md §7 — is respected by filtering on strat_fold
    before sampling, same column syngen's own PTBXLDataset uses)."""
    import numpy as np

    df = _cached_ptbxl_df(ptbxl_csv)
    candidates = sorted(df[df["strat_fold"].isin(folds)].index.tolist())
    if not candidates:
        raise ValueError(f"no records found for folds={folds}")
    rng = np.random.default_rng(seed)
    return int(rng.choice(candidates))
