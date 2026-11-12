# M4-0 Clinical Evidence Verification

**Milestone:** M4-0 — Evidence Verification (research/documentation only).
**Status:** Complete. No code, schema, or generator change.
**Date:** 2026-09-26

This document records what evidence actually exists to support M4's
planned clinical-generation stages (`docs/M4_CLINICAL_GENERATION_PLAN.md`),
following the same discipline as M2A/M2C-0/M2D: SUPPORTED /
PARTIALLY SUPPORTED / NOT SUPPORTED per variable, no invented
prevalence, non-identical studies never blended.

---

## 1. Family History

| Field | Finding |
|---|---|
| Source | **Ahmed W (2024), "Additive interaction of family medical history of diabetes with hypertension...", BMC Public Health**, using **LASI** (Longitudinal Ageing Study in India) data — NOT ICMR-INDIAB |
| Population | 58,612 LASI respondents, **adults 45+**, all states/UTs except Sikkim |
| Year | LASI fieldwork 2017-18; paper published 2024 |
| Definition | Self-reported family history of diabetes (any relation) |
| Geographic scope | National |
| Directly usable? | **Only for the 45+ sub-population**, not our full 20-89 range |
| Finding | **Family history of diabetes (any relation): 14.33%** (8,822/58,612). Associational finding also reported: diabetes prevalence 27.8% among those with family history vs. 9.2% without. |
| Limitation | Different study/population from ICMR-INDIAB (our primary risk-factor source) — do not blend. Relation-specific (parental/sibling/maternal/paternal) breakdown exists in the paper but was not extracted. Restricted to 45+, not the full 20-89 generator range. |

**Status: PARTIALLY SUPPORTED** — a real, citable percentage exists, but
from a different source/population than this project's primary
risk-factor evidence (ICMR-INDIAB), and only for ages 45+. ICMR-INDIAB's
own family-history-of-diabetes percentage (which M3.5 flagged as needing
verification) was **not locatable** in this pass either.

- **Family history of CVD:** still **NOT SUPPORTED** — confirmed absent
  from every dataset examined across M2A, M2C-0, and this pass (9+
  datasets now).
- **Relationship categories, condition types beyond diabetes, age of
  onset:** **NOT SUPPORTED** at the granularity this project would need
  (the LASI paper's relation-specific breakdown wasn't extracted; no
  other source addresses age of onset for family history specifically).

**Recommendation:** if family history is pursued in M4A, it should be
scoped to the LASI-sourced 45+ subpopulation only, with the mismatch to
our generator's full 20-89 range explicitly disclosed (the same kind of
age-range-extrapolation caveat already used for BMI/smoking, but here the
direction is reversed — we'd have evidence for *older* patients only,
not younger ones). This is a narrower and differently-shaped gap than
M3.5 anticipated (which expected either "found the INDIAB %" or
"nothing") — a new option, not previously on the table.

---

## 2. Medical History

| Component | Finding | Status |
|---|---|---|
| Stroke incidence/prevalence | 105-152/100,000/year incidence; 26-757/100,000 prevalence — a systematic review of **heterogeneous** underlying studies, wide range reflects that heterogeneity, not a single number | PARTIALLY SUPPORTED — real figures exist but span too wide a range to responsibly generate a single population rate from |
| Heart failure prevalence/incidence | 1.3-4.6 million prevalence, 491,600-1.8 million/year incidence — a **modeled estimate**, not a direct survey | PARTIALLY SUPPORTED — same caveat, modeled not measured |
| Heart failure registry (NHFR India) | 10,850 patients, mortality/etiology outcomes | **NOT SUPPORTED for population generation** — hospital-registry-derived, same non-representativeness class already established for CREATE/STEMI-ACT in M2A |
| General CVD prevalence | Pooled ~11% (male 12%/female 14%; urban 12%/rural 6%) from a 2025 meta-analysis of 15 heterogeneous studies (2000-2024) | PARTIALLY SUPPORTED — a real pooled figure, but definitions of "CVD" likely vary across the 15 underlying studies; treat as directional, not a precise generation parameter |
| Cardiac procedures (angioplasty/CABG) prevalence | **Not found** | **NOT SUPPORTED** |
| Age distribution of first CVD event | Not found as a direct figure (age-of-onset findings below are for hypertension/diabetes, not CVD events specifically) | **NOT SUPPORTED** |

