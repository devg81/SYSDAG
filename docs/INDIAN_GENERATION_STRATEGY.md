# Indian Generation Strategy (M2B)

**Milestone:** M2B — Indian Generation Strategy (design/research checkpoint,
no implementation).
**Status:** Design complete. No code, schema, or configuration was modified.
**Date:** 2026-09-25
**Builds on:** `docs/INDIAN_DATA_SOURCES.md` (M2A). This document does not
repeat that research — it uses its conclusions as given facts and designs
the smallest defensible generation strategy on top of them.

> **Addendum (2026-09-25, post-M2B):** The schema questions this document
> left `OPEN` in §15/§17 (whether to adopt `region`/`state` and
> `urban_rural`) have been **resolved** — both are adopted as first-class
> `Demographics` fields. See `docs/DECISIONS.md` D005 for the decision
> record. The analysis below is left as-written (the historical reasoning
> that led to the original, more conservative recommendation) rather than
> rewritten — D005 supersedes §15's "USEFUL, not required" classification
> and §17/§18's corresponding open items for these two fields specifically.
> Everything else in this document (variable definitions, dependency graph,
> fallback strategy, etc.) is unaffected and still applies. The actual
> evidence-backed distributions for these two fields (M2C-2/M2C-3) are
> **not yet implemented** — see D005's "scope of this change" note.

> **Addendum 2 (2026-09-26, post-M2D):** §11's "Definition of 'Indian' for
> This Project" is now made precise at the project level: the target is
> the **general Indian population** (`docs/DECISIONS.md` D008), not a
> CVD-only/hospital/clinic/high-risk/registry population — resolving the
> ambiguity M2D's audit (`docs/session_logs/2026-09-25_M2D-calibration-quality-gate.md`)
> found between this document's demographic-conditioning discussion and
> the risk-factor sources' own narrower surveyed populations (NNMS adults
> 18-69, ICMR-INDIAB adults 20+). D008 does not claim these sources
> combine into one internally consistent observed population — see D008
> for the full per-source mapping. No other part of this document changes.

---

## 1. Executive Summary

The smallest defensible Indian-conditioning layer uses **only already-public,
peer-reviewed/official aggregate statistics** (age/sex-stratified prevalence
tables from ICMR-INDIAB, ICMR-NNMS, and NFHS-5) as calibration parameters —
never restricted microdata, and never a claim of joint/individual-level
modeling M2A didn't establish evidence for. Demographics (age, sex) and five
risk factors (BMI, smoking status, hypertension, diabetes, dyslipidemia) are
the minimum viable set; family history of CVD specifically has **no
confirmed Indian evidence source** and should be left unpopulated rather
than invented. Two schema additions (`urban_rural`, `region/state`) are
flagged as candidates but not made — they require a human checkpoint before
M2C, per this milestone's restriction.

Generation should follow a dependency order (age → sex → [urban/rural] →
BMI → smoking → hypertension → diabetes → dyslipidemia → family history →
downstream clinical fields) because sex and age drive large, evidence-backed
differences in every risk factor's prevalence in the Indian data (e.g.,
smoking is overwhelmingly male in every source examined) — independent
per-field randomization would silently discard that evidence. Where only
marginal or simple age/sex-stratified aggregate statistics exist (true for
nearly everything examined), that is exactly what should be used; where a
paper reports an adjusted odds ratio for a combination (e.g., diabetes
associated with age+BMI), that documented association may be used as an
explicit, cited rule — but no full multi-way joint distribution should be
claimed, because M2A did not find accessible individual-level clinical data
that would support one.

A previously undocumented gap surfaced while writing this strategy: the
project's only ECG source so far (PTB-XL, via M1) is a **German**, not
Indian, cohort. Indian-conditioned demographics/risk-factors sitting next to
a non-Indian-sourced ECG is an internal-coherence gap this document
surfaces but does not resolve — that belongs to Stage 4.

---

## 2. M2A Findings Used

This section restates only the conclusions from `docs/INDIAN_DATA_SOURCES.md`
that drive design decisions below — see that document for full detail,
citations, and per-dataset analysis. Not re-verified here.

- Individual-level data is **restricted** for every clinically-rich source
  (ICMR-INDIAB, ICMR-NNMS, NFHS-5, LASI) — query-mediated or
  registration/request-gated. **Aggregate/published statistics are free for
  all eight** datasets researched.
- IHDS and the NSS 75th Round are the only sources with open individual-level
  microdata, but neither has strong direct cardiovascular clinical
  variables.
- **No dataset's license was found to explicitly address synthetic-data
  generation**, in either direction, for any of the 8 sources — every
  instance was marked `Not verified` in M2A, not assumed permitted.
- IHDS's ICPSR terms explicitly bar feeding its data to any LLM that
  retains/trains on it.
- Variable definitions are **not confirmed identical** across sources for
  hypertension, diabetes, and smoking granularity.
- GBD India State-Level is a modeled aggregate — validation/reference role
  only, and risks double-counting if treated as an independent calibration
  source alongside its own likely underlying input surveys.
- CREATE/STEMI-ACT are the only clinical-event (not risk-factor-survey)
  sources, but are the weakest on practical accessibility.
- Current schema (`schemas/patient_schema.py`, from M1) has `demographics`
  (age, sex, height_cm, weight_kg) implemented; `risk_factors`,
  `family_history`, `medical_history`, `diagnoses`, `medications`, `labs`,
  `encounters` are all unset `Optional[dict]`/`Optional[list]` placeholders
  — Stage 3 work, not yet implemented (per `docs/PROJECT_STATE.md`'s M2
  stub and `docs/DECISIONS.md` D004).
- M1's demographics for `PAT_000001` were reused from a real PTB-XL
  (German-population) record, explicitly documented in D004 as a
  placeholder to be superseded, not a permanent design.

---

## 3. Dataset Role Classification

