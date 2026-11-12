"""M9-1 field-completeness audit (read-only).

Streams every record in a dataset directory and reports, per target field:
valid / null / invalid counts, plus the observed distribution compared
against configs/indian_population.yaml. Never writes into the dataset
directory -- the frozen v0.8 dataset is a reference artifact.

Also measures how much probability mass the 20 mmHg pulse-pressure floor
removes per (sex, age band, label region), re-evaluating the same
bivariate-normal density the generator's _bp_joint_pmf uses with and
without the floor -- quantifies its effect without changing generation.

Usage:
    python -m integration.audit_field_completeness outputs/m8/100k_patients_v08 \
        --json-out docs/M9_FIELD_COMPLETENESS_AUDIT.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from generation import indian_population as ip
from schemas.patient_schema import SMOKING_STATUSES
from validation.statistical import compare_bernoulli, compare_uniform_continuous
from validation.statistical import compare_categorical as _compare_categorical

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Any key that would indicate an environmental/vital field we have not implemented.
_UNEXPECTED_KEY = re.compile(r"aqi|air_quality|pm2|pm10|pollut|environment|heart_rate|pulse_rate|resp|temperature|spo2|oxygen", re.I)


class _Field:
    """valid / null / invalid tally for one field."""

    def __init__(self) -> None:
        self.valid = self.null = self.invalid = 0
        self.invalid_examples: list[str] = []

    def add(self, value: Any, ok: bool, pid: str) -> None:
        if value is None:
            self.null += 1
        elif ok:
            self.valid += 1
        else:
            self.invalid += 1
            if len(self.invalid_examples) < 5:
                self.invalid_examples.append(f"{pid}: {value!r}")

    def to_dict(self, n: int) -> dict[str, Any]:
        pct = lambda k: round(100 * k / n, 3) if n else 0.0  # noqa: E731
        return {
            "valid": self.valid, "valid_pct": pct(self.valid),
            "null": self.null, "null_pct": pct(self.null),
            "invalid": self.invalid, "invalid_pct": pct(self.invalid),
            "invalid_examples": self.invalid_examples,
        }


def _walk_keys(obj: Any, prefix: str = "") -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(f"{prefix}{k}")
            out += _walk_keys(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for v in obj:
            out += _walk_keys(v, prefix)
    return out


def _bmi_category(bmi: float) -> str:
    return "normal_or_underweight" if bmi < 25.0 else ("overweight" if bmi < 30.0 else "obese")


def floor_mass_removed(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Fraction of each (sex, band, region) PMF the PP floor removes,
    computed with the generator's own _bp_joint_pmf at floor=0 vs floor=20.
    Only the bands the 20-89 generator actually reaches are reported."""
    dist = config["risk_factors"]["blood_pressure"]["distribution"]
    lc = dist["label_conditioning"]
    corr = float(dist["sbp_dbp_correlation"]["value"])
    sb, db = tuple(dist["sbp_bounds"]), tuple(dist["dbp_bounds"])
    floor = int(dist["min_pulse_pressure_mm_hg"])
    rows = []
    for sex_key, bands in dist["age_bands_by_sex"].items():
        for band in bands:
            if band[1] < 20:
                continue
            for region in ("normotensive", "raised", "unconstrained"):
                b = tuple(float(v) for v in band)
                # Rebuild the unnormalised density once, then compare kept mass.
                _, _, ms, ss, md, sd = b
                s = np.arange(sb[0], sb[1] + 1)[:, None]
                d = np.arange(db[0], db[1] + 1)[None, :]
                zs, zd = (s - ms) / ss, (d - md) / sd
                dens = np.exp(-0.5 * (zs**2 - 2 * corr * zs * zd + zd**2) / (1 - corr**2))
                region_mask = s > d
                if region == "normotensive":
                    region_mask = region_mask & (s < lc["sbp_threshold"]) & (d < lc["dbp_threshold"])
                elif region == "raised":
                    region_mask = region_mask & ((s >= lc["sbp_threshold"]) | (d >= lc["dbp_threshold"]))
                before = dens[region_mask].sum()
                after = dens[region_mask & (s - d >= floor)].sum()
                # raised region only: share that is isolated diastolic (DBP>=90, SBP<140)
                idh = dens[region_mask & (s - d >= floor) & (s < lc["sbp_threshold"])].sum()
                rows.append({
                    "sex": sex_key, "band": f"{int(band[0])}-{int(band[1])}", "region": region,
                    "mass_removed_by_floor_pct": round(100 * (1 - after / before), 3),
                    "isolated_diastolic_share_after_floor_pct": round(100 * idh / after, 3) if region == "raised" else None,
                })
    return rows


