# Schema v0.10 change report — response to the 2026-11-12 review

Decision record: `docs/DECISIONS.md` D022. Raw numbers:
`docs/V010_REVIEW_COHORT_CHECKS.json`, which `python -m integration.review_v010_report 5000`
regenerates. Regression tests: `tests/test_v010_review_fixes.py`. 187/187 tests pass.

**Not done yet:** the frozen 100K dataset is still v0.9. Regenerating it at v0.10
takes about 2 hours and needs your go-ahead. Every number below comes from 5,000
records regenerated in memory, using the same sequence numbers as v0.9.

## Per issue

### 1. Lipids (HIGH) — fixed
- **Root cause confirmed:** TC, TG and HDL were drawn independently (r(lnTG,HDL) = −0.03 in v0.9).
- **Where the LDL = 30.0 came from:** a `clip_range: [30, 300]` applied after the
  Friedewald step. It put 7.26% of records at exactly 30.0, all with a stored LDL
  different from Friedewald. You were right that this contradicted "never independently set".
- **What I did:**
  - TC, ln(TG) and HDL are now drawn from one trivariate normal.
  - Each mean is solved so the INDIAB-17 category rate is hit exactly (the same tier-A rates as before).
  - SDs come from the ICMR-INDIAB phase I lipid paper (PMC4016101): TC 40, HDL 12,
    ln(TG) 0.477 (from GM 116 and 29.5% ≥150). These replace the uniform within-category shapes.
  - LDL is still Friedewald and is never clipped. A panel with LDL < 30, TG > 400 or
    TC/HDL outside plausible bounds is rejected and redrawn whole. If the retry budget
    runs out, the code raises an error instead of clamping.
- **Correlations:** no Indian coefficient exists (searched; PMC4016101 reports none).
  - The three latent correlations (TC–lnTG 0.45, lnTG–HDL −0.40, TC–HDL 0.40) are
    fitted to three Indian targets the independent model missed: 81.2% dyslipidaemia,
    20.9% LDL ≥130, and an LDL SD of 32.
  - The fit is flat along a ridge. Within it, I chose the pair that gives the usual
    moderate negative TG–HDL link. That tie-break is my judgement and is labelled tier C.
- **TG > 400:** these panels are not generated (about 0.6% of the fitted distribution is
  lost). Alternative left open: LDL = null with reason "Friedewald invalid".
- **Alternatives rejected:**
  - Sampling LDL and deriving TC breaks protected item 1.
  - INDIAB-17 joint tables don't exist publicly.
  - Copula over the old uniform marginals: fitting it needed an unrealistic TC–TG r = 0.8.

| Check (5,000 records) | v0.9 | v0.10 | Target / literature |
|---|---|---|---|
| r(lnTG, HDL) | −0.03 | **−0.36** | moderate negative, typically reported −0.3 to −0.45 (non-Indian, unverified in this session) |
| r(TG, HDL) raw | −0.05 | −0.33 | — |
| r(TC, LDL) | 0.91 | 0.94 | strong positive (LDL is most of TC) |
| LDL exactly 30.0 | 7.26% | **0%** | 0 |
| LDL ≠ Friedewald | 7.18% | **0%** | 0 |
| LDL < 0 | 0% | 0% | 0 |
| Most common single LDL value | 30.0 (7.26%) | 110.4 (0.26%) | no pile-up |
| LDL ≥130 | 27.8% | 22.8% | 20.9% |
| NCEP dyslipidaemia from panel | 83.3% | 80.9% | 81.2% |
| TC ≥200 / TG ≥150 / low HDL | 24.4 / 30.0 / 68.4% | 25.1 / 31.3 / 65.2% | 24.0 / 32.1 / 66.9% |

### 2. BP above the NFHS-5 age range (HIGH) — improved, still low confidence
- **What changed:** above coverage (men > 54, women > 49), mean SBP now follows NFHS-5's
  own linear trend, fitted on bands from age 35 up: +0.34 mmHg/yr for men, +0.68 for women.
  Mean DBP and both SDs stay at the oldest band.
