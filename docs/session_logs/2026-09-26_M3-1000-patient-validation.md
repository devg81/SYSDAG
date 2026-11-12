# Session Log — 2026-09-26 — M3: 1,000-Patient Population Validation & Pattern Analysis

**Milestone hit:** M3 — 1,000-Patient Population Validation & Pattern
Analysis (COMPLETE).

## 1. Objective

Generate a controlled 1,000-patient development population with the
current (unmodified) generator and determine: does it behave according to
its configured distributions; are all patients structurally valid; are
there anomalies; which relationships are visible vs. not modeled; what
must improve before scaling toward 100K. Explicitly a validation/analysis
milestone — no generator optimization, no re-rolling for nicer numbers, no
invented medical relationships.

## 2. Configuration

`configs/base.yaml` (`random_seed: 42`) + `configs/indian_population.yaml`
(`random_seed: 42`), both unchanged since M2D's documentation-only edits
(verified: distribution values and `evidence_tier` fields untouched).
Generator code (`generation/indian_population.py`,
`integration/build_patient.py`) unchanged since M2C.

## 3. Generation

`python integration/generate_population.py 1000 --out-dir
outputs/m3/1000_patients`. **1,000 patients generated, 1,000/1,000 unique
patient IDs (`PAT_000001`-`PAT_001000`), 1,000/1,000 structurally valid.**

**Wall time: 37m18s** (user CPU time only 1.7s) — confirms the run is
I/O-bound: `build_patient()` re-reads the full PTB-XL CSV (via
`build_label_map()` and a separate `pd.read_csv` in
`ingestion/ptbxl_source.py`) on every single patient. This did not matter
at n=10/100 but is now a clear, measured scaling blocker — at this rate,
100,000 patients would take on the order of **60+ hours**. See Candidate
Generator Improvements.

## 4. Structural Validation

1,000/1,000 valid, 0 invalid, 0 validation errors, 0 duplicate patient
IDs, 0 missing required fields, 0 invalid enum values, 0 invalid ranges,
0 malformed structures. Two things surfaced by ECG-specific checks (not
schema failures — both structurally valid, both worth noting):
- 58/1,000 (5.8%) have an empty `ecg.superclasses` list.
- 30 distinct `ecg_id` values are each reused across 2-3 different
  patients (61 patients affected).

Full detail and per-category counts: `docs/M3_DATA_QUALITY_REPORT.md` §3,
`outputs/m3/m3_analysis_report.json`.

## 5. Demographic Results

| Variable | Result |
|---|---|
| Age | mean 55.0, median 55.4, std 19.8, p25/p50/p75 = 38.4/55.4/71.6, range [20.0, 88.9], band counts 126-143/decade |
| Sex | male 50.1%, female 49.9% (configured 51.47%/48.53%) |
| Urban/rural | urban 30.9%, rural 69.1% (configured 31.16%/68.84%) |
| State | 29/35 distinct observed; 6 zero-count (Andaman & Nicobar, Dadra & Nagar Haveli, Daman & Diu, Lakshadweep, Nagaland, Sikkim — all <0.2% configured share, zero-count is expected, not anomalous) |

Age's evidence status is restated explicitly here per instructions: **this
is an engineering assumption (`uniform(20,89)`), not an empirically
validated Indian age distribution** (`docs/DECISIONS.md` D007).

n=1,000 does not itself validate the 2011 Census distribution or any
source figure — it only checks the sampler against its own configured
targets (confirmed in §8).

## 6. Risk-Factor Results

| Variable | Observed | Configured | Abs. diff | Sampling variation? |
|---|---|---|---|---|
| BMI (male) categories | 70.9%/25.1%/4.0% | 72.4%/23.3%/4.3% | ≤1.9pp | Yes (chi-square p=0.60) |
| BMI (female) categories | 61.3%/29.3%/9.4% | 62.4%/29.3%/8.3% | ≤1.1pp | Yes (p=0.66) |
| Smoking (male) current% | 50.9% | 51.2% | 0.3pp | Yes (p=0.89) |
| Smoking (female) current% | 13.6% | 13.0% | 0.6pp | Yes (p=0.68) |
| Hypertension | 36.2% | 35.5% | 0.7pp | Yes (binomial p=0.64) |
| Diabetes | 11.3% | 11.4% | 0.1pp | Yes (p=0.96) |
| Hyperlipidemia | 80.1% | 81.2% | 1.1pp | Yes (p=0.37) |
| Family history of CVD | 0/1,000 | not generated | — | n/a (correct, by design) |

**No evidence of implementation bias in any risk factor** — every
deviation is well within what the corresponding statistical test says is
plausible sampling variation.

## 7. Relationship Analysis

