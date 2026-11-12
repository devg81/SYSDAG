# M3 Pattern Inventory

**Population analyzed:** 1,000 synthetic patients, `outputs/m3/1000_patients/`
(seed: `random_seed: 42` in both `configs/base.yaml` and
`configs/indian_population.yaml`, sequences 1-1000).
**Purpose:** distinguish what the generator *intentionally* encodes, what
emerges *mechanically* as a side effect of implementation choices, what is
*not yet represented* at all, and what would require real evidence before
it could be added. This inventory is a map of the current generator's
actual behavior, not a claim about the real Indian population.

---

## A. Patterns Intentionally Encoded

These are deliberate, evidence-backed generation choices
(`configs/indian_population.yaml`, `generation/indian_population.py`):

1. **State follows Census-2011-weighted sampling** — 35 states/UTs, each
   drawn with probability equal to its 2011 Census population share.
2. **Urban/rural follows Census 2011's national marginal** (rural 68.84%,
   urban 31.16%).
3. **Sex follows Census 2011's national marginal** (male 51.47%, female
   48.53%).
4. **BMI category is sex-conditioned** (ICMR-NNMS: distinct
   overweight/obese probabilities for men vs. women).
5. **Smoking status is sex-conditioned** (ICMR-NNMS: distinct current/never
   probabilities for men vs. women).
6. **Hypertension, diabetes, hyperlipidemia are unconditioned national
   marginals** (ICMR-INDIAB-17: 35.5%, 11.4%, 81.2% respectively) — a
   *deliberate* choice, confirmed correct by the M2D audit, not an
   oversight.
7. **Age is `uniform(20, 89)`** — an explicit engineering default, not
   evidence-derived (`docs/DECISIONS.md` D007).
8. **Family history of CVD is never generated** (left `null`) — no Indian
   evidence source exists (`docs/DECISIONS.md` D004).
9. **Hypertension/diabetes diagnoses are a 1:1 promotion of the already
   evidence-backed risk_factors flags** (M4D, `docs/DECISIONS.md` D015) —
   reformats already-evidence-backed data, invents no new prevalence.

## B. Patterns Emerging Mechanically From the Generator

These are side effects of *how* the generator is built, not intentional
epidemiological claims:

1. **Within-BMI-category continuous values are uniform** — an artifact of
   the sampling implementation (no shape evidence exists for how BMI is
   distributed *within* "overweight" or "obese"), not an epidemiological
   claim about the real shape.
2. **~5.8% of generated patients have an ECG record with no diagnostic
   superclass** (58/1,000 observed) — this mechanically inherits PTB-XL's
   own ~6.5% zero-superclass rate at the 50%-confidence threshold
   (`docs/INDIAN_DATA_SOURCES.md`/`docs/syngen-codebase-analysis.md` §5),
   restricted to training folds. Not a bug — a known, already-documented
   characteristic of the reused ECG metadata source.
3. **Duplicate ECG records across distinct synthetic patients** — 30
   distinct `ecg_id` values were each assigned to 2-3 different patients
   in this 1,000-patient run (see `outputs/m3/m3_analysis_report.json`,
   `structural.duplicate_ecg_ids`). This is the birthday-paradox effect of
   independently sampling from a training-fold pool of only ~17,470
   records — mathematically expected (~28.6 collision pairs predicted,
   ~30 observed), not a defect in this run, but a real scaling concern
   (see Candidate Generator Improvements below).
4. **Small residual, statistically non-significant "noise" correlations**
   between variables the generator treats as independent (e.g. age×sex
   r=0.052, p=0.10) — expected sampling variation at n=1,000, not a
   modeled relationship. See §M3-7 in the session log for the full table.
5. **`medical_history` references `diagnoses` by id rather than
   re-deriving from `risk_factors`** (M4D, D015) — an engineering
   structural choice (avoid a second independent generator), not itself
   new evidence.
