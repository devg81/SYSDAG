# M4B-0 — Clinical Value Generation Design

**Milestone:** M4B-0 (design/evidence audit, part of the combined M4B
session). No code changes in this section — implementation follows in
M4B-1 below this document's conclusions.
**Date:** 2026-09-26
**Builds on:** `docs/M4_CLINICAL_ARCHITECTURE.md` (D011),
`docs/M4_CLINICAL_EVIDENCE.md`, `docs/M4-0A_DYSLIPIDEMIA_DECISION_BRIEF.md`.

**Human checkpoint: NO.** No new medical threshold, no dataset, no
population-definition change, no conflict with D011/D008 was found while
designing this. Proceeding automatically to M4B-1 per instructions.

---

## A1. Lipid Generation — Evidence and Conditioning

| Analyte | Continuous distribution evidence | Category/marginal evidence | Conditioning support |
|---|---|---|---|
| Total cholesterol (TC) | **NOT SUPPORTED** (no mean/SD found anywhere) | **SUPPORTED**: TC≥200 mg/dL = 24.0% (INDIAB-17, national) | Sex/age/urban-rural: **NOT SUPPORTED** (no stratified TC table found) |
| Triglycerides (TG) | **NOT SUPPORTED** | **SUPPORTED**: TG≥150 mg/dL = 32.1% (INDIAB-17, national) | **NOT SUPPORTED** for any stratification |
| HDL | **NOT SUPPORTED** | **SUPPORTED**: low HDL (sex-specific cutoff <40M/<50F) = 66.9% (INDIAB-17, national, **pooled across sexes** — no sex-specific *prevalence split* found, only a sex-specific *cutoff definition*) | Sex: **PARTIALLY SUPPORTED** (cutoff is sex-specific; prevalence is not) |
| LDL | **NOT SUPPORTED** as an independently-measured continuous value | **SUPPORTED**: LDL≥130 mg/dL = 20.9% (INDIAB-17, NCEP) — **but see A2**: LDL is derived here, not independently sampled from this figure | N/A — derived (A2) |

**Conclusion:** no demographic conditioning (sex/age/urban-rural) is
supported by evidence for any lipid component's *value* — only national
marginal category rates exist. This matches M4-0's own conclusion and is
not revisited. TC, TG, and HDL are generated as **category-then-uniform**
draws from their national marginal rates — the same engineering pattern
already established and approved for BMI (`configs/indian_population.yaml`
`risk_factors.bmi`), not a new invention.

---

## A2. Lipid Relationships — Using Friedewald, Not Inventing a Correlation

**Quantified check performed before deciding:** assuming all four
components are statistically **independent** at their own cited marginal
rates (TC 24.0%, TG 32.1%, HDL 66.9%, LDL 20.9%) implies a composite
"any-abnormal" rate of **86.5%** — but the actual cited composite is
**81.2%**. This ~5-point gap indicates the four components are **not**
independent in the real population (a well-known clinical fact: lipid
abnormalities cluster together) — full independence would systematically
overstate the true composite rate.

