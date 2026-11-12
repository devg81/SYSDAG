# M3 Data Quality Report

**Population:** 1,000 synthetic patients, `outputs/m3/1000_patients/`
**Date:** 2026-09-26
**Target population:** General Indian population (`docs/DECISIONS.md` D008)

---

## 1. Generation Configuration

- `configs/base.yaml`: `random_seed: 42`, `training_folds: [1..8]`,
  `ptbxl_csv`/`scp_csv` unchanged from M1.
- `configs/indian_population.yaml`: `random_seed: 42`, unchanged from
  M2D (documentation-only edits since M2C; no distribution values
  touched — verified in the M2D-DECISION session).
- Generator: `integration/build_patient.py::build_patient()`, unchanged
  code since M2C/M2D.
- Command: `python integration/generate_population.py 1000 --out-dir
  outputs/m3/1000_patients`.
- Per-patient seed: `config["random_seed"] + sequence` for ECG selection;
  `indian_config["random_seed"] + sequence` for demographics/risk factors
  (independently seeded, both deterministic — unchanged pattern since M1).

## 2. Population Size / Generation

- **1,000 patients generated** (`PAT_000001`-`PAT_001000`).
- Wall time: **37m18s** (user CPU time only 1.7s — confirms this is
  I/O-bound, not compute-bound: the per-patient PTB-XL CSV re-read pattern
  inherited from M1 is the bottleneck). See Candidate Generator
  Improvements.
- **1,000/1,000 unique patient IDs.**

## 3. Structural Validity

| Check | Result |
|---|---|
| Total | 1,000 |
| Valid | 1,000 |
| Invalid | 0 |
| Validation errors by category | none (empty) |
| Duplicate patient IDs | 0 |
| Duplicate ECG IDs | **30 distinct `ecg_id` values reused across 2-3 patients each** (see §9) |
| Missing required fields | none |
| Invalid enum values (state/urban_rural/smoking_status) | none |
| Invalid ranges (age, BMI) | none |
| Malformed nested structures | none |
| ECG inconsistencies | 58/1,000 empty `superclasses` (expected — see §9) |

Full detail: `outputs/m3/m3_analysis_report.json`.

## 4. Demographic Distributions

| Variable | Generated | Configured | Notes |
|---|---|---|---|
| Age | mean 55.0, median 55.4, std 19.8, range [20.0, 88.9] | `uniform(20,89)` — **engineering assumption, NOT empirically validated** | Band counts 126-143 per decade, consistent with uniform |
| Sex | male 50.1%, female 49.9% | male 51.47%, female 48.53% | close |
| Urban/rural | urban 30.9%, rural 69.1% | urban 31.16%, rural 68.84% | close |
| State | 29/35 distinct observed; 6 zero-count (all <0.2% share) | Census 2011 weighted | top state (UP) 16.0% observed vs. 16.5% configured |

**n=1,000 does not validate the 2011 Census distribution itself** — it
only checks whether the sampler reproduces its own configured targets
(confirmed, see §7).

## 5. Risk-Factor Distributions

| Variable | Generated | Configured | Abs. diff |
|---|---|---|---|
| BMI (male) | mean 22.7, categories 70.9%/25.1%/4.0% | mean n/a (categorical source), 72.4%/23.3%/4.3% | ≤1.9pp per category |
| BMI (female) | mean 24.0, categories 61.3%/29.3%/9.4% | 62.4%/29.3%/8.3% | ≤1.1pp per category |
| Smoking (male) | current 50.9% | 51.2% | 0.3pp |
| Smoking (female) | current 13.6% | 13.0% | 0.6pp |
| Hypertension | 36.2% | 35.5% | 0.7pp |
| Diabetes | 11.3% | 11.4% | 0.1pp |
| Hyperlipidemia | 80.1% | 81.2% | 1.1pp |
| Family history of CVD | 0/1,000 populated | not generated (D004) | as expected |

## 6. Sampler vs. Population (A/B/C Distinction)

| Variable | A. Source evidence | B. Configured generator | C. Observed (n=1,000) |
|---|---|---|---|
| Hypertension | ICMR-INDIAB-17: 35.5% [33.8-37.3] national marginal | `Bernoulli(p=0.355)` | 36.2% |
| Diabetes | ICMR-INDIAB-17: 11.4% [10.2-12.5] | `Bernoulli(p=0.114)` | 11.3% |
| Hyperlipidemia | ICMR-INDIAB-17 sub-cohort: 81.2% | `Bernoulli(p=0.812)` | 80.1% |
| Sex | Census 2011: 943F/1000M → 48.53%/51.47% | categorical(0.5147, 0.4853) | 49.9%/50.1% |