- **Why DBP stays flat:** NFHS-5's own DBP gains already shrink toward zero, and the DBP
  plateau after 50–60 is well documented in non-Indian cohorts (Franklin 1997). That
  is a non-Indian prior, labelled as such in the config.
- **Pulse pressure** now widens with age (table below). Your narrow-PP examples are gone:
  PAT_000013 is now 125/77 (PP 48) and PAT_078682 is 159/75 (PP 84).
- **New field:** `blood_pressure.confidence` = "low" on every extrapolated record, so
  downstream users can filter them out.
- **SBP/DBP correlation:** already modelled (r = 0.7255, derived from Indian variances).
  The v0.9 provenance text wrongly said otherwise; that is corrected.
- **Better source not found:** LASI Wave 1 mean BP by 45+ age band would replace the
  extrapolation. I didn't locate it.

| Mean SBP / DBP / PP | v0.9 | v0.10 |
|---|---|---|
| Men 50–59 | 127.7 / 84.1 / 43.7 | 127.1 / 83.6 / 43.5 |
| Men 70–79 | 127.7 / 83.4 / 44.3 | 132.0 / 82.5 / 49.5 |
| Men 80–89 | 127.4 / 83.4 / 44.0 | 133.7 / 81.3 / 52.3 |
| Women 50–59 | 125.6 / 82.0 / 43.6 | 128.3 / 81.2 / 47.0 |
| Women 70–79 | 124.9 / 81.9 / 43.0 | 134.8 / 78.6 / 56.2 |
| Women 80–89 | 127.8 / 83.7 / 44.2 | 139.8 / 77.8 / 62.0 |

All 14 sex × decade bands are in the JSON. They include normotensive-only SBP, which also rises with age.

### 3. HbA1c for diabetics, and empty values (HIGH) — fixed
- **Diabetics now get HbA1c**, conditional on the label as before.
  - Distribution: a log-normal with P(< 7%) = 36.3% (ICMR-INDIAB-13, 4,834 self-reported
    diabetics, national) and SD 2.2 (INDIAB phase I regional SDs 2.0–2.4). Its mean is
    about 8.0%, consistent with the phase-I regional means of 8.0–9.1.
  - That source covers *known* diabetes. So it is tagged observed for treated diabetics,
    and **borrowed, confidence "low"** for untreated ones, including undiagnosed.
    No source exists for the untreated group.
  - Generated check: 34.7% of treated diabetics have HbA1c < 7, against 36.3%.
- **Empty-value convention**, now in the schema docstring:
  - `None` means not modelled (height, echo, diagnosed_date).
  - `[]` means modelled, and nothing applies.
  - `labs` is never null now. `Lab` gains `derivation` and `confidence` fields.

### 4. Longitudinal dimension (HIGH) — option (b), partial
- **New fields on each diagnosis**, all tagged modelled and low confidence:
  `age_at_onset_years`, `onset_date`, `onset_derivation` = "modeled_…", `onset_confidence` = "low".
  There is also a `condition_onset_modeled` timeline event.
- **Method:** inverse-CDF on prevalence-by-age curves. Onset given the condition is present
  at age A follows P(a)/P(A) on [20, A].
  - Hypertension curve: read off the same NFHS-5 BP model the generator uses.
  - Diabetes curve: LASI 45–59 and 60+ prevalence, assumed 0 at age 20.
- **Guarantees:** onset ≤ age (tested and validated). `diagnosed_date` stays null on
  purpose: onset is not diagnosis, and about half of cases are undiagnosed.
  Medication start dates stay null; there is no evidence for time-to-treatment.
- **Known weakness (open question):** onset skews early. The median hypertension onset
  for people now 60–69 is 38, because NFHS-5 shows about 8.5% raised BP already at age 20.
  Fixing it needs INDIAB-17 age-specific prevalence.
