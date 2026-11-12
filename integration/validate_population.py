"""Run statistical validation over a generated population's JSON output,
comparing observed distributions against `configs/indian_population.yaml`.

M2C's 100-patient development run
(`docs/session_logs/2026-09-25_M2C-indian-conditioning.md`).
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

from generation.indian_population import expected_prevalence_uniform_age, load_config  # noqa: E402
from validation.statistical import (  # noqa: E402
    compare_bernoulli,
    compare_categorical,
    compare_uniform_continuous,
)

if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/m2c/100_patients"
    files = sorted(glob.glob(str(_REPO_ROOT / in_dir / "*.json")))
    patients = [json.load(open(f, encoding="utf-8")) for f in files]
    n = len(patients)
    config = load_config()

    report: dict = {"n": n, "source_dir": in_dir}

    ages = [p["demographics"]["age"] for p in patients]
    age_dist = config["demographics"]["age"]["distribution"]
    report["age"] = compare_uniform_continuous(ages, age_dist["min"], age_dist["max"])

    sex_labels = {0: "male", 1: "female"}
    sex_counts = Counter(sex_labels[p["demographics"]["sex"]] for p in patients)
    report["sex"] = compare_categorical(
        dict(sex_counts), config["demographics"]["sex"]["distribution"]["categories"]
    )

    ur_counts = Counter(p["demographics"]["urban_rural"] for p in patients)
    report["urban_rural"] = compare_categorical(
        dict(ur_counts), config["demographics"]["urban_rural"]["distribution"]["categories"]
    )

    state_counts = Counter(p["demographics"]["state"] for p in patients)
    report["state"] = compare_categorical(
        dict(state_counts), config["demographics"]["state"]["distribution"]["categories"]
    )
    report["state"]["distinct_states_observed"] = len(state_counts)
    report["state"]["distinct_states_available"] = len(
        config["demographics"]["state"]["distribution"]["categories"]
    )

    htn = sum(p["risk_factors"]["hypertension"] for p in patients)
    # D027 (v0.13; -jatin): targets are the age-curve marginals under the
    # generator's own age/sex distribution, not INDIAB-17's national figures.
    report["hypertension"] = compare_bernoulli(
        htn, n, expected_prevalence_uniform_age(config, "hypertension")
    )
    dm = sum(p["risk_factors"]["diabetes"] for p in patients)
    report["diabetes"] = compare_bernoulli(
        dm, n, expected_prevalence_uniform_age(config, "diabetes")
    )
    lipid = sum(p["risk_factors"]["hyperlipidemia"] for p in patients)
    report["hyperlipidemia"] = compare_bernoulli(
        lipid, n, config["risk_factors"]["hyperlipidemia"]["distribution"]["p"]
    )

    for sex_code, sex_key in ((0, "male"), (1, "female")):
        sub = [p for p in patients if p["demographics"]["sex"] == sex_code]
        smoke_counts = Counter(p["risk_factors"]["smoking_status"] for p in sub)
        expected = config["risk_factors"]["smoking_status"]["distribution"]["categories_by_sex"][
            sex_key
        ]
        report[f"smoking_status[{sex_key}]"] = compare_categorical(dict(smoke_counts), expected)

        bmi_dist = config["risk_factors"]["bmi"]["distribution"]
        low_r, mid_r, high_r = (
            bmi_dist["category_ranges"]["normal_or_underweight"],
            bmi_dist["category_ranges"]["overweight"],
            bmi_dist["category_ranges"]["obese"],
        )
        bmi_cats = Counter()
        for p in sub:
            bmi = p["risk_factors"]["bmi"]
            if bmi <= low_r[1]:
                bmi_cats["normal_or_underweight"] += 1
            elif bmi <= mid_r[1]:
                bmi_cats["overweight"] += 1
            else:
                bmi_cats["obese"] += 1
        expected_bmi = bmi_dist["categories_by_sex"][sex_key]
        report[f"bmi_category[{sex_key}]"] = compare_categorical(dict(bmi_cats), expected_bmi)

    # Output path derives from the input dir's own milestone folder (e.g.
    # outputs/m2c/100_patients -> outputs/m2c/validation_summary.json) so
    # runs against different milestones/populations never overwrite each
    # other -- fixed after M3 accidentally clobbered M2C's summary by
    # reusing a hardcoded path.
    out_path = (_REPO_ROOT / in_dir).parent / "validation_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    for key, val in report.items():
        if isinstance(val, dict) and "p_value" in val:
            print(f"{key}: p={val['p_value']:.4f} ({val['test']})")
