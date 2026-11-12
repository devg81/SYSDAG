# Session Log — 2026-09-25 — M2D: Indian Population Calibration & Quality Gate

**Milestone hit:** M2D — Indian Population Calibration & Quality Gate
(COMPLETE).

## 1. Objective

Answer: "Are the assumptions currently feeding our Indian synthetic
patient generator defensible enough to scale?" Audit the 7 flagged M2C
limitations (age, BMI, smoking, hypertension, diabetes, hyperlipidemia,
state/urban-rural), fix only what evidence justifies, and explicitly
surface anything that can't be resolved rather than inventing an answer.
Family history stayed out of scope, per instructions.

## 2. M2C Baseline

Read directly from this session's own prior state (not re-derived):
`configs/indian_population.yaml`, `generation/indian_population.py`,
`validation/{structural,statistical}.py`, `integration/build_patient.py`,
`tests/test_m2c_indian_conditioning.py`, and
`docs/session_logs/2026-09-25_M2C-indian-conditioning.md`. M2C's own
evidence table was treated as the audit's starting point, per instructions
not to repeat completed analysis.

## 3. Evidence Reviewed

### M2D-1 — Age (new research)

Beyond M2C's original 4 attempts, tried 6 more angles this session: UN
World Population Prospects (portal located, but granular 5-year-band data
is behind an interactive JS chart, not fetchable as text), India's Sample
Registration System Statistical Report 2020 (official Registrar-General
source, direct PDF link found at `censusindia.gov.in` — fetch failed on an
**SSL certificate error**, a tooling problem, not a content problem, worth
retrying with a different method), PopulationPyramid.net (JS-rendered,
same problem as WPP), Worldometers (same), StatisticsTimes (no
finer-than-headline table found), and dataforindia.com (**succeeded** —
found a properly-sourced 3-band figure from India's Registrar General
population projections, Census-2011-based, explicitly transparent about
being a projection: 0-14 24%, 15-59 65%, 60+ 11%, as of ~2026).

**Quantified rejection of the new figure** (the key finding of this
audit): converting "15-59"/"60+" into our 20-89 range requires assuming
uniform density within the 45-year 15-59 band. Computed directly (not
asserted): this implies a 20-59/60-89 split of **84%/16%**, versus
`uniform(20,89)`'s **57%/43%**. That's not a minor correction — it would
cut the 60-89 share nearly in half, in exactly the age band where
cardiovascular risk concentrates, based on an assumption (flat density
across 45 years) known to be false for any real population pyramid.
**Decision: kept `uniform(20,89)`** — recorded as `docs/DECISIONS.md` D007.

### M2D-2 — BMI

Source provides categorical prevalence (%overweight, %obese) by sex only
— confirmed, not a continuous distribution, not age-conditioned. Current
implementation (category draw from evidence-backed sex-specific
probabilities, then within-category uniform continuous sampling) audited
and judged reasonable: the category assignment is real evidence; the
within-category shape has zero evidence either way, so uniform is the
*least*-assumption-laden choice, not an arbitrary one — a peaked
distribution would itself be inventing shape information we don't have.
**New finding not previously flagged**: NNMS's surveyed population is
adults 18-69, but the config applies its probabilities to the full
20-89 generator range — patients 70-89 get extrapolated values. Documented
in the config, not fixed (no alternative source exists for that slice).
**Verdict: KEEP**, documentation strengthened.

### M2D-3 — Smoking

Re-checked the current/never mapping against the actual source figures:
confirmed `current` correctly maps to NNMS's "current tobacco use (any)"
headline figure (51.2% men / 13.0% women), not the narrower "daily smoked"
figure (13.6%/0.7%) which would have understated prevalence. Same
18-69-vs-20-89 age-range mismatch as BMI, same reasoning, documented.
**Verdict: KEEP**, mapping confirmed correct, documentation strengthened.

### M2D-4 — Hypertension / Diabetes / Hyperlipidemia

Re-confirmed: no accessible age/sex-stratified table exists for any of
the three (ICMR-INDIAB-17's primary paper remains paywalled). The current
unconditioned-marginal implementation is the **correct** reading of
available evidence, not a shortcut taken for convenience — there is
nothing to condition on that we can actually cite. No complexity added.
P(condition | age, sex) recorded explicitly as a future modelling
opportunity (tier E), contingent on the paper becoming accessible.
**Verdict: KEEP**, all three.

### M2D-5 — State / Urban-Rural

Confirmed the state distribution is population-weighted (not
equal-probability per state, which would have been wrong) — no error
there. Two real findings surfaced:
1. **Boundary staleness**: the 35-entry state/UT table uses 2011
   administrative boundaries. Telangana (created 2014) doesn't appear
   separately; "Jammu and Kashmir" predates its 2019 split into two UTs;
   "Daman and Diu" and "Dadra and Nagar Haveli" predate their 2020 merger.
   This is a *boundary* problem, distinct from the already-documented
   *count staleness* (15-year-old population figures) — not fixed (no
   current-boundary Census-quality table was located), documented.
2. state and urban_rural are sampled **independently** — a real joint
   Census table exists but wasn't pulled in (unchanged from M2C, still
   judged not worth the complexity for now).

