# Evidence and Assumptions — 50-Record Pilot (Schema v0.8)

Every field M8 newly populates, what it rests on, and exactly where the
evidence stops. Classification per the task's four tiers:

| Tier | Meaning |
|---|---|
| **ESD** | Evidence-supported population distribution |
| **ESC** | Evidence-supported conditional distribution |
| **EA** | Explicit engineering assumption |
| **DEF** | Not supportable with current evidence — deferred |

Project-internal tiers (`configs/indian_population.yaml`'s own A–E scale,
in use since M2D) are given alongside so this document and the config
agree rather than competing.

---

## 1. Blood pressure — IMPLEMENTED

### 1.1 Sources

| Field | Value |
|---|---|
| **Primary source** | Hypertension screening across different age groups in Indian adults: Evidence from nationally representative cross-sectional data. *PLOS ONE*, 2025. doi:10.1371/journal.pone.0332226 (PMC12571314) |
| **Underlying survey** | NFHS-5 (National Family Health Survey, round 5) |
| **Population** | 101,839 men and 724,115 women, aged 15+, India |
| **Measurement** | Measured, not self-reported — three readings per respondent, 5-minute intervals, Omron monitor |
| **Geographic scope** | National, all states/UTs |
| **Fieldwork year** | 2019–21 (paper published 2025) |
| **Units** | mmHg |
| **What it gives** | Mean SBP and mean DBP with 95% CI and sample size, for five-year age bands × sex (men 15–19…50–54, women 15–19…45–49) |
| **Corroborating source** | Pestilent relationship between smoking and hypertension or pulse pressure among males over 15 years in India: NFHS-5 Survey (PMC11068163), Table 1 — SD(SBP) 13.8, SD(DBP) 10.2, SD(PP) 9.5, mean PP 42.9, n ≈ 88,807–92,805 men |

This is the **first age-conditioned cardiovascular evidence this project
has located at national scope.** M2D concluded no age-stratified
ICMR-INDIAB table was accessible; that remains true. NFHS-5 is a
*different survey*, used only for blood pressure and never blended into
INDIAB's prevalence figures.

### 1.2 What is observed vs. computed

| Quantity | Tier | How obtained |
|---|---|---|
| Mean SBP/DBP per age band × sex | **ESC** / project A | Read directly from the source's table |
| SD per age band × sex | **ESC** / project B | **Derived**: `SD = (CI_high − CI_low) / (2 × 1.96) × √n` from the source's own mean, 95% CI and per-band n |
| SBP/DBP correlation r = 0.7255 | **ESC** / project B | **Derived**: since `PP = SBP − DBP`, `Var(PP) = Var(S) + Var(D) − 2r·SD_S·SD_D` solves for r from the three SDs PMC11068163 publishes together |
| Per-patient (SBP, DBP) pair | **EA** / project C | Reconstructed — a draw from the above, not observed data |

**The derived SDs were independently validated, not just asserted.**
Recombining the per-band SDs into a total SD (pooled within-band
variance + between-band variance of the means) gives:

| | Derived here | Independently published (PMC11068163) | Agreement |
|---|---|---|---|
| Male SD(SBP) | 13.69 mmHg | 13.8 mmHg | 0.8% |
| Male SD(DBP) | 10.24 mmHg | 10.2 mmHg | 0.4% |

Two papers, two different analyses, same answer. That agreement is the
evidence that the CI→SD derivation is sound, and it is why the SDs are
tier B rather than a guess.

**The correlation has two independent corroborations.** r = 0.73 sits
squarely inside the 0.6–0.75 range adult populations are generally
observed at; and PMC11068163's published mean PP of 42.9 mmHg agrees to
~2% with the 42.13 mmHg implied by the *other* paper's age-band grand
means (122.04 − 79.91).

### 1.3 Architecture: label primary, measurement conditional

The hypertension label was already this project's most evidence-backed
variable (ICMR-INDIAB-17 national marginal, 35.5%). BP is generated
**conditional on that label**, using the label's own published
definition as the conditioning boundary:

> SBP ≥ 140 mmHg **and/or** DBP ≥ 90 mmHg **and/or** current use of
> antihypertensive medication

