"""D027 (v0.13; -jatin): hypertension and diabetes depend on age (and sex for
hypertension), following observed Indian survey curves.

Pure generator tests: no build_patient(), so they run without PTB-XL/pandas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generation.indian_population import (  # noqa: E402
    _conditional_on_exposure,
    diabetes_prevalence,
    expected_prevalence_uniform_age,
    generate_indian_attributes,
    hypertension_prevalence,
    load_config,
    sample_diabetes,
    sample_hypertension,
)

CFG = load_config()


def test_curves_hit_their_source_anchors():
    # LASI 45-49 (BMC Public Health 2022 Table 2) and NNMS 18-29 / LASI 70-74.
    assert hypertension_prevalence(CFG, 47, 0) == pytest.approx(0.3212)
    assert hypertension_prevalence(CFG, 47, 1) == pytest.approx(0.2821)
    assert diabetes_prevalence(CFG, 24) == pytest.approx(0.022)
    assert diabetes_prevalence(CFG, 72) == pytest.approx(0.234)


def test_prevalence_rises_from_young_to_old():
    for sex in (0, 1):
        assert hypertension_prevalence(CFG, 25, sex) < hypertension_prevalence(CFG, 45, sex) < hypertension_prevalence(CFG, 70, sex)
    assert diabetes_prevalence(CFG, 25) < diabetes_prevalence(CFG, 45) < diabetes_prevalence(CFG, 65)


def test_curves_are_flat_outside_anchors():
    assert hypertension_prevalence(CFG, 20, 1) == hypertension_prevalence(CFG, 22, 1)
    assert hypertension_prevalence(CFG, 89, 0) == hypertension_prevalence(CFG, 75, 0)
    assert diabetes_prevalence(CFG, 89) == diabetes_prevalence(CFG, 80)


def test_diabetes_is_not_sex_conditioned():
    # Signature takes no sex: evidence shows no consistent sex difference.
    assert diabetes_prevalence(CFG, 50) == diabetes_prevalence(CFG, 50.0)


def test_samplers_use_exactly_one_draw():
    for sampler, args in ((sample_hypertension, (60.0, 1)), (sample_diabetes, (60.0,))):
        rng_a, rng_b = np.random.default_rng(7), np.random.default_rng(7)
        sampler(rng_a, CFG, *args)
        rng_b.random()
        assert rng_a.random() == rng_b.random()  # streams still aligned


def test_expected_marginals_under_uniform_age():
    assert expected_prevalence_uniform_age(CFG, "hypertension") == pytest.approx(0.3564, abs=0.002)
    assert expected_prevalence_uniform_age(CFG, "diabetes") == pytest.approx(0.1527, abs=0.002)


def test_generated_population_shows_the_gradient():
    young, old = [0, 0, 0, 0], [0, 0, 0, 0]  # htn, dm, n_htn_eligible, n
    for seed in range(1, 6001):
        a = generate_indian_attributes(np.random.default_rng(10_000 + seed), CFG)
        age = a["demographics"]["age"]
        bucket = young if age < 35 else old if age >= 65 else None
        if bucket is None:
            continue
        bucket[0] += a["risk_factors"]["hypertension"]
        bucket[1] += a["risk_factors"]["diabetes"]
        bucket[3] += 1
    assert young[0] / young[3] < 0.20 < 0.40 < old[0] / old[3]
    assert young[1] / young[3] < 0.06 < 0.18 < old[1] / old[3]


def test_family_history_marginal_stays_calibrated_at_any_age():
    # D027 passes the age-specific diabetes prevalence into the D020 OR model.
    m = CFG["risk_factors"]["family_history"]["distribution"]["observed_marginal"]["diabetes"]
    odds_ratio = CFG["risk_factors"]["family_history"]["distribution"]["diabetes_crude_odds_ratio"]
    for age in (47.0, 72.0):
        p = diabetes_prevalence(CFG, age)
        p_if, p_not = _conditional_on_exposure(m, p, odds_ratio)
        assert p * p_if + (1 - p) * p_not == pytest.approx(m, abs=1e-6)