| Dataset | Role | Why |
|---|---|---|
| ICMR-INDIAB | **B — Calibration Source** (primary for clinical risk factors); secondarily **C — Validation Reference** | Most clinically rigorous protocol (OGTT/measured, not just self-report) among the researched sources; individual-level restricted, but published age/sex-stratified prevalence is exactly the aggregate calibration input this strategy needs |
| ICMR-NNMS | **B — Calibration Source** (primary for behavioral risk factors); secondarily **C** | Richest behavioral data (smoking, alcohol, physical activity, diet); same access posture as INDIAB (aggregate only) |
| NFHS-5 | **B — Calibration Source** (primary for demographic/geographic backbone); secondarily **C** | Broadest sample, only source with confirmed district-level granularity; coarser clinical measurement than INDIAB, so not primary for clinical risk factors |
| LASI | **B — Calibration Source, scoped to the 45+ age band only** | Restricted to ages 45+; useful to enrich that specific high-CV-risk band, not as a general-population primary source |
| IHDS | **D — Contextual Source** | Individual-level access is open, but weak on clinical CV variables; strength is socioeconomic/household context, for which no schema field currently exists (see §15). Its ICPSR LLM-use restriction is a separate reason to keep any raw IHDS data out of any future LLM-touching pipeline stage, regardless of role. |
| NSS 75th Round | **D — Contextual Source** (currently **E — Not Used**, deferred) | Individual-level open, but represents healthcare-utilization/expenditure behavior, not a modality the current schema or M2C scope generates yet (`encounters` is unimplemented) |
| GBD India State-Level | **C — Validation Reference only** | Modeled aggregate synthesis, not a primary survey; must never be treated as an independent calibration input alongside the surveys it likely already incorporates |
| CREATE / STEMI-ACT | **E — Not Used** | No confirmed accessible individual- or aggregate-level dataset beyond a single dated (2008) published paper and a conference abstract; not population-representative (hospital-based cohort); usable only as narrative citation context (e.g., "X% of India's ACS admissions are STEMI per CREATE"), not as a generation or calibration input |

No dataset is forced into a role it doesn't support — in particular, nothing
here is classified as a Generation Input in the sense of feeding raw
individual records directly into the generator, because M2A did not
establish that any clinically-relevant source permits that.

---

## 4. Minimum Indian Conditioning Variables

Evaluated against the six required questions for every candidate field.
"Schema change?" answers refer only to whether the *container* exists
already (it does, as an untyped placeholder) vs. needing defined sub-keys —
see §15 for the full gap analysis.

### Demographics

| Field | Why needed | Source | Individual/Aggregate | Can influence generation? | Useful for CV modeling? | Schema change? |
|---|---|---|---|---|---|---|
| age | Drives nearly every downstream risk-factor prevalence | NFHS-5 (broadest), cross-checked NNMS/INDIAB | Aggregate (age-sex pyramid, published) | Yes — as a marginal sampling distribution | Yes, directly | No — field exists |
| sex | Large, evidence-backed differential in smoking, hypertension, diabetes prevalence | NFHS-5, NNMS, INDIAB | Aggregate | Yes — marginal, and as a conditioning variable for other fields | Yes, directly | No — field exists |

### Risk factors

| Field | Why needed | Source | Individual/Aggregate | Can influence generation? | Useful for CV modeling? | Schema change? |
|---|---|---|---|---|---|---|
| hypertension | Core CVD risk factor, directly measured in all 3 primary Indian sources | ICMR-INDIAB (primary, clinically measured), NNMS/NFHS (cross-check) | Aggregate (age/sex-stratified prevalence tables) | Yes, as age/sex-conditioned probability | Yes, directly | Sub-key formalization needed (container exists) |
| diabetes | Core cardiometabolic risk factor, OGTT-based in INDIAB | ICMR-INDIAB (primary) | Aggregate | Yes, as age/sex/BMI-conditioned probability where an adjusted association is published | Yes, directly | Sub-key formalization needed |
| BMI | Standard CV risk covariate; also lets `height_cm`/`weight_kg` (already implemented) be populated coherently | ICMR-INDIAB / NNMS / NFHS (all report it) | Aggregate | Yes, as age/sex-conditioned distribution | Yes, directly | Sub-key formalization needed |
| smoking status | Strongly sex-differentiated in every source; established CV risk factor | ICMR-NNMS (primary, finer categories), INDIAB (coarser, cross-check) | Aggregate | Yes, as sex/age-conditioned probability | Yes, directly | Sub-key formalization needed |
| hyperlipidemia / dyslipidemia | Established CV risk factor | ICMR-INDIAB **only** confirmed source, and only on a ~25,647-person sub-cohort (not the full ~107–111k sample) | Aggregate, but reduced coverage — flag this caveat wherever the figure is used | Yes, with the sub-sample caveat documented | Yes, directly | Sub-key formalization needed |
| family history of CVD | Would inform inherited-risk conditioning | **No source found in M2A confirms this variable for CVD specifically** (INDIAB captures family history of *diabetes*, not CVD) | N/A | **No — not currently supported by any researched Indian source** | Would be, if evidence existed | Sub-key formalization needed, but leave unpopulated until a source is found (see §17, OPEN) |

### Potential contextual fields