This is the **reversed, label → value** direction `docs/DECISIONS.md`
D011 approved for HbA1c — *not* the lipid raw → label direction. Three
cases:

| Patient | Admissible region | Why |
|---|---|---|
| `hypertension = false` | SBP < 140 **and** DBP < 90 | Medication is never generated without the diagnosis, so the medication arm cannot fire; the label can only be false if both readings are below threshold |
| `hypertension = true`, no antihypertensive | SBP ≥ 140 **or** DBP ≥ 90 | A measurement at threshold is the *only* way the published definition can have been satisfied |
| `hypertension = true`, on antihypertensive | **unconstrained** | The definition is *already* satisfied by medication use. A treated patient may be controlled or uncontrolled, so the measurement is left free |

That third row is the one that matters most. **Forcing a raised reading
for treated patients would be inventing a measurement to confirm an
existing label** — precisely the failure mode this design had to avoid.
In the pilot batch, 1 of 3 treated hypertensives is controlled
(SBP < 140 and DBP < 90), which is the observable proof the region is
genuinely unconstrained. `tests/test_m8_bp_encounters.py::
test_treated_hypertensive_bp_is_not_forced_high` asserts it as a
generator property (>100 of 500 controlled), not as a property of this
one sample.

BP is **never** used to re-derive hypertension, and introduces no new
prevalence claim.

### 1.4 Sampling method

The joint distribution is evaluated on the **integer mmHg grid**
(SBP 70–260 × DBP 40–160), cells outside the label region or violating
the constraints are zeroed, and one cell is drawn from the renormalised
result. 45 distinct distributions (15 sex×band × 3 regions) are cached.

Chosen over truncated marginals or rejection sampling because it is
exact for every region through one code path; has no retry budget and
therefore no bail-out bias in the thin tails young patients fall into
(the raised region sits ~2.6 SD out for women aged 20–24); and makes
whole-mmHg rounding *intrinsic* rather than a post-step that can push a
value back across the threshold it was truncated against.

That last point was a real bug, caught and fixed: truncating at the
threshold itself let a normotensive draw of 139.6 round to 140, breaking
the label rule in **1.7% of 20,000 records**. It is now 0%.

### 1.5 Limitations — stated, quantified, and machine-filterable

**(a) Age coverage is the material one.** The source covers men to 54
and women to 49; this project generates ages 20–89. Patients above
coverage receive the **oldest available band's mean and SD held
constant** — deliberately the conservative choice, because BP is known
to keep rising with age, so this **understates** BP in older patients
rather than inventing a continuing trend.

About **52% of the population** (64% — 32/50 — of this pilot batch, a
small-sample fluctuation) falls outside source coverage. This is not a
rounding detail. Every record therefore carries
`blood_pressure.age_band_source` and
`blood_pressure.extrapolated_beyond_source_age_range`, so affected
patients are **filterable in one line** rather than only described here.

*To close it:* LASI Wave 1 (45+, 2017–18) is the specific candidate and
does measure BP. An age-banded mean+SD table from it was **not** verified
in this pass — search-level figures appeared (e.g. rural male 131.3±20.1
SBP) but no primary table was fetched, so nothing from LASI is used.

**(b) The generated BP marginal is NOT NFHS-5's marginal.** Because BP
is restricted to agree with the hypertension label, and that label's
prevalence (35.5%, INDIAB-17) is higher than the raised-BP fraction
NFHS-5's own distribution implies (~20–22%), the result is NFHS-5's
per-band *shape* re-weighted to be internally consistent with INDIAB-17's
prevalence.

**It must not be validated against, or described as, NFHS-5's observed BP
distribution.** This is the direct, unavoidable cost of two sources
disagreeing, and it is exactly why the label — not the measurement —
remains primary.

**(c) Correlation is sex- and age-unstratified.** r = 0.7255 is derived
from a men-only analysis and applied to women, and is a single
whole-population figure applied to all age bands. No sex-specific or
age-stratified Indian pulse-pressure SD was located.

**(d) Office BP from one survey visit is not a diagnosis.** Three
readings at a single sitting is NFHS-5's protocol, not the repeat-visit
confirmation clinical diagnosis requires.