### M2D-6 — Population Target Definition

**The most important finding of this audit.** The generator currently has
**no single consistent target population** — it stitches together three
different source populations per patient:
- `demographics.sex/state/urban_rural` ← Census 2011's **general**
  population (all ages)
- `risk_factors.bmi/smoking_status` ← ICMR-NNMS's surveyed **adults
  18-69**
- `risk_factors.hypertension/diabetes/hyperlipidemia` ← ICMR-INDIAB's
  surveyed **adults 20+** (the best match to our 20-89 scope)

No existing project document (`CLAUDE.md`, `docs/PROJECT_STATE.md`,
`docs/INDIAN_GENERATION_STRATEGY.md`) explicitly defines whether this
generator targets "general Indian population," "Indian adult population,"
or "Indian cardiovascular-risk population." Per instructions, this
ambiguity is **recorded, not resolved** —
`configs/indian_population.yaml`'s new
`population.target_population_ambiguity_M2D6` field, and here.

## 4. Findings Summary

| Parameter | Current approach | Evidence | Finding | Action |
|---|---|---|---|---|
| Age | `uniform(20,89)` | NOT SUPPORTED | Better-sourced 3-band figure found but quantitatively rejected (84/16 vs 57/43 split, wrong direction for CVD risk) | KEEP, documented (D007) |
| BMI | Category (sex) → uniform-in-range | PARTIALLY SUPPORTED | Reconstruction is defensible; NNMS 18-69 extrapolated to 20-89 (new finding) | KEEP, documented |
| Smoking | Category (sex) | PARTIALLY SUPPORTED | Mapping re-verified correct; same age extrapolation | KEEP, documented |
| Hypertension | `Bernoulli(0.355)` | SUPPORTED (marginal) | Unconditioned marginal confirmed correct, not a shortcut | KEEP |
| Diabetes | `Bernoulli(0.114)` | SUPPORTED (marginal) | Same | KEEP |
| Hyperlipidemia | `Bernoulli(0.812)` | PARTIALLY SUPPORTED | Same; reduced-coverage caveat reiterated | KEEP |
| State | Census 2011 weighted, 35 entries | SUPPORTED (marginal) | Population-weighting correct; boundaries are 2011-vintage (Telangana/J&K/Daman-Diu, new finding) | KEEP, documented |
| Urban/rural | Census 2011 marginal | SUPPORTED (marginal) | Sampled independently of state (unchanged) | KEEP, documented |
| *(population target)* | — | — | **No single consistent target population across sources** | RECORDED as open question, not resolved |

## 5. Changes Made

**Code (behavior): NONE.** No sampling logic, distribution values, or
generation-order changed — every audit concluded the existing
implementation was already the evidence-correct choice.

**Configuration/documentation (metadata only):**
- `configs/indian_population.yaml`: added
  `population.target_population_ambiguity_M2D6` (the M2D-6 finding);
  added `evidence_tier` fields (A/B/C/D/E classification per M2D-12) to
  every parameter; substantially expanded `age`'s `transformation`/
  `limitations` with the new research and quantified rejection reasoning;
  added the NNMS age-range-mismatch finding to `bmi`/`smoking_status`;
  added the boundary-staleness finding to `state`; added
  general-vs-adult-population cross-references to `sex`/`urban_rural`.
- `docs/DECISIONS.md`: D007 (keep uniform age, with full reasoning).
- New diagnostic script: `integration/sampler_check.py` (M2D-10, isolated
  10,000-draw sampler-correctness checks — not patient generation).

## 6. Tests

Full suite re-run after the config changes: **16/16 passing**
(`tests/test_stage2_foundation.py` + `tests/test_m2c_indian_conditioning.py`,
unchanged from M2C since no sampling logic changed). No new tests were
needed — M2C's existing tests already cover age bounds, BMI validity,
smoking category validity, state validity, urban/rural validity, and
reproducibility; M2D didn't change what any of them assert.

## 7. 100-Patient Validation (Regression Check)

