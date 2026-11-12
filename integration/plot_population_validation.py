"""Compact visual sanity-check for the M2C 100-patient population —
one static PNG, not a dashboard (CLAUDE.md M2C §23). Reuses matplotlib,
already a syngen dependency (docs/syngen-codebase-analysis.md §3).
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/m2c/100_patients"
    files = sorted(glob.glob(str(_REPO_ROOT / in_dir / "*.json")))
    patients = [json.load(open(f, encoding="utf-8")) for f in files]

    ages = [p["demographics"]["age"] for p in patients]
    sex = Counter("male" if p["demographics"]["sex"] == 0 else "female" for p in patients)
    ur = Counter(p["demographics"]["urban_rural"] for p in patients)
    bmi = [p["risk_factors"]["bmi"] for p in patients]
    rf_names = ["hypertension", "diabetes", "hyperlipidemia"]
    rf_pct = [
        100 * sum(p["risk_factors"][k] for p in patients) / len(patients) for k in rf_names
    ]

    fig, axes = plt.subplots(2, 3, figsize=(13, 7))

    axes[0, 0].hist(ages, bins=15, color="#4C72B0")
    axes[0, 0].set_title("Age (n=100)")

    axes[0, 1].bar(sex.keys(), sex.values(), color="#55A868")
    axes[0, 1].set_title("Sex")

    axes[0, 2].bar(ur.keys(), ur.values(), color="#C44E52")
    axes[0, 2].set_title("Urban/Rural")

    axes[1, 0].hist(bmi, bins=15, color="#8172B2")
    axes[1, 0].set_title("BMI")

    axes[1, 1].bar(rf_names, rf_pct, color="#CCB974")
    axes[1, 1].set_title("Risk factor prevalence (%)")
    axes[1, 1].set_ylim(0, 100)

    smoke = Counter(p["risk_factors"]["smoking_status"] for p in patients)
    axes[1, 2].bar(smoke.keys(), smoke.values(), color="#64B5CD")
    axes[1, 2].set_title("Smoking status")

    fig.suptitle(
        "M2C 100-patient sanity check — synthetic, evidence-conditioned, "
        "not a representativeness claim"
    )
    fig.tight_layout()

    out_path = _REPO_ROOT / "outputs" / "m2c" / "validation_plot.png"
    fig.savefig(out_path, dpi=120)
    print(f"Wrote {out_path}")