| Field | Why needed | Source | Individual/Aggregate | Can influence generation? | Useful for CV modeling? | Schema change? |
|---|---|---|---|---|---|---|
| region/state | Finer geographic realism; NFHS-5 supports district-level | NFHS-5 (primary if adopted), INDIAB's cardinal-region reporting (supplementary) | Aggregate | Yes, as an additional stratification axis | Indirect (through risk-factor variation by region) | **New field** — not currently in schema |
| urban/rural | Large, consistently-reported prevalence differences across every source (INDIAB samples both explicitly, NNMS stratifies 300/300 by design) | NFHS-5, NNMS, INDIAB all report it | Aggregate | Yes, as a stratification axis with outsized effect on several risk factors | Direct, evidence-backed | **New field** — not currently in schema |
| socioeconomic/context | Would let IHDS/NSS content connect to something | IHDS, NSS 75th Round | Individual-level (rare case where it's open) | Not without a schema container | Indirect at best; no schema destination | **New field**, and no immediate generation use case identified — defer (§15: OPTIONAL) |

**Conclusion:** the minimum viable set is age, sex, BMI, smoking status,
hypertension, diabetes, and dyslipidemia (with its coverage caveat) —
all directly evidence-supported by already-public aggregate statistics
from sources already classified as Calibration Sources. Family history of
CVD is explicitly excluded from the minimum set pending evidence.
Urban/rural is the strongest contextual candidate for inclusion given its
outsized, consistently-reported effect, but is not made a requirement of
this document — see §15 and §17.

---

## 5. Marginal vs. Joint Distribution Analysis

### What "marginal" means here
`P(hypertension)`, `P(diabetes)`, `P(smoking)`, `P(BMI category)` — a
single variable's population-level distribution, with no conditioning.
**Fully supported** by M2A's findings: every primary source publishes these
as aggregate, peer-reviewed/official prevalence figures with confidence
intervals.

### What "simple stratified conditional" means here
`P(hypertension | age band)`, `P(smoking | sex)`, `P(BMI | age band, sex)` —
a variable's distribution *within* a reported subgroup. This is a distinct,
weaker claim than full joint modeling: it only requires that the source
*already publishes* the subgroup breakdown (which age/sex/urban-rural
cross-tabs commonly are in these surveys' own reports), not that we have
access to individual records to compute it ourselves. **Likely available for
most of the minimum-set variables** (age, sex, and often urban/rural
breakdowns are standard in these reports), but M2A did not verify every
specific cross-tab for every variable — treat as **RESOLVED in principle,
OPEN per-variable**: each specific stratified table must be located and
cited before it's encoded as a configuration parameter (see M2C-0 in §16).

### What "documented multivariable association" means here
A published regression model's adjusted odds ratio or similar coefficient
(e.g., "diabetes odds increase with age and BMI, adjusted OR=X, 95% CI
[...]" from a peer-reviewed paper). This is **not** a joint distribution —
it's a single documented relationship that can be encoded as an explicit,
cited deterministic rule (e.g., a multiplicative adjustment to a baseline
probability). M2A did not systematically catalog which such associations
exist in the primary sources' full papers (only headline prevalence figures
were captured) — **OPEN**, would need targeted verification per
relationship before use, and each one used must carry its own citation, not
be treated as general modeling license.

### What "full joint/individual-record distribution" means here
`P(hypertension | diabetes, age, sex, BMI, ...)` estimated directly from
individual-level records showing the actual joint co-occurrence in a real
Indian population. **Not supported.** M2A found individual-level data for
ICMR-INDIAB, NNMS, NFHS-5, and LASI — the sources with the richest clinical
risk-factor content — to be restricted (query-mediated or request-gated),
and did not confirm the licensing terms even permit this kind of derived
use once obtained. IHDS and NSS 75th Round have open individual-level data
but weak clinical CV content, so they cannot fill this gap either.

**This document does not claim any joint clinical-risk-factor distribution
is available from Indian evidence.** Where dependencies are proposed in §6,
they are built from marginals, stratified aggregates, and (where cited)
documented associations — never an invented or assumed joint distribution.

### CVD diagnosis itself
No source in M2A provides Indian population-representative individual-level
data linking risk factors to a confirmed CVD diagnosis (CREATE/STEMI-ACT are
hospital-based, not population-representative, and largely inaccessible).
Any rule connecting generated risk factors to a generated CVD diagnosis
would currently have to be either (a) a transparently-labeled engineering
rule (not evidence-derived), or (b) based on a clinical risk-scoring
instrument (e.g., a WHO/ISH or similar risk chart recalibrated for South
Asian populations) — which is a **new evidence source not covered by M2A**
and would need its own verification pass before use. Flagged as OPEN in
§17, not resolved here.

---

## 6. Proposed Generation Dependency Graph

```text
Step 1 — age
  Marginal, calibrated primarily from NFHS-5 (broadest sample);
  cross-checked against NNMS/INDIAB age structure.

        ↓

Step 2 — sex
  Marginal, same sources. Generated early because it has a large,
  evidence-backed effect on several downstream fields (smoking especially).

        ↓

Step 3 — urban_rural (IF adopted — see §15, human checkpoint required)
  Marginal, from NFHS-5/NNMS/INDIAB. Generated early because M2A/this
  document found it has an outsized, consistently-reported effect on
  several risk factors across every source that reports it.

        ↓

Step 4 — BMI
  Conditioned on (age band, sex) using published stratified figures where
  located (M2C-0); height_cm/weight_kg (already-implemented schema fields)
  derived or sampled to stay internally consistent with BMI via a
  deterministic engineering rule (BMI = weight / height^2) — an engineering
  constraint, not a clinical claim.

        ↓

Step 5 — smoking_status
  Conditioned on sex primarily (very large, consistently-reported
  differential in every Indian source examined), secondarily age band.
  Primary source: ICMR-NNMS (finer categories).

        ↓

Step 6 — hypertension
  Conditioned on (age band, sex); BMI-conditioning only if a specific
  documented association is located and cited (§5's "documented
  multivariable association" tier) — not invented. Primary source:
  ICMR-INDIAB.

        ↓

Step 7 — diabetes
  Conditioned on (age band, sex); BMI-conditioning only if cited (as above).
  Primary source: ICMR-INDIAB.

        ↓

Step 8 — dyslipidemia / hyperlipidemia
  Conditioned on (age band, sex) where the source's stratified figures
  support it. Primary source: ICMR-INDIAB, WITH the sub-sample-size caveat
  carried into the config/provenance (see §14).

        ↓

Step 9 — family_history (CVD)
  NOT generated from Indian evidence — no source found. Leave unpopulated
  (None), or generate from an explicitly-labeled non-Indian-evidence
  placeholder ONLY if the project decides that's preferable to leaving it
  null — this is a decision for the M2C checkpoint, not made here (§17,
  OPEN).

        ↓

Step 10 — medical_history / diagnoses
  Deterministic engineering rules over the already-generated risk factors
  (e.g., documented, clearly-labeled thresholds), NOT a claimed Indian
  joint distribution (§5). Any use of a clinical risk-scoring instrument
  here is a new, unverified evidence source (§5) — OPEN.

        ↓

Step 11 — medications
  Depends on diagnoses. No Indian standard-of-care/prescribing-pattern
  source was researched in M2A — OPEN, out of scope for M2C's initial
  implementation.

        ↓

Step 12 — labs
  Partially informed by ICMR-INDIAB's glucose/lipid sub-sample data;
  otherwise depends on diagnoses/risk factors via engineering rules.

        ↓

Step 13 — encounters / clinical_timeline
  Primarily engineering/timeline logic (already partly implemented in M1 —
  `TimelineEvent`). NSS 75th Round could inform utilization-pattern realism
  contextually in a later stage — not required for M2C, OPTIONAL per §15.

        ↓

Step 14 — ECG / Echo
  Already-established track (M1, `docs/DECISIONS.md` D003) sourced from
  PTB-XL. NOTE: PTB-XL is a German cohort — this step is NOT Indian-
  conditioned, and generating Indian-conditioned demographics/risk-factors
  next to a non-Indian ECG source is an internal-coherence gap this
  document surfaces but does not resolve (§12, §17).
```

### Why not independent randomization

```text
age = random
sex = random
BMI = random
diabetes = random
hypertension = random
smoking = random
```

is insufficient because it discards exactly the evidence M2A gathered:
smoking prevalence in every Indian source examined is overwhelmingly higher
in males than females; hypertension/diabetes/BMI all vary substantially by
age; if generated independently, a synthetic population would produce
combinations (e.g., high smoking prevalence in young synthetic women)
directly contradicted by the cited sources, undermining the entire point of
this milestone. This also directly conflicts with `docs/Claude.md` §9's
patient-record philosophy, already invoked once in `docs/DECISIONS.md` D004
for the same reason.

### Separating evidence tiers (per instructions, do not conflate these)

- **Evidence-supported relationships:** age/sex-conditioned marginals for
  BMI, smoking, hypertension, diabetes, dyslipidemia (pending each specific
  stratified table's citation, M2C-0).
- **Project assumptions:** any placeholder used where no Indian evidence
  exists (e.g., if family history is populated at all rather than left
  null) must be labeled as such in provenance, never presented as
  Indian-evidence-derived.
- **Deterministic engineering rules:** BMI↔height/weight consistency,
  and any diagnosis/medication logic built from already-generated fields
  rather than from a cited population distribution.
- **Future modeling opportunities:** full joint/individual-level modeling
  (if restricted microdata access is ever obtained and its license
  confirmed to permit derived/synthetic use), and any CVD-diagnosis risk
  instrument (if verified) — both explicitly deferred, not designed here.

---

## 7. Dataset Definition Compatibility

Per M2A §13/§14, definitions are not confirmed identical across sources for
several key variables. Proposed handling (not implemented):

| Variable | M2A finding | Proposed approach |
|---|---|---|
| Hypertension | Exact BP cutoff not confirmed identical across INDIAB/NNMS/NFHS | **(3) Use one source as primary definition** — ICMR-INDIAB (clinically measured, most rigorous protocol among the three). Treat NNMS/NFHS figures as directional cross-validation only, never blended into a single merged number. Verify INDIAB's exact cutoff directly (M2C-0) before encoding it. |
| Diabetes | INDIAB uses OGTT/fasting-glucose criteria; NNMS uses single-visit capillary testing — different diagnostic rigor | **(3) Use ICMR-INDIAB as primary**; NNMS retained for behavioral-risk context only, not as an alternate diabetes-prevalence source to merge with INDIAB's. |
| BMI/obesity | Generally WHO-standard cutoffs believed used across sources, but not independently confirmed identical | **(2) Keep source-specific initially.** Treat as approximately comparable, but confirm each source's stated cutoff (M2C-0) before merging any figures across sources. |
| Smoking/tobacco | INDIAB: coarser (never/current/past); NNMS: finer (smoked vs. smokeless tracked separately) | **(1) Standardize to a canonical category set** informed by NNMS's finer scheme (the richer source) as the schema's intended granularity; downgrade to INDIAB's coarser scheme only when cross-referencing INDIAB figures. Document the mapping in the config (not implemented yet). |
| Age groups | LASI restricted to 45+; general surveys 15/18/20+ | **(3) Use general-population surveys (NFHS/NNMS/INDIAB) as primary for the full age range; use LASI only to enrich the 45+ band**, never as a conflicting primary source for younger ages. |
| Urban/rural definition | Mostly Census-based across sources; exact vintage/consistency not independently confirmed | **(2) Keep source-specific pending confirmation**; treat as approximately comparable with a documented caveat until verified. |
| Geographic classification | INDIAB reports cardinal regions; NFHS-5 reports state/district | **(3) Use NFHS-5 as the primary geographic reference (finest granularity) if geography is adopted at all (§15)**; INDIAB's regional reporting used only as supplementary validation. |
| Survey years | INDIAB 2008–2020 (5 phases); NNMS 2017–18; NFHS-5 2019–21; IHDS 2004–05/2011–12 (oldest, and status of a newer wave unresolved per M2A) | Prioritize the most recent applicable wave per variable; treat IHDS as historical context only, never as a current-year demographic source, consistent with M2A's freshness finding. Record each parameter's source year alongside it in configuration (§14). |

None of this standardization is implemented in this milestone — this table
is the proposed approach for M2C to execute, starting with M2C-0's direct
verification pass.

---

## 8. Access/Licensing Constraints

Summarized from M2A (`docs/INDIAN_DATA_SOURCES.md` §10); not re-derived
here.

```text
What we can directly use today:
  - Published aggregate prevalence figures (with citations) from
    ICMR-INDIAB, ICMR-NNMS, and NFHS-5 peer-reviewed papers / official
    factsheets — already public, no access request needed.

What requires access (not pursued in this milestone):
  - Individual-level ICMR-INDIAB / NNMS data (NHRDR query-mediated)
  - Individual-level NFHS-5 / LASI data (registration/request-gated)

What is aggregate-only by nature:
  - GBD India State-Level Disease Burden Initiative (validation use only,
    §3)

What is restricted with an EXPLICIT usage bar found:
  - IHDS microdata — ICPSR terms bar feeding it to any LLM that retains or
    trains on it. Not used as a generation input in this strategy at all
    (classified Contextual/D, deferred — §3), so this bar is not currently
    triggered, but it must be re-checked before IHDS is used in any future
    stage that involves an LLM.

What is still legally/operationally unclear:
  - Whether synthetic-data generation derived from ANY of the eight
    datasets is licensed — M2A found this `Not verified` for every source
    examined, and this document does not resolve it.
```

**Design consequence:** this strategy deliberately restricts M2C's initial
scope to already-public aggregate statistics precisely because that
sidesteps the unresolved "does the license permit synthetic-data
generation" question for individual-level data — citing a published
prevalence figure as a calibration parameter in our own configuration is a
categorically different act from deriving/redistributing from restricted
microdata. **This is a design rationale, not a legal conclusion** — it is
recommended that a human/legal reviewer confirm this reasoning before M2C-2
encodes any parameters, especially since even public aggregate figures
still carry citation obligations (already planned for, §14).

---

## 9. Fallback Strategy

```text
Tier 1 — Preferred:
  Age/sex-stratified published prevalence from ICMR-INDIAB / ICMR-NNMS /
  NFHS-5 (clinically measured where available, nationally representative,
  already public).

        ↓ specific stratified table not locatable for a given variable?

Tier 2 — Broader aggregate:
  Unstratified national marginal from the same or another already-public
  Indian source (e.g., a national prevalence figure without the age/sex
  breakdown).

        ↓ no Indian aggregate exists at all for this variable?
        (This is the case today for: family history of CVD)

Tier 3 — Public-use individual-level Indian dataset:
  Only for non-clinical context variables where IHDS/NSS 75th Round might
  apply (e.g., a future socioeconomic field) — NOT used to fill a clinical
  gap, since neither source has the needed clinical content.

        ↓ still nothing?

Tier 4 — Transparent, explicitly-labeled project assumption:
  A stated placeholder (e.g., leaving the field null, or a clearly-labeled
  non-Indian-evidence default), never presented as Indian-evidence-derived.

        ↓

Tier 5 — Documented limitation:
  Recorded in the patient's own `provenance` (schema field already exists,
  no change needed to record this) and in `docs/DECISIONS.md`/
  `docs/PROJECT_STATE.md` at implementation time.
```

Applying this today: demographics, BMI, smoking, hypertension, diabetes, and
dyslipidemia all resolve at **Tier 1**. Family history of CVD resolves at
**Tier 4/5** — left unpopulated, with the limitation documented, rather than
invented. This fallback hierarchy means development is **not** blocked on
ever obtaining restricted ICMR/NFHS/LASI microdata — the minimum viable
layer needs only Tier 1/2 (already-public) data.

---

## 10. Validation Strategy

### Demographic validation
- Age distribution vs. NFHS-5 (primary) / Census.
- Sex distribution vs. NFHS-5 / NNMS.
- Urban/rural distribution vs. NFHS-5 / NNMS/INDIAB, **only if that field is
  adopted** (§15).
- Region/state distribution — **only if that field is adopted**, and only
  against NFHS-5 (the sole source with confirmed district-level breakdowns).

### Risk-factor validation
- BMI distribution vs. INDIAB/NNMS/NFHS (whichever was used as the *primary*
  calibration source for a given cell — see below on avoiding circularity).
- Hypertension prevalence vs. INDIAB (primary calibration source; see
  circularity note).
- Diabetes prevalence vs. INDIAB.
- Smoking prevalence vs. NNMS.
- Hyperlipidemia prevalence vs. INDIAB, **with its sub-sample caveat carried
  into the validation report, not silently dropped.**

### Avoiding circular validation (a methodological point not explicit in the
milestone brief, but necessary given the sources available)
Where the *same* published figure both calibrates the generator and is used
to validate its output, the "validation" is close to vacuous — it mostly
confirms the sampling code works, not that the population is realistic.
Where more than one source reports the same stratified statistic (e.g.,
hypertension by age/sex appears in both INDIAB and NFHS), the strategy
should **calibrate from one and validate against the independent figure
from the other**, wherever that's possible, rather than validating against
the exact number used to generate.

### Conditional validation where evidence permits
- Hypertension by age group (against whichever source wasn't used to
  calibrate, per the circularity note above).
- Diabetes by age group (likewise).
- Smoking by sex (likewise).
- BMI by age/sex (likewise).

### What is explicitly NOT proposed
No validation against multi-way joint distributions, individual-level
co-occurrence statistics, or any figure this document has not confirmed is
publicly obtainable (§5, §8) — consistent with not claiming evidence this
project doesn't have.

### Reuse opportunity (not a new build)
`syngen/SynGen/SynGen/evaluate_class.py` already implements distribution-
comparison statistics (KS test, KL divergence, per-variable summary stats)
for comparing real vs. synthetic ECG signal distributions
(`docs/syngen-codebase-analysis.md` §8). The same statistical machinery is
directly applicable to comparing a generated population's age/sex/
risk-factor marginals against the published Indian figures above —
`CLAUDE.md` §3's "reuse before rebuild" principle applies here too. This is
a design note for M2C, not implemented in this milestone.

---

## 11. Definition of "Indian" for This Project

Explicitly, "Indian conditioning" in this project means: the generated
population's **age structure, sex ratio, and cardiometabolic risk-factor
prevalence (hypertension, diabetes, BMI/obesity, dyslipidemia, smoking)**
are calibrated to match published Indian national statistics from the
sources classified as Calibration Sources in §3, **and**, if adopted per
§15, **urban/rural** and **region/state** distribution.

It does **not** mean, and this project should not claim it means:
- Reproduction of any real individual's data (already a hard rule —
  `CLAUDE.md` §10/§31, and already respected in M1's PTB-XL reuse — see
  `docs/DECISIONS.md` D004).
- Genetic, ethnic, linguistic, or religious subgroup variation within India
  — no source researched supports this, and it was not investigated.
- Fine-grained socioeconomic microsegmentation — no schema field exists,
  and no immediate generation use case was identified (§15: OPTIONAL, not
  pursued).
- Indian-population-specific ECG/echo signal characteristics — the current
  ECG source (PTB-XL) is German, a known limitation carried forward from
  §6/§12, not addressed by this document.
- Real Indian healthcare-system treatment/prescribing patterns —
  medications generation (§6 Step 11) has no researched Indian evidence
  source and is explicitly OPEN.

---

## 12. Representativeness Limitations

Per instructions, this project must not claim:

> "This is a representative synthetic Indian population."

unless validation evidence actually supports that specific, scoped claim.
Recommended language instead, to be used once any Indian-conditioned
generation exists:

> "Synthetic cardiovascular records conditioned using selected, cited
> Indian population evidence (age/sex-stratified prevalence from
> ICMR-INDIAB, ICMR-NNMS, and NFHS-5)."

Even this should be scoped to the specific validated dimensions once
validation (§10) actually runs — e.g., "the generated population's
age-sex-hypertension marginal distribution matches [source]'s published
estimate within [X]" is a defensible, specific claim; "representative of
India" is not, absent nationwide multi-dimensional validation this project
has not designed or run.

**Known limitation to carry forward prominently:** the ECG modality (M1,
Stage 4) is sourced from PTB-XL, a German population. Any representativeness
claim about the *overall* patient record — not just its demographic/risk-
factor fields — must account for this mismatch. This document does not
propose a resolution; it is raised here so it isn't silently forgotten by
the time Stage 4/10 converge.

---

## 13. Minimal Architecture

```text
configs/indian_population.yaml   (IndianPopulationConfig)
              ↓
generation/indian_calibration.py  (Distribution / Calibration Layer —
                                    pure functions over the config: marginal
                                    + age/sex-stratified sampling, and any
                                    cited documented-association rules)
              ↓
integration/build_patient.py   (Patient Generator — extended to call the
                                 calibration layer in the §6 dependency
                                 order, replacing the M1 PTB-XL-demographics
                                 placeholder per D004)
              ↓
schemas/patient_schema.py   (Patient Record — risk_factors/family_history
                              formalized from untyped dict into defined
                              sub-fields; see §15)
              ↓
validation/   (extended with a statistical/distribution module alongside
               the existing validation/structural.py, reusing syngen's
               KS/KL comparison approach — §10)
```

Placement rationale: `docs/Claude.md`/top-level `CLAUDE.md` §4 both require
the `generation/` layer to stay isolated from schema/ingestion/validation,
and the Candidate A structure (`docs/DECISIONS.md` D001) already reserves
`generation/` for exactly this kind of synthetic-data-generation logic —
this is a placement recommendation for M2C, consistent with the existing
architecture decision, not a new one.

Design properties (per instructions):
- **Deterministic where appropriate** — seeded RNG, matching M1's existing
  `(sequence, seed)` reproducibility pattern (`integration/build_patient.py`,
  `docs/session_logs/2026-09-25_M1-foundation.md`).
- **Configurable** — every distribution parameter lives in YAML, not
  hardcoded, per `CLAUDE.md` §6.
- **Reproducible** — same seed → same generated population.
- **Testable** — pure sampling functions over an explicit config, following
  the same pattern as `validation/structural.py`'s pure `validate_patient()`.
- **Easy to replace later** — a `CalibrationSource`-style interface (the
  same spirit as `ml/interfaces.py`'s existing model-agnostic contracts,
  `ml/README.md`) would let a future ML-based or CardioSynth-informed
  generator swap in without changing the schema/validation layers — a
  design note for M2C, not built here.

No ML training, fine-tuning, GAN, LLM generation, or AWS infrastructure is
part of this architecture, per this milestone's restriction.

---

## 14. Configuration Requirements

Each parameter below is a **requirement to document**, not a value to
encode in this milestone.

| Parameter | Intended source | Individual/Aggregate | Marginal or conditional | Expected format/units | Update cadence |
|---|---|---|---|---|---|
| `age_distribution` | NFHS-5 (primary) | Aggregate | Marginal | Age-band → population share (%) | Re-verify on NFHS-6 publication |
| `sex_ratio` | NFHS-5 | Aggregate | Marginal | Male/female share (%) | Re-verify on NFHS-6 publication |
| `urban_rural_distribution` *(if adopted, §15)* | NFHS-5 | Aggregate | Marginal | Urban/rural share (%) | Re-verify on NFHS-6 |
| `bmi_by_age_sex` | ICMR-INDIAB / NNMS (M2C-0 to pick primary per cell) | Aggregate | Age×sex-stratified | Mean/SD or category-share per (age band, sex) cell, with source-year tag | Re-verify on next INDIAB phase or NNMS wave |
| `smoking_by_sex_age` | ICMR-NNMS (primary) | Aggregate | Sex×age-stratified | Category share (%) per (sex, age band), with source-year tag | Re-verify on next NNMS wave |
| `hypertension_by_age_sex` | ICMR-INDIAB (primary) | Aggregate | Age×sex-stratified | Prevalence (%) with 95% CI per cell, with source-year tag and the exact BP cutoff used (M2C-0) | Re-verify on next INDIAB phase |
| `diabetes_by_age_sex` | ICMR-INDIAB (primary) | Aggregate | Age×sex-stratified | Prevalence (%) with 95% CI per cell, source-year tag, diagnostic method noted (OGTT) | Re-verify on next INDIAB phase |
| `dyslipidemia_by_age_sex` | ICMR-INDIAB **only** | Aggregate, reduced-coverage sub-sample | Age×sex-stratified | Prevalence (%) with 95% CI, **explicit sub-sample-size annotation** | Re-verify on next INDIAB phase |
| `family_history_cvd` | **None found** | N/A | N/A | N/A — field left unpopulated per §6/§9 unless/until a source is found | Re-check if M2A is ever revisited |
| `region_state_distribution` *(if adopted, §15)* | NFHS-5 (finest granularity) | Aggregate | Marginal, state/district-level | State/district → population share (%) | Re-verify on NFHS-6 |

Every parameter's config entry should carry its source dataset, publication
year, and the exact citation — not just the number — so staleness (§7's
survey-years concern) is visible at a glance rather than silently baked in.

---

## 15. Schema Gap Analysis

| Field | Classification | Reasoning |
|---|---|---|
| `risk_factors` sub-keys (hypertension, diabetes, bmi, smoking_status, dyslipidemia) | **REQUIRED** | Needed to hold the minimum-set variables identified in §4; the container already exists (`Optional[dict]`), only its internal structure needs formalizing — additive, low-risk, but still a schema change requiring the human checkpoint this milestone defers to M2C (§16) |
| `family_history` sub-key for CVD | **REQUIRED (structurally), but leave unpopulated** | The container should exist so the field's *absence* of Indian evidence is visible (e.g., `None` with a documented reason) rather than the field simply not existing at all |
| `urban_rural` | **USEFUL** | Outsized, consistently-reported effect on risk-factor prevalence across every source examined (§4); not classified REQUIRED because a defensible minimum layer can function on national marginals alone — but it's the strongest candidate for a first schema addition beyond the risk-factor sub-keys |
| `region`/`state` | **USEFUL** | Adds geographic realism and validation granularity (NFHS-5 supports it down to district level), but not necessary for a first defensible layer; weaker case than urban/rural since no researched source showed as large an effect specifically attributable to region alone (as opposed to urban/rural, which several sources report as a primary stratification axis) |
| `socioeconomic_context` | **OPTIONAL** | IHDS/NSS data exists and is even openly accessible, but no concrete generation use case was identified in this document, and IHDS carries the LLM-use restriction (§8) worth avoiding until there's an actual need |
| Signal/waveform-level Indian-population ECG source | **NOT NEEDED for this milestone** | Out of scope — PTB-XL/Stage 4 concern (§12), not a demographic/risk-factor schema question |

**No schema change is made in this milestone.** Per instructions, if a
change is judged necessary, it is reported here rather than implemented:

> **Proposed schema change (for M2C, human checkpoint required per
> `CLAUDE.md` §28's "major schema change" trigger, even though each
> individual change is additive/non-breaking):**
> 1. Formalize `risk_factors` from `Optional[dict]` into a typed dataclass
>    with fields: `bmi`, `hypertension`, `diabetes`, `smoking_status`,
>    `dyslipidemia` (all `Optional`, since not every patient will have
>    every field populated depending on which fallback tier applied, §9).
> 2. Formalize `family_history` similarly, with at least a `cvd` field that
>    can be `None` with a documented reason.
> 3. **Decide** (not decided here) whether to add `urban_rural` and/or
>    `region`/`state` to `Demographics` — both are additive `Optional`
>    fields if adopted, so low structural risk, but still a real product
>    decision about how far Indian conditioning should reach in this
>    project's timeline (§17, OPEN).

---

## 16. M2C Implementation Plan

Adjusted from the illustrative template based on this document's actual
findings — not implemented in this milestone.

```text
M2C-0
Verify exact definitions/cutoffs (hypertension BP threshold, diabetes
diagnostic criterion, BMI cutoff convention, smoking category granularity)
directly from each primary source's own methodology chapter/questionnaire,
resolving the "Not verified"s in §7 before any number is encoded.

M2C-1
Human checkpoint: decide the schema changes proposed in §15 (risk_factors/
family_history formalization — low-risk; urban_rural/region adoption —
a real scope decision). Implement only what's approved.

M2C-2
Create `configs/indian_population.yaml` (IndianPopulationConfig) — only
already-public aggregate parameters per §14, each with source/year/
citation attached. No restricted-data dependency.

M2C-3
Implement `generation/indian_calibration.py` — deterministic, seeded,
dependency-ordered per §6 (age → sex → [urban_rural] → BMI → smoking →
hypertension → diabetes → dyslipidemia), pure functions over the config.

M2C-4
Integrate into `integration/build_patient.py`, replacing the M1 PTB-XL-
demographics placeholder (superseding `docs/DECISIONS.md` D004 with a new,
dated decision entry rather than silently overwriting it).

M2C-5
Add internal-consistency engineering rules (e.g., BMI↔height/weight
coherence), clearly labeled in provenance as engineering rules, not
Indian-evidence-derived.

M2C-6
Generate + structurally validate 10 patients, reusing/extending
`validation/structural.py`.

M2C-7
Add a statistical/distribution validation module (reusing syngen's KS/KL
comparison approach, §10), validating against an independent source from
the one used to calibrate wherever possible (avoiding the circularity
noted in §10).

M2C-8
Generate 100 patients (dovetails with the existing Stage 3/M3 milestone
already in `docs/PROJECT_STATE.md`/`docs/Claude.md`), run statistical
validation, document results.

M2C-9
Update `docs/DECISIONS.md` and `docs/PROJECT_STATE.md`; human checkpoint
before pursuing any restricted-data access application or before scaling
beyond 100 patients.
```

---

## 17. Open Questions

- Which Indian source should be the primary calibration reference for each
  specific variable? **RESOLVED — evidence: §3/§7** (ICMR-INDIAB for
  clinical risk factors, ICMR-NNMS for behavioral, NFHS-5 for demographic/
  geographic backbone, LASI for 45+ enrichment only) **for the sources
  researched in M2A; individual stratified-table citations still OPEN
  (M2C-0).**
- Which variables require individual-level data? **RESOLVED — evidence:
  §5** (none of the minimum-set variables require it; only full
  multi-way joint modeling would, and that's explicitly out of scope.)
- Which aggregate statistics are sufficient? **RESOLVED — evidence: §4/§6**
  (marginal and age/sex-stratified aggregates for the minimum set), but
  **OPEN** per the specific citation for each stratified cell (M2C-0).
- Which definitions should become canonical? **Proposed in §7, not yet
  verified — OPEN pending M2C-0.**
- Should region/state be included in the patient schema? **OPEN** — §15
  classifies it USEFUL, not REQUIRED; a product/scope decision for the
  M2C-1 human checkpoint.
- How should urban/rural conditioning be handled? **OPEN** — §15
  classifies it as the strongest contextual candidate, but adoption itself
  is a human-checkpoint decision, not resolved here.
- What level of Indian population conditioning is defensible within the
  project timeline? **OPEN** — this document proposes a minimum viable
  layer (§4) as defensible now; broader conditioning (region, socioeconomic
  context, joint modeling) is explicitly deferred, not ruled out.
- Which data sources can legally and practically be used for synthetic-data
  generation? **OPEN** — M2A found this unresolved for every dataset; §8's
  design response (use only public aggregate figures) sidesteps rather than
  answers this question, and is explicitly flagged as not a legal
  conclusion.
- Which characteristics should be validation-only? **RESOLVED — evidence:
  §3** (GBD India State-Level; and, more narrowly, whichever of two sources
  reporting the same stratified statistic is *not* chosen as the
  calibration source for that cell, per §10's circularity note).
- Does the current ECG source (PTB-XL, German) undermine any
  representativeness claim about the *complete* patient record, even if
  demographics/risk-factors are well Indian-calibrated? **OPEN** —
  surfaced in §11/§12, not resolved; a Stage 4/10 question.
- Should a populated (vs. left-null) placeholder be used for family history
  of CVD, given no Indian source exists? **OPEN** — §6/§9 lean toward
  leaving it null, but this is a product decision, not made here.
- Is there a verifiable, citable clinical CVD-risk instrument (e.g., a
  South-Asian-recalibrated risk chart) that could support Step 10's
  diagnosis-generation logic? **OPEN** — this would be a new evidence
  source requiring its own M2A-style verification pass before use.

---

## 18. Decision Recommendations

These are recommendations for the M2C checkpoint to accept, reject, or
modify — not implementation decisions made by this document.

1. **Use ICMR-INDIAB as the primary calibration source for clinical risk
   factors** (hypertension, diabetes, BMI, dyslipidemia); **ICMR-NNMS as
   primary for behavioral risk factors** (smoking, alcohol, physical
   activity); **NFHS-5 as primary for demographic/geographic backbone**
   (age, sex, and urban/rural or region if adopted); **LASI scoped strictly
   to the 45+ age band as an enrichment layer**.
2. **Defer IHDS and NSS 75th Round** — contextual role only, not required
   for the minimum viable layer; revisit only if a socioeconomic schema
   section is separately justified.
3. **Use GBD India State-Level strictly as a post-hoc validation
   reference**, never as an independent calibration input alongside the
   primary surveys it likely already incorporates.
4. **Do not use CREATE/STEMI-ACT** as a data source at this time — citation
   context only, pending resolution of their accessibility.
5. **Restrict M2C-2's initial configuration to already-public aggregate
   statistics only** — no dependency on restricted ICMR-INDIAB/NNMS/NFHS-5/
   LASI microdata, sidestepping the unresolved synthetic-data-generation
   licensing question for this first implementation (§8) while allowing
   development to proceed.
6. **Leave `family_history.cvd` unpopulated** rather than invent a
   placeholder, pending either a located Indian source or an explicit
   product decision to use a clearly-labeled non-Indian default.
7. **Recommend adopting `urban_rural`** as a schema addition at the M2C-1
   checkpoint, given its outsized and consistently-reported effect across
   every source examined; **treat `region`/`state` and
   `socioeconomic_context` as lower-priority, deferrable additions.**
8. **Place the calibration/sampling logic under `generation/`**, per the
   existing architecture isolation rule and the Candidate A structure
   decision (`docs/DECISIONS.md` D001) — do not let it leak into
   `schemas/`, `ingestion/`, or `validation/`.
9. **Run M2C-0 (definition verification) before encoding any numeric
   parameter** — several of this document's proposed approaches (§7) rest
   on assumptions about source definitions that M2A did not confirm and
   this document does not either.
10. **Surface the PTB-XL/German-ECG-source mismatch explicitly** in any
    future representativeness claim or Stage 4/10 planning — not resolved
    here, but should not be silently forgotten.

---

## Verification Notes

This document performs no new web research — every factual claim traces
back to `docs/INDIAN_DATA_SOURCES.md` (M2A) or to this session's own prior
work (`schemas/patient_schema.py`, `docs/DECISIONS.md`,
`docs/session_logs/2026-09-25_M1-foundation.md`). Where M2A left something
`Not verified`, this document preserves that status rather than resolving
it by assumption, and marks its own new open questions explicitly as
`OPEN` rather than silently deciding them.
