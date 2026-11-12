"""M3: comprehensive analysis of a generated population.

Covers M3-2 (structural validation categorization), M3-3/M3-4 (demographic
and risk-factor distributions vs. configured targets), M3-6 (relationship
classification), M3-7 (association measures), M3-8 (edge cases). Writes one
JSON report. Does NOT modify the generator (M3-13) — read-only analysis of
already-generated JSON records.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
from scipy import stats

from generation.indian_population import load_config, valid_states  # noqa: E402
from schemas.patient_schema import SMOKING_STATUSES  # noqa: E402

BMI_ABS_MIN, BMI_ABS_MAX = 16.0, 40.0  # construction bounds, per configs/indian_population.yaml


def load_population(in_dir: str) -> list[dict]:
    files = sorted(glob.glob(str(_REPO_ROOT / in_dir / "*.json")))
    return [json.load(open(f, encoding="utf-8")) for f in files]


# ---------------------------------------------------------------- M3-2 ----

def structural_report(patients: list[dict], config: dict) -> dict[str, Any]:
    n = len(patients)
    states = valid_states(config)
    ids = [p["patient_id"] for p in patients]
    id_counts = Counter(ids)
    duplicate_ids = {pid: c for pid, c in id_counts.items() if c > 1}

    ecg_ids = [p["ecg"]["ecg_id"] for p in patients]
    ecg_dup = {eid: c for eid, c in Counter(ecg_ids).items() if c > 1}

    errors_by_category: Counter = Counter()
    missing_required: Counter = Counter()
    invalid_enum: Counter = Counter()
    invalid_range: Counter = Counter()
    malformed: Counter = Counter()
    ecg_inconsistent: Counter = Counter()

    valid_count = 0
    for p in patients:
        if p["validation"]["validated"]:
            valid_count += 1
        for e in p["validation"]["errors"]:
            errors_by_category[e.split(":")[0]] += 1

        d = p["demographics"]
        for field in ("age", "sex", "state", "urban_rural"):
            if d.get(field) is None:
                missing_required[f"demographics.{field}"] += 1
        rf = p.get("risk_factors")
        if rf is None:
            malformed["risk_factors missing entirely"] += 1
        else:
            for field in ("bmi", "smoking_status", "hypertension", "diabetes", "hyperlipidemia"):
                if rf.get(field) is None:
                    missing_required[f"risk_factors.{field}"] += 1

        if d.get("state") is not None and d["state"] not in states:
            invalid_enum["state"] += 1
        if d.get("urban_rural") is not None and d["urban_rural"] not in ("urban", "rural"):
            invalid_enum["urban_rural"] += 1
        if rf and rf.get("smoking_status") is not None and rf["smoking_status"] not in SMOKING_STATUSES:
            invalid_enum["smoking_status"] += 1

        if d.get("age") is not None and not (20 <= d["age"] <= 89):
            invalid_range["age"] += 1
        if rf and rf.get("bmi") is not None and not (BMI_ABS_MIN <= rf["bmi"] <= BMI_ABS_MAX):
            invalid_range["bmi"] += 1

        ecg = p.get("ecg")
        if ecg is None:
            ecg_inconsistent["ecg missing entirely"] += 1
        else:
            if ecg.get("signal_shape") != [1000, 12]:
                ecg_inconsistent["signal_shape"] += 1
            if ecg.get("strat_fold") not in range(1, 9):
                ecg_inconsistent["strat_fold outside training folds 1-8"] += 1
            if not ecg.get("superclasses"):
                ecg_inconsistent["empty superclasses"] += 1

    return {
        "total": n,
        "valid": valid_count,
        "invalid": n - valid_count,
        "errors_by_category": dict(errors_by_category),
        "duplicate_patient_ids": duplicate_ids,
        "duplicate_ecg_ids": ecg_dup,
        "missing_required_fields": dict(missing_required),
        "invalid_enum_values": dict(invalid_enum),
        "invalid_ranges": dict(invalid_range),
        "malformed_structures": dict(malformed),
        "ecg_inconsistencies": dict(ecg_inconsistent),
    }


# ------------------------------------------------------------ M3-3/4 ----

def demographic_report(patients: list[dict], config: dict) -> dict[str, Any]:
    n = len(patients)
    ages = np.array([p["demographics"]["age"] for p in patients])
    age_dist = config["demographics"]["age"]["distribution"]

    bands = [(20, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 89)]
    band_counts = {
        f"{lo}-{hi}": int(np.sum((ages >= lo) & (ages <= hi))) for lo, hi in bands
    }

    age_report = {
        "evidence_status": "ENGINEERING ASSUMPTION (NOT an empirically validated Indian age "
        "distribution) — see configs/indian_population.yaml demographics.age.evidence_tier",
        "min": float(ages.min()),
        "max": float(ages.max()),
        "mean": float(ages.mean()),
        "median": float(np.median(ages)),
        "std": float(ages.std(ddof=1)),
        "quantiles": {
            "p25": float(np.percentile(ages, 25)),
            "p50": float(np.percentile(ages, 50)),
            "p75": float(np.percentile(ages, 75)),
        },
        "age_band_counts": band_counts,
        "configured_distribution": {"type": "uniform", "min": age_dist["min"], "max": age_dist["max"]},
    }

    sex_counts = Counter("male" if p["demographics"]["sex"] == 0 else "female" for p in patients)
    sex_configured = config["demographics"]["sex"]["distribution"]["categories"]
    sex_report = {
        "counts": dict(sex_counts),
        "percentages": {k: 100 * v / n for k, v in sex_counts.items()},
        "configured_percentages": {k: 100 * v for k, v in sex_configured.items()},
    }

    state_counts = Counter(p["demographics"]["state"] for p in patients)
    all_states = valid_states(config)
    zero_count_states = sorted(all_states - set(state_counts.keys()))
    state_configured = config["demographics"]["state"]["distribution"]["categories"]
    state_report = {
        "distinct_observed": len(state_counts),
        "distinct_available": len(all_states),
        "zero_count_states": zero_count_states,
        "top_10": [
            {"state": s, "count": c, "pct": 100 * c / n, "configured_pct": 100 * state_configured[s]}
            for s, c in state_counts.most_common(10)
        ],
        "note": "n=1,000 is NOT sufficient to validate the 2011 Census distribution itself — "
        "this only checks whether the SAMPLER reproduces its own configured targets.",
    }

    ur_counts = Counter(p["demographics"]["urban_rural"] for p in patients)
    ur_configured = config["demographics"]["urban_rural"]["distribution"]["categories"]
    ur_report = {
        "counts": dict(ur_counts),
        "percentages": {k: 100 * v / n for k, v in ur_counts.items()},
        "configured_percentages": {k: 100 * v for k, v in ur_configured.items()},
    }

    return {"age": age_report, "sex": sex_report, "state": state_report, "urban_rural": ur_report}


def risk_factor_report(patients: list[dict], config: dict) -> dict[str, Any]:
    n = len(patients)
    report: dict[str, Any] = {}

    bmis = np.array([p["risk_factors"]["bmi"] for p in patients])
    sexes = np.array([p["demographics"]["sex"] for p in patients])
    bmi_dist = config["risk_factors"]["bmi"]["distribution"]
    bmi_by_sex = {}
    for sex_code, sex_key in ((0, "male"), (1, "female")):
        sub = bmis[sexes == sex_code]
        expected_cats = bmi_dist["categories_by_sex"][sex_key]
        low_r = bmi_dist["category_ranges"]["normal_or_underweight"][1]
        mid_r = bmi_dist["category_ranges"]["overweight"][1]
        cats = Counter()
        for b in sub:
            if b <= low_r:
                cats["normal_or_underweight"] += 1
            elif b <= mid_r:
                cats["overweight"] += 1
            else:
                cats["obese"] += 1
        bmi_by_sex[sex_key] = {
            "n": len(sub),
            "mean": float(sub.mean()),
            "median": float(np.median(sub)),
            "std": float(sub.std(ddof=1)),
            "observed_category_pct": {k: 100 * v / len(sub) for k, v in cats.items()},
            "configured_category_pct": {k: 100 * v for k, v in expected_cats.items()},
        }
    report["bmi"] = bmi_by_sex

    smoking_dist = config["risk_factors"]["smoking_status"]["distribution"]
    smoking_by_sex = {}
    for sex_code, sex_key in ((0, "male"), (1, "female")):
        sub = [p["risk_factors"]["smoking_status"] for p in patients if p["demographics"]["sex"] == sex_code]
        counts = Counter(sub)
        expected = smoking_dist["categories_by_sex"][sex_key]
        smoking_by_sex[sex_key] = {
            "n": len(sub),
            "observed_pct": {k: 100 * v / len(sub) for k, v in counts.items()},
            "configured_pct": {k: 100 * v for k, v in expected.items()},
        }
    report["smoking_status"] = smoking_by_sex

    for key in ("hypertension", "diabetes", "hyperlipidemia"):
        vals = [p["risk_factors"][key] for p in patients]
        observed = sum(vals)
        expected_p = config["risk_factors"][key]["distribution"]["p"]
        binom = stats.binomtest(observed, n, expected_p)
        report[key] = {
            "observed_count": observed,
            "observed_pct": 100 * observed / n,
            "configured_pct": 100 * expected_p,
            "abs_diff_pct": 100 * observed / n - 100 * expected_p,
            "binomial_test_p_value": float(binom.pvalue),
            "plausibly_sampling_variation": bool(binom.pvalue > 0.01),
        }

    fh_populated = sum(1 for p in patients if p.get("family_history") is not None)
    report["family_history_of_cvd"] = {
        "populated_count": fh_populated,
        "note": "Not generated by design (docs/DECISIONS.md D004) — expected 0.",
    }

    return report


# ------------------------------------------------------------- M3-6/7 ----

RELATIONSHIP_CLASSIFICATION = {
    "age x sex": "INDEPENDENT BY DESIGN",
    "age x BMI": "INDEPENDENT BY DESIGN",
    "sex x BMI": "EXPLICITLY MODELED",
    "sex x smoking_status": "EXPLICITLY MODELED",
    "sex x hypertension": "INDEPENDENT BY DESIGN",
    "sex x diabetes": "INDEPENDENT BY DESIGN",
    "sex x hyperlipidemia": "INDEPENDENT BY DESIGN",
    "age x hypertension": "INDEPENDENT BY DESIGN",
    "age x diabetes": "INDEPENDENT BY DESIGN",
    "age x hyperlipidemia": "INDEPENDENT BY DESIGN",
    "BMI x hypertension": "INDEPENDENT BY DESIGN",
    "BMI x diabetes": "INDEPENDENT BY DESIGN",
    "smoking_status x hypertension": "INDEPENDENT BY DESIGN",
}


def cramers_v(cat1: list, cat2: list) -> dict[str, Any]:
    contingency = np.array(
        [[sum(1 for a, b in zip(cat1, cat2) if a == u and b == v) for v in sorted(set(cat2))]
         for u in sorted(set(cat1))]
    )
    chi2, p, dof, _ = stats.chi2_contingency(contingency)
    n = len(cat1)
    r, k = contingency.shape
    v = np.sqrt((chi2 / n) / max(min(r - 1, k - 1), 1))
    return {"measure": "Cramer's V", "value": float(v), "chi2_p_value": float(p)}


def point_biserial(binary: list[int], numeric: list[float]) -> dict[str, Any]:
    r, p = stats.pointbiserialr(binary, numeric)
    return {"measure": "point-biserial r", "value": float(r), "p_value": float(p)}


def pearson(x: list[float], y: list[float]) -> dict[str, Any]:
    r, p = stats.pearsonr(x, y)
    return {"measure": "Pearson r", "value": float(r), "p_value": float(p)}


def relationship_report(patients: list[dict]) -> dict[str, Any]:
    age = [p["demographics"]["age"] for p in patients]
    sex = [p["demographics"]["sex"] for p in patients]
    bmi = [p["risk_factors"]["bmi"] for p in patients]
    smoking = [p["risk_factors"]["smoking_status"] for p in patients]
    htn = [int(p["risk_factors"]["hypertension"]) for p in patients]
    dm = [int(p["risk_factors"]["diabetes"]) for p in patients]
    lipid = [int(p["risk_factors"]["hyperlipidemia"]) for p in patients]

    measures = {
        "age x sex": point_biserial(sex, age),
        "age x BMI": pearson(age, bmi),
        "sex x BMI": point_biserial(sex, bmi),
        "sex x smoking_status": cramers_v(sex, smoking),
        "sex x hypertension": point_biserial(sex, htn),
        "sex x diabetes": point_biserial(sex, dm),
        "sex x hyperlipidemia": point_biserial(sex, lipid),
        "age x hypertension": point_biserial(htn, age),
        "age x diabetes": point_biserial(dm, age),
        "age x hyperlipidemia": point_biserial(lipid, age),
        "BMI x hypertension": point_biserial(htn, bmi),
        "BMI x diabetes": point_biserial(dm, bmi),
        "smoking_status x hypertension": cramers_v(smoking, htn),
    }

    report = {}
    for key, measure in measures.items():
        report[key] = {
            "classification": RELATIONSHIP_CLASSIFICATION[key],
            **measure,
            "interpretation": (
                "Any non-zero association here is sampling noise, not a modeled relationship "
                "(no shared generation logic connects these variables)"
                if RELATIONSHIP_CLASSIFICATION[key] == "INDEPENDENT BY DESIGN"
                else "Association is expected because the generator explicitly conditions one on the other"
            ),
        }
    return report


# ------------------------------------------------------------------------

def edge_case_report(patients: list[dict]) -> dict[str, Any]:
    cases = []
    for p in patients:
        d, rf = p["demographics"], p["risk_factors"]
        if rf["bmi"] >= 39.0 or rf["bmi"] <= 16.2:
            cases.append({"patient_id": p["patient_id"], "type": "extreme BMI", "value": rf["bmi"],
                          "classification": "valid (within construction bounds, rare tail)"})
        if d["age"] < 30 and rf["hypertension"] and rf["diabetes"] and rf["hyperlipidemia"]:
            cases.append({
                "patient_id": p["patient_id"], "type": "young patient with all 3 conditions",
                "age": d["age"],
                "classification": "unsupported by current evidence — generator has no age "
                "conditioning on these, so this rate is neither validated nor ruled out by real data",
            })
        if not p["ecg"]["superclasses"]:
            cases.append({"patient_id": p["patient_id"], "type": "empty ECG superclasses",
                          "classification": "valid (record had no confident diagnostic label above threshold)"})
    state_counts = Counter(p["demographics"]["state"] for p in patients)
    rare_states = [s for s, c in state_counts.items() if c == 1]
    return {"flagged_patients": cases, "count": len(cases), "states_observed_exactly_once": rare_states}


if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/m3/1000_patients"
    patients = load_population(in_dir)
    config = load_config()

    report = {
        "n": len(patients),
        "source_dir": in_dir,
        "structural": structural_report(patients, config),
        "demographics": demographic_report(patients, config),
        "risk_factors": risk_factor_report(patients, config),
        "relationships": relationship_report(patients),
        "edge_cases": edge_case_report(patients),
    }

    out_path = _REPO_ROOT / "outputs" / "m3" / "m3_analysis_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Structural: {report['structural']['valid']}/{report['structural']['total']} valid")
    print(f"Duplicate patient IDs: {len(report['structural']['duplicate_patient_ids'])}")
    print(f"Edge cases flagged: {report['edge_cases']['count']}")