**(e) Three surveys, three populations.** NFHS-5 (BP), ICMR-INDIAB-17
(hypertension label), ICMR-NNMS (treatment rate) are different studies.
They are used for three *separate* components and never averaged — the
same documented pattern as Census/NNMS/INDIAB elsewhere in this project
(`configs/indian_population.yaml`
`population.target_population_ambiguity_M2D6`).

### 1.6 The one engineering assumption: pulse-pressure floor = 20 mmHg

**Tier EA / project B. The only shaping parameter in the BP design that
is neither read off nor derived from a source.**

A Gaussian copula reproduces the centre of the joint BP distribution
well but not its corners, and the label truncation adds corners of its
own (isolated diastolic hypertension, where DBP ≥ 90 pairs with
SBP < 140). Measured over 20,000 draws:

| Implementation | Records with pulse pressure < 20 mmHg |
|---|---|
| SBP/DBP sampled independently | **10.70%** |
| + derived correlation r = 0.7255 | **1.98%** |
| + 20 mmHg floor | **0%** |

A pulse pressure under 20 mmHg at these absolute BP levels is not a
general-population finding — it indicates cardiogenic shock or severe
aortic stenosis. Leaving 2% of records there would have shipped a known
clinical absurdity into clinical review.

**Why 20, and why only a floor.** 20 mmHg sits ~2.4 SD below the
published Indian mean PP (42.9 ± 9.5 mmHg), so it excludes a region the
source's own distribution already places under 1% of the population; it
is also the conventional clinical boundary for a narrow pulse pressure.
Deliberately **asymmetric — no upper cap** — because a wide pulse
pressure (80–100 mmHg) is genuinely expected in older hypertensive
patients and capping it would delete real signal.

The value remains a judgement, not a measurement. Both the with- and
without-floor distributions are recorded above and in
`validation_report.md` so a reviewer can see precisely what it changed.

Note that independence was **not** a harmless simplification here, and
this is the clearest case in the pilot where measuring a limitation
rather than merely documenting it changed the implementation.

---

## 2. Encounters — IMPLEMENTED (structural only)

**Tier EA / project B.**

One encounter per record:

```json
{
  "encounter_id": "PAT_0xxxxx_ENC01",
  "encounter_type": "synthetic_baseline_assessment",
  "date": "<the measurement date the record already carried>",
  "patient_id": "PAT_0xxxxx",
  "recorded_measurements": ["blood_pressure", "lipid_panel", "labs.HbA1c"],
  "source": "synthetic_structural_container"
}
```

**What it claims:** that this record's blood pressure, lipid panel and
HbA1c form a single synthetic measurement cross-section, taken on one
date, and that the cross-section now has an identifier.

**What it does not claim:** that any healthcare contact occurred. No
visit, admission, appointment, physician, procedure, treatment event or
follow-up date is generated. `ENCOUNTER_TYPES` contains exactly one
value and it is named for what it actually is.

**Why this and not `null`.** Every measurement in the record already
carried the same date, and until M8 that date had no owner — which is
why `docs/CLINICAL_RECORD_DESIGN.md` §H shows
`Encounter --reference_id--> (nothing yet)`. Naming the cross-section
invents nothing and gives the timeline something real to index. No date
is created: the encounter date is taken from the record's existing
`labs.measured_at` (falling back to its `synthetic_record_created`
date).

**What stays deferred.** A care-seeking / utilization encounter model.
The only candidate source, NSS 75th Round, measures healthcare
*expenditure behaviour*, not clinical encounters, and
`docs/INDIAN_GENERATION_STRATEGY.md` already classifies it
"**E — Not Used**, deferred". Real visit types remain unsupported until
such evidence exists.

**Decisions a reviewer may want to reverse:** whether a structural
container belongs in `encounters` at all, versus leaving the field null
and introducing a `measurement_session` concept instead. The field is
cheap to empty — `derive_encounters()` returning `[]` propagates
correctly through the timeline and both validators.

---

## 3. Clinical timeline — EXTENDED

**Tier EA / project B.**

`TimelineEvent` gains `reference_id: Optional[str]` — the reference
mechanism `docs/CLINICAL_RECORD_DESIGN.md` §H proposed as "a small,
additive schema change", implemented as such. Two events per record:

