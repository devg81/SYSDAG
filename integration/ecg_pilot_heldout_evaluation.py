"""ECG milestone — controlled pilot: re-evaluate the INHERITED per-class
GAN (syngen/SynGen/SynGen) against truly held-out real data.

Why this exists: `docs/syngen-codebase-analysis.md` section 12.1 (HIGH)
documented that the existing `eval_<CLASS>/metrics.json` numbers compare
generated samples against the GAN's OWN TRAINING DATA (`real_<CLASS>.npy`
was built from folds 1-8, the identical folds `train_gan()` trained on)
— not held-out data. Those numbers therefore measure memorization
fidelity, not generalization, and cannot answer "is this model suitable
for synthetic-data use."

This script fixes exactly that methodology bug and nothing else:
  - Reuses `build_label_map`/`PTBXLDataset` from the inherited
    `gan_pytorch.py` UNCHANGED, with `folds=[9]` (PTB-XL's validation
    fold — per this project's own `configs/base.yaml` training_folds
    [1-8], fold 9 was never trained on by any of the 5 generators).
  - Reuses `compute_metrics`/`kl_divergence_1d` from the inherited
    `evaluate_class.py` UNCHANGED — same metric math, same thresholds.
  - Compares against the ALREADY-GENERATED `synthetic_data/<CLASS>_
    synthetic.npy` files. No retraining, no new generation, no new
    dependency, no model selection, no cost.
  - Writes results to a NEW directory
    (`syngen/SynGen/SynGen/eval_<CLASS>_heldout/`) — the original
    (leaky) `eval_<CLASS>/` directories are left untouched, so both the
    original and corrected numbers remain inspectable side by side.

This is an engineering/measurement fix (Category 2 in the task's
classification), not a model-selection or architecture decision —
model selection (reuse this GAN vs. SSSD-ECG vs. anything else) remains
the open human checkpoint `docs/PROJECT_STATE.md` M6/M7 already
established and is NOT addressed, decided, or advanced by this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SYNGEN_DIR = _REPO_ROOT / "syngen" / "SynGen" / "SynGen"
if str(_SYNGEN_DIR) not in sys.path:
    sys.path.insert(0, str(_SYNGEN_DIR))

from gan_pytorch import build_label_map, PTBXLDataset  # noqa: E402  (reused, not reimplemented)
from evaluate_class import compute_metrics  # noqa: E402  (reused, not reimplemented)

import yaml  # noqa: E402

_CLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]
_HELD_OUT_FOLD = [9]  # validation fold — never in training_folds [1-8] per configs/base.yaml
_TRAIN_FOLDS = [1, 2, 3, 4, 5, 6, 7, 8]


def _load_config() -> dict[str, Any]:
    with open(_REPO_ROOT / "configs" / "base.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dataset_to_array(label_map: dict, data_root: str, cls: str, folds: list[int]) -> np.ndarray:
    ds = PTBXLDataset(label_map, data_root, cls, folds=folds)
    if len(ds) == 0:
        return np.zeros((0, 1000, 12), dtype=np.float32)
    return np.stack([ds[i].numpy() for i in range(len(ds))], axis=0)


def run() -> dict[str, Any]:
    config = _load_config()
    ptbxl_csv = str(_REPO_ROOT / config["ptbxl_csv"])
    scp_csv = str(_REPO_ROOT / config["scp_csv"])
    data_root = str(Path(ptbxl_csv).parent)

    label_map = build_label_map(ptbxl_csv, scp_csv)
    results: dict[str, Any] = {}

    for cls in _CLASSES:
        synthetic_path = _SYNGEN_DIR / "synthetic_data" / f"{cls}_synthetic.npy"
        if not synthetic_path.exists():
            results[cls] = {"error": f"missing {synthetic_path.name} -- no retraining/generation performed"}
            continue

        real_heldout = _dataset_to_array(label_map, data_root, cls, _HELD_OUT_FOLD)
        real_train = _dataset_to_array(label_map, data_root, cls, _TRAIN_FOLDS)
        fake = np.load(synthetic_path)

        if real_heldout.shape[0] == 0:
            results[cls] = {
                "error": "zero held-out (fold 9) records for this class -- cannot evaluate generalization",
                "train_fold_count": int(real_train.shape[0]),
            }
            continue

        # Fair comparison: use the smaller of the two sample counts for
        # both metric passes, so the held-out-vs-training comparison
        # below isn't itself confounded by sample-size differences.
        n = min(real_heldout.shape[0], fake.shape[0])
        heldout_metrics = compute_metrics(real_heldout[:n], fake[:n])

        n_train = min(real_train.shape[0], fake.shape[0])
        train_metrics = compute_metrics(real_train[:n_train], fake[:n_train])

        out_dir = _SYNGEN_DIR / f"eval_{cls}_heldout"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "metrics.json").write_text(
            json.dumps(heldout_metrics, indent=2), encoding="utf-8"
        )

        results[cls] = {
            "held_out_fold9_record_count": int(real_heldout.shape[0]),
            "train_fold1_8_record_count": int(real_train.shape[0]),
            "synthetic_record_count": int(fake.shape[0]),
            "compared_n": n,
            "held_out_metrics": {
                "ks_statistic_mean": round(heldout_metrics["ks_statistic_mean"], 4),
                "kl_divergence_mean": round(heldout_metrics["kl_divergence_mean"], 4),
                "mse_waveform_shape": round(heldout_metrics["mse_waveform_shape"], 4),
                "variance": round(heldout_metrics["variance"], 4),
            },
            "original_leaky_metrics_recomputed_for_reference": {
                "ks_statistic_mean": round(train_metrics["ks_statistic_mean"], 4),
                "kl_divergence_mean": round(train_metrics["kl_divergence_mean"], 4),
                "mse_waveform_shape": round(train_metrics["mse_waveform_shape"], 4),
            },
            "generalization_gap": {
                "ks_statistic_mean_delta": round(
                    heldout_metrics["ks_statistic_mean"] - train_metrics["ks_statistic_mean"], 4
                ),
                "kl_divergence_mean_delta": round(
                    heldout_metrics["kl_divergence_mean"] - train_metrics["kl_divergence_mean"], 4
                ),
            },
        }
        print(f"{cls}: held-out KS={heldout_metrics['ks_statistic_mean']:.4f} "
              f"(train-fold KS={train_metrics['ks_statistic_mean']:.4f}, "
              f"delta={heldout_metrics['ks_statistic_mean']-train_metrics['ks_statistic_mean']:+.4f}) "
              f"n_heldout={real_heldout.shape[0]} n_fake={fake.shape[0]}")

    return results


if __name__ == "__main__":
    report = run()
    out_path = _REPO_ROOT / "docs" / "M8_ECG_HELDOUT_PILOT_REPORT.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nfull report -> {out_path.relative_to(_REPO_ROOT)}")