- **Option (c), handing longitudinal simulation to Synthea:** not chosen. It's a strategic
  change for you to decide.

### 5. `hyperlipidemia` ≈ universal (MEDIUM) — checked, decision needed
- **Prevalence matches the source:** 80.9% generated against the cited INDIAB-17 81.2%.
- **It does NOT agree with `lipid_interpretations`** (69% agreement), because it is an
  independent Bernoulli draw by your earlier decision D014. PAT_000011 is an example.
- **Why it matters now:** the joint lipid model makes NCEP dyslipidaemia computed from
  the panel come out at 80.9%, matching the same 81.2%. Deriving the flag from the panel
  would therefore keep the prevalence *and* remove the inconsistency.
- **I didn't apply it:** it reverses D014, so it's your decision (open question 1).
- **No statin:** there is no Indian population treatment-rate evidence, unchanged from
  D016. So untreated high LDL is expected.

### 6. LAI 2020 vs NCEP (MEDIUM) — verified, test added
The two configured definitions differ only in the LDL cutoff (100 vs 130), so they agree
unless 100 ≤ LDL < 130. A new test uses LDL 115: LAI flags it and NCEP doesn't.
Cohort: LAI 90.0% against NCEP 80.9%. The real LAI framework is risk-tiered (LDL goals
<100, <70 or <50); only its screening cutoff is implemented, because tiering needs an
ASCVD risk category this generator doesn't model (open question 3).

### 7. Smaller items (LOW)
- **Age:** rounded to 2 decimals.
- **Height and weight:** still null (6 searches found no mean + SD).
- **AQI fallback:** not added (optional).
- **Treatment realism** is now stated in the schema docstring: most hypertensives are
  untreated, and "hypertension + diabetes" does not mean both are treated.

## Before and after on the reviewed seeds

Format: TC/TG/HDL/LDL | BP (pulse pressure) | HbA1c | modelled onset age.