| Event | Date | reference_id |
|---|---|---|
| `synthetic_record_created` | preserved from the v0.7 record | `null` |
| `synthetic_baseline_assessment` | the measurement date | the encounter's id |

**One event per encounter, not one per measurement** — the measurements
are already enumerated inside the encounter, so per-measurement events
would be the duplicate representation this project's design rules
forbid.

**No diagnosis-onset, medication-start/stop or follow-up event is
emitted.** No evidence-backed per-patient date distribution exists for
any of them (`docs/M4_CLINICAL_EVIDENCE.md` §7), which is the same
reason `diagnosed_date` and `start_date` remain null.

The timeline is rebuilt from scratch on every run rather than appended
to — that is what makes re-migration idempotent.

---

## 4. Height and weight — DEFERRED

**Tier DEF / project E (unavailable).**

**What is missing:** a national mean **and standard deviation** of adult
height in cm, by sex, for Indian adults.

The mean alone is insufficient. Without a dispersion figure any
generated height distribution would have an invented shape — the
identical objection this project already used, and accepted, to *reject*
a peaked within-BMI-category distribution (`configs/indian_population.yaml`
`risk_factors.bmi.limitations`, M2D-2). Applying a weaker standard to
height than to BMI would be inconsistent.

**Research attempts: 6 total (3 in M4-0, 3 added by M8).** The three new
ones:

| Attempt | Result |
|---|---|
| NFHS-5-based adult-height literature — PLOS ONE doi:10.1371/journal.pone.0255676 | Reports only round-to-round **changes** in mean height (e.g. men 26–50 declined 0.86 cm between NFHS-III and NFHS-IV). No absolute mean, no SD. |
| Deaton, *Height, health and inequality: the distribution of adult heights in India* (PMC2630164) | **State-level** means at age 20 from NFHS-3 (men 157.2–168.6 cm, women 149.1–154.9 cm). Explicitly **no** all-India mean and **no** all-India SD — it uses a regression standard error as its dispersion measure instead. |
| ICMR-focused pass | Surfaced only the ICMR-NIN 2020 "Reference Indian Adult Man/Woman" (65 kg / 1.77 m; 55 kg / 1.62 m) — an **idealised reference individual, not a population distribution**, and whose 1.77 m is plainly inconsistent with the ~165 cm national male mean, so it must not be used as one. |

Secondary summaries put the NFHS-5 means near 165 cm (men) and 152 cm
(women), consistent with Deaton's state ranges — but no primary table
carrying **both** the mean and the SD was verified.

