"""M2D-10: isolated 10,000-draw sampler-correctness check.

Tests the SAMPLING FUNCTIONS directly (no Patient records, no ECG, no
patient IDs) — this verifies the implementation reproduces the configured
distribution, NOT that the underlying evidence represents India's real
population. Those are different claims; see
docs/session_logs/2026-09-25_M2D-calibration-quality-gate.md.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np

from generation.indian_population import (  # noqa: E402
    load_config,
    sample_age,
    sample_bmi,
    sample_diabetes,
    sample_hyperlipidemia,
    sample_hypertension,
    sample_sex,
    sample_smoking_status,
    sample_state,
    sample_urban_rural,
)

N = 10_000

if __name__ == "__main__":
    config = load_config()
    rngs = [np.random.default_rng(200_000 + i) for i in range(N)]

    print(f"n={N} isolated draws per variable (independent large seeds, not patient generation)\n")

    ages = [sample_age(r, config) for r in rngs]
    print(f"age: mean={np.mean(ages):.3f} (expected 54.5), min={min(ages):.1f}, max={max(ages):.1f}")

    sexes = [sample_sex(r, config) for r in rngs]
    male_pct = 100 * sexes.count(0) / N
    print(f"sex: male%={male_pct:.2f} (expected 51.47)")

    urs = [sample_urban_rural(r, config) for r in rngs]
    urban_pct = 100 * urs.count("urban") / N
    print(f"urban_rural: urban%={urban_pct:.2f} (expected 31.16)")

    states = Counter(sample_state(r, config) for r in rngs)
    expected_state = config["demographics"]["state"]["distribution"]["categories"]
    top = states.most_common(3)
    print(f"state: distinct={len(states)}/35, top3={top}")
    for name, _ in top:
        print(
            f"  {name}: observed={100*states[name]/N:.2f}% "
            f"expected={100*expected_state[name]:.2f}%"
        )

    for sex_code, sex_key in ((0, "male"), (1, "female")):
        sub_rngs = [np.random.default_rng(300_000 + sex_code * 100_000 + i) for i in range(N)]
        bmis = [sample_bmi(r, config, sex_code) for r in sub_rngs]
        smokes = Counter(sample_smoking_status(r, config, sex_code) for r in sub_rngs)
        expected_smoke = config["risk_factors"]["smoking_status"]["distribution"][
            "categories_by_sex"
        ][sex_key]
        print(
            f"bmi[{sex_key}]: mean={np.mean(bmis):.2f}, "
            f"min={min(bmis):.1f}, max={max(bmis):.1f}"
        )
        print(
            f"smoking[{sex_key}]: current%={100*smokes['current']/N:.2f} "
            f"(expected {100*expected_smoke['current']:.2f})"
        )

    htn_rngs = [np.random.default_rng(400_000 + i) for i in range(N)]
    dm_rngs = [np.random.default_rng(500_000 + i) for i in range(N)]
    lipid_rngs = [np.random.default_rng(600_000 + i) for i in range(N)]
    htn_pct = 100 * sum(sample_hypertension(r, config) for r in htn_rngs) / N
    dm_pct = 100 * sum(sample_diabetes(r, config) for r in dm_rngs) / N
    lipid_pct = 100 * sum(sample_hyperlipidemia(r, config) for r in lipid_rngs) / N
    print(f"hypertension: {htn_pct:.2f}% (expected 35.5)")
    print(f"diabetes: {dm_pct:.2f}% (expected 11.4)")
    print(f"hyperlipidemia: {lipid_pct:.2f}% (expected 81.2)")