13 pairs analyzed (`age×sex`, `age×BMI`, `sex×BMI`, `sex×smoking`,
`sex×hypertension/diabetes/hyperlipidemia`,
`age×hypertension/diabetes/hyperlipidemia`, `BMI×hypertension/diabetes`,
`smoking×hypertension`), each classified before interpretation:

| Relationship | Classification | Measure | Value | p |
|---|---|---|---|---|
| age × sex | INDEPENDENT BY DESIGN | point-biserial | 0.052 | 0.10 |
| age × BMI | INDEPENDENT BY DESIGN | Pearson r | -0.031 | 0.33 |
| **sex × BMI** | **EXPLICITLY MODELED** | point-biserial | 0.120 | **0.0001** |
| **sex × smoking** | **EXPLICITLY MODELED** | Cramér's V | 0.396 | **<0.0001** |
| sex × hypertension | INDEPENDENT BY DESIGN | point-biserial | -0.003 | 0.93 |
| sex × diabetes | INDEPENDENT BY DESIGN | point-biserial | -0.021 | 0.50 |
| sex × hyperlipidemia | INDEPENDENT BY DESIGN | point-biserial | 0.017 | 0.60 |
| age × hypertension | INDEPENDENT BY DESIGN | point-biserial | -0.035 | 0.27 |
| age × diabetes | INDEPENDENT BY DESIGN | point-biserial | 0.009 | 0.77 |
| age × hyperlipidemia | INDEPENDENT BY DESIGN | point-biserial | -0.021 | 0.51 |
| BMI × hypertension | INDEPENDENT BY DESIGN | point-biserial | 0.015 | 0.64 |
| BMI × diabetes | INDEPENDENT BY DESIGN | point-biserial | -0.0003 | 0.99 |
| smoking × hypertension | INDEPENDENT BY DESIGN | Cramér's V | 0.011 | 0.73 |

**Exactly the two intentionally-modeled relationships show significant
association; every relationship the generator treats as independent shows
p>0.10.** This is the clean, expected result — it confirms the generator
implements what it was designed to implement, nothing more and nothing
less. Absence of a relationship here does **not** prove the real
population lacks it — it only reflects what this generator currently
models. Full inventory with A/B/C/D categorization:
`docs/M3_PATTERN_INVENTORY.md`.

## 8. Statistical Analysis

Full null-hypothesis/appropriateness/result/interpretation/limitation
table: `docs/M3_DATA_QUALITY_REPORT.md` §7. Headline: every distribution
tested (age vs. uniform, sex, urban/rural, state, hypertension, diabetes,
hyperlipidemia, BMI category by sex, smoking by sex) came back consistent
with its configured target (p-values 0.25-0.96) — **no implementation
bias detected at n=1,000.** Notably, age's KS test — which flagged
p=0.0096 at M2C's n=100 — now shows **p=0.68 at n=1,000**, exactly
confirming that finding was sampling noise, not a defect, as M2C's own
investigation predicted.

## 9. Edge Cases

See `docs/M3_DATA_QUALITY_REPORT.md` §9 for full detail and
classifications. Summary: 58 empty-superclass ECGs (valid, inherited from
PTB-XL), 30 reused ECG records across 61 patients (implementation issue,
scaling concern), 24 extreme-tail BMI values (valid), 6 young (21-28)
patients with all three major risk factors simultaneously (unsupported by
current evidence, not impossible).

## 10. Visual Validation

`outputs/m3/m3_validation_plot.png` — 6-panel static comparison (age
histogram labeled as an engineering-assumption distribution; sex,
generated-vs-configured bars; top-10 states; BMI histogram; smoking
status; risk-factor prevalence generated-vs-configured bars). No
misleading scales — bar charts share consistent axes within each panel;
percentage panels use 0-100 fixed y-limits.

## 11. Pattern Inventory

