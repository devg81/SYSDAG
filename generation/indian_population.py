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
    return float(rng.uniform(dist["min"], dist["max"]))


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


def sample_lipid_panel(rng: np.random.Generator, config: dict[str, Any], sex: int) -> dict[str, float]:
    """TC, TG, HDL sampled (category-then-uniform, evidence-backed
    marginal categories); LDL DERIVED via the Friedewald equation, never
    independently sampled — docs/M4B_GENERATION_DESIGN.md A2 (the same
    formula ICMR-INDIAB-17 itself used).

    A triple where TC < HDL + TG/5 makes the Friedewald LDL negative —
    a physical impossibility (measured at 2.28% of 100,000 records,
    docs/M8_FULL_DATASET_VALIDATION_REPORT.md §4) — not merely a low
    LDL. Per the approved fix (docs/DECISIONS.md D019, "reject-and-redraw"),
    such triples are discarded and redrawn from the exact same
    evidence-backed marginals; no new correlation or assumption is
    introduced, only infeasible combinations are excluded. This does
    NOT address the separate, smaller LDL-clip-floor population (low_raw
    in [0, 30) rounding up to the 30 mg/dL floor, 9.83% of records) —
    those are physiologically plausible low-LDL draws, not impossible
    ones, and are left exactly as before."""
    lp = config["risk_factors"]["lipid_panel"]
    sex_key = "male" if sex == 0 else "female"

    tc_dist = lp["total_cholesterol"]["distribution"]
    tg_dist = lp["triglycerides"]["distribution"]
    hdl_dist = lp["hdl"]["distribution"]
    ldl_dist = lp["ldl"]["distribution"]
    low, high = ldl_dist["clip_range"]

    for _ in range(_LIPID_MAX_REDRAW_ATTEMPTS):
        total_cholesterol = _sample_category_then_uniform(
            rng, tc_dist["categories"], tc_dist["category_ranges"]
        )
        triglycerides = _sample_category_then_uniform(
            rng, tg_dist["categories"], tg_dist["category_ranges"]
        )
        hdl = _sample_category_then_uniform(
            rng, hdl_dist["categories_by_sex"][sex_key], hdl_dist["category_ranges_by_sex"][sex_key]
        )
        ldl_raw = total_cholesterol - hdl - triglycerides / 5.0
        if ldl_raw >= 0:
            break
    # Safety net only — at the measured 97.72% per-draw feasibility rate,
    # exhausting 1000 attempts has effectively zero probability; the clip
    # floor below still applies to the (now impossible-triple-free) result.
    ldl = round(float(min(max(ldl_raw, low), high)), 1)

    return {
        "total_cholesterol_mg_dl": total_cholesterol,
        "triglycerides_mg_dl": triglycerides,
        "hdl_mg_dl": hdl,
        "ldl_mg_dl": ldl,
    }


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


def sample_hba1c(
    rng: np.random.Generator, config: dict[str, Any], age: float, sex: int, diabetes: bool
) -> Optional[float]:
    """Conditional on the already-generated `diabetes` label (D011's
    reversed-direction finding for HbA1c) — never used to derive it.
    Only generated for non-diabetic (NGT) patients; diabetic-population
    HbA1c has insufficient evidence (docs/M4B_GENERATION_DESIGN.md A4)."""
    if diabetes:
        return None
    dist = config["risk_factors"]["hba1c"]["distribution"]
    sex_key = "male" if sex == 0 else "female"
    slope = dist["sex_decade_slope"][sex_key]
    mean = dist["baseline_mean_at_age_25"] + slope * (age - dist["reference_age"]) / 10.0
    value = rng.normal(mean, dist["sd"])
    low, high = dist["clip_range"]
    return round(float(min(max(value, low), high)), 2)


def _bp_band(config: dict[str, Any], age: float, sex: int) -> tuple[list[float], str, bool]:
    """Pick the NFHS-5 age band for this patient.

    Above the source's own age coverage (men >54, women >49) the OLDEST
    available band is held constant -- the conservative choice, since BP
    keeps rising with age, so this UNDERSTATES rather than invents a
    continuing trend. The returned flag is written onto the record so
    those patients stay machine-filterable.
    """
    dist = config["risk_factors"]["blood_pressure"]["distribution"]
    sex_key = "male" if sex == 0 else "female"
    bands = dist["age_bands_by_sex"][sex_key]
    coverage_max = dist["source_age_coverage_max_by_sex"][sex_key]
    # `age` is continuous but the source's bands are stated in whole
    # years, where "50-54" means everyone who has turned 50 and not yet
    # 55. So match half-open on [low, high+1) -- matching inclusively on
    # [low, high] would drop every patient whose age has a fractional
    # part (e.g. 24.6 belongs to the 20-24 band, not to a gap).
    extrapolated = age >= coverage_max + 1
    band = bands[-1] if extrapolated else next(b for b in bands if b[0] <= age < b[1] + 1)
    return band, f"NFHS-5 {sex_key} {int(band[0])}-{int(band[1])}", bool(extrapolated)


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
    lipid_values = sample_lipid_panel(rng, config, sex)
    lipid_interpretations = derive_lipid_interpretations(config, lipid_values, sex)
    hba1c = sample_hba1c(rng, config, age, sex, diabetes)
    medication_treatment = sample_medication_treatment(rng, config, hypertension, diabetes)
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
