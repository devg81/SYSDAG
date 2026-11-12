# Session Log — 2026-09-25 — M2C: Indian Conditioning Implementation

**Milestone hit:** M2C — Indian Conditioning Implementation (COMPLETE).

## Objective

Implement the first working version of the Indian-conditioned synthetic
cardiovascular patient generator: demographics (age, sex, state,
urban_rural) and 5 risk factors (BMI, smoking_status, hypertension,
diabetes, hyperlipidemia), strictly scoped per `docs/PROJECT_STATE.md` —
no ECG/echo generation, no model selection/training, no AWS, no scale
beyond 100 patients.

---

## M2C-0: Evidence Verification

Used 3 parallel research forks (grouped by primary source) plus 5 direct
follow-up `WebFetch`/`WebSearch` calls for the weakest-evidenced variable
(age). Full per-variable evidence table:

| Parameter | Source | Year | Stratification found | Status |
|---|---|---|---|---|
| age | *(none — see below)* | — | none (adult-specific) | **NOT SUPPORTED** |
| sex | Census of India 2011 | 2011 | national marginal (+ urban/rural conditional, not used) | SUPPORTED |
| state | Census of India 2011 | 2011 | full 35-entry state/UT table | SUPPORTED |
| urban_rural | Census of India 2011 | 2011 | national marginal | SUPPORTED |
| BMI | ICMR-NNMS 2017-18 | 2017-18 | national, by sex only (no age) | PARTIALLY SUPPORTED |
| smoking_status | ICMR-NNMS 2017-18 | 2017-18 | national, by sex only (no age); no "former" category | PARTIALLY SUPPORTED |
| hypertension | ICMR-INDIAB-17 | 2023 | national marginal only (primary paper paywalled) | SUPPORTED (marginal only) |
| diabetes | ICMR-INDIAB-17 | 2023 | national marginal only (primary paper paywalled) | SUPPORTED (marginal only) |
| hyperlipidemia | ICMR-INDIAB-17 (sub-cohort) | 2023 | national marginal only, reduced-coverage sub-sample | PARTIALLY SUPPORTED |
| family_history_cvd | none found | — | — | **NOT SUPPORTED** |

**Age — the one genuine evidence gap.** Three separate attempts (a
dedicated research fork; direct `WebFetch` of Wikipedia's Demographics of
India page; direct `WebFetch` of MoSPI's "Women and Men in India 2022"
population-statistics PDF; a CIA World Factbook attempt that failed because
the Factbook has been sunset) found only a coarse whole-population 3-band
split (0-14: 25.68%, 15-64: 67.49%, 65+: 6.83%) attributed ambiguously to
"2021 census estimates" — India's 2021 Census was never actually conducted,
so that figure's provenance is doubtful, and it doesn't resolve to an
adult-specific (20-89) shape regardless. Rather than force an adult
distribution out of a dubiously-sourced whole-population split, age is
generated as an explicit, documented **uniform(20, 89) engineering
default** (Tier 4 fallback per `docs/INDIAN_GENERATION_STRATEGY.md` §9).
The 20-89 range itself matches ICMR-INDIAB's sampled population and M1's
existing PTB-XL 89-year age-clip convention (`docs/DECISIONS.md` D004) — a
scoping choice, not itself evidence-derived.

**Evidence Gate outcome:** every parameter classified above is either
SUPPORTED or PARTIALLY SUPPORTED and was implemented; the two NOT SUPPORTED
parameters (age shape, family_history_cvd) resolved to documented fallbacks
(uniform default; left null) rather than invented values, per M2C's §4
evidence-gate rule. No human-checkpoint STOP condition was triggered —
every gap had a defensible, documented fallback path.

Full per-variable metadata (source/year/population/geographic scope/
definition/stratification/marginal-or-conditional/transformation/
limitations) is recorded directly in `configs/indian_population.yaml`
(single source of truth, not duplicated here).

---

## Implementation

- **`schemas/patient_schema.py`**: added `RiskFactors` dataclass (`bmi`,
  `smoking_status`, `hypertension`, `diabetes`, `hyperlipidemia`);
  `Patient.risk_factors` changed from `Optional[dict]` to
  `Optional[RiskFactors]`; added `SMOKING_STATUSES` controlled vocabulary.
  `SCHEMA_VERSION` bumped `0.3` → `0.4`. Recorded as `docs/DECISIONS.md`
  D006.