def audit(in_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    states = ip.valid_states(config)
    bp_cfg = config["risk_factors"]["blood_pressure"]["distribution"]
    sb_lo, sb_hi = bp_cfg["sbp_bounds"]
    db_lo, db_hi = bp_cfg["dbp_bounds"]
    floor = bp_cfg["min_pulse_pressure_mm_hg"]
    cov_max = bp_cfg["source_age_coverage_max_by_sex"]
    age_min, age_max = config["demographics"]["age"]["distribution"]["min"], config["demographics"]["age"]["distribution"]["max"]

    f: dict[str, _Field] = defaultdict(_Field)
    ages: list[float] = []
    sex_c, ur_c, state_c = Counter(), Counter(), Counter()
    state_urban: dict[str, Counter] = defaultdict(Counter)
    bmi_cat = {0: Counter(), 1: Counter()}
    smoke = {0: Counter(), 1: Counter()}
    rf = Counter()
    age_bands = Counter()
    pp_hist = Counter()
    bp_region = defaultdict(lambda: {"n": 0, "violations": 0, "sbp_sum": 0, "dbp_sum": 0, "below_140_90": 0})
    extrap_mismatch = band_mismatch = 0
    dates = Counter()
    unexpected_keys = Counter()
    fh_values = Counter()
    hba1c_rule_violations = 0
    n = 0

    for path in sorted(in_dir.glob("PAT_*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        n += 1
        pid = rec.get("patient_id", path.stem)
        for k in _walk_keys(rec):
            if _UNEXPECTED_KEY.search(k.split(".")[-1]) and k.split(".")[-1] not in ("diastolic_mm_hg",):
                unexpected_keys[k] += 1

        d = rec["demographics"]
        age, sex = d.get("age"), d.get("sex")
        f["demographics.age"].add(age, isinstance(age, (int, float)) and age_min <= age <= age_max, pid)
        f["demographics.sex"].add(sex, sex in (0, 1), pid)
        f["demographics.state"].add(d.get("state"), d.get("state") in states, pid)
        f["demographics.urban_rural"].add(d.get("urban_rural"), d.get("urban_rural") in ("urban", "rural"), pid)
        f["demographics.height_cm"].add(d.get("height_cm"), False, pid)
        f["demographics.weight_kg"].add(d.get("weight_kg"), False, pid)
        ages.append(age)
        age_bands["20-44" if age < 45 else ("45-69" if age < 70 else "70-89")] += 1
        sex_c["male" if sex == 0 else "female"] += 1
        ur_c[d["urban_rural"]] += 1
        state_c[d["state"]] += 1
        state_urban[d["state"]][d["urban_rural"]] += 1

        r = rec.get("risk_factors") or {}
        bmi = r.get("bmi")
        f["risk_factors.bmi"].add(bmi, isinstance(bmi, (int, float)) and 16.0 <= bmi <= 40.0, pid)
        f["risk_factors.smoking_status"].add(r.get("smoking_status"), r.get("smoking_status") in SMOKING_STATUSES, pid)
        for k in ("hypertension", "diabetes", "hyperlipidemia"):
            f[f"risk_factors.{k}"].add(r.get(k), isinstance(r.get(k), bool), pid)
            rf[k] += bool(r.get(k))
        bmi_cat[sex][_bmi_category(bmi)] += 1
        smoke[sex][r["smoking_status"]] += 1

        fh = rec.get("family_history")
        f["family_history"].add(fh, False, pid)
        fh_values[json.dumps(fh)] += 1

        bp = rec.get("blood_pressure") or {}
        s, dd = bp.get("systolic_mm_hg"), bp.get("diastolic_mm_hg")
        f["blood_pressure.systolic_mm_hg"].add(s, isinstance(s, int) and sb_lo <= s <= sb_hi, pid)
        f["blood_pressure.diastolic_mm_hg"].add(dd, isinstance(dd, int) and db_lo <= dd <= db_hi, pid)
        ok_pp = isinstance(s, int) and isinstance(dd, int) and s - dd >= floor
        f["blood_pressure.pulse_pressure(derived)"].add(None if s is None or dd is None else s - dd, ok_pp, pid)
        f["blood_pressure.measured_at"].add(bp.get("measured_at"), bool(_ISO_DATE.match(str(bp.get("measured_at")))), pid)
        f["blood_pressure.age_band_source"].add(bp.get("age_band_source"), isinstance(bp.get("age_band_source"), str), pid)
        f["blood_pressure.extrapolated_beyond_source_age_range"].add(
            bp.get("extrapolated_beyond_source_age_range"), isinstance(bp.get("extrapolated_beyond_source_age_range"), bool), pid)
        dates[bp.get("measured_at")] += 1
        if s is not None and dd is not None:
            pp_hist[s - dd] += 1
            sk = "male" if sex == 0 else "female"
            expect_extrap = age >= cov_max[sk] + 1
            extrap_mismatch += expect_extrap != bp.get("extrapolated_beyond_source_age_range")
            band, label, _ = ip._bp_band(config, age, sex)
            band_mismatch += label != bp.get("age_band_source")
            treated = any(m.get("drug_class") == "antihypertensive" for m in rec.get("medications") or [])
            region = ip._bp_region(r["hypertension"], treated)
            g = bp_region[region]
            g["n"] += 1
            g["sbp_sum"] += s
            g["dbp_sum"] += dd
            below = s < 140 and dd < 90
            g["below_140_90"] += below
            g["violations"] += (region == "normotensive" and not below) or (region == "raised" and below)

        labs = rec.get("labs") or []
        has_hba1c = any(l.get("analyte") == "HbA1c" for l in labs)
        hba1c_rule_violations += has_hba1c == bool(r.get("diabetes"))
        f["labs.HbA1c"].add(True if has_hba1c else None, True, pid)

    # --- distribution comparisons vs config ---
    dem = config["demographics"]
    rfc = config["risk_factors"]

    def compare_categorical(observed: Counter, expected: dict[str, float]) -> dict[str, Any]:
        # Out-of-vocabulary values are already counted as invalid per field; keep them out of the GOF sums.
        return _compare_categorical({k: v for k, v in observed.items() if k in expected}, expected)

    comparisons = {
        "age_uniform_ks": compare_uniform_continuous(ages, age_min, age_max),
        "sex": compare_categorical(sex_c, dem["sex"]["distribution"]["categories"]),
        "urban_rural": compare_categorical(ur_c, dem["urban_rural"]["distribution"]["categories"]),
        "state": compare_categorical(state_c, dem["state"]["distribution"]["categories"]),
        **{f"bmi_category_{s_}": compare_categorical(bmi_cat[i], rfc["bmi"]["distribution"]["categories_by_sex"][s_])
           for i, s_ in ((0, "male"), (1, "female"))},
        **{f"smoking_{s_}": compare_categorical(smoke[i], rfc["smoking_status"]["distribution"]["categories_by_sex"][s_])
           for i, s_ in ((0, "male"), (1, "female"))},
        # D027 (v0.13; -jatin): HTN/DM targets are the age-curve marginals.
        **{k: compare_bernoulli(rf[k], n, ip.expected_prevalence_uniform_age(config, k)) for k in ("hypertension", "diabetes")},
        "hyperlipidemia": compare_bernoulli(rf["hyperlipidemia"], n, rfc["hyperlipidemia"]["distribution"]["p"]),
    }
    urban_share_by_state = {
        st: round(c["urban"] / (c["urban"] + c["rural"]), 4) for st, c in sorted(state_urban.items())
    }

    return {
        "source_dir": str(in_dir).replace("\\", "/"),
        "n_records": n,
        "fields": {k: v.to_dict(n) for k, v in sorted(f.items())},
        "distribution_vs_config": comparisons,
        "age_coverage_bands": {
            **dict(age_bands),
            "note": "45-69 overlaps both NNMS (18-69) and LASI (45+); 70-89 is beyond NNMS coverage; <45 is outside LASI coverage",
        },
        "smoking_status_counts_by_sex": {"male": dict(smoke[0]), "female": dict(smoke[1])},
        "urban_share_by_state_generated": urban_share_by_state,
        "urban_share_by_state_spread": [min(urban_share_by_state.values()), max(urban_share_by_state.values())],
        "family_history_distinct_values": dict(fh_values),
        "blood_pressure": {
            "by_label_region": {
                k: {"n": v["n"], "mean_sbp": round(v["sbp_sum"] / v["n"], 2), "mean_dbp": round(v["dbp_sum"] / v["n"], 2),
                    "pct_below_140_90": round(100 * v["below_140_90"] / v["n"], 2), "label_region_violations": v["violations"]}
                for k, v in bp_region.items()
            },
            "pulse_pressure_counts_20_to_25": {str(k): pp_hist.get(k, 0) for k in range(18, 26)},
            "extrapolated_flag_mismatches": extrap_mismatch,
            "age_band_source_mismatches": band_mismatch,
            "pp_floor_mass_removed_by_band_region": floor_mass_removed(config),
        },
        "hba1c_presence_rule_violations": hba1c_rule_violations,
        "measurement_dates_distinct": {str(k): v for k, v in sorted(dates.items(), key=lambda kv: str(kv[0])) if v},
        "unexpected_environment_or_vital_keys": dict(unexpected_keys),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("in_dir")
    p.add_argument("--json-out")
    a = p.parse_args(argv)
    report = audit(Path(a.in_dir), ip.load_config())
    text = json.dumps(report, indent=2, default=str)
    if a.json_out:
        Path(a.json_out).write_text(text, encoding="utf-8")
    print(text[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