B is set to equal A by construction in every case (this project encodes
cited figures directly, not a re-estimated approximation of them). **C is
never itself evidence of A** — it only checks that B was implemented
correctly. Full table: `outputs/m3/m3_analysis_report.json`.

## 7. Statistical Checks

All tests via `validation/statistical.py` (`scipy.stats`), against the
population's own configured targets (`outputs/m3/validation_summary.json`).

| Test | Null hypothesis | Why appropriate | Result (p) | Interpretation | Limitation |
|---|---|---|---|---|---|
| Age vs. uniform(20,89) | Sample is drawn from `uniform(20,89)` | Age is explicitly generated as uniform — KS-against-a-known-target is exactly its designed use | 0.68 | No evidence against — consistent with correct sampling | Only tests whether the SAMPLER matches its own target, not whether uniform is the right real-world shape |
| Sex | Sample proportions match 51.47%/48.53% | 2-category chi-square GoF, standard fit | 0.39 | No evidence against | n/a |
| Urban/rural | Sample proportions match 68.84%/31.16% | Same | 0.86 | No evidence against | n/a |
| State | Sample proportions match the 35-entry Census table | Chi-square GoF | 0.25 | No evidence against | Several small-share states still have expected count <5 at n=1,000 (chi-square approximation weaker there — flagged in the raw output, not hidden) |
| Hypertension/diabetes/hyperlipidemia | Sample proportion matches configured p | Exact binomial test (small-sample-exact, appropriate for a single Bernoulli rate) | 0.64 / 0.96 / 0.37 | No evidence against, all three | n/a |
| BMI category / smoking (by sex) | Sample category proportions match configured sex-specific values | Chi-square GoF, 2-3 categories | 0.60-0.89 | No evidence against, all four | n/a |

**At n=1,000, failing to reject these null hypotheses does not prove the
distributions are identical** — it means no meaningful deviation was
detected at this sample size. Conversely, a significant result at large n
would not automatically be *practically* important. Both cautions apply
here even though nothing was flagged.

## 8. Relationship / Association Audit

See `docs/M3_PATTERN_INVENTORY.md` and the session log for the full table
(13 pairs, each classified EXPLICITLY MODELED / INDEPENDENT BY DESIGN).
Summary: the two intentionally-modeled relationships (sex×BMI, p=0.0001;
sex×smoking, p<0.0001) show real, significant association, exactly as
designed. All 11 relationships the generator treats as independent showed
p>0.10 — **no evidence of unintended implementation bias.**

## 9. Edge Cases

- **58 patients (5.8%) have an ECG with no diagnostic superclass** —
  mechanically inherited from PTB-XL's own ~6.5% zero-superclass rate at
  the 50%-confidence threshold (already documented,
  `docs/INDIAN_DATA_SOURCES.md`). Classification: **valid**.
- **30 distinct ECG records reused across 2-3 patients each** (61 patients
  affected) — expected birthday-paradox effect of independent sampling
  from a ~17,470-record training-fold pool at n=1,000. Classification:
  **implementation issue** (not wrong per se, but a real scaling concern —
  see Candidate Generator Improvements).
- **24 patients with BMI at the extreme tails** (≤16.2 or ≥39.0) —
  expected tail behavior of the configured category ranges.
  Classification: **valid**.
- **6 patients aged 21-28 with hypertension, diabetes, and
  hyperlipidemia simultaneously** — arises naturally from three
  independent Bernoulli draws; nothing in the generator prevents it.
  Classification: **unsupported by current evidence** (not "impossible" —
  we simply have no Indian data on how often this combination occurs at
  that age, so its generated rate here is neither validated nor refuted).

## 10. Known Source Mismatches (carried forward, not new)

- BMI/smoking's source population (NNMS, adults 18-69) doesn't cover the
  full 20-89 generator range — ages 70-89 receive extrapolated
  probabilities (M2D-2/M2D-3 finding).
- State/UT boundaries are 2011-vintage (Telangana, J&K, Daman-Diu/DNH —
  M2D-5 finding).
- ECG source (PTB-XL) remains a German cohort, unrelated to the Indian
  demographic/risk-factor layer (M1/M2B/M2C/M2D finding, unchanged).

## 11. Recommendations

See "Candidate Generator Improvements" in the session log
(`docs/session_logs/2026-09-26_M3-1000-patient-validation.md`) for the
full, confidence-rated list. Headline items: (1) the per-patient CSV
re-read performance bottleneck must be addressed before any 10K/100K-scale
run is practical; (2) ECG record reuse across patients needs a decision
(draw without replacement? accept duplication? expand the pool?) before
scaling; (3) NNMS's already-cited urban/rural BMI stratification is a
low-effort, high-confidence improvement — the evidence already exists in
this project's own research trail and only needs wiring in.