- **`configs/indian_population.yaml`**: the full, traceable configuration —
  every distribution's source/year/population/geographic scope/definition/
  stratification/marginal-conditional status/transformation/limitations
  documented inline, per M2C §9's traceability requirement. State shares
  computed programmatically from Census 2011 raw population figures (not
  by hand) — verified to sum to exactly 1.0 and match the official national
  total (1,210,854,977) exactly.
- **`generation/indian_population.py`** (new top-level `generation/`
  directory, per the existing Candidate A architecture decision,
  `docs/DECISIONS.md` D001, and `CLAUDE.md`'s generation/-isolation rule):
  pure, deterministic sampling functions (`sample_age`, `sample_sex`,
  `sample_state`, `sample_urban_rural`, `sample_bmi`, `sample_smoking_status`,
  `sample_hypertension`, `sample_diabetes`, `sample_hyperlipidemia`),
  `generate_indian_attributes()` orchestrating the dependency order (age →
  sex → state → urban_rural → BMI → smoking → hypertension → diabetes →
  hyperlipidemia, per `docs/INDIAN_GENERATION_STRATEGY.md` §6 — though in
  practice only BMI/smoking end up actually sex-conditioned, since that's
  what the evidence supports), plus `valid_states()` (the single canonical
  state/UT list, referenced by validation rather than duplicated) and
  `validate_config()` (categorical-probability sanity checks).
- **`validation/structural.py`**: extended to check state membership (via
  the canonical list), `urban_rural`/`smoking_status` controlled
  vocabularies, and BMI plausibility range — all additive, M1's checks
  unchanged.
- **`validation/statistical.py`** (new): population-level validation reusing
  `scipy.stats` directly (the same library syngen's `evaluate_class.py`
  already uses for its own KS/KL comparisons — a shared-toolkit level of
  reuse, not literal function reuse, since that module's functions are
  built for `(1000,12)` ECG arrays, a different data shape). Chi-square
  goodness-of-fit for categoricals (flags low-expected-count cells rather
  than trusting a shaky p-value silently), exact binomial test for the
  three Bernoulli risk factors, one-sample KS for the uniform age
  distribution — deliberately NOT applied to BMI's mixture distribution,
  per the instruction not to blindly apply KS/KL everywhere.
- **`integration/build_patient.py`**: extended (not rewritten) — added an
  optional `indian_config` parameter (defaults to
  `configs/indian_population.yaml`, so the existing 2-arg call signature
  used throughout M1's tests keeps working unchanged), now generates
  demographics/risk_factors via `generation.indian_population` instead of
  reusing PTB-XL fields (superseding D004, exactly as that decision said it
  should be "when Stage 3 implements real synthetic demographic
  generation"). ECG metadata generation is byte-for-byte unchanged from M1.
  `provenance.generator` now states explicitly which fields are
  Indian-evidence-conditioned vs. not modeled, including the specific
  `indian_random_seed` used.
- **`integration/generate_population.py`** (new): thin orchestration
  utility — calls `build_patient()` N times, writes JSON, reports
  structural-validity/duplicate-ID summary. No new generation logic.
- **`integration/validate_population.py`** (new): runs
  `validation/statistical.py` over a generated population's JSON output,
  writes `outputs/m2c/validation_summary.json`.
- **`integration/plot_population_validation.py`** (new): one compact
  6-panel static PNG (age/sex/urban-rural/BMI/risk-factor-prevalence/
  smoking), not a dashboard — reuses matplotlib, already a syngen
  dependency.

**Two bugs found and fixed during implementation** (systematic-debugging):
1. `numpy.random.Generator.choice(p=...)` requires probabilities to sum to
   *exactly* 1.0 within a very tight tolerance; YAML-parsed floats (e.g.
   35 state shares each rounded to 6dp) drifted by ~3e-6, which numpy
   rejected outright (`ValueError: probabilities do not sum to 1`). Fixed
   by defensively normalizing (`probs / probs.sum()`) in
   `_sample_categorical()` rather than hand-tuning YAML values to force an
   exact sum — the normalization is the robust fix, not the data.
2. `validate_config()`'s own probability-sum check used too tight a
   tolerance (`1e-6`) for the same reason, causing a false-positive test
   failure. Relaxed to `1e-4` (still tight enough to catch a genuine
   data-entry mistake, loose enough for 35-entry rounding drift) and
   applied the same normalization inside `validation/statistical.py`'s
   `compare_categorical()`, which hit an identical issue with `scipy.stats.
   chisquare`'s stricter exact-sum requirement.

---

## Tests

`tests/test_m2c_indian_conditioning.py` (new, 11 tests, TDD-style,
mapped to the 11 tests specified for M2C):

1. `test_single_patient_generates_and_validates` — PASS
2. `test_required_demographic_fields_present` — PASS
3. `test_required_risk_factors_present` — PASS
4. `test_state_is_from_canonical_list` — PASS (20 sequences checked)
5. `test_urban_rural_is_controlled_value` — PASS (20 sequences checked)
6. `test_age_within_configured_bounds` — PASS (20 sequences checked)
7. `test_bmi_within_plausible_range` — PASS (20 sequences checked)
8. `test_config_probabilities_are_valid` — PASS (after the tolerance fix
   above)
9. `test_reproducibility_same_config_same_seed_same_output` — PASS
10. M1 regression — `tests/test_stage2_foundation.py`, all 5 PASS,
    unchanged
11. ECG regression — covered by
    `test_build_one_patient_is_structurally_valid`'s `signal_shape`
    check, PASS

Plus two extra tests written alongside the required 11:
`test_smoking_status_is_controlled_value`,
`test_family_history_remains_unpopulated`.

**Full suite: 16/16 passing** (`tests/test_stage2_foundation.py` +
`tests/test_m2c_indian_conditioning.py`).

---

## 10-Patient Result

`python integration/generate_population.py 10` →
`outputs/m2c/10_patients/PAT_000001.json` .. `PAT_000010.json`.

**10/10 structurally valid, 0 errors.** Manual inspection (printed compact
summary of every field): sequential IDs, 10 distinct ECG IDs all within
training folds 1-8, ages within [20,89], both sexes present, states
concentrated toward higher-population states (expected under
population-weighted sampling with only 10 draws), BMI values within
expected category ranges, no missing fields, no invalid states/urban-rural
values, no duplicate IDs, no broken ECG metadata. Diabetes was 0/10 in this
small sample — checked against the ~11.4% marginal probability
(P(zero in 10 draws) ≈ 28%, not anomalous) before moving on, rather than
assuming it was fine without checking.

---

## 100-Patient Result

`python integration/generate_population.py 100` →
`outputs/m2c/100_patients/PAT_000001.json` .. `PAT_000100.json`.

**100/100 structurally valid, 0 errors, 100/100 unique patient_ids, 100/100
unique ecg_ids.** `family_history` populated on 0/100 (correct — not
generated, per D004).

Summary statistics vs. configured values:

| Variable | Observed | Configured |
|---|---|---|
| sex | male 43%, female 57% | male 51.47%, female 48.53% |
| urban_rural | urban 33%, rural 67% | urban 31.16%, rural 68.84% |
| hypertension | 34% | 35.5% |
| diabetes | 9% | 11.4% |
| hyperlipidemia | 81% | 81.2% |
| male current-smoking | 39.5% | 51.2% |
| female current-smoking | 8.8% | 13.0% |
| distinct states observed | 19/35 | — |

All within ordinary sampling variance for n=100, except age (see next
section).

---

## Statistical Validation

`python integration/validate_population.py` →
`outputs/m2c/validation_summary.json`. Results (p-values):

| Test | p-value | Test type |
|---|---|---|
| age vs. uniform(20,89) | **0.0096** | one-sample KS |
| sex | 0.0901 | chi-square |
| urban_rural | 0.6912 | chi-square |
| state | 0.8765 (caution: 26/35 cells have expected count <5) | chi-square |
| hypertension | 0.8346 | exact binomial |
| diabetes | 0.5311 | exact binomial |
| hyperlipidemia | 0.8988 | exact binomial |
| smoking_status[male] | 0.1259 | chi-square |
| smoking_status[female] | 0.3425 | chi-square |
| bmi_category[male] | 0.6628 | chi-square |
| bmi_category[female] | 0.8842 | chi-square |

**Age's p=0.0096 flagged and investigated, not ignored.** Systematic
debugging: ran `sample_age()` directly (bypassing the CSV/ECG overhead) at
n=10,000 with independent seeds — mean came back 54.56, matching the
theoretical uniform(20,89) mean of 54.5 almost exactly, confirming the
sampler itself is unbiased. The n=100 result (observed mean 59.4, visibly
skewed older in the validation plot) is therefore ordinary sampling
variance for this specific 100-seed range (43-142), consistent with
what's expected under multiple comparisons across 11 tests (≈43% chance of
at least one p<0.05 by chance alone, even with every test correctly
calibrated). **Decision: documented honestly rather than re-generated with
a different seed to get a nicer p-value** — re-rolling until the numbers
look better would be evidence-shopping, which runs directly against this
project's whole verification standard.

The state chi-square's `assumption_note` field explicitly flags that 26 of
35 categories have expected count below 5 at n=100 — the chi-square
approximation is unreliable there, so p=0.8765 should not be over-trusted;
this will resolve naturally at larger sample sizes (1,000+/10,000+, a later
milestone).

---

## Visual Validation

`python integration/plot_population_validation.py` →
`outputs/m2c/validation_plot.png` — one 6-panel static image (age
histogram, sex bar chart, urban/rural bar chart, BMI histogram, risk-factor
prevalence bars, smoking status bar chart). Visually confirms the age
skew discussed above (visible bimodal-ish shape, more mass in 60s-80s than
a flat uniform would show) — consistent with, not contradicting, the
statistical finding.

---

## Decisions Added

- `docs/DECISIONS.md` D006 — `RiskFactors` schema formalization,
  superseding D004's demographics placeholder with Indian-conditioned
  generation.

---

## Known Limitations

1. **Age has no real Indian-evidence-based shape** — uniform(20,89)
   engineering default, documented as the weakest-evidenced parameter in
   the whole configuration. Revisit if NFHS-5's full India Report (Table
   3.1, a 600+ page PDF that exceeded practical fetch limits in this
   session) can be obtained and read directly.
2. **BMI, smoking_status are sex-conditioned only, not age-conditioned** —
   no accessible national age-band table was found for either (only
   region-scoped tables exist, and using those nationally would
   misrepresent the evidence).
3. **Hypertension, diabetes, hyperlipidemia are unconditioned national
   marginals** — no accessible age/sex-stratified table was found for any
   of the three (ICMR-INDIAB-17's primary paper is paywalled); likely such
   tables exist inside it, but this could not be confirmed.
4. **`family_history` remains entirely unpopulated** — no Indian CVD
   family-history source exists in any of the 9 datasets examined across
   M2A/M2C-0.
5. **`height_cm`/`weight_kg` are not modeled** — out of M2C's strict scope;
   BMI is generated directly as a category-then-continuous-value, not
   derived from height/weight.
6. **This is an implementation sanity check, not a representativeness
   claim.** Every statistic above is compared against the very
   distributions used to generate the data — a close match mainly confirms
   the sampler works correctly, not that the underlying evidence is itself
   representative of India's population. Precise language going forward:
   "Synthetic cardiovascular patient records conditioned using selected
   Indian population evidence," not "representative of the Indian
   population" (`CLAUDE.md` M2C §28).
7. **The ECG modality remains PTB-XL-sourced (German cohort)** — unchanged
   from M1/M2B's already-flagged limitation; Indian-conditioned
   demographics now sit next to a non-Indian ECG source in every generated
   record. Not addressed in M2C — a Stage 4 question.

---

## Human Checkpoints Encountered

**None.** Every evidence gap resolved to a documented, non-inventive
fallback (uniform default for age; left-null for family history) rather
than triggering a STOP condition. No new dependency was required (pyyaml,
numpy, scipy, matplotlib were all already present from M1/the existing
anaconda environment). No schema redesign beyond the additive changes
already anticipated in D005/the M2B strategy doc. No licensing/access
problem — every parameter used a published aggregate figure, consistent
with the fallback strategy `docs/INDIAN_GENERATION_STRATEGY.md` designed
specifically to avoid depending on restricted microdata.

---

## Next Milestone

M2D / Stage 3 continuation: `height_cm`/`weight_kg` generation, then
`medical_history`/`diagnoses`/`medications`/`labs`/`encounters`, still
without claiming clinical validity. Per `CLAUDE.md` M2C §31, explicitly
NOT starting: 1,000+/100K-scale generation, ECG waveform generation,
CardioSynth/CardioSync selection, model training, or AWS.