**Why not generate anyway.** BMI is already this project's
evidence-primary anthropometric variable
(`docs/M4_CLINICAL_ARCHITECTURE.md` §1, M4-0's resolved recommendation).
Height from an invented dispersion plus `weight = bmi × (height/100)²`
would leave BMI exactly correct while making height and weight
model-generated numbers wearing the clothes of measurements. That trade
was declined.

**BMI is untouched.** All 50 records keep their original BMI byte-for-byte;
`height_cm` and `weight_kg` are written as explicit `null` rather than
left absent, so a reviewer can see they were considered.

**Concrete recommendation, in preference order:**

1. **Obtain a primary mean+SD.** The DHS/NFHS-5 recode files, or the
   NFHS-5 India Report (FR375) anthropometry tables, are the direct
   source. **One verified mean+SD-by-sex table unblocks this
   immediately.**
2. If only Deaton's verified **state-level** means are obtainable, a
   national mean can be assembled from them using this project's own
   Census-2011 state distribution (`demographics.state`) as weights —
   fully traceable, no new assumption beyond the weighting. But that
   still yields no SD, so route 1 remains necessary.

The implementation hook already exists and is tested as a deliberate
no-op: `generation.indian_population.sample_height_cm()` returns `None`
and **raises `NotImplementedError` if the config ever gains height
evidence while the function still returns `None`** — so the gap cannot
rot silently. `derive_weight_kg()` is implemented and tested now, so
only the height draw is outstanding.

---

## 5. Family history — DEFERRED (an open human decision, not an evidence gap)

**Tier DEF / project C — requires explicit human decision.**

This one is different from height: evidence *does* partially exist, and
the blocker is a scope choice that is not the implementer's to make.

| Component | Status |
|---|---|
| Family history of **diabetes** | **PARTIALLY SUPPORTED** — 14.33% (8,822/58,612), LASI, Ahmed W (2024) *BMC Public Health*, adults **45+ only** |
| Family history of **CVD** | **NOT SUPPORTED** — confirmed absent across 9+ datasets (`docs/DECISIONS.md` D004) |
| Relation (mother/father/sibling), age of onset, any other condition | **NOT SUPPORTED** at usable granularity |

`docs/M4F_FINAL_CLINICAL_AUDIT.md` already classifies the scope choice
"**C — requires explicit human decision**": generate the LASI-sourced
45+ diabetes-family-history figure for part of the population, or leave
family history entirely unpopulated. That is a product-scope judgement
(partial-population coverage vs. no coverage), not an evidence question,
and M8 did not make it. `family_history` stays `null` in all 50 records.

**A family *tree* is a separate and much larger gap.** A family-history
*record* (does any relative have condition X) and a family *tree*
(identified relatives, parent-child and sibling links, their own
records) are different objects. Nothing in any source examined supports
relatives as entities. **No relatives, family sizes, hereditary
conditions or kinship links were invented**, and no family-tree schema is
proposed here — doing so for an urgent batch would be designing a data
model around absent evidence.

---

## 6. Preserved unchanged — and verified so

These were already evidence-backed and M8 asserts them byte-identical
(`integration/migrate_v07_to_v08.py` `_UNCHANGED_FIELDS`, enforced in
code — a silent overwrite is a hard error, not something a reviewer has
to notice):

| Domain | Rule preserved |
|---|---|
| **Diagnoses** | 1:1 promotion of the hypertension/diabetes risk-factor flags, never independently sampled. `diagnosed_date` null (no per-patient onset evidence). Hyperlipidemia's diagnosis **stays deferred** (D015) |
| **Medical history** | `chronic_condition` entries referencing diagnoses by id, never re-derived. **Not expanded** — no evidence supports surgeries, admissions, CV events or procedures |
| **Medications** | Drug-class only (antihypertensive/antidiabetic), NNMS treatment-rate gated (14.5%/36.1%), never a specific drug name. `start_date`/`stop_date` null (no per-patient initiation-date evidence). **No statin or antiplatelet added** — no population treatment-rate evidence |
| **Lipids** | Raw-first: TC/TG/HDL sampled, LDL derived via Friedewald then clipped, interpretations computed per named definition. `risk_factors.hyperlipidemia` and `lipid_interpretations` remain intentionally distinct and are never compared (D014) |
| **HbA1c** | Generated only for non-diabetic patients, age+sex-conditioned, conditional on the diabetes label and never the reverse |
| **ECG** | Metadata only. `signal_available: false` in all 50. No waveform generated, no missing superclass guessed (2 records have empty superclasses; both are warned about, neither filled in) |
| **Echo** | `null` in all 50. No measurement, image, video or report generated |

### Medication dates: reviewed, still null

The task asked whether medication dates can now be generated
defensibly. They cannot. NNMS's treatment rate is a **cross-sectional
point-prevalence** of "currently treated" — it carries no information
about when treatment began, how long it has continued, or adherence.
A `start_date` would be a free parameter with no distribution behind it,
and because `diagnosed_date` is also null there is not even an anchor to
offset from. `current_status` stays `"active"`, and `"discontinued"`
remains a structurally valid value the generator never produces.

---

## 7. What no field rests on

For the avoidance of doubt, no field in this batch was produced by:

- an arbitrary uniform distribution chosen to fill a gap (the one
  uniform in the project, within-BMI-category, predates M8 and is
  documented as the least-assumption choice given only category
  boundaries are known);
- a fixed placeholder or hand-picked value;
- a value copied across patients (38 distinct systolic and 30 distinct
  diastolic values across 50 records; ≥45 distinct BP pairs asserted by
  test);
- an identical encounter history shared by everyone (the encounter's
  contents vary with what was actually measured — 46 records carry
  HbA1c, 4 diabetic records correctly do not);
- a correlation introduced to make records look coherent (the one
  correlation used is derived arithmetically from published variances,
  and the independence that preceded it was discarded because it was
  *measurably wrong*, not because correlation looked better).