6. **A pre-existing, unrelated `ecg.superclasses` list-*order*
   non-determinism** across separate process runs at the same seed
   (observed during M4D's regression check) — traced to a `set()` in
   reused `syngen/SynGen/SynGen/gan_pytorch.py`'s `build_label_map()`,
   whose iteration order depends on the per-process hash seed. Content
   (which superclasses apply) is unaffected — only list order.

## C. Patterns NOT Currently Represented

Real relationships the generator does not attempt to model — some because
no accessible evidence exists, one because accessible evidence exists but
was never wired in:

1. **Age-dependent hypertension/diabetes/hyperlipidemia prevalence** — no
   accessible age-stratified table exists (ICMR-INDIAB-17 is paywalled).
2. **Age-dependent BMI/smoking prevalence** — only a *region-scoped* (not
   national) age×sex table was found for NNMS; using it nationally would
   misrepresent the evidence, so it was correctly excluded.
3. **Urban/rural-dependent BMI** — **evidence exists and is already cited**
   (NNMS: overweight urban 42.5%/rural 18.0%; obese urban 11.2%/rural
   3.7%, per this project's own M2C-0 research) but was **never
   incorporated into `configs/indian_population.yaml`**. Unlike item 2
   above, this is not an evidence gap — it's an implementation gap. Flagged
   as a Candidate Generator Improvement below.
4. **Region/state-dependent risk-factor prevalence** — NNMS's own
   regional-estimates paper shows real regional variation; not
   incorporated (would require deciding how to map India's ~6 NNMS regions
   onto the 35-entry state/UT list, itself requiring a documented,
   evidence-checked mapping, not invented).
5. **BMI-dependent or smoking-dependent hypertension/diabetes prevalence**
   — no accessible quantitative association was located (M2D-4 audit).
6. **Joint state × urban/rural distribution** — sampled independently;
   Census 2011 has the real joint table, not pulled in.
7. **Any multi-way joint distribution** among the 5 risk factors —
   generated as independent marginals/pairwise-sex-conditionals only.
8. **Stroke, heart failure, general CVD, cardiac procedures** (M4D audit,
   `docs/M4_CLINICAL_EVIDENCE.md` §2) — real figures exist but are
   heterogeneous, modeled-not-measured, or hospital-registry-derived;
   not precise enough for individual-record generation.
9. **Any diagnosis onset/`diagnosed_date`** (M4D) — no per-patient
   onset-date distribution exists, only population rates by age band
   (LASI, 45+ only); `Diagnosis.diagnosed_date` stays `None`.

## D. Patterns Requiring Real Evidence Before Consideration

Relationships that should **not** be inferred from this synthetic data
alone, and should not be added to the generator without a citable source:

1. Any specific numeric age × condition relationship (hypertension,
   diabetes, hyperlipidemia, BMI, or smoking) at the national level.
2. Any specific numeric BMI/smoking × condition relationship (e.g. "does
   current smoking increase generated hypertension probability" — it
   currently cannot, by construction, and should not be added without a
   cited adjusted-odds-ratio source).
3. A finer-grained (sub-decade) adult age distribution — `docs/DECISIONS.md`
   D007 already documents why the best located alternative was rejected.
4. A current (post-2011) state/UT boundary mapping — needed before the
   35-entry list can be considered current rather than historically
   accurate (Telangana, J&K reorganization, Daman-Diu/Dadra-Nagar-Haveli
   merger — see M2D's audit).
5. Whether the assembled general-Indian-population target
   (`docs/DECISIONS.md` D008) should eventually support a *joint*
   demographic-and-risk-factor distribution, versus remaining an assembly
   of independent/pairwise marginals — this is a design question for a
   future milestone, not something this analysis resolves.
6. **Which `lipid_interpretations` definition (if any) should drive a
   future `diagnoses.hyperlipidemia` entry** (M4D, D015) — NCEP_ATP_III
   and LAI_2020 disagree by design (D011); picking one to feed a single
   diagnosis boolean would silently make the canonical-definition choice
   D011 declined to make. Deferred pending a human decision, not an
   evidence gap.

---

This inventory should be revisited (not rewritten from scratch) once a
larger-scale population exists, since some "not currently represented"
items in §C could become directly actionable (item 3 in particular)
without further research.
