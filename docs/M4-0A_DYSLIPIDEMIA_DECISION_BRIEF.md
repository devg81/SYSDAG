# M4-0A — Dyslipidemia Evidence Conflict: Decision Brief

**Milestone:** M4-0A (research/documentation only — no code, schema, or
generator changes).
**Status:** Research complete. Two decisions await explicit human
input; nothing is finalized here.
**Date:** 2026-09-26

---

## Correction to M4-0's framing

M4-0's report characterized the new figure as "~90%." Deeper primary-
source verification in this pass found the actual reported figure is
**87.3%**, not ~90% — the earlier "nearly 9 in 10" phrasing was an
imprecise paraphrase carried over from a summary source, not the paper's
own stated number. This brief uses 87.3% throughout.

---

## Conflict 1 — Dyslipidemia Prevalence

### Source A — ICMR-INDIAB-17 (currently configured value: 81.2%)

| Field | Value |
|---|---|
| Exact study | Anjana RM et al., "Metabolic non-communicable disease health report of India: the ICMR-INDIAB national cross-sectional study (ICMR-INDIAB-17)," *Lancet Diabetes & Endocrinology* 2023;11(7):474-489 |
| Publication year | 2023 |
| Population | 113,043 adults ≥20y, national (31 states/UTs + NCT Delhi), fieldwork Oct 2008-Dec 2020 |
| Sample size | Full cohort 113,043 (rural 79,506 / urban 33,537); lipid sub-sample **25,647 measured, 18,492 with complete data** |
| Geographic scope | National |
| Age range | 20+ |
| Sex composition | Not confirmed specifically for the lipid sub-sample (overall cohort composition known; sub-sample breakdown not located) |
| Urban/rural composition | Not confirmed specifically for the 18,492 lipid sub-sample |
| Dyslipidemia definition | Composite via **NCEP/ATP III criteria**: any of TC≥200, TG≥150, HDL<40(M)/<50(F), LDL≥130 (all mg/dL) |
| Lipid thresholds used | TC≥200, TG≥150, HDL<40M/<50F, **LDL≥130** |
| Age-standardized or crude | Crude/weighted (complex multistage survey weighting); no indication of age-standardization |
| Nationally representative | Yes, explicitly claimed |
| **Reported prevalence** | **81.2%** (14,895/18,492) |
| Per-component detail | TC≥200: 24.0%; TG≥150: 32.1%; **HDL low: 66.9%** (dominant component); LDL≥130: 20.9% |
| Limitations | Measured on a sub-sample (~16% of the full cohort), not the full 113,043 |

### Source B — ICMR-INDIAB-25 (new figure: 87.3%, not "~90%")

