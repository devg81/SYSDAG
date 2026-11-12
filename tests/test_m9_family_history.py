"""D020 -- family history (LASI observed 45+, calibrated parent simulation 20-44)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import (
    _conditional_on_exposure,
    diabetes_prevalence,
    family_history_marginals,
    load_config,
    sample_family_history,
    validate_config,
)

CONFIG = load_config()
OBSERVED = CONFIG["risk_factors"]["family_history"]["distribution"]["observed_marginal"]


def test_config_is_valid():
    assert validate_config(CONFIG) == []


@pytest.mark.parametrize("age", [45.0, 60.0, 89.0])
def test_45_plus_uses_lasi_observed_marginals(age):
    marginals, derivation = family_history_marginals(CONFIG, age)
    assert derivation == "lasi_observed_45_plus"
    assert marginals == OBSERVED


def test_calibration_makes_the_age_45_boundary_continuous():
    # At 44.9 both parents are already 60+, the band the 45+ anchor
    # calibrates -- so the model must reproduce the observed figure there.
    below, derivation = family_history_marginals(CONFIG, 44.9)
    assert derivation == "parent_simulation_calibrated"
    for condition, observed in OBSERVED.items():
        assert below[condition] == pytest.approx(observed, abs=1e-9)


def test_20_44_is_non_decreasing_with_age_and_below_the_45_plus_anchor():
    for condition in OBSERVED:
        values = [family_history_marginals(CONFIG, a)[0][condition] for a in np.arange(20, 45, 0.5)]
        assert values == sorted(values)
        assert values[0] < OBSERVED[condition]


def test_20_44_average_stays_under_the_carrs_urban_cross_check():
    # CARRS (PMC9453056): diabetes 22.2%, heart disease 7.1% + stroke 1.9%.
    ages = np.arange(20, 45, 0.1)
    mean = {c: np.mean([family_history_marginals(CONFIG, a)[0][c] for a in ages]) for c in OBSERVED}
    assert mean["diabetes"] <= 0.222
    assert mean["cardiovascular_disease"] <= 0.071 + 0.019


@pytest.mark.parametrize("m,p,r", [(0.1433, 0.114, 3.80), (0.05, 0.3, 2.0), (0.4, 0.05, 6.0)])
def test_conditioning_preserves_the_marginal_and_hits_the_odds_ratio(m, p, r):
    q1, q0 = _conditional_on_exposure(m, p, r)
    assert p * q1 + (1 - p) * q0 == pytest.approx(m)
    assert (q1 / (1 - q1)) / (q0 / (1 - q0)) == pytest.approx(r)


def test_sampled_rates_match_marginals_and_diabetics_report_more_family_history():
    rng = np.random.default_rng(0)
    # D027 (v0.13; -jatin): diabetes must be drawn at the SAME age-specific
    # prevalence the family-history model now conditions on.
    p_dm = diabetes_prevalence(CONFIG, 60.0)
    draws = [(d := bool(rng.random() < p_dm), sample_family_history(rng, CONFIG, 60.0, d)) for _ in range(40_000)]
    fh_dm = np.array([fh["diabetes"] for _, fh in draws])
    fh_cvd = np.array([fh["cardiovascular_disease"] for _, fh in draws])
    diabetic = np.array([d for d, _ in draws])
    assert fh_dm.mean() == pytest.approx(OBSERVED["diabetes"], abs=0.006)
    assert fh_cvd.mean() == pytest.approx(OBSERVED["cardiovascular_disease"], abs=0.006)
    # LASI: 27.8% diabetes with vs 9.2% without family history -- the
    # reverse direction, P(fh | diabetic) > P(fh | not), must show up.
    assert fh_dm[diabetic].mean() > fh_dm[~diabetic].mean() + 0.15
