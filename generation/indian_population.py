"""Indian population calibration/sampling layer (M2C).

Deterministic, evidence-traceable sampling over `configs/indian_population.yaml`.
Kept isolated from `schemas/`/`ingestion/`/`validation/` per `CLAUDE.md`'s
generation/-isolation rule and `docs/DECISIONS.md` D001. Every distribution
used here has a matching, cited entry in the config — see
`docs/INDIAN_GENERATION_STRATEGY.md` and
`docs/session_logs/2026-09-25_M2C-indian-conditioning.md` (M2C-0 section)
for the evidence behind each one. Do not add a sampling relationship here
without a corresponding citation in the config.
"""

from __future__ import annotations

import math
from pathlib import Path
from statistics import NormalDist
from typing import Any, Optional

import numpy as np
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "configs" / "indian_population.yaml"

# Matches schemas/patient_schema.py's PTB-XL-derived convention (M1):
# sex = 0 male, sex = 1 female.
_SEX_ENCODING = {"male": 0, "female": 1}


def load_config(path: Path | None = None) -> dict[str, Any]:
    with open(path or _DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def valid_states(config: dict[str, Any]) -> set[str]:
    """The single canonical Indian state/UT list — sourced from the config,
    not duplicated elsewhere (CLAUDE.md M2C §7)."""
    return set(config["demographics"]["state"]["distribution"]["categories"].keys())


def _sample_categorical(rng: np.random.Generator, categories: dict[str, float]) -> str:
    names = list(categories.keys())
    probs = np.array(list(categories.values()), dtype=float)
    # Defensive normalization: YAML-parsed floats can drift from exactly
    # 1.0 by floating-point error even when the source values are correct
    # (validate_config() below checks the drift is small, not exactly zero).
    probs = probs / probs.sum()
    return str(rng.choice(names, p=probs))


def sample_age(rng: np.random.Generator, config: dict[str, Any]) -> float:
    dist = config["demographics"]["age"]["distribution"]
    # v0.10: 2 decimals (~4 days) -- the float's 14 decimals were false precision.
    return round(float(rng.uniform(dist["min"], dist["max"])), 2)


def sample_sex(rng: np.random.Generator, config: dict[str, Any]) -> int:
    categories = config["demographics"]["sex"]["distribution"]["categories"]
    return _SEX_ENCODING[_sample_categorical(rng, categories)]


def sample_state(rng: np.random.Generator, config: dict[str, Any]) -> str:
    categories = config["demographics"]["state"]["distribution"]["categories"]
    return _sample_categorical(rng, categories)


def sample_urban_rural(rng: np.random.Generator, config: dict[str, Any]) -> str:
    categories = config["demographics"]["urban_rural"]["distribution"]["categories"]
    return _sample_categorical(rng, categories)


def _sample_category_then_uniform(
    rng: np.random.Generator, categories: dict[str, float], category_ranges: dict[str, list]
) -> float:
    category = _sample_categorical(rng, categories)
    low, high = category_ranges[category]
    return round(float(rng.uniform(low, high)), 1)


def sample_bmi(rng: np.random.Generator, config: dict[str, Any], sex: int) -> float:
    """Category (evidence-backed) then within-category continuous value
    (engineering approximation — see the config's own documented caveat)."""
    dist = config["risk_factors"]["bmi"]["distribution"]
    sex_key = "male" if sex == 0 else "female"
    return _sample_category_then_uniform(rng, dist["categories_by_sex"][sex_key], dist["category_ranges"])


def sample_smoking_status(rng: np.random.Generator, config: dict[str, Any], sex: int) -> str:
    dist = config["risk_factors"]["smoking_status"]["distribution"]
    sex_key = "male" if sex == 0 else "female"
    categories = dist["categories_by_sex"][sex_key]
    return _sample_categorical(rng, categories)


def _sample_bernoulli(rng: np.random.Generator, config: dict[str, Any], key: str) -> bool:
    p = config["risk_factors"][key]["distribution"]["p"]
    return bool(rng.random() < p)


def sample_hypertension(rng: np.random.Generator, config: dict[str, Any]) -> bool:
    return _sample_bernoulli(rng, config, "hypertension")


def sample_diabetes(rng: np.random.Generator, config: dict[str, Any]) -> bool:
    return _sample_bernoulli(rng, config, "diabetes")


def sample_hyperlipidemia(rng: np.random.Generator, config: dict[str, Any]) -> bool:
    return _sample_bernoulli(rng, config, "hyperlipidemia")


_LIPID_MAX_REDRAW_ATTEMPTS = 1000
_N01 = NormalDist()


def lipid_joint_parameters(config: dict[str, Any]) -> dict[str, Any]:
    """Means/SDs/correlation for the v0.10 joint lipid model (issue 1).

    Location is NOT a free parameter: each mean is solved so the national
    ICMR-INDIAB-17 category rate (the same tier-A rates v0.9 used) is
    reproduced exactly, given the dispersion reported by the ICMR-INDIAB
    phase-I lipid paper (PMC4016101, Table 3). See the config's
    lipid_panel.joint_model block for every number's source."""
    lp = config["risk_factors"]["lipid_panel"]
    jm = lp["joint_model"]
    p_tc_high = lp["total_cholesterol"]["distribution"]["categories"]["high"]
    p_tg_high = lp["triglycerides"]["distribution"]["categories"]["high"]
    p_hdl_low = lp["hdl"]["distribution"]["categories_by_sex"]
    hdl_cut = jm["hdl_low_cutoff_by_sex"]
    sd_tc, sd_hdl = jm["total_cholesterol_sd"], jm["hdl_sd"]
    sig_tg = jm["triglycerides_log_sd"]
    return {
        "mu_tc": jm["total_cholesterol_threshold"] - _N01.inv_cdf(1 - p_tc_high) * sd_tc,
        "sd_tc": sd_tc,
        "mu_log_tg": math.log(jm["triglycerides_threshold"]) - sig_tg * _N01.inv_cdf(1 - p_tg_high),
        "sig_log_tg": sig_tg,
        "mu_hdl": {
            k: hdl_cut[k] - _N01.inv_cdf(p_hdl_low[k]["low"]) * sd_hdl for k in ("male", "female")
        },
        "sd_hdl": sd_hdl,
        "chol": np.linalg.cholesky(np.array(jm["latent_correlation"]["matrix_tc_logtg_hdl"], dtype=float)),
        "bounds": jm["rejection_bounds"],
    }


def sample_lipid_panel(rng: np.random.Generator, config: dict[str, Any], sex: int) -> dict[str, float]:
    """v0.10 (issue 1): TC, ln(TG), HDL drawn JOINTLY from one trivariate
    normal; LDL DERIVED by Friedewald (LDL = TC - HDL - TG/5), never
    sampled and never clamped.

    v0.9 drew the three independently (category-then-uniform), which lost
    the real TG/HDL and TC/TG dependence and needed a [30, 300] LDL clamp
    that silently piled 7.7% of records at exactly 30.0. Here a draw whose
    derived LDL falls below the physiological rejection floor, or whose TG
    exceeds 400 mg/dL (Friedewald's validity limit), or that leaves the
    plausible TC/HDL range, is REJECTED AND REDRAWN as a whole panel --
    no value is ever moved to a bound. Exhausting the retry budget raises
    instead of returning a clamped value."""
    jp = lipid_joint_parameters(config)
    b = jp["bounds"]
    sex_key = "male" if sex == 0 else "female"
    for _ in range(_LIPID_MAX_REDRAW_ATTEMPTS):
        z = jp["chol"] @ rng.standard_normal(3)
        tc = round(float(jp["mu_tc"] + jp["sd_tc"] * z[0]), 1)
        tg = round(float(math.exp(jp["mu_log_tg"] + jp["sig_log_tg"] * z[1])), 1)
        hdl = round(float(jp["mu_hdl"][sex_key] + jp["sd_hdl"] * z[2]), 1)
        ldl = round(tc - hdl - tg / 5.0, 1)
        if (
            b["tc_min"] <= tc <= b["tc_max"]
            and tg <= b["tg_max_friedewald"]
            and b["hdl_min"] <= hdl <= b["hdl_max"]
            and ldl >= b["ldl_min"]
        ):
            return {
                "total_cholesterol_mg_dl": tc,
                "triglycerides_mg_dl": tg,
                "hdl_mg_dl": hdl,
                "ldl_mg_dl": ldl,
            }
    raise RuntimeError("lipid panel: no admissible draw in retry budget -- check joint_model bounds")


def derive_lipid_interpretations(
    config: dict[str, Any], lipid_values: dict[str, float], sex: int
) -> list[dict[str, Any]]:
    """COMPUTE (never sample) one interpretation per documented definition
    — docs/DECISIONS.md D011. Every definition in
    config["risk_factors"]["lipid_definitions"] is evaluated; none is
    treated as more correct than another."""
    definitions = config["risk_factors"]["lipid_definitions"]
    sex_key = "male" if sex == 0 else "female"
    interpretations = []
    for name, d in definitions.items():
        hdl_threshold = d["hdl_threshold_male"] if sex_key == "male" else d["hdl_threshold_female"]
        components_abnormal = []
        if lipid_values["total_cholesterol_mg_dl"] >= d["total_cholesterol_threshold"]:
            components_abnormal.append("total_cholesterol")
        if lipid_values["triglycerides_mg_dl"] >= d["triglycerides_threshold"]:
            components_abnormal.append("triglycerides")
        if lipid_values["hdl_mg_dl"] < hdl_threshold:
            components_abnormal.append("HDL")
        if lipid_values["ldl_mg_dl"] >= d["ldl_threshold"]:
            components_abnormal.append("LDL")
        interpretations.append(
            {
                "definition": name,
                "dyslipidemia": len(components_abnormal) > 0,
                "components_abnormal": components_abnormal,
                "source_citation": d["source_citation"],
            }
        )
    return interpretations


def _diabetic_hba1c_lognormal(dist: dict[str, Any]) -> tuple[float, float]:
    """(mu, sigma) of the log-normal whose SD equals `sd` and whose
    P(HbA1c < control_threshold) equals the observed controlled share.
    Solved by bisection on the mean -- both targets are published figures,
    so no free parameter is left."""
    sd, thr, p_ctrl = dist["sd"], dist["control_threshold"], dist["p_below_control_threshold"]

    def params(mean: float) -> tuple[float, float]:
        sig = math.sqrt(math.log(1.0 + (sd / mean) ** 2))
        return math.log(mean) - sig * sig / 2.0, sig

    lo, hi = 4.0, 20.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        mu, sig = params(mid)
        if _N01.cdf((math.log(thr) - mu) / sig) > p_ctrl:
            lo = mid
        else:
            hi = mid
    return params((lo + hi) / 2.0)


def sample_hba1c(
    rng: np.random.Generator,
    config: dict[str, Any],
    age: float,
    sex: int,
    diabetes: bool,
    on_antidiabetic: bool = False,
) -> dict[str, Any]:
    """HbA1c, always CONDITIONAL on the already-generated diabetes label,
    never used to derive it (D011). Returns {value, derivation, confidence}.

    - Non-diabetic: ICMR-INDIAB-12 NGT age x sex trend (unchanged from v0.9).
    - Diabetic (new in v0.10, issue 3): log-normal fitted to ICMR-INDIAB-13's
      national share with HbA1c < 7% (36.3%) and the phase-I SD (~2.2).
      That source covers SELF-REPORTED (known, mostly treated) diabetes, so
      it is applied as observed to treated patients and BORROWED, flagged
      low-confidence, for untreated ones (incl. undiagnosed) -- no Indian
      source for that group was located."""
    if not diabetes:
        dist = config["risk_factors"]["hba1c"]["distribution"]
        sex_key = "male" if sex == 0 else "female"
        slope = dist["sex_decade_slope"][sex_key]
        mean = dist["baseline_mean_at_age_25"] + slope * (age - dist["reference_age"]) / 10.0
        value = rng.normal(mean, dist["sd"])
        low, high = dist["clip_range"]
        return {
            "value": round(float(min(max(value, low), high)), 2),
            "derivation": "observed_distribution_indiab12_ngt",
            "confidence": "moderate",
        }
    dist = config["risk_factors"]["hba1c_diabetes"]["distribution"]
    mu, sig = _diabetic_hba1c_lognormal(dist)
    low, high = dist["rejection_bounds"]
    for _ in range(_LIPID_MAX_REDRAW_ATTEMPTS):
        value = round(float(math.exp(rng.normal(mu, sig))), 2)
        if low <= value <= high:
            break
    else:
        raise RuntimeError("diabetic HbA1c: no admissible draw in retry budget")
    if on_antidiabetic:
        return {"value": value, "derivation": "observed_distribution_indiab13_self_reported_diabetes", "confidence": "moderate"}
    return {"value": value, "derivation": "borrowed_from_indiab13_self_reported_diabetes_untreated_unsourced", "confidence": "low"}


def _bp_band(config: dict[str, Any], age: float, sex: int) -> tuple[list[float], str, bool]:
    """Pick the NFHS-5 age band for this patient.

    v0.10 (issue 2): above the source's age coverage (men >54, women >49)
    the mean SBP is EXTRAPOLATED along the linear trend NFHS-5 itself shows
    across its bands from `fit_from_age` upward (least squares on band
    midpoints), evaluated at the patient's whole-year age. Mean DBP and both
    SDs stay at the oldest band: NFHS-5's own DBP increments already shrink
    toward zero in the oldest bands, and DBP is widely reported to plateau
    after ~50-60 (non-Indian prior, labelled in the config) -- so pulse
    pressure now widens with age instead of staying frozen. Records stay
    flagged extrapolated and get confidence "low".
    """
    dist = config["risk_factors"]["blood_pressure"]["distribution"]
    sex_key = "male" if sex == 0 else "female"
    bands = dist["age_bands_by_sex"][sex_key]
    coverage_max = dist["source_age_coverage_max_by_sex"][sex_key]
    # `age` is continuous but the source's bands are stated in whole
    # years, where "50-54" means everyone who has turned 50 and not yet
    # 55. So match half-open on [low, high+1).
    extrapolated = age >= coverage_max + 1
    if not extrapolated:
        band = next(b for b in bands if b[0] <= age < b[1] + 1)
        return band, f"NFHS-5 {sex_key} {int(band[0])}-{int(band[1])}", False
    fit_from = dist["beyond_coverage_extrapolation"]["fit_from_age"]
    fit = [b for b in bands if b[0] >= fit_from]
    x = np.array([(b[0] + b[1] + 1) / 2.0 for b in fit])
    y = np.array([b[2] for b in fit])
    slope, intercept = np.polyfit(x, y, 1)
    whole_age = math.floor(age)  # whole years keeps the PMF cache small (<=70 keys per region)
    last = list(bands[-1])
    last[2] = round(float(intercept + slope * (whole_age + 0.5)), 2)
    label = (
        f"NFHS-5 {sex_key} {int(bands[-1][0])}-{int(bands[-1][1])} DBP/SDs; SBP linear trend "
        f"(bands {fit_from}-{int(bands[-1][1])}, {slope:+.2f} mmHg/yr) extrapolated to age {whole_age}"
    )
    return last, label, True


def _bp_region(hypertension: bool, on_antihypertensive: bool) -> str:
    """Which region of the (SBP, DBP) plane the hypertension label
    confines this patient to, under the label's OWN published definition
    (SBP>=140 and/or DBP>=90 and/or on antihypertensive medication).

    The `unconstrained` case is the important one: a TREATED hypertensive
    already satisfies the definition through medication use, so the
    measurement says nothing further and is left free -- a treated
    patient may be controlled or uncontrolled. Forcing a raised reading
    there would be inventing a measurement to confirm a label.
    """
    if not hypertension:
        return "normotensive"
    return "unconstrained" if on_antihypertensive else "raised"


# Cache of joint BP distributions, keyed by everything that defines one.
# There are only 15 (sex, age band) pairs x 3 regions = 45 distinct
# distributions for the whole 100,000-record dataset, so each is built
# once and then sampled by index.
_BP_PMF_CACHE: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def _bp_joint_pmf(
    band: tuple[float, ...],
    region: str,
    corr: float,
    sbp_bounds: tuple[int, int],
    dbp_bounds: tuple[int, int],
    sbp_threshold: int,
    dbp_threshold: int,
    min_pulse_pressure: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build (or reuse) the bivariate-normal PMF over the INTEGER mmHg
    grid, with cells outside the label region -- or violating SBP > DBP
    -- zeroed, then renormalised.

    Why a grid rather than truncated marginals or rejection sampling:
    one code path covers all three regions exactly; there is no retry
    budget and therefore no bail-out bias in the thin tails young
    patients fall into (the raised region sits ~2.6 SD out for women
    aged 20-24); whole-mmHg rounding is intrinsic instead of a post-step
    that can push a value back across the threshold it was truncated
    against; and SBP > DBP is enforced by construction rather than by a
    repair step. Returns (cdf, sbp_flat, dbp_flat) so a draw is one
    uniform plus a searchsorted.
    """
    key = (
        band,
        region,
        corr,
        sbp_bounds,
        dbp_bounds,
        sbp_threshold,
        dbp_threshold,
        min_pulse_pressure,
    )
    cached = _BP_PMF_CACHE.get(key)
    if cached is not None:
        return cached

    _, _, mean_sbp, sd_sbp, mean_dbp, sd_dbp = (float(v) for v in band)
    sbp_axis = np.arange(sbp_bounds[0], sbp_bounds[1] + 1)
    dbp_axis = np.arange(dbp_bounds[0], dbp_bounds[1] + 1)
    sbp_grid, dbp_grid = np.meshgrid(sbp_axis, dbp_axis, indexing="ij")

    z_s = (sbp_grid - mean_sbp) / sd_sbp
    z_d = (dbp_grid - mean_dbp) / sd_dbp
    # Standard bivariate-normal exponent; the normalising constant is
    # irrelevant because the result is renormalised over the kept cells.
    quad = (z_s**2 - 2.0 * corr * z_s * z_d + z_d**2) / (1.0 - corr**2)
    # Subtract the max before exponentiating so no cell underflows to
    # zero purely from the shared offset.
    density = np.exp(-0.5 * (quad - quad.min()))

    # Two separate constraints, with very different standing:
    #  - SBP > DBP is definitional (what blood pressure IS), and is
    #    implied by the floor below but kept explicit so the invariant
    #    survives any future change to the floor.
    #  - the pulse-pressure floor is an EXPLICIT ENGINEERING ASSUMPTION,
    #    declared as such in the config, which exists because a Gaussian
    #    copula's corners put ~2% of records at a clinically absurd
    #    PP < 20 mmHg. No upper cap: wide pulse pressure is real in
    #    older hypertensives. See the config's own measurements.
    keep = (sbp_grid > dbp_grid) & (sbp_grid - dbp_grid >= min_pulse_pressure)
    if region == "normotensive":
        keep &= (sbp_grid < sbp_threshold) & (dbp_grid < dbp_threshold)
    elif region == "raised":
        keep &= (sbp_grid >= sbp_threshold) | (dbp_grid >= dbp_threshold)
    elif region != "unconstrained":
        raise ValueError(f"unknown blood-pressure region {region!r}")

    pmf = np.where(keep, density, 0.0).ravel()
    total = pmf.sum()
    if total <= 0.0:
        raise ValueError(
            f"blood-pressure region {region!r} has zero probability mass for band "
            f"{band} -- the physiological bounds, label thresholds and pulse-pressure "
            "floor leave no admissible cell"
        )
    cdf = np.cumsum(pmf / total)
    cdf[-1] = 1.0  # guard floating-point shortfall so searchsorted can never run off the end
    built = (cdf, sbp_grid.ravel(), dbp_grid.ravel())
    _BP_PMF_CACHE[key] = built
    return built


def sample_blood_pressure(
    rng: np.random.Generator,
    config: dict[str, Any],
    age: float,
    sex: int,
    hypertension: bool,
    on_antihypertensive: bool,
) -> dict[str, Any]:
    """SBP/DBP conditional on the already-generated hypertension label (M8).

    The label stays primary (ICMR-INDIAB-17 national marginal); the
    measurement is drawn from NFHS-5's age-band x sex bivariate normal
    restricted to the region the label's OWN published definition
    implies (see _bp_region). BP is therefore never used to re-derive
    hypertension and introduces no new prevalence claim.

    The SBP/DBP correlation is DERIVED from published Indian variances
    rather than assumed -- see the config's sbp_dbp_correlation block,
    including the measurement showing that modelling it (rather than
    sampling the two independently) is what keeps pulse pressure
    clinically plausible.
    """
    dist = config["risk_factors"]["blood_pressure"]["distribution"]
    lc = dist["label_conditioning"]
    corr = float(dist["sbp_dbp_correlation"]["value"])
    sbp_bounds = tuple(int(v) for v in dist["sbp_bounds"])
    dbp_bounds = tuple(int(v) for v in dist["dbp_bounds"])

    band, band_label, extrapolated = _bp_band(config, age, sex)
    cdf, sbp_flat, dbp_flat = _bp_joint_pmf(
        tuple(float(v) for v in band),
        _bp_region(hypertension, on_antihypertensive),
        corr,
        sbp_bounds,
        dbp_bounds,
        int(lc["sbp_threshold"]),
        int(lc["dbp_threshold"]),
        int(dist["min_pulse_pressure_mm_hg"]),
    )
    idx = int(np.searchsorted(cdf, rng.random(), side="right"))
    idx = min(idx, cdf.size - 1)

    return {
        "systolic_mm_hg": int(sbp_flat[idx]),
        "diastolic_mm_hg": int(dbp_flat[idx]),
        "age_band_source": band_label,
        "extrapolated_beyond_source_age_range": extrapolated,
        "confidence": "low" if extrapolated else "moderate",
    }


def sample_height_cm(
    rng: np.random.Generator, config: dict[str, Any], sex: int
) -> Optional[float]:
    """Returns None -- height is NOT generated (M8).

    A deliberate no-op hook, not an oversight: a national mean AND SD of
    Indian adult height by sex was searched for 6 times (3 in M4-0, 3 in
    M8) and never located, so there is no non-invented dispersion to
    sample from. Full trail and the two routes to unblock:
    configs/indian_population.yaml
    risk_factors.anthropometrics_height_weight. Once a mean+SD lands in
    that config entry this becomes a Normal draw, derive_weight_kg()
    completes the pair, and BMI -- already evidence-primary -- stays
    untouched either way.
    """
    status = config["risk_factors"]["anthropometrics_height_weight"]["status"]
    if not status.startswith("NOT SUPPORTED"):
        raise NotImplementedError(
            "height evidence has appeared in configs/indian_population.yaml "
            "(risk_factors.anthropometrics_height_weight) -- implement the "
            "Normal draw here instead of returning None"
        )
    return None


def derive_weight_kg(bmi: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    """weight = bmi * (height/100)^2 -- DERIVED, never sampled, so BMI
    (the evidence-primary anthropometric variable) is preserved exactly.
    Returns None while height is unavailable, which is every patient
    today."""
    if bmi is None or height_cm is None:
        return None
    return round(float(bmi) * (float(height_cm) / 100.0) ** 2, 1)


def sample_medication_treatment(
    rng: np.random.Generator, config: dict[str, Any], hypertension: bool, diabetes: bool
) -> dict[str, bool]:
    """One evidence-backed Bernoulli draw per diagnosable condition present
    -- NNMS treatment-rate marginals (docs/DECISIONS.md D016). Statin/
    antiplatelet treatment is not drawn here: no population treatment-rate
    evidence exists for either (docs/M4E_MEDICATION_EVIDENCE.md)."""
    treated = {}
    if hypertension:
        p = config["medications"]["antihypertensive_treatment_rate"]["distribution"]["p"]
        treated["hypertension"] = bool(rng.random() < p)
    if diabetes:
        p = config["medications"]["antidiabetic_treatment_rate"]["distribution"]["p"]
        treated["diabetes"] = bool(rng.random() < p)
    return treated


FAMILY_HISTORY_CONDITIONS = ("diabetes", "cardiovascular_disease")


def _parent_rates(dist: dict[str, Any], condition: str, sex_key: str) -> list[float]:
    """[age 45-59, age 60+] parent-generation prevalence. CVD = heart
    disease or stroke, combined assuming independence (config limitation 6)."""
    rates = dist["parent_rates_by_sex"]
    if condition == "diabetes":
        return rates["diabetes"][sex_key]
    return [
        1.0 - (1.0 - h) * (1.0 - s)
        for h, s in zip(rates["heart_disease"][sex_key], rates["stroke"][sex_key])
    ]


def _calibration_factor(observed: float, p_mother: float, p_father: float) -> float:
    """k such that 1-(1-k*p_mother)(1-k*p_father) == observed (smaller
    root of the quadratic, the one keeping k*p in [0, 1])."""
    a, b = p_mother, p_father
    return ((a + b) - math.sqrt((a + b) ** 2 - 4 * a * b * observed)) / (2 * a * b)


def family_history_marginals(config: dict[str, Any], age: float) -> tuple[dict[str, float], str]:
    """Per-condition P(family history) for a patient of this age, plus the
    derivation tag stored on the record (D020). 45+: LASI observed
    marginal. 20-44: calibrated parent simulation -- see
    configs/indian_population.yaml risk_factors.family_history."""
    dist = config["risk_factors"]["family_history"]["distribution"]
    observed = dist["observed_marginal"]
    if age >= dist["observed_min_age"]:
        return dict(observed), "lasi_observed_45_plus"
    gaps = dist["parent_age_gap_years"]
    marginals = {}
    for condition in FAMILY_HISTORY_CONDITIONS:
        mother, father = _parent_rates(dist, condition, "female"), _parent_rates(dist, condition, "male")
        # Parents of a 45+ patient are both 60+, so the 45+ anchor fixes k.
        k = _calibration_factor(observed[condition], mother[1], father[1])
        p_m = k * mother[0 if age + gaps["mother"] < 60 else 1]
        p_f = k * father[0 if age + gaps["father"] < 60 else 1]
        marginals[condition] = 1.0 - (1.0 - p_m) * (1.0 - p_f)
    return marginals, "parent_simulation_calibrated"


def _conditional_on_exposure(marginal: float, p_exposure: float, odds_ratio: float) -> tuple[float, float]:
    """(P(fh | exposed), P(fh | unexposed)) for a 2x2 table with the given
    margins and odds ratio, so conditioning leaves the fh marginal intact."""
    m, p, r = marginal, p_exposure, odds_ratio
    # a = P(fh and exposed) solves (r-1)a^2 - (1 + (r-1)(m+p))a + r*m*p = 0
    qa, qb, qc = r - 1.0, -(1.0 + (r - 1.0) * (m + p)), r * m * p
    a = (-qb - math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa)
    return a / p, (m - a) / (1.0 - p)


def sample_family_history(
    rng: np.random.Generator, config: dict[str, Any], age: float, diabetes: bool
) -> dict[str, Any]:
    """D020. Diabetes family history is conditional on the patient's own,
    already-generated diabetes label (LASI crude OR), never the reverse;
    CVD family history is a marginal draw (no patient-level CVD label)."""
    marginals, derivation = family_history_marginals(config, age)
    dist = config["risk_factors"]["family_history"]["distribution"]
    p_diabetes = config["risk_factors"]["diabetes"]["distribution"]["p"]
    p_if_diabetic, p_if_not = _conditional_on_exposure(
        marginals["diabetes"], p_diabetes, dist["diabetes_crude_odds_ratio"]
    )
    return {
        "diabetes": bool(rng.random() < (p_if_diabetic if diabetes else p_if_not)),
        "cardiovascular_disease": bool(rng.random() < marginals["cardiovascular_disease"]),
        "derivation": derivation,
    }


_HTN_PREV_CACHE: dict[tuple[int, int], float] = {}


def _hypertension_prevalence_at(config: dict[str, Any], whole_age: int, sex: int) -> float:
    """P(SBP>=140 or DBP>=90) at a whole-year age, read off the SAME
    NFHS-5 bivariate BP distribution sample_blood_pressure() uses
    (extrapolated above coverage exactly as there). Measured-BP prevalence,
    so it excludes treated-and-controlled people -- used only for the
    SHAPE of the age curve, not as a prevalence claim."""
    key = (whole_age, sex)
    if key not in _HTN_PREV_CACHE:
        dist = config["risk_factors"]["blood_pressure"]["distribution"]
        lc = dist["label_conditioning"]
        band, _, _ = _bp_band(config, whole_age + 0.5, sex)
        cdf, sbp, dbp = _bp_joint_pmf(
            tuple(float(v) for v in band),
            "unconstrained",
            float(dist["sbp_dbp_correlation"]["value"]),
            tuple(int(v) for v in dist["sbp_bounds"]),
            tuple(int(v) for v in dist["dbp_bounds"]),
            int(lc["sbp_threshold"]),
            int(lc["dbp_threshold"]),
            int(dist["min_pulse_pressure_mm_hg"]),
        )
        pmf = np.diff(cdf, prepend=0.0)
        raised = (sbp >= lc["sbp_threshold"]) | (dbp >= lc["dbp_threshold"])
        _HTN_PREV_CACHE[key] = float(pmf[raised].sum())
    return _HTN_PREV_CACHE[key]


def _diabetes_prevalence_at(config: dict[str, Any], age: float, sex: int) -> float:
    anchors = config["onset_model"]["diabetes_prevalence_anchors_by_sex"]["male" if sex == 0 else "female"]
    xs = [float(a[0]) for a in anchors]
    ys = [float(a[1]) for a in anchors]
    return float(np.interp(age, xs, ys))


def _sample_onset_age(rng: np.random.Generator, age: float, prevalence, zero_age: float) -> float:
    """Onset age given the condition is present at `age`.

    Treats the cross-sectional prevalence-by-age curve P(a) as cumulative
    incidence (no cohort effect, no differential mortality, no remission
    -- all stated in the config), so onset has CDF P(a)/P(age) on
    [zero_age, age], with P(zero_age) = 0 as a stated assumption.
    Inverse-CDF on a whole-year grid with linear interpolation. Onset can
    never exceed `age` by construction."""
    inner = np.arange(math.floor(zero_age) + 1, math.floor(age) + 1, dtype=float)
    grid = np.concatenate(([zero_age], inner[inner < age], [age]))
    p = np.concatenate(([0.0], [prevalence(g) for g in grid[1:]]))
    p = np.maximum.accumulate(p)
    if p[-1] <= 0.0:
        return math.floor(age * 10) / 10.0
    target = rng.random() * p[-1]
    keep = np.concatenate(([True], np.diff(p) > 0))  # np.interp needs strictly increasing x
    onset = float(np.interp(target, p[keep], grid[keep]))
    return min(math.floor(onset * 10) / 10.0, age)


def sample_onset_ages(
    rng: np.random.Generator, config: dict[str, Any], age: float, sex: int, hypertension: bool, diabetes: bool
) -> dict[str, dict[str, Any]]:
    """v0.10 (issue 4, option b): modeled onset age per present condition.
    Every value is tagged derivation=modeled; nothing here is observed."""
    out: dict[str, dict[str, Any]] = {}
    if hypertension:
        out["hypertension"] = {
            "age_at_onset_years": _sample_onset_age(
                rng, age, lambda a: _hypertension_prevalence_at(config, int(math.floor(a)), sex),
                config["onset_model"]["zero_prevalence_age"]["hypertension"],
            ),
            "onset_derivation": "modeled_from_nfhs5_bp_age_curve",
            "onset_confidence": "low",
        }
    if diabetes:
        out["diabetes"] = {
            "age_at_onset_years": _sample_onset_age(
                rng, age, lambda a: _diabetes_prevalence_at(config, a, sex),
                config["onset_model"]["zero_prevalence_age"]["diabetes"],
            ),
            "onset_derivation": "modeled_from_lasi_age_prevalence",
            "onset_confidence": "low",
        }
    return out


def aqi_category(config: dict[str, Any], aqi: float) -> str:
    """CPCB National AQI category (upper bounds inclusive, config order)."""
    for category, upper in config["environment"]["air_quality"]["category_breakpoints"].items():
        if aqi <= upper:
            return category
    raise ValueError(f"AQI {aqi} exceeds the CPCB scale")


def derive_air_quality(config: dict[str, Any], state: str) -> dict[str, Any]:
    """D021: deterministic lookup by state -- an observed fact about a
    place and year, never sampled, so it consumes no rng."""
    aq = config["environment"]["air_quality"]
    row = aq["by_state"].get(state)
    if row is None:
        return {
            "aqi": None,
            "category": None,
            "reference_year": aq["reference_year"],
            "stations": None,
            "cities": None,
            "unavailable_reason": aq["unavailable"][state],
        }
    return {
        "aqi": row["aqi"],
        "category": aqi_category(config, row["aqi"]),
        "reference_year": aq["reference_year"],
        "stations": row["stations"],
        "cities": row["cities"],
        "unavailable_reason": None,
    }


def generate_indian_attributes(rng: np.random.Generator, config: dict[str, Any]) -> dict[str, Any]:
    """Dependency order per docs/INDIAN_GENERATION_STRATEGY.md section 6
    and docs/M4_CLINICAL_ARCHITECTURE.md section 9:
    age -> sex -> state -> urban_rural -> BMI -> smoking -> hypertension ->
    diabetes -> hyperlipidemia -> lipid panel -> lipid interpretations ->
    HbA1c -> medication treatment. Only BMI/smoking (sex), HbA1c (age+sex,
    conditional on diabetes), and medication_treatment (conditional on
    hypertension/diabetes) are conditioned; hypertension/diabetes/
    hyperlipidemia/lipid panel components are unconditioned marginals;
    lipid interpretations and LDL are COMPUTED, never sampled. See the
    config for exactly which relationships are evidence-supported versus
    deliberately left unconditioned (M2C-0/M4B-0/M4E-0 evidence gates).
    """
    age = sample_age(rng, config)
    sex = sample_sex(rng, config)
    state = sample_state(rng, config)
    urban_rural = sample_urban_rural(rng, config)
    bmi = sample_bmi(rng, config, sex)
    smoking_status = sample_smoking_status(rng, config, sex)
    hypertension = sample_hypertension(rng, config)
    diabetes = sample_diabetes(rng, config)
    hyperlipidemia = sample_hyperlipidemia(rng, config)
    # v0.10: lipids and HbA1c each draw from their own child stream (one
    # parent draw each), so their variable-length rejection loops can never
    # shift any later field's random numbers again.
    lipid_values = sample_lipid_panel(np.random.default_rng(int(rng.integers(2**63))), config, sex)
    lipid_interpretations = derive_lipid_interpretations(config, lipid_values, sex)
    hba1c_rng = np.random.default_rng(int(rng.integers(2**63)))
    medication_treatment = sample_medication_treatment(rng, config, hypertension, diabetes)
    hba1c = sample_hba1c(
        hba1c_rng, config, age, sex, diabetes, on_antidiabetic=medication_treatment.get("diabetes", False)
    )
    # M8 -- LAST in the draw order on purpose. Every pre-existing field
    # consumes the rng stream before BP does, so adding BP leaves all of
    # them byte-identical for the same seed (verified in
    # tests/test_m8_bp_encounters.py). height/weight stay None: no
    # evidence (see sample_height_cm's docstring).
    height_cm = sample_height_cm(rng, config, sex)
    blood_pressure = sample_blood_pressure(
        rng,
        config,
        age,
        sex,
        hypertension,
        on_antihypertensive=medication_treatment.get("hypertension", False),
    )
    # D020 -- after BP for the same reason BP is last: every earlier field
    # stays byte-identical for the same seed.
    family_history = sample_family_history(rng, config, age, diabetes)
    # v0.10 -- last, same reasoning.
    onset = sample_onset_ages(rng, config, age, sex, hypertension, diabetes)

    return {
        "demographics": {
            "age": age,
            "sex": sex,
            "state": state,
            "urban_rural": urban_rural,
            "height_cm": height_cm,
            "weight_kg": derive_weight_kg(bmi, height_cm),
        },
        "risk_factors": {
            "bmi": bmi,
            "smoking_status": smoking_status,
            "hypertension": hypertension,
            "diabetes": diabetes,
            "hyperlipidemia": hyperlipidemia,
        },
        "lipid_panel": lipid_values,
        "lipid_interpretations": lipid_interpretations,
        "hba1c": hba1c,
        "medication_treatment": medication_treatment,
        "blood_pressure": blood_pressure,
        "family_history": family_history,
        "air_quality": derive_air_quality(config, state),
        "onset": onset,
    }


def validate_config(config: dict[str, Any]) -> list[str]:
    """Sanity-check every categorical distribution: non-negative
    probabilities, sums to 1.0 within floating-point tolerance."""
    errors: list[str] = []

    def _check_categorical(label: str, categories: dict[str, float]) -> None:
        if not categories:
            errors.append(f"{label}: no categories defined")
            return
        for name, p in categories.items():
            if p < 0:
                errors.append(f"{label}: negative probability for {name!r}: {p}")
        total = sum(categories.values())
        # Tolerance loose enough for rounded YAML literals (e.g. 35 state
        # shares each rounded to 6dp can drift ~1e-5 in sum) but still tight
        # enough to catch a genuine data-entry mistake.
        if abs(total - 1.0) > 1e-4:
            errors.append(f"{label}: probabilities sum to {total}, expected 1.0")

    _check_categorical(
        "demographics.sex", config["demographics"]["sex"]["distribution"]["categories"]
    )
    _check_categorical(
        "demographics.state", config["demographics"]["state"]["distribution"]["categories"]
    )
    _check_categorical(
        "demographics.urban_rural",
        config["demographics"]["urban_rural"]["distribution"]["categories"],
    )
    for sex_key, cats in config["risk_factors"]["bmi"]["distribution"]["categories_by_sex"].items():
        _check_categorical(f"risk_factors.bmi[{sex_key}]", cats)
    for sex_key, cats in config["risk_factors"]["smoking_status"]["distribution"][
        "categories_by_sex"
    ].items():
        _check_categorical(f"risk_factors.smoking_status[{sex_key}]", cats)

    for key in ("hypertension", "diabetes", "hyperlipidemia"):
        p = config["risk_factors"][key]["distribution"]["p"]
        if not (0.0 <= p <= 1.0):
            errors.append(f"risk_factors.{key}: p={p} out of [0,1]")

    lp = config["risk_factors"]["lipid_panel"]
    _check_categorical(
        "risk_factors.lipid_panel.total_cholesterol",
        lp["total_cholesterol"]["distribution"]["categories"],
    )
    _check_categorical(
        "risk_factors.lipid_panel.triglycerides",
        lp["triglycerides"]["distribution"]["categories"],
    )
    for sex_key, cats in lp["hdl"]["distribution"]["categories_by_sex"].items():
        _check_categorical(f"risk_factors.lipid_panel.hdl[{sex_key}]", cats)

    for key in ("antihypertensive_treatment_rate", "antidiabetic_treatment_rate"):
        p = config["medications"][key]["distribution"]["p"]
        if not (0.0 <= p <= 1.0):
            errors.append(f"medications.{key}: p={p} out of [0,1]")

    # --- D020: family history -- the youngest patient's parents must fall
    # inside LASI's 45+ parent-rate bands ---
    fh = config["risk_factors"]["family_history"]["distribution"]
    youngest_parent = config["demographics"]["age"]["distribution"]["min"] + min(
        fh["parent_age_gap_years"].values()
    )
    if youngest_parent < 45:
        errors.append(
            f"risk_factors.family_history: youngest parent age {youngest_parent} "
            "is below LASI's 45+ parent-rate coverage"
        )

    # --- D021: every generatable state needs an AQI value or a stated
    # reason for its absence, never both ---
    aq = config["environment"]["air_quality"]
    for state in config["demographics"]["state"]["distribution"]["categories"]:
        if (state in aq["by_state"]) == (state in aq["unavailable"]):
            errors.append(
                f"environment.air_quality: {state!r} must be in exactly one of by_state / unavailable"
            )
    for state, row in aq["by_state"].items():
        if not 0 <= row["aqi"] <= 500:
            errors.append(f"environment.air_quality[{state!r}]: aqi {row['aqi']} outside CPCB 0-500")

    # --- M8: blood_pressure age bands ---
    bp = config["risk_factors"]["blood_pressure"]["distribution"]
    for sex_key, bands in bp["age_bands_by_sex"].items():
        prev_high = None
        for band in bands:
            if len(band) != 6:
                errors.append(
                    f"risk_factors.blood_pressure[{sex_key}]: band {band} must be "
                    "[age_low, age_high, mean_sbp, sd_sbp, mean_dbp, sd_dbp]"
                )
                continue
            low, high, mean_sbp, sd_sbp, mean_dbp, sd_dbp = band
            if low > high:
                errors.append(f"risk_factors.blood_pressure[{sex_key}]: band {low}-{high} inverted")
            if prev_high is not None and low != prev_high + 1:
                errors.append(
                    f"risk_factors.blood_pressure[{sex_key}]: gap/overlap between "
                    f"band ending {prev_high} and band starting {low}"
                )
            prev_high = high
            if sd_sbp <= 0 or sd_dbp <= 0:
                errors.append(f"risk_factors.blood_pressure[{sex_key}] band {low}-{high}: non-positive SD")
            if mean_sbp <= mean_dbp:
                errors.append(
                    f"risk_factors.blood_pressure[{sex_key}] band {low}-{high}: "
                    f"mean SBP {mean_sbp} <= mean DBP {mean_dbp}"
                )
        coverage_max = bp["source_age_coverage_max_by_sex"].get(sex_key)
        if coverage_max is not None and prev_high is not None and coverage_max != prev_high:
            errors.append(
                f"risk_factors.blood_pressure[{sex_key}]: source_age_coverage_max "
                f"{coverage_max} does not match last band's upper age {prev_high}"
            )
    sbp_lo, sbp_hi = bp["sbp_bounds"]
    dbp_lo, dbp_hi = bp["dbp_bounds"]
    lc = bp["label_conditioning"]
    if not (sbp_lo < lc["sbp_threshold"] < sbp_hi):
        errors.append(f"risk_factors.blood_pressure: sbp_threshold outside sbp_bounds {bp['sbp_bounds']}")
    if not (dbp_lo < lc["dbp_threshold"] < dbp_hi):
        errors.append(f"risk_factors.blood_pressure: dbp_threshold outside dbp_bounds {bp['dbp_bounds']}")

    return errors