**Decision: derive LDL from TC, HDL, and TG via the Friedewald equation**
(`LDL = TC − HDL − TG/5`, all mg/dL) — **this is not an invented
correlation.** It is the standard clinical calculation method, and
**ICMR-INDIAB-17 itself used this exact formula** to compute LDL from
directly-measured TC/HDL/TG (confirmed in M4-0A's research). Using it
here is reusing an established clinical/mathematical relationship, not
building "a sophisticated multivariate model... merely because it is
technically possible" — it is the simplest approach that is also
medically correct, satisfying both halves of this milestone's stated
optimization goals (defensibility *and* simplicity).

**Consequence:** only **3** independent category-then-uniform draws are
needed (TC, HDL, TG); LDL is computed, not drawn. Friedewald is known to
be unreliable above TG≈400 mg/dL — the TG category's own upper bound
(400, chosen below) keeps generated values within Friedewald's valid
range as a side benefit, not a coincidence.

**Safeguard:** computed LDL is clipped to a physiologically plausible
range `[30, 300]` mg/dL — documented as an **engineering safeguard**
against implausible arithmetic combinations from independent TC/HDL/TG
draws (e.g. very low TC with very high HDL and TG could otherwise yield
a nonsensical or negative value), not a claim about the true LDL
distribution's shape.

**Classification:** TC/HDL/TG generation — SUPPORTED (marginal category
rate) + ENGINEERING (within-category continuous value, same pattern as
BMI). LDL — ENGINEERING (Friedewald computation) with a real clinical
basis, not an invented statistical correlation.

### Category ranges (all ENGINEERING choices for the within-category continuous value — not evidence, exactly like BMI's existing category ranges)

| Analyte | Category | Range (mg/dL) | Rationale |
|---|---|---|---|
| TC | <200 | [100, 199.9] | NCEP "desirable" zone lower-bounded at a plausible physiological floor |
| TC | ≥200 | [200, 320] | NCEP "borderline-high"/"high" zone, capped at a plausible outer bound |
| TG | <150 | [50, 149.9] | NCEP "normal" zone |
| TG | ≥150 | [150, 400] | NCEP "borderline-high"/"high" zone; capped at 400 to stay within Friedewald's valid range |
| HDL (male) | <40 (low) | [20, 39.9] | NCEP "low HDL" for men |
| HDL (male) | ≥40 | [40, 80] | Normal/protective range for men |
| HDL (female) | <50 (low) | [20, 49.9] | NCEP "low HDL" for women |
| HDL (female) | ≥50 | [50, 90] | Normal/protective range for women |

**HDL note:** only the *pooled* 66.9% low-HDL rate is evidenced, not a
sex-specific split — applied identically to both sexes (each within
their own sex-specific cutoff-defined range), documented as an
engineering necessity, not itself evidenced. This mirrors the same
honest-disclosure pattern already used for BMI's within-category shape.

---

## A3. Lipid Interpretation — Computed, Never Sampled

Per D011: `LipidInterpretation.dyslipidemia` is **computed** from the
generated TC/HDL/TG/LDL values against each definition's own documented
thresholds — never an independent random draw. Both already-approved
definitions are computed for every patient with a lipid panel:

```text
NCEP_ATP_III: TC>=200 OR TG>=150 OR HDL<40(M)/50(F) OR LDL>=130
LAI_2020:     TC>=200 OR TG>=150 OR HDL<40(M)/50(F) OR LDL>=100
```

(Both share identical TC/TG/HDL cutoffs; only LDL differs — exactly
matching M4-0A's confirmed source comparison.) `components_abnormal`
records which specific component(s) triggered each definition, and
`source_citation` records the originating paper for each definition
(ICMR-INDIAB-17/NCEP; ICMR-INDIAB-25/LAI). No new universal threshold is
introduced — these are the same two definitions D011 already approved.

---

## A4. HbA1c — Conditional on the Existing Diabetes Label

Per M4-0B/D011: diabetes status (already generated, primary evidence) →
HbA1c generated conditionally on it, never the reverse.

**Non-diabetic (NGT) patients — SUPPORTED, the strongest continuous-
variable evidence in this project:** ICMR-INDIAB-12 (n=14,222, confirmed
NGT adults 20+): age-decade trend 5.16±0.71% (20-29y) → 5.49±0.69%
(70+y), with a **sex**-specific decade slope (female +0.10%/decade,
male +0.06%/decade) and a separate **urban/rural**-specific decade slope
(urban +0.10%/decade, rural +0.08%/decade).

**Design decision — sex-conditioning only, not urban/rural too:** the
sex effect (0.06 vs. 0.10, a 67% relative difference) is meaningfully
larger and more clearly reported than the urban/rural effect (0.08 vs.
0.10, a 25% relative difference). Combining both dimensions
simultaneously would require an **interaction assumption neither paper
reports** (whether/how the two slopes combine for, say, an urban woman
vs. a rural woman) — inventing one would cross from "engineering
simplification" into "invented conditioning." Implementing sex-
conditioning only is also **architecturally consistent**: BMI and
smoking are already sex-conditioned elsewhere in this generator, so
this doesn't introduce a new conditioning axis, just extends an
existing one to a new variable. **Urban/rural HbA1c conditioning is
real evidence that exists but is deliberately not implemented in M4B** —
documented as a future refinement, not silently dropped.

**Formula (engineering choices explicitly marked):**
```text
mean(age, sex) = 5.16 + sex_slope(sex) * (age - 25) / 10
  sex_slope: female=0.10, male=0.06   [EVIDENCE: ICMR-INDIAB-12]
  reference point age=25              [ENGINEERING: midpoint of the
                                        reported 20-29y band]
sd = 0.70                              [ENGINEERING: average of the two
                                        reported SDs, 0.71/0.69]
value = Normal(mean, sd), clipped to [4.0, 6.4]
  lower bound 4.0                      [ENGINEERING: physiological floor]
  upper bound 6.4                      [ENGINEERING: kept just below the
                                        standard international ADA
                                        diabetic threshold (>=6.5%), so a
                                        NGT-labeled patient never gets an
                                        HbA1c value that would itself
                                        suggest diabetes — an internal-
                                        consistency safeguard, same
                                        principle as D011's core rule,
                                        applied here even though HbA1c
                                        isn't literally this project's
                                        diabetes-diagnostic criterion]
```

**Diabetic patients — NOT SUPPORTED for confident generation.** Only
thin, non-representative 4-state data exists (Chandigarh, Tamil Nadu,
Jharkhand, Maharashtra — 480 people total, an earlier ICMR-INDIAB phase).
Using any of these regional figures as if national would misrepresent
the evidence, and this project's own `state` field is drawn from an
unrelated Census-based national distribution, not these four specific
states. **Decision: HbA1c is not generated for diabetic patients in
M4B** — `labs` stays `None` for these patients, exactly matching the
existing precedent of leaving evidence-insufficient fields unpopulated
(`family_history`, D004) rather than fabricating a number. This is an
evidence-driven scope decision already anticipated in
`docs/M4_CLINICAL_EVIDENCE.md`, not a new human checkpoint.

---

## A5. Missingness

**Lipid panel:** generated for **every** patient (100% "coverage").
INDIAB-17's own lipid sub-sample covered only ~16% of its full cohort —
but this reflects the **survey's own sub-sampling logistics** (a
cost/logistics decision about who got tested), not a real-world
statistic about how often lipid measurements are unavailable in Indian
clinical practice. Treating the survey's internal sub-sampling rate as
if it were a population missingness rate would conflate two different
things. **Decision (engineering, not evidence-derived): populate
`lipid_panel`/`lipid_interpretations` for every generated patient.** If
genuine clinical-completeness evidence is found later, this can be
revisited — not attempted here.

**HbA1c:** binary, evidence-and-scope-driven (not a probabilistic
missingness model) — present for all non-diabetic patients, absent for
all diabetic patients, per A4.

---

## A6. Temporal Placement

**Decision (engineering, explicitly simple):** every new clinical value
receives `measured_at` equal to the patient's own generation date
(`provenance.generated_at`, truncated to date) — a single snapshot, not
a longitudinal history. This matches the existing minimal temporal model
(`clinical_timeline` currently has exactly one event,
`synthetic_record_created`, at the same date). **No new
`clinical_timeline` event is added** for labs in M4B — wiring labs into
the timeline via a `reference_id` field is real future work
(`docs/CLINICAL_RECORD_DESIGN.md` §H) that requires a schema field not
yet approved; adding it now would exceed this milestone's schema-stable
scope. Deferred, not forgotten.

---

## Summary Table

| Component | Generation method | Classification |
|---|---|---|
| TC | Category (marginal, INDIAB-17) → uniform within category | SUPPORTED (category) + ENGINEERING (continuous value) |
| TG | Category (marginal, INDIAB-17) → uniform within category | SUPPORTED (category) + ENGINEERING (continuous value) |
| HDL | Category (pooled marginal, INDIAB-17; sex-specific cutoff range) → uniform within category | SUPPORTED (category) + ENGINEERING (continuous value, pooled-rate-per-sex simplification) |
| LDL | Friedewald computation from TC/HDL/TG, clipped to [30,300] | ENGINEERING (real clinical formula, not invented) |
| LipidInterpretation (both definitions) | Computed from raw values, never sampled | Direct implementation of D011 |
| HbA1c (non-diabetic) | Age+sex-conditioned Normal distribution, clipped | SUPPORTED (age/sex trend, ICMR-INDIAB-12) + ENGINEERING (SD, reference point, clip bounds) |
| HbA1c (diabetic) | Not generated | NOT SUPPORTED — left `None` |
| Lab `measured_at` | = patient generation date | ENGINEERING |

## Known Limitations (carried into implementation, not hidden)

1. Independence-implied composite dyslipidemia rate (86.5%) exceeds the
   real cited rate (81.2%) — using Friedewald for LDL reduces but does
   not fully eliminate this gap, since TC/HDL/TG are still drawn
   independently of each other. Will be checked empirically at n=100.
2. HDL's sex-specific cutoff is applied to a sex-*pooled* prevalence
   rate — no true sex-specific HDL prevalence split was found.
3. Urban/rural HbA1c conditioning (real evidence) is not implemented.
4. All within-category continuous shapes remain uniform (no evidence for
   the true shape within a category) — same limitation already accepted
   for BMI.
5. Diabetic-population HbA1c remains ungenerated pending better evidence.

No human checkpoint is triggered by any of the above — each is a
documented engineering choice or a scope limitation already anticipated
in prior milestones, not a new medical assumption or unresolved
conflict.
