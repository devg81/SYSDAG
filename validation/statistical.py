"""Statistical (population-level) validation for a generated patient
population, comparing it against the configured/reference Indian
population distributions (`configs/indian_population.yaml`).

Uses `scipy.stats` directly — the same library syngen's existing
`evaluate_class.py` uses for its KS/KL comparisons (see
`docs/syngen-codebase-analysis.md` §8) — rather than reusing that module's
specific functions, which are built for `(1000, 12)` ECG signal arrays, a
different data shape than scalar/categorical demographic fields. This is
an implementation sanity check, NOT proof of population representativeness
(`CLAUDE.md` M2C §21/§28) — statistics computed here are compared against
the very distributions used to generate the data, so a close match mainly
confirms the sampler works correctly, not that the underlying evidence is
itself representative of India.
"""

from __future__ import annotations

from typing import Any

from scipy import stats


def compare_categorical(
    observed_counts: dict[str, int], expected_probs: dict[str, float]
) -> dict[str, Any]:
    """Chi-square goodness-of-fit: observed category counts vs. the
    configured probabilities. Only meaningful when expected counts per
    category aren't too small (rule of thumb: >=5) — flagged in the
    result rather than silently trusted otherwise."""
    n = sum(observed_counts.values())
    categories = list(expected_probs.keys())
    prob_total = sum(expected_probs.values())  # defensive normalization — see generation/indian_population.py's identical rationale
    observed = [observed_counts.get(c, 0) for c in categories]
    expected = [expected_probs[c] / prob_total * n for c in categories]

    low_expected = [c for c, e in zip(categories, expected) if e < 5]
    chi2, p = stats.chisquare(f_obs=observed, f_exp=expected)

    return {
        "test": "chi-square goodness-of-fit",
        "n": n,
        "statistic": float(chi2),
        "p_value": float(p),
        "categories_with_expected_count_below_5": low_expected,
        "assumption_note": (
            "chi-square approximation is unreliable for categories with "
            "expected count < 5 -- treat the p-value cautiously if any are "
            "listed above"
            if low_expected
            else "all expected counts >= 5"
        ),
    }


def compare_bernoulli(observed_successes: int, n: int, expected_p: float) -> dict[str, Any]:
    """Exact binomial test: observed success count vs. the configured
    marginal probability."""
    result = stats.binomtest(observed_successes, n, expected_p)
    return {
        "test": "exact binomial test",
        "n": n,
        "observed_proportion": observed_successes / n,
        "expected_proportion": expected_p,
        "p_value": float(result.pvalue),
    }


def compare_uniform_continuous(values: list[float], low: float, high: float) -> dict[str, Any]:
    """One-sample Kolmogorov-Smirnov test against the configured uniform
    distribution. Appropriate here because age is explicitly generated as
    uniform(low, high) -- KS against a known target distribution is exactly
    what it's designed for (CLAUDE.md M2C §22: don't apply KS where its
    assumptions don't hold)."""
    ks_stat, p = stats.kstest(values, "uniform", args=(low, high - low))
    return {
        "test": "one-sample Kolmogorov-Smirnov (vs. configured uniform)",
        "n": len(values),
        "statistic": float(ks_stat),
        "p_value": float(p),
    }
