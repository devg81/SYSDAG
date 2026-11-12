"""Streaming distribution check of the v0.9 100K dataset against config targets."""
import collections
import glob
import json
import math
import sys

import yaml

d = sys.argv[1]
cfg = yaml.safe_load(open("configs/indian_population.yaml", encoding="utf-8"))
rf = cfg["risk_factors"]
n = 0
c = collections.Counter()
states = collections.Counter()
for f in glob.iglob(d + "/PAT_*.json"):
    r = json.load(open(f, encoding="utf-8"))
    n += 1
    age = r["demographics"]["age"]
    young = age < 45
    states[r["demographics"]["state"]] += 1
    c["sex_female"] += r["demographics"]["sex"] == 1
    c["urban"] += r["demographics"]["urban_rural"] == "urban"
    for k in ("hypertension", "diabetes", "hyperlipidemia"):
        c[k] += r["risk_factors"][k]
    lp = r["lipid_panel"]
    c["lipid_infeasible"] += lp["total_cholesterol_mg_dl"] - lp["hdl_mg_dl"] - lp["triglycerides_mg_dl"] / 5 < 0
    fh = r["family_history"]
    tier = "young" if young else "old"
    c[f"n_{tier}"] += 1
    c[f"fh_dm_{tier}"] += fh["diabetes"]
    c[f"fh_cvd_{tier}"] += fh["cardiovascular_disease"]
    c["deriv_mismatch"] += fh["derivation"] != ("parent_simulation_calibrated" if young else "lasi_observed_45_plus")
    dm = r["risk_factors"]["diabetes"]
    c["n_dm"] += dm
    c["fh_dm_in_dm"] += dm and fh["diabetes"]
    c["fh_dm_in_nodm"] += (not dm) and fh["diabetes"]
    aq = r["air_quality"]
    c["aqi_null"] += aq["aqi"] is None
    c["aqi_null_no_reason"] += aq["aqi"] is None and not aq["unavailable_reason"]
    c["schema_09"] += r["provenance"]["schema_version"] == "0.9"


def z(obs, p, m):
    se = math.sqrt(p * (1 - p) / m)
    return f"{100 * obs / m:.2f}% vs {100 * p:.2f}% (z={(obs / m - p) / se:+.2f})"


print("n", n, "schema 0.9:", c["schema_09"])
for k in ("hypertension", "diabetes", "hyperlipidemia"):
    print(k, z(c[k], rf[k]["distribution"]["p"], n))
print("female", z(c["sex_female"], cfg["demographics"]["sex"]["distribution"]["categories"]["female"], n))
print("urban", z(c["urban"], cfg["demographics"]["urban_rural"]["distribution"]["categories"]["urban"], n))
obs = rf["family_history"]["distribution"]["observed_marginal"]
print("FH diabetes 45+", z(c["fh_dm_old"], obs["diabetes"], c["n_old"]))
print("FH CVD 45+", z(c["fh_cvd_old"], obs["cardiovascular_disease"], c["n_old"]))
print(f"FH 20-44 diabetes {100 * c['fh_dm_young'] / c['n_young']:.2f}%  CVD {100 * c['fh_cvd_young'] / c['n_young']:.2f}%  (CARRS urban caps 22.2 / 9.0)")
print(f"FH diabetes among diabetic {100 * c['fh_dm_in_dm'] / c['n_dm']:.1f}% vs non-diabetic {100 * c['fh_dm_in_nodm'] / (n - c['n_dm']):.1f}%")
print("derivation mismatches", c["deriv_mismatch"])
na_share = sum(v for k, v in cfg["demographics"]["state"]["distribution"]["categories"].items() if k in cfg["environment"]["air_quality"]["unavailable"])
print("AQI null", z(c["aqi_null"], na_share, n), "null without reason:", c["aqi_null_no_reason"])
print("lipid infeasible", c["lipid_infeasible"])
cats = cfg["demographics"]["state"]["distribution"]["categories"]
chi2 = sum((states[s] - n * p) ** 2 / (n * p) for s, p in cats.items())
print(f"state chi2 {chi2:.1f} on {len(cats) - 1} df")