| Field | Value |
|---|---|
| Exact study | "Prevalence of dyslipidemia in India: The ICMR-INDIAB National Study (ICMR-INDIAB-25)," *Journal of Clinical Lipidology*, 2026 |
| Publication year | 2026 |
| Population | 121,078 adults ≥20y, national, all states/UTs |
| Sample size | Lipid sub-sample: every 5th participant, **n=23,665** (approx. urban 7,026 / rural 16,636, per an earlier pass's fork finding) |
| Geographic scope | National |
| Age range | 20+ |
| Sex composition | Reported directionally as "higher among females"; no specific % breakdown confirmed |
| Urban/rural composition | Reported directionally as "higher in urban areas"; approx. sub-sample split noted above |
| Dyslipidemia definition | Composite via **Lipid Association of India (LAI) guidelines**: any of TC≥200, TG≥150, HDL<40(M)/<50(F), **LDL≥100** (all mg/dL) |
| Lipid thresholds used | TC≥200 (same as NCEP), TG≥150 (same as NCEP), HDL<40M/<50F (same as NCEP), **LDL≥100 (stricter than NCEP's 130)** |
| Age-standardized or crude | Crude/weighted ("weighted prevalence" stated); no indication of age-standardization |
| Nationally representative | Yes, explicitly claimed |
| **Reported prevalence** | **87.3%** |
| Per-component detail | **HDL low: 66.8%** (nearly identical to INDIAB-17's 66.9%) |
| Limitations | Total cohort (121,078) differs from INDIAB-17's (113,043) — appears to be a different/expanded phase, not a re-analysis of the same data |

### Are 81.2% and 87.3% measuring the same thing?

**Classification: primarily B (different definitions), with a secondary,
smaller contribution from C (different populations/phases) — explicitly
NOT A (direct contradiction), and not primarily D.**

Reasoning: the two studies share **identical TC, TG, and HDL cutoffs**.
The dominant component (low HDL-C) is **nearly identical between the two
studies** (66.9% vs. 66.8%) — meaning the shared components are not
driving the gap. The one component that **differs** (LDL: ≥130 vs. ≥100
mg/dL) is the most plausible explanation for the ~6-point overall gap,
since a stricter cutoff mechanically increases how many people qualify
as having "any" abnormal component in an any-of-four composite
definition. A secondary, smaller contribution from differing cohort
size/phase (113,043 vs. 121,078 total, suggesting a later/expanded
program phase rather than identical sampling) cannot be ruled out, since
neither figure is age-standardized and the two survey rounds' age
compositions weren't compared directly in this pass. **Neither figure is
wrong.** They are internally valid answers to two subtly different
operational questions.

---

## Conflict 2 — LDL Cutoff

### NCEP (≥130 mg/dL — currently configured)

- **Intended clinical context:** part of NCEP ATP III's 5-tier LDL
  classification (<100 optimal / 100-129 near-optimal / **130-159
  borderline-high** / 160-189 high / ≥190 very high).
- **Risk stratification assumptions:** NCEP ATP III is explicitly
  **risk-stratified, not a single fixed threshold** — actual treatment
  goals depend on a person's overall CHD-risk category (0-1 risk
  factors / 2+ risk factors / established CHD or CHD-risk-equivalent),
  each with its own LDL goal.
- **Defines "elevated LDL"?** Used this way in population-surveillance
  research (as INDIAB-17 does) — yes, operationally. As NCEP's own
  document, it's a classification tier, not a single elevated/normal
  binary.
- **Diagnostic threshold?** Not a disease diagnosis threshold per se —
  a population/screening classification boundary, repurposed by
  epidemiological studies for prevalence reporting.
- **Treatment threshold?** Not directly — treatment initiation in the
  ATP III framework depends on overall risk category, not LDL alone at
  this mark (someone with 0-1 risk factors may not be treated until
  LDL≥190).
- **Target threshold?** Coincidentally, 130 mg/dL is also the LDL *goal*
  for people with 2+ risk factors specifically in the ATP III framework
  — but this is a risk-category-specific goal, not a universal target.
- **Population/context intended:** general (originally US) adult
  population; adopted in Indian research (both PMC4016101 and
  INDIAB-17) in the absence of a Indian-specific standard at the time.
- **Appropriate for synthetic population labeling?** Reasonably, as a
  population-prevalence classification consistent with what INDIAB-17
  (this project's currently-cited source) actually reported. Less
  appropriate if the goal is simulating individual clinical
  treatment-eligibility, which needs the full risk-category logic, not
  a single LDL number.

### Lipid Association of India / LAI (≥100 mg/dL — new)

- **Intended clinical context:** LAI consensus statements/guidelines,
  developed specifically for the Indian/South Asian population.
- **Risk stratification assumptions:** LAI's documented *treatment
  targets* are notably more aggressive than NCEP's (e.g., <50 mg/dL
  general goal, <30 mg/dL for extreme-risk secondary prevention, per
  this pass's research) — reflecting a view that Indians carry elevated
  cardiometabolic risk at any given LDL level. **This connection between
  LAI's aggressive treatment philosophy and their specific 100 mg/dL
  prevalence-screening cutoff is this brief's interpretation, not a
  directly-confirmed citable rationale** — a specific sentence
  explaining *why* the prevalence cutoff is 100 (as opposed to why
  their *treatment goals* are aggressive) was not located.
- **Defines "elevated LDL"?** Used this way in INDIAB-25's prevalence
  reporting — yes, operationally, analogous in role to NCEP's 130.
- **Diagnostic threshold?** Same role as NCEP's — a population
  screening/classification boundary, not a disease diagnosis per se.
- **Treatment threshold?** No — LAI's actual treatment *targets* (once
  someone is already being managed) are far lower (<50/<30 mg/dL) than
  this 100 mg/dL prevalence-screening boundary. The 100 mg/dL figure
  appears to be LAI's "not-optimal, needs attention" screening boundary,
  distinct from their much-more-aggressive treatment goals.
- **Target threshold?** No, for the reason above.
- **Population/context intended:** specifically developed for
  Indian/South Asian patients.
- **Appropriate for synthetic population labeling?** Arguably *more*
  contextually appropriate (India-specific) than NCEP's US-derived
  boundary, if the project wants an India-specific clinical framing —
  but adopting it would represent a genuine departure from what this
  project's primary source (INDIAB-17) actually used, not a "correction"
  of an error, and would raise the encoded prevalence relative to what's
  currently in `configs/indian_population.yaml`.

### Critical clarification (per this milestone's own instruction)

**A clinical treatment target is NOT the same as a population-
distribution threshold — and neither NCEP's 130 nor LAI's 100, *as used
in these two prevalence studies*, is a treatment-initiation threshold.**
Both are population-classification/screening boundaries adapted for
epidemiological reporting. Neither guideline body says "treat everyone
above this number" — both make actual treatment decisions depend on
overall cardiovascular risk category. This distinction matters because
it means the choice between 130 and 100 is a choice about **which
population-surveillance convention to follow**, not a choice about
clinical treatment policy.

---

## Dataset Design Question — Generation Variable vs. Derived Clinical Label

**Not decided here.** Four architectural options, with consequences:

### A. Generate the clinical label first, generate LDL conditionally
Mirrors this project's existing BMI pattern (category from evidence,
then a within-category continuous value as an engineering
approximation). **Pro:** the label itself is directly evidence-backed
(we have solid category-level prevalence). **Con:** the "which
threshold" conflict resurfaces at the LDL-value-generation step — if the
label is "high LDL," which cutoff does the generated continuous value
need to exceed?

### B. Generate LDL continuously first, derive the label downstream
**Pro:** cleanest separation of generation-evidence from clinical
interpretation; a future session could reinterpret under a different
guideline without regenerating data. **Con:** requires a continuous
LDL mean/SD/percentile distribution, which **M4-0 confirmed does not
exist in any source examined** — not implementable today without
inventing a distribution shape, which this project does not do.

### C. Keep both independently generated
**Not recommended.** Recreates exactly the "two independently-random,
inconsistent representations of the same fact" problem this project has
already explicitly avoided elsewhere (`docs/DECISIONS.md` D004, and the
risk-factors→diagnoses "derive, don't duplicate" principle in
`docs/CLINICAL_RECORD_DESIGN.md` §E). Listed for completeness, not
because it's viable.

### D. Store category membership at multiple thresholds, no single continuous value
Since both NCEP-classified and LAI-classified category fractions are now
known (from these same two papers), a patient's LDL status could be
represented as two independent derived flags (`elevated_ldl_ncep`,
`elevated_ldl_lai`) from one underlying evidence-backed category
assignment, without ever synthesizing a single continuous number that
isn't evidence-supported. **Pro:** avoids inventing a continuous
distribution; defers the "which guideline is canonical" choice to
interpretation time rather than generation time. **Con:** more schema
complexity than a single field; still requires deciding the underlying
category-assignment probability (which itself depends on picking a
data-source/definition, same underlying question).

**No option above is selected in this document.**

---

## Source Comparability Matrix

| Issue | Source A (INDIAB-17) | Source B (INDIAB-25) | Comparable? | Why/Why Not | Implication |
|---|---|---|---|---|---|
| Dyslipidemia prevalence | 81.2% | 87.3% | Partially | Same composite concept, different LDL cutoff | ~6pt gap plausibly explained by the LDL threshold difference alone |
| LDL cutoff | ≥130 mg/dL (NCEP) | ≥100 mg/dL (LAI) | No | Different guideline bodies, different underlying risk philosophy | Primary driver of the prevalence gap |
| HDL cutoff | <40M/<50F mg/dL | <40M/<50F mg/dL | Yes | Identical | Confirms HDL isn't the source of the gap (66.9% vs. 66.8%) |
| TC cutoff | ≥200 mg/dL | ≥200 mg/dL | Yes | Identical | Not a source of the gap |
| TG cutoff | ≥150 mg/dL | ≥150 mg/dL | Yes | Identical | Not a source of the gap |
| Total cohort size | 113,043 | 121,078 | No | Different N — likely a different/expanded program phase | Not literally the same sampling frame, though both national |
| Lipid sub-sample | 25,647 measured / 18,492 complete | 23,665 (every 5th participant) | Partially | Different sub-sampling method and size | Different precision/coverage; not directly poolable |
| Age range | 20+ | 20+ | Yes | Identical | — |
| Geographic scope | National, 31 states/UTs + NCT | National, all states/UTs | Yes (nominally) | Both claim national representativeness | — |
| Crude vs. standardized | Crude/weighted | Crude/weighted | Yes | Same posture | Neither is age-standardized — a residual, unquantified source of possible divergence between survey rounds |

---

## Recommendation (neutral, evidence-based)

**FACT:**
- INDIAB-17 reports 81.2% dyslipidemia (NCEP criteria, n=18,492 of a
  113,043-person national cohort).
- INDIAB-25 reports 87.3% dyslipidemia (LAI criteria, n=23,665 of a
  121,078-person national cohort).
- The two studies use identical TC/TG/HDL cutoffs but different LDL
  cutoffs (130 vs. 100 mg/dL).
- The dominant shared component (low HDL-C) is nearly identical across
  both studies (66.9% vs. 66.8%).

**EVIDENCE (well-supported inference from the facts above):**
- The prevalence gap is plausibly attributable primarily to the LDL
  cutoff difference, since the shared components don't diverge
  comparably.
- Neither figure is erroneous — both are internally valid answers to
  two different operational definitions of "dyslipidemia."

**INTERPRETATION (reasoned judgment, not directly stated by either
source — flagged as such, not presented as fact):**
- LAI's stricter threshold likely reflects a clinical view that Indians
  carry elevated cardiometabolic risk at a given LDL level, but the
  specific rationale for their *prevalence-screening* cutoff (as
  opposed to their treatment targets) was not directly confirmed in
  either paper's retrievable text.
- Neither NCEP's nor LAI's figure is "more correct" on the evidence
  alone — this project has not established a principled reason to
  prefer either guideline body over the other.

**PROJECT DESIGN CHOICE (requires human decision, not determined by
evidence alone):**
- Whether to keep the current NCEP-based 81.2% figure, adopt the
  LAI-based 87.3% figure, or represent the ambiguity explicitly (e.g.,
  Option D above) rather than picking one.
- Which guideline body governs this project's lipid-classification
  conventions going forward — a decision with implications beyond this
  one number, since it would also apply to any future LDL-conditioned
  generation logic (§ Dataset Design Question).

**This brief does not choose a winner merely because ICMR-INDIAB-25 is
newer** — per this milestone's explicit instruction, and because the
evidence genuinely doesn't establish one figure as more valid than the
other; they answer different questions.

---

### Decision Required

1. **Dyslipidemia prevalence:**
   - Current: 81.2%
   - New evidence: **87.3%** (corrected from M4-0's imprecise "~90%")
   - What the evidence actually establishes: both figures are
     internally valid, from different (though overlapping-program)
     national ICMR-INDIAB phases, using genuinely different LDL
     cutoffs while sharing identical TC/TG/HDL cutoffs; the gap is well
     explained by the LDL threshold difference, not measurement error
     or contradiction.
   - Decision required: which composite definition (NCEP-based 81.2%,
     LAI-based 87.3%, or a documented dual-tracked representation)
     should this project treat as canonical going forward — noting
     this also implicitly decides which guideline body governs future
     LDL-related generation logic.

2. **LDL representation:**
   - Candidate approaches: (A) binary flag now, matching current
     schema pattern but baking in a threshold choice; (B) continuous
     `ldl_value` with the label derived downstream, most flexible but
     blocked on missing continuous-distribution evidence; (C) both
     independently generated, not recommended; (D) store category
     membership at multiple thresholds without a single continuous
     value.
   - Evidence: category-level prevalence exists for both NCEP and LAI
     cutoffs; no continuous LDL distribution evidence exists anywhere
     in this project's research to date.
   - Decision required: which architecture to adopt — explicitly not
     decided in this document.

3. **LDL threshold:**
   - NCEP: ≥130 mg/dL — the "borderline-high" tier of a risk-stratified,
     US-derived 5-tier classification; used here as a population-
     surveillance boundary, not a universal treatment-initiation
     threshold.
   - LAI: ≥100 mg/dL — a stricter, India-specific classification;
     likely (by interpretation, not directly confirmed) reflecting a
     view that Indians carry elevated risk at a given LDL level; also
     used here as a population-surveillance boundary, distinct from
     LAI's own much more aggressive treatment-target numbers.
   - What each represents: population-classification/screening
     boundaries repurposed for epidemiological prevalence reporting —
     **neither is a literal treatment-initiation threshold** in its own
     source framework.
   - Decision required: which population-classification boundary (if
     either) this project adopts as canonical, and whether the schema
     should encode a single binary interpretation of "elevated LDL" at
     all, versus preserving information to support either
     interpretation later (see Dataset Design Question above).