| Record (seed) | v0.9 | v0.10 |
|---|---|---|
| PAT_000001 (43), M 65, HTN | 307/77.8/**20.1**/271.3 · 154/97 · 4.97 | 197.7/154.7/34.5/132.3 · 141/85 (conf low) · 5.25 · HTN onset 25.8 |
| PAT_000011 (53), F 20.8 | 130.1/112.9/43.3/64.2 · 116/76 · 5.30 | 164.0/82.0/47.0/100.6 · 113/75 · 4.96 |
| PAT_000013 (55), F 77, DM | 160.1/84.0/49.0/94.3 · 119/84 (PP 35) · **labs null** | 161.8/123.2/40.9/96.3 · 125/77 (PP 48) · **10.41** (treated) · DM onset 50.1 |
| PAT_000015 (57), M 67 | 148.2/**390.3**/32.8/**37.3** · 113/62 · 6.35 | 221.9/274.9/31.0/135.9 · 138/77 · 4.70 |
| PAT_000095 (137), M 79, HTN+DM | 296.1/277.5/29.3/211.3 · **184/118** · **labs null** | 143.2/70.4/45.8/83.3 · 141/86 · 9.58 (untreated, conf low) · onsets HTN 26.3, DM 67.9 |
| PAT_019321, M 84 | 148.0/339.6/75.2/**30.0 (clamped; Friedewald 4.9)** | 230.8/339.0/43.9/119.1 |
| PAT_033933, F 78, HTN | 145.0/308.0/78.6/**30.0 (clamped; Friedewald 4.8)** · 133/99 (PP 34) | 220.4/115.4/52.9/144.4 · 158/83 (PP 75) |
| PAT_078682, F 65, HTN | 184.9/127.4/60.4/99.0 · 122/93 (**PP 29**) | 98.0/59.1/49.9/36.3 · 159/75 (PP 84) |

Notes on the table:
- Batch 1 had 5 records; only 3 were named in the review, so the other 2 are not shown.
- Age, sex, state, BMI, smoking and the three risk-factor flags are identical between
  versions; a test confirms this. Lipids, HbA1c and BP differ by design, and because the
  random-number order changed. Lipids and HbA1c now draw from their own child random
  streams, so future changes there won't shift any other field.

## Null and empty rate per field (v0.10, 5,000 records)

| Field | Rate | Reason |
|---|---|---|
| height_cm, weight_kg | 100% null | not modelled: no Indian mean + SD for height |
| echo | 100% null | not modelled |
| diagnoses[].diagnosed_date | 100% null | diagnosis timing not modelled (onset is) |
| medications[].start_date / stop_date | 100% null | no time-to-treatment evidence |
| air_quality.aqi / category / stations / cities | 3.0% null | 9 states/UTs without adequate monitoring; `unavailable_reason` set |
| diagnoses, medical_history | 56.5% `[]` | patient has neither hypertension nor diabetes |
| medications | 90.7% `[]` | untreated, by NNMS treatment rates |
| labs | 0% null, 0% `[]` | HbA1c for everyone |
| diagnoses[].onset_date | 0% null | every diagnosis has a modelled onset |

## Open questions (need evidence or your decision)

1. **RESOLVED 2026-11-12 → D023 (v0.11): reversed, flag derived from NCEP. -jatin** Original question: **D014 reversal:** derive `risk_factors.hyperlipidemia` from the panel (NCEP any-abnormal,
   now 80.9%, against 81.2%)? This removes the 31% disagreement. Your call.
2. **RESOLVED 2026-11-12 → D025: keep rejecting. -jatin** Original: **TG > 400:** keep rejecting, or emit LDL = null with a reason? This affects about 0.6%
   of real-world panels.
3. **RESOLVED 2026-11-12 → D024 (v0.12): simple rule-based LAI tier added. -jatin** Original: **LAI risk tiers:** these need an ASCVD risk category. Is a simple rule acceptable
   (for example, diabetes means high risk), or should we leave the screening cutoff only?
4. **SEARCHED, no change:** skew is a model assumption; INDIAB-17 table paywalled. Evidence search 2026-11-12: `docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`. -jatin Original: **Onset curves:** INDIAB-17 age-specific prevalence for hypertension and diabetes would
   replace the NFHS-5/LASI-derived curves and fix the early-onset skew. The full-text
   tables weren't accessible.
5. **SEARCHED, no change:** LASI Table 9.1 has the means, but the report PDF needs a download. Evidence search 2026-11-12: `docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`. -jatin Original: **BP at 55+:** LASI Wave 1 mean BP by age band would replace the extrapolation.
6. **SEARCHED, no change:** no Indian correlation matrix exists; urban/rural gap not adopted. Evidence search 2026-11-12: `docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`. -jatin Original: **Lipid correlations:** any Indian cohort with a published lipid correlation matrix would
   replace the calibrated values. Also: the lipid panel isn't age/sex/urban conditioned;
   INDIAB phase I shows an urban/rural gap of 13 mg/dL in TC.
7. **SEARCHED, no change:** no undiagnosed HbA1c distribution published; LASI 45.7% control kept as a cross-check. Evidence search 2026-11-12: `docs/OPEN_QUESTIONS_4-7_EVIDENCE-jatin.md`. -jatin Original: **HbA1c in untreated or undiagnosed diabetes:** currently borrowed from known diabetes.
8. **UPDATED 2026-11-12 → D026: regenerate at v0.12 on AWS, plan in `docs/AWS_RUN_PLAN-jatin.md`, awaiting launch go-ahead. -jatin** Original: **Regenerate the 100K at v0.10:** about 2 hours locally. Needs your go-ahead.
9. **RESOLVED 2026-11-12 → D026: rebuild at v0.12 (`validation/pilot_50_records/rebuild_v012.py`), run on AWS. -jatin** Original: **Old pilot:** the v0.8 `validation/pilot_50_records` package is stale. Retire it or rebuild it?
