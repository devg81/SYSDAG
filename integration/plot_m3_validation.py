"""M3-9: visual validation for the 1,000-patient population — configured
target vs. generated sample, side by side where meaningful. Static PNGs,
not a dashboard.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from generation.indian_population import load_config  # noqa: E402

if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/m3/1000_patients"
    files = sorted(glob.glob(str(_REPO_ROOT / in_dir / "*.json")))
    patients = [json.load(open(f, encoding="utf-8")) for f in files]
    n = len(patients)
    config = load_config()

    ages = [p["demographics"]["age"] for p in patients]
    sex_counts = Counter("male" if p["demographics"]["sex"] == 0 else "female" for p in patients)
    ur_counts = Counter(p["demographics"]["urban_rural"] for p in patients)
    state_counts = Counter(p["demographics"]["state"] for p in patients)
    bmi = [p["risk_factors"]["bmi"] for p in patients]
    smoke_counts = Counter(p["risk_factors"]["smoking_status"] for p in patients)
    rf_names = ["hypertension", "diabetes", "hyperlipidemia"]
    rf_observed = [100 * sum(p["risk_factors"][k] for p in patients) / n for k in rf_names]
    rf_configured = [100 * config["risk_factors"][k]["distribution"]["p"] for k in rf_names]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    axes[0, 0].hist(ages, bins=14, color="#4C72B0")
    axes[0, 0].set_title(f"Age (n={n}) — ENGINEERING ASSUMPTION, not observed evidence")
    axes[0, 0].set_xlabel("age")

    sex_cfg = config["demographics"]["sex"]["distribution"]["categories"]
    x = np.arange(2)
    axes[0, 1].bar(x - 0.2, [sex_counts.get(k, 0) / n * 100 for k in ("male", "female")],
                   width=0.4, label="generated", color="#55A868")
    axes[0, 1].bar(x + 0.2, [sex_cfg[k] * 100 for k in ("male", "female")],
                   width=0.4, label="configured", color="#B0B0B0")
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(["male", "female"])
    axes[0, 1].set_title("Sex: generated vs. configured (%)")
    axes[0, 1].legend(fontsize=8)

    top_states = state_counts.most_common(10)
    axes[0, 2].barh([s for s, _ in top_states][::-1], [c for _, c in top_states][::-1], color="#C44E52")
    axes[0, 2].set_title(f"Top 10 states (of {len(state_counts)}/35 observed)")

    axes[1, 0].hist(bmi, bins=20, color="#8172B2")
    axes[1, 0].set_title("BMI (both sexes pooled)")
    axes[1, 0].set_xlabel("BMI")

    smoke_cats = sorted(smoke_counts.keys())
    axes[1, 1].bar(smoke_cats, [smoke_counts[c] for c in smoke_cats], color="#64B5CD")
    axes[1, 1].set_title("Smoking status")

    xw = np.arange(3)
    axes[1, 2].bar(xw - 0.2, rf_observed, width=0.4, label="generated", color="#CCB974")
    axes[1, 2].bar(xw + 0.2, rf_configured, width=0.4, label="configured", color="#B0B0B0")
    axes[1, 2].set_xticks(xw)
    axes[1, 2].set_xticklabels(rf_names, rotation=15, fontsize=8)
    axes[1, 2].set_ylim(0, 100)
    axes[1, 2].set_title("Risk factor prevalence (%): generated vs. configured")
    axes[1, 2].legend(fontsize=8)

    fig.suptitle(
        f"M3 — {n}-patient sanity check (synthetic, evidence-conditioned; "
        "NOT a representativeness claim)"
    )
    fig.tight_layout()
    out_path = _REPO_ROOT / "outputs" / "m3" / "m3_validation_plot.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    print(f"Wrote {out_path}")