Regenerated at `outputs/m2d/100_patients/` (same config, same seeds).
**Diff against the M2C baseline** (`outputs/m2c/100_patients/`):
`demographics` — 0/100 differ; `risk_factors` — 0/100 differ; `ecg` —
14/100 differ, but investigated and confirmed to be **superclass list
ORDER only** (e.g. `['STTC','HYP']` vs `['HYP','STTC']`), not content —
inherited from syngen's `build_label_map()` using a Python `set()`, whose
iteration order is hash-seed-dependent across separate process runs. This
is pre-existing behavior in reused code, unrelated to M2D, and out of
scope to fix here (M2D explicitly excludes ECG work) — noted as a minor
future cleanup opportunity (sorting the list in
`ingestion/ptbxl_source.py` would fix it without touching syngen itself),
not acted on.

**Confirms**: M2D's changes were purely additive documentation with zero
behavioral impact, exactly as intended. Since demographics/risk_factors
output is byte-identical to M2C's, the M2C statistical-validation numbers
(`outputs/m2c/validation_summary.json`) remain the accurate description of
this population — not recomputed here as they'd be identical.

## 8. 10,000-Draw Sampler Checks

`python integration/sampler_check.py` — isolated sampling-function calls
only (no Patient records, no ECG, no patient IDs; independent large seeds
200,000+). **This tests sampler correctness, not population
representativeness** — a close match confirms the code correctly
reproduces its configured targets, nothing more.

| Variable | Observed (n=10,000) | Configured |
|---|---|---|
| age (mean) | 54.465 | 54.5 |
| sex (male%) | 51.25% | 51.47% |
| urban_rural (urban%) | 30.90% | 31.16% |
| state (top 3) | UP 15.68%, Maharashtra 9.41%, Bihar 9.19% | UP 16.50%, Maharashtra 9.28%, Bihar 8.60% |
| BMI (male mean) | 22.73 | — |
| BMI (female mean) | 23.69 | — |
| smoking (male current%) | 50.64% | 51.20% |
| smoking (female current%) | 13.42% | 13.00% |
| hypertension | 36.03% | 35.5% |
| diabetes | 11.53% | 11.4% |
| hyperlipidemia | 81.12% | 81.2% |

All within normal sampling noise at n=10,000. **No implementation bias
detected.**

## 9. Remaining Limitations

1. Age has no real Indian-evidence-based shape (unchanged from M2C,
   re-confirmed after substantive additional research). SRS Statistical
   Report 2020 and NFHS-5's full report remain the two live leads,
   blocked on access-method problems (SSL cert error; PDF size), not
   confirmed dead ends.
2. BMI/smoking are sex-conditioned only; both extrapolate NNMS's 18-69
   sampled range across the generator's full 20-89 range (newly
   documented, not newly created).
3. Hypertension/diabetes/hyperlipidemia remain unconditioned marginals —
   confirmed as evidence-correct, not a shortcut.
4. State/urban_rural represent the **general** Census population (all
   ages), not an adult-specific one — part of the M2D-6 population-target
   ambiguity.
5. State/UT boundaries are 2011-vintage, not current (Telangana, J&K
   reorganization, Daman-Diu/Dadra-Nagar-Haveli merger) — newly
   identified this session.
6. **No single consistent target population** across the generator's
   three source populations (general Census vs. NNMS-surveyed adults
   18-69 vs. INDIAB-surveyed adults 20+) — the central open question of
   this audit, recorded, not resolved.
7. ECG superclass list ordering has pre-existing, harmless
   run-to-run non-determinism (Python `set()` iteration) — noted, not
   fixed (out of M2D's scope).
8. Family history remains out of scope (per instructions) and unpopulated
   (unchanged from M1/M2C).
9. ECG remains PTB-XL (German cohort)-sourced — unchanged, carried
   forward from M1/M2B/M2C.

## 10. Decisions

- `docs/DECISIONS.md` D007 — keep `uniform(20,89)` for age, full
  reasoning recorded, two live leads (SRS, NFHS-5) named for future
  follow-up rather than declared exhausted.

No other new decisions — every other audit concluded "keep, document
better," which isn't a new architectural decision, just confirmation of
M2C's existing ones.

## 11. Recommendation for M3

**Before scaling generation volume**, the population-target ambiguity
(§3, M2D-6) should get an explicit human decision — it determines whether
"scaling" means more of an internally-inconsistent amalgam, or whether the
demographic layer needs to be re-scoped first (e.g., restricting Census
figures to an adult-only re-derivation, or explicitly accepting the
amalgam as a documented limitation and moving on). This isn't a blocker
in the sense of stopping all progress — M2C/M2D's outputs are internally
valid and clearly documented — but it *is* the kind of decision that gets
more expensive to revisit the more patients exist under the current
assumptions. Recommend raising it as an explicit question before M3
begins, rather than silently carrying it into a 1,000+/100K-scale run.

Secondary recommendation: retry SRS Statistical Report 2020 access (the
SSL error looks like a fixable tooling issue, not a genuine access
restriction) before concluding age evidence doesn't exist — it remains
the single most promising unresolved lead in the entire evidence base.