Full document: `docs/M3_PATTERN_INVENTORY.md` — 8 intentionally-encoded
patterns (A), 4 mechanically-emerging patterns (B), 7 not-currently-
represented patterns (C, including one — urban/rural×BMI — where evidence
already exists but wasn't wired in), 5 patterns requiring real evidence
before consideration (D).

## 12. Candidate Generator Improvements

Per M3-13, **nothing below was implemented this session** — documented
for a future decision only.

1. **Issue:** Per-patient CSV re-read makes generation I/O-bound and
   unscalable (37min/1,000 patients measured; ~60+ hours projected for
   100K). **Evidence:** measured wall-clock vs. user-CPU time this
   session. **Impact:** blocks any 10K/100K run without a fix. **Proposed
   change:** cache `build_label_map()`'s parsed label map and the
   demographics CSV read once per process instead of once per patient.
   **Confidence:** high (clear, measured cause). **Human review required:**
   recommended before implementing, since it touches the reused
   `ingestion/ptbxl_source.py` adapter, not just the Indian-population
   layer.
2. **Issue:** ECG records are drawn independently per patient, causing
   duplicate ECG signals across distinct synthetic patients at increasing
   rates as population size grows (birthday-paradox effect against a
   ~17,470-record pool). **Evidence:** 30 duplicate `ecg_id`s observed at
   n=1,000, mathematically predicted (~28.6 expected). **Impact:** at
   100K scale, duplication would be severe (pool exhaustion — more
   patients than available unique training-fold records). **Proposed
   change:** decide policy (draw without replacement per class/fold until
   exhausted, then decide a fallback; or explicitly accept duplication as
   a documented limitation for now). **Confidence:** high on the finding,
   medium on which policy is right. **Human review required:** yes — this
   is a design decision, not a pure bug fix.
3. **Issue:** NNMS's urban/rural BMI stratification (overweight urban
   42.5%/rural 18.0%; obese urban 11.2%/rural 3.7%) was found during
   M2C-0's own research but never incorporated into
   `configs/indian_population.yaml` or the sampler. **Evidence:** this
   project's own prior research (§M2C-0 fork notes); re-confirmed absent
   from the current config in this session. **Impact:** a real, national,
   already-cited relationship is currently silently treated as
   INDEPENDENT BY DESIGN when it needn't be. **Proposed change:** add
   urban/rural-conditioning to BMI (and re-verify whether the same paper
   gives a usable smoking urban/rural split). **Confidence:** high
   (evidence already in hand, no new research needed). **Human review
   required:** low-risk, but still a generator behavior change, so
   recommend a lightweight review before implementing, not silent
   auto-adoption.
4. **Issue:** 2011-vintage state/UT boundaries (Telangana, J&K, Daman-Diu/
   Dadra-Nagar-Haveli) don't match India's current administrative map.
   **Evidence:** M2D-5 audit. **Impact:** low for aggregate distribution
   validity, but real for anyone expecting current state names. **Proposed
   change:** locate a current-boundary Census-quality population table
   (not found in M2C/M2D's research passes) and remap. **Confidence:**
   medium (fix is clear once a source exists; the source itself hasn't
   been found). **Human review required:** yes, if/when a source is found.

## 13. Remaining Limitations

Carried forward, none newly introduced by this milestone: age has no
real evidence-based shape (D007); BMI/smoking extrapolate NNMS's 18-69
sampled range to the full 20-89 generator range; hypertension/diabetes/
hyperlipidemia remain unconditioned marginals; state/UT boundaries are
2011-vintage; ECG remains PTB-XL (German cohort)-sourced; family history
unpopulated. Newly measured (not newly created): the I/O performance
bottleneck and ECG-reuse-at-scale issue (§12).

## 14. Tests

Full suite (`tests/test_stage2_foundation.py` +
`tests/test_m2c_indian_conditioning.py`) re-run after the 1,000-patient
generation and analysis. See the tool-call record for the exact pass
count logged this session (expected 16/16, unchanged — no generator code
was modified). No new tests were added: M3 is an analysis milestone over
already-covered generation code, and the one code change made
(`integration/validate_population.py`'s output-path fix, §Correction
below) is analysis tooling, not generator behavior, and doesn't need new
schema/sampling tests.

**Correction made during this session (tooling, not generator):**
`integration/validate_population.py` had a hardcoded output path
(`outputs/m2c/validation_summary.json`) left over from M2C. Running it
against the M3 population silently overwrote M2C's original validation
summary. Caught immediately, fixed by deriving the output path from the
input directory's own milestone folder, and both summaries were
regenerated (M2C's re-confirmed byte-identical to its original recorded
p-values, confirming no data was actually lost — just briefly
overwritten on disk).

## 15. Recommendation for M4

M3's baseline is clean: 1,000/1,000 structurally valid, no implementation
bias detected in any distribution or relationship, all deviations
explained as ordinary sampling variation. Two findings should be resolved
**before** scaling toward 10K/100K, not left for later:
1. The I/O performance bottleneck (§12 item 1) — at the measured rate,
   100K patients would take multiple days.
2. The ECG-reuse policy (§12 item 2) — needs a decision before scale
   makes duplication severe rather than occasional.

Item 3 (urban/rural×BMI) is a good candidate for the *next* small
implementation step regardless of scaling, since the evidence is already
in hand and the change is well-scoped. Item 4 (state boundaries) can wait
for a source to be found.

**Recommend:** review this session's Candidate Generator Improvements
list explicitly, decide which to implement, then move to M4 (which should
include implementing the approved improvements before any 10K+ run,
per this project's progressive-scaling principle — `CLAUDE.md` §27/§7).
