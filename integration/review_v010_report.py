"""v0.10 (D022) review evidence: before/after on the reviewed seeds and
cohort checks over N records, v0.9 (frozen dataset) vs v0.10 (regenerated
in memory, same sequence numbers). Writes docs/V010_REVIEW_COHORT_CHECKS.{md,json}.

    python -m integration.review_v010_report [N]
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from generation.indian_population import load_config
from integration.build_patient import build_patient, load_config as load_base

ROOT = Path(__file__).resolve().parents[1]
V09 = ROOT / "outputs" / "m9" / "100k_patients_v09"
SEQS = [1, 11, 13, 15, 95, 19321, 33933, 78682]  # seeds 43/53/55/57/137 + named batch-1 IDs


def _v09(seq: int) -> dict | None:
    p = V09 / f"PAT_{seq:06d}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _summary(r: dict) -> dict:
    lp, bp = r["lipid_panel"], r["blood_pressure"]
    hba1c = next((l["value"] for l in (r["labs"] or []) if l["analyte"] == "HbA1c"), None)
    return {
        "age": r["demographics"]["age"],
        "sex": r["demographics"]["sex"],
        "htn/dm/hld": [r["risk_factors"][k] for k in ("hypertension", "diabetes", "hyperlipidemia")],
        "TC/TG/HDL/LDL": [lp[k] for k in ("total_cholesterol_mg_dl", "triglycerides_mg_dl", "hdl_mg_dl", "ldl_mg_dl")],
        "NCEP/LAI dyslip": [i["dyslipidemia"] for i in r["lipid_interpretations"]],
        "BP": f"{bp['systolic_mm_hg']}/{bp['diastolic_mm_hg']} (PP {bp['systolic_mm_hg'] - bp['diastolic_mm_hg']})",
        "BP extrapolated/conf": [bp["extrapolated_beyond_source_age_range"], bp.get("confidence")],
        "HbA1c": hba1c if r["labs"] is not None else "labs=null",
        "onset ages": {d["code"]: d.get("age_at_onset_years") for d in r["diagnoses"]},
        "meds": [m["drug_class"] for m in r["medications"]],
    }


def _cohort(records: list[dict]) -> dict:
    f = lambda path: np.array([path(r) for r in records], dtype=float)  # noqa: E731
    tc = f(lambda r: r["lipid_panel"]["total_cholesterol_mg_dl"])
    tg = f(lambda r: r["lipid_panel"]["triglycerides_mg_dl"])
    hdl = f(lambda r: r["lipid_panel"]["hdl_mg_dl"])
    ldl = f(lambda r: r["lipid_panel"]["ldl_mg_dl"])
    sex = f(lambda r: r["demographics"]["sex"])
    age = f(lambda r: r["demographics"]["age"])
    sbp = f(lambda r: r["blood_pressure"]["systolic_mm_hg"])
    dbp = f(lambda r: r["blood_pressure"]["diastolic_mm_hg"])
    rf = lambda k: f(lambda r: r["risk_factors"][k])  # noqa: E731
    ncep = f(lambda r: r["lipid_interpretations"][0]["dyslipidemia"])
    lai = f(lambda r: r["lipid_interpretations"][1]["dyslipidemia"])
    low_hdl = np.where(sex == 1, hdl < 50, hdl < 40)
    htn, dm = rf("hypertension").astype(bool), rf("diabetes").astype(bool)
    meds = [{m["drug_class"] for m in r["medications"]} for r in records]
    tx_htn = np.array(["antihypertensive" in m for m in meds])
    tx_dm = np.array(["antidiabetic" in m for m in meds])
    hba1c = np.array([
        next((l["value"] for l in (r["labs"] or []) if l["analyte"] == "HbA1c"), np.nan) for r in records
    ])
    vals, counts = np.unique(ldl, return_counts=True)
    bands = {}
    for s, sk in ((0, "M"), (1, "F")):
        for lo in range(20, 90, 10):
            m = (sex == s) & (age >= lo) & (age < lo + 10)
            if m.sum():
                bands[f"{sk} {lo}-{lo + 9}"] = {
                    "n": int(m.sum()),
                    "SBP": round(float(sbp[m].mean()), 1),
                    "DBP": round(float(dbp[m].mean()), 1),
                    "PP": round(float((sbp - dbp)[m].mean()), 1),
                    "SBP_normotensive_only": round(float(sbp[m & ~htn].mean()), 1),
                }
    pct = lambda x: round(100 * float(np.mean(x)), 2)  # noqa: E731
    return {
        "n": len(records),
        "lipid_correlations": {
            "r(lnTG, HDL)": round(float(np.corrcoef(np.log(tg), hdl)[0, 1]), 3),
            "r(TG, HDL)": round(float(np.corrcoef(tg, hdl)[0, 1]), 3),
            "r(TC, LDL)": round(float(np.corrcoef(tc, ldl)[0, 1]), 3),
            "r(TC, lnTG)": round(float(np.corrcoef(tc, np.log(tg))[0, 1]), 3),
        },
        "ldl_floor": {
            "pct_LDL_exactly_30.0": pct(ldl == 30.0),
            "most_common_LDL_value": float(vals[counts.argmax()]),
            "pct_at_most_common_value": round(100 * counts.max() / len(ldl), 2),
            "pct_LDL_not_equal_friedewald": pct(np.abs(ldl - (tc - hdl - tg / 5)) > 0.11),
            "pct_LDL_below_0": pct(ldl < 0),
            "pct_TG_above_400": pct(tg > 400),
        },
        "prevalence_pct_vs_source": {
            "hypertension (INDIAB-17 35.5)": pct(htn),
            "diabetes (INDIAB-17 11.4)": pct(dm),
            "hyperlipidemia flag (INDIAB-17 81.2)": pct(rf("hyperlipidemia")),
            "NCEP dyslipidaemia from panel (INDIAB-17 81.2)": pct(ncep),
            "LAI dyslipidaemia from panel": pct(lai),
            "TC>=200 (INDIAB-17 24.0)": pct(tc >= 200),
            "TG>=150 (INDIAB-17 32.1)": pct(tg >= 150),
            "low HDL (INDIAB-17 66.9)": pct(low_hdl),
            "LDL>=130 (INDIAB-17 20.9)": pct(ldl >= 130),
            "antihypertensive | htn (NNMS 14.5)": pct(tx_htn[htn]),
            "antidiabetic | dm (NNMS 36.1)": pct(tx_dm[dm]),
            "HbA1c<7 | treated dm (INDIAB-13 36.3)": pct(hba1c[dm & tx_dm] < 7) if (dm & tx_dm).any() else None,
            "hyperlipidemia flag agrees with NCEP interpretation": pct(rf("hyperlipidemia") == ncep),
        },
        "bp_by_age_band": bands,
    }


def _null_empty(records: list[dict]) -> dict:
    out = {}
    for key in records[0]:
        vals = [r[key] for r in records]
        if isinstance(vals[0], dict) and key not in ("provenance", "validation"):
            for sub in vals[0]:
                v = [x.get(sub) if x else None for x in vals]
                out[f"{key}.{sub}"] = round(100 * sum(e is None for e in v) / len(v), 2)
        else:
            out[key] = {
                "null_pct": round(100 * sum(v is None for v in vals) / len(vals), 2),
                "empty_list_pct": round(100 * sum(v == [] for v in vals) / len(vals), 2),
            }
    dx = [d for r in records for d in r["diagnoses"]]
    out["diagnoses[].diagnosed_date"] = round(100 * sum(d["diagnosed_date"] is None for d in dx) / max(len(dx), 1), 2)
    out["diagnoses[].onset_date"] = round(100 * sum(d.get("onset_date") is None for d in dx) / max(len(dx), 1), 2)
    return out


def main(n: int) -> None:
    base, cfg = load_base(ROOT / "configs" / "base.yaml"), load_config()
    new = [asdict(build_patient(s, base, cfg)) for s in range(1, n + 1)]
    old = [r for r in (_v09(s) for s in range(1, n + 1)) if r is not None]
    seeds = {}
    for s in SEQS:
        before = _v09(s)
        after = asdict(build_patient(s, base, cfg))
        seeds[f"PAT_{s:06d} (seed {42 + s})"] = {
            "v0.9": _summary(before) if before else None,
            "v0.10": _summary(after),
        }
    report = {
        "seeds": seeds,
        "cohort_v0.9": _cohort(old),
        "cohort_v0.10": _cohort(new),
        "null_empty_pct_v0.10": _null_empty(new),
    }
    (ROOT / "docs" / "V010_REVIEW_COHORT_CHECKS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