**Status: PARTIALLY SUPPORTED at best, for a few headline figures; NOT
SUPPORTED for anything requiring age/sex-conditioned generation.** None
of these figures come from a population-representative, directly-usable
source with the precision this project requires before generating
individual-level records. **Do not generate** stroke/heart-failure/
CVD-event/procedure fields from these figures — they inform narrative
context (as CREATE/STEMI-ACT already do) but not individual-record
generation parameters.

---

## 3. Diagnoses

This section draws on already-established project design
(`docs/CLINICAL_RECORD_DESIGN.md` §E), not new web research — it's a
schema/design question, answered from what's already documented.

- **Which categories can eventually be supported:** only the three
  already-evidence-backed risk factors — hypertension, diabetes,
  hyperlipidemia — as **derived** diagnoses (1:1 promotion of the
  existing boolean flags, per M3.5's design). Any actual CVD-event
  diagnosis (MI, stroke, angina, heart failure) remains **NOT SUPPORTED**
  per §2 above.
- **Code/vocabulary recommendation:** ICD-10 (or ICD-11) is the
  WHO-endorsed international standard, generally used in Indian
  clinical/research/insurance contexts. This is a **data-format/
  interoperability convention, not a clinical evidence claim** — it
  doesn't need epidemiological citation, but is still a design choice
  worth lightweight review before adoption (not a full human checkpoint
  in the "clinical assumption" sense).
- **Prevalence support:** confirmed for HTN/diabetes/hyperlipidemia
  (already generated); **NOT SUPPORTED** for anything else.
- **Independent vs. derived:** **derived from risk_factors**, per
  M3.5's already-established design — restated here as still correct,
  not re-litigated.

**Status: as designed in M3.5, unchanged by this evidence pass** — no
new diagnosis category earned support.

---

## 4. Medications

| Question | Finding | Status |
|---|---|---|
| Treatment guidelines (drug classes) | **National List of Essential Medicines (NLEM) 2022** (MoHFW/ICMR, official) confirms amlodipine, atorvastatin, teneligliptin, insulin glargine are essential medicines. Metformin's presence could not be independently re-confirmed this pass (near-certain given WHO/NLEM-2015 precedent, but not verified — do not assert without confirming) | **PARTIALLY SUPPORTED** — real official document exists, but full class-by-class extraction failed (PDF hosts DNS-failed or returned unparseable binary); a full read is needed before treating this as fully supported |
| Real-world treatment rates | **SUPPORTED**, from NNMS (a source this project already uses): diabetes — 36.1% of diagnosed diabetics on treatment; hypertension — 27.9% aware / 14.5% treated / 12.6% controlled nationally, **explicitly not sex-varying** per the source. A conflicting sex-split figure (men 25%/women 35%) was found in a lower-confidence snippet and is explicitly **not used** — likely a different, narrower-population source (e.g. NFHS-5's reproductive-age-focused analysis), not traced or verified | **SUPPORTED** for the treatment-rate figures above |
| Discontinuation/adherence | Only fragmented, small, single-site studies (19-96% adherence range across incompatible small samples); one broader WHO-SAGE-based ~43.4% antidiabetic-adherence figure (adherence, not discontinuation — a different concept) | **NOT SUPPORTED** at usable precision — no citable national discontinuation-rate or treatment-duration figure exists |

**New evidence source flagged, not yet investigated:** **ICMR-INDIAB-25**
("Prevalence of dyslipidemia in India," *Journal of Clinical Lipidology*,
2026) — surfaced by the medications fork as an aside; investigated
properly in §5 below.

**Status: medications remain mostly blocked**, exactly as M3.5
anticipated, but less completely than expected — NLEM 2022 gives a real
(if incompletely-extracted) drug-class source, and NNMS gives real
treatment-*rate* data (i.e., what fraction of diagnosed patients should
even show a medication at all), which is new and directly usable
information M3.5 didn't have. Discontinuation/duration remains a genuine
gap with no responsible way to fill it yet.

---

## 5. Labs

| Analyte | Finding | Status |
|---|---|---|
| HbA1c (non-diabetic / NGT population) | **ICMR-INDIAB-12** (Sridhar GR et al., *Acta Diabetologica* 2022), n=14,222 confirmed-NGT adults 20+, national. Age-decade trend: **5.16 ± 0.71% at 20-29y → 5.49 ± 0.69% at 70+y**, with genuine **age×sex** (females +0.10%/decade vs. males +0.06%/decade) and **age×urban/rural** (urban +0.10%/decade vs. rural +0.08%/decade) conditional detail | **SUPPORTED** — this is genuinely strong, granular evidence, better-conditioned than almost anything else this project has found for a continuous analyte |
| HbA1c (diabetic population) | A much smaller, older ICMR-INDIAB Phase I sub-study (n=480 diabetics, 4 states only) reports state-level means (e.g. Chandigarh 9.1±2.3%, Tamil Nadu 8.2±2.0%) | **PARTIALLY SUPPORTED** — real numbers, but non-representative (4 states, small n); do not blend with the NGT figures above (different population, different phase) |
| LDL / total cholesterol / triglycerides (continuous mean/SD) | **Not found** in any source examined, old or new | **NOT SUPPORTED** |
| Dyslipidemia prevalence — **new source, material discrepancy found** | **ICMR-INDIAB-25** (*J Clin Lipidology*, 2026), n=23,665 (of a stated ~121,078-person national sample), adults 20+, national: dyslipidemia **~90%** ("nearly 9 in 10"), higher urban/female/Central India, low HDL-C the main driver | **PARTIALLY SUPPORTED at the category level — but see conflict below** |
| Reference ranges | ICMR-INDIAB-25 uses **Lipid Association of India** guidelines: high LDL-C ≥100 mg/dL — **stricter than the NCEP cutoff (≥130 mg/dL) already used in this project's config**, sourced from the older PMC4016101 paper. TC/TG appear unchanged (≥200/≥150 mg/dL); HDL-C cutoff for the new study not confirmed | **PARTIALLY SUPPORTED** — confirms a real India-specific guideline body exists, but the full cutoff set isn't confirmed, and it materially conflicts with what's currently documented |
| Height/weight (continuous mean/SD) | No reliable figure confirmed. Two secondary/aggregator sources gave **conflicting** NFHS-5-attributed means (165/152 cm vs. 167/155 cm, male/female) — neither traced to a primary NFHS-5 table (FR375.pdf remains inaccessible, per M2C/M2D/this pass, all three attempts). A trend paper covers NFHS-II→IV round-to-round *changes*, not absolute values, and doesn't cover NFHS-5 at all | **NOT SUPPORTED** |

### Material discrepancy — flagged for human review, not resolved

`configs/indian_population.yaml`'s current `hyperlipidemia` figure
(81.2%, cited from a "~25,647-person INDIAB-17-associated sub-cohort")
and this newly-found ICMR-INDIAB-25 figure (~90%, n=23,665) have **close
but non-identical sample sizes and differing total-sample denominators**
(121,078 vs. 113,043 previously cited for INDIAB-17). These may describe
the same underlying data differently, or genuinely different
analyses/cutoffs — **this pass could not determine which, and does not
guess.** Additionally, the two sources appear to use **different LDL-C
cutoffs** (Lipid Association of India ≥100 mg/dL vs. NCEP ≥130 mg/dL).
**Do not average, blend, or silently prefer one figure over the other.**
This is exactly the "evidence conflicts materially" human-checkpoint
condition this milestone was instructed to watch for — see Proposed
Decisions below.

**Status summary:** HbA1c generation for non-diabetic patients has
genuinely strong, well-conditioned evidence and is the single best
candidate for M4C's first lab. Continuous LDL/cholesterol/triglyceride
generation remains unsupported. The hyperlipidemia evidence base itself
now has an unresolved internal conflict that predates and is independent
of the labs question.

---

## 6. BMI vs. Height/Weight

Per M3.5's flagged design tension (`docs/CLINICAL_RECORD_DESIGN.md` §A):

| Option | Evidence support |
|---|---|
| A. BMI primary (current approach) | Category-level prevalence by sex is solid (NNMS, already used) |
| B. Height + weight primary, BMI derived | **NOT SUPPORTED** — no verified continuous height/weight distribution exists for the Indian adult population from any source examined (conflicting, unverifiable secondary figures only) |
| C. Hybrid | Not applicable — hybrid would still need B's missing evidence for the height/weight component |

**Recommendation: Option A (keep BMI as the primary generated variable,
current approach unchanged).** This is not a default-by-convenience
choice — it's the only option with actual verified evidence behind it.
Height/weight should remain unpopulated (as they are today) rather than
back-derived from BMI via an invented anthropometric assumption, unless a
future session can actually access a primary NFHS-5 table (still blocked
by the same 600+-page PDF access problem noted in M2C, M2D, and this
pass — three separate failed attempts now).

**This resolves M3.5's open design tension** — it does not remain "human
decision required" in the sense of insufficient evidence to have an
opinion; the evidence clearly favors Option A. It's presented as a
recommendation, and a human may still choose to invest in solving the
NFHS-5 PDF access problem if the height/weight fields are wanted later.

---

## 7. Temporal Evidence

| Finding | Source | Status |
|---|---|---|
| Hypertension diagnosis-rate peaks at **14.7% in the 75+ age band** | Chakraborty A & Yadav S (2026), *BMC Public Health*, LASI, n=60,643 adults 45+ | **SUPPORTED**, but LASI-scoped (45+ only) |
| Diabetes diagnosis-rate peaks at **6.13% in the 55-64 age band** | Same paper | **SUPPORTED**, same scope caveat |
| Survival-curve onset patterns by urban/rural and sex (e.g. urban female earliest onset ~30) | Same paper, described qualitatively in the retrievable snippet | **PARTIALLY SUPPORTED** — real finding exists, but exact quantitative curves were not extracted this pass |
| A general national age-band hypertension/diabetes table (for our full 20-89 range) | Still not found for ICMR-INDIAB directly (its primary paper remains paywalled) | **NOT SUPPORTED** at the national, full-range level M2D already concluded |

**What can be evidence-backed:** diagnosis *rate by age band*, for ages
45+ specifically (LASI). **What remains necessarily engineering-derived:**
any specific `onset_date` value for an individual generated patient (no
source gives a per-patient onset distribution, only population rates by
band), and anything for ages 20-44 (outside LASI's scope).

**New finding for the parent project, beyond this fork's original
questions:** the LASI-secondary-analysis paper family (2 papers found
this pass) is a **previously-unexamined evidence family** — distinct from
the 8 datasets M2A audited and from ICMR-INDIAB/NNMS. It provides real
age-stratified hypertension/diabetes evidence that M2D concluded didn't
exist accessibly from INDIAB — but scoped to ages 45+, a different
design (longitudinal panel, self-reported diagnosis) than INDIAB's
cross-sectional clinical measurement. **Flagged as a candidate for a
fuller M2A-style audit if age-conditioned risk-factor generation becomes
a priority** — not pursued further in this pass (out of scope).

---

## 8. Source Quality Table

| Component | Variable | Source | Population | Year | Evidence status | Limitations | Future use |
|---|---|---|---|---|---|---|---|
| Family history | Diabetes family history % | LASI (Ahmed W, BMC Public Health 2024) | 58,612 adults 45+ | 2017-18 fieldwork / 2024 pub | PARTIALLY SUPPORTED | Different study/population than INDIAB; 45+ only | Candidate for M4A, scoped to 45+ |
| Family history | CVD family history | None | — | — | NOT SUPPORTED | Confirmed absent across 9+ datasets | Do not generate |
| Family history | Relation, condition detail, age of onset | None at usable granularity | — | — | NOT SUPPORTED | — | Do not generate |
| Medical history | Stroke incidence/prevalence | Systematic review (heterogeneous studies) | Varies | 2000s-2020s pooled | PARTIALLY SUPPORTED | Very wide range, heterogeneous definitions | Narrative context only |
| Medical history | Heart failure prevalence/incidence | Modeled estimate | National | Recent | PARTIALLY SUPPORTED | Modeled, not measured | Narrative context only |
| Medical history | Heart failure registry (NHFR) | Hospital registry | 10,850 patients | Recent | NOT SUPPORTED for generation | Hospital-based, non-representative | Citation context only |
| Medical history | General CVD prevalence | Meta-analysis, 15 studies | Pooled, national | 2000-2024 | PARTIALLY SUPPORTED | Heterogeneous underlying definitions | Narrative context only |
| Medical history | Cardiac procedures | None found | — | — | NOT SUPPORTED | — | Do not generate |
| Diagnoses | HTN/diabetes/hyperlipidemia | ICMR-INDIAB-17 (already used) | 113,043 adults 20+ | 2023 pub | SUPPORTED | Already generated as risk_factors | Derive diagnosis entries from existing flags |
| Diagnoses | Any other condition | None | — | — | NOT SUPPORTED | — | Do not generate |
| Medications | Drug classes (guideline) | NLEM 2022 (MoHFW/ICMR) | National | 2022 | PARTIALLY SUPPORTED | Full extraction failed this pass | Re-fetch before use |
| Medications | Treatment rates | NNMS (already used) | National adults | 2017-18 | SUPPORTED | Not drug-class-specific | Gate whether a medication exists at all |
| Medications | Discontinuation/duration | Fragmented small studies | Various small samples | Various | NOT SUPPORTED | No national figure | Do not generate |
| Labs | HbA1c (non-diabetic) | ICMR-INDIAB-12 | 14,222 NGT adults 20+ | 2022 pub | SUPPORTED | Age×sex×urban/rural conditional | Strong M4C candidate |
| Labs | HbA1c (diabetic) | ICMR-INDIAB Phase I sub-study | 480 diabetics, 4 states | Earlier phase | PARTIALLY SUPPORTED | Small, non-representative | Use cautiously, don't blend with NGT figures |
| Labs | LDL/TC/TG continuous values | None found | — | — | NOT SUPPORTED | — | Do not generate as continuous |
| Labs | Dyslipidemia prevalence (new) | ICMR-INDIAB-25 | 23,665 (of ~121,078) adults 20+ | 2026 pub | PARTIALLY SUPPORTED — conflicts with existing 81.2% figure | Material discrepancy, unresolved | Human review required before use |
| Labs | LDL reference range | Lipid Association of India (per INDIAB-25) vs. NCEP (per existing config) | — | — | CONFLICTING | Two different cutoffs in use across this project's own sources | Human review required |
| Anthropometrics | Height/weight continuous | None verified | — | — | NOT SUPPORTED | Conflicting unverifiable secondary figures only | Do not generate; keep BMI-primary |
| Temporal | HTN/diabetes diagnosis rate by age band | LASI (Chakraborty A, BMC Public Health 2026) | 60,643 adults 45+ | 2026 pub | SUPPORTED (45+ only) | Different design/population than INDIAB | Candidate for future age-conditioning, scoped to 45+ |
| Temporal | Individual onset_date | None | — | — | NOT SUPPORTED | Only population rates by band exist, not per-patient distributions | Remains engineering assumption |

---

## Proposed Decisions (NOT finalized — human approval required)

1. **Dyslipidemia figure conflict (81.2% vs. ~90%).** Proposed next step:
   read ICMR-INDIAB-25's full paper (currently 403-blocked) to determine
   whether it describes the same underlying cohort as the existing
   81.2% figure or a genuinely different one, before using either number
   in any new generation logic. **Do not resolve this by picking one
   arbitrarily.**
2. **LDL reference range conflict (NCEP ≥130 mg/dL vs. Lipid Association
   of India ≥100 mg/dL).** Proposed next step: if labs are pursued in
   M4C, explicitly decide (with human input) which body's guideline this
   project follows, and document the choice — do not silently default to
   whichever was encoded first.
3. **BMI vs. height/weight (§6).** Proposed: adopt the evidence-based
   recommendation (keep BMI-primary, Option A) as the working default,
   but confirm with a human before treating this as permanently settled,
   since it rests on an *absence* of height/weight evidence rather than a
   comparison of two supported options.
4. **Family history scope.** Proposed: if M4A proceeds, scope it to the
   LASI-sourced 45+ diabetes-family-history figure only (14.33%), with
   the age-range mismatch to the 20-89 generator explicitly disclosed —
   pending human confirmation this narrower scope is worth implementing
   at all versus leaving family history unpopulated entirely.

None of these are implemented or finalized by this document.
