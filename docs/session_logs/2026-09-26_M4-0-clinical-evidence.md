# Session Log — 2026-09-26 — M4-0: Clinical Evidence Verification

**Milestone hit:** M4-0 — Clinical Evidence Verification (COMPLETE,
research/documentation only).

## Objective

Determine what evidence actually exists to support M4's planned clinical-
generation stages (`docs/M4_CLINICAL_GENERATION_PLAN.md`), before writing
any generation code. No code, schema, or generator changes.

## Method

Read all listed project context (already current in this session from
prior milestones — not re-derived). Launched 3 parallel research forks
for genuinely new questions this project hadn't researched before:
(1) family-history percentage, medical-history/CVD-event evidence,
temporal/age-of-onset evidence; (2) Indian medication/treatment-guideline
evidence; (3) lab analytes (HbA1c, LDL/cholesterol/triglycerides) and
height/weight distribution evidence. The diagnoses question (§3) was
answered directly from already-established project design
(`docs/CLINICAL_RECORD_DESIGN.md` §E) — a design/schema question, not new
research.

## Findings Summary

Full detail: `docs/M4_CLINICAL_EVIDENCE.md`. Headlines:

- **Family history of diabetes:** a real percentage exists (14.33%,
  LASI, adults 45+) — but from a different study/population than ICMR-
  INDIAB, and restricted to 45+. Family history of CVD remains confirmed
  absent (9+ datasets now checked).
- **Medical history (CVD events/procedures):** only partial, heterogeneous,
  or modeled figures exist (stroke, heart failure); cardiac procedures
  entirely unsupported. None precise enough for individual-record
  generation.
- **Diagnoses:** unchanged from M3.5's design — derive HTN/diabetes/
  hyperlipidemia from existing risk factors; nothing else supported.
- **Medications:** NLEM 2022 (official) confirms real drug classes exist
  as a citable source (partially extracted); NNMS (already our own
  source) has real treatment-*rate* data (36.1% of diabetics treated;
  27.9%/14.5%/12.6% hypertension awareness/treatment/control cascade);
  discontinuation/duration data remains genuinely unsupported.
- **Labs:** HbA1c for non-diabetics has strong, well-conditioned
  (age×sex×urban/rural) evidence (ICMR-INDIAB-12) — the best candidate
  for a first lab implementation. Continuous LDL/cholesterol/
  triglyceride distributions remain unsupported.
- **Material discrepancy found, not resolved:** a newly-located 2026
  paper (ICMR-INDIAB-25) reports ~90% dyslipidemia prevalence, materially
  different from the existing 81.2% figure already in
  `configs/indian_population.yaml`, with similar-but-non-identical sample
  sizes. The same new paper also uses a different LDL-C cutoff (Lipid
  Association of India, ≥100 mg/dL) than the project's existing NCEP-
  based cutoff (≥130 mg/dL). **Neither conflict is resolved here** — both
  are flagged as Proposed Decisions requiring human input.
- **BMI vs. height/weight (M3.5's open design tension):** resolved with
  an evidence-based recommendation. No verified continuous height/weight
  distribution exists anywhere (conflicting, unverifiable secondary
  figures only; the primary NFHS-5 table remains inaccessible — a third
  failed attempt across M2C/M2D/this session). **Recommendation: keep
  BMI-primary (current approach)** — not a default-by-convenience choice,
  the only option with actual evidence.
- **New evidence family surfaced:** LASI secondary-analysis papers
  (2 found) provide genuine age-stratified hypertension/diabetes evidence
  M2D concluded didn't exist accessibly from INDIAB — but scoped to 45+
  and a different study design. Flagged as a candidate for deeper future
  audit, not pursued further this session (out of scope).

## Human Checkpoints

Two genuine "evidence conflicts materially" triggers found (dyslipidemia
prevalence, LDL cutoff) — both documented as **Proposed Decisions**, not
resolved or finalized, per this milestone's explicit instruction. No
other STOP conditions were triggered (no new dataset introduced without
documentation, no schema decision forced, no clinical assumption invented,
no unsupportable medication generation attempted, and the BMI/height-
weight question resolved cleanly via evidence rather than remaining
irreconcilably ambiguous).

## Files Created/Modified

**Created:** `docs/M4_CLINICAL_EVIDENCE.md`, this session log.
**Modified:** none (no code, schema, `configs/`, or `docs/DECISIONS.md`
changes — proposed decisions are recorded in `docs/M4_CLINICAL_EVIDENCE.md`
only, per instructions not to finalize them).

## Tests

No code was changed this session. Full suite re-run to confirm (success
criteria explicitly requires "existing tests remain unaffected") — see
the tool-call record for this session's exact pass count.

## Recommendation

M4A (family history) can proceed narrowly-scoped to the LASI 45+ figure,
pending human confirmation it's worth implementing at that narrow scope.
M4C (labs) should start with HbA1c for non-diabetic patients — the
strongest evidence found in this entire pass — while treating the
dyslipidemia/LDL-cutoff conflicts as blocking for any lipid-value work
until a human resolves them. M4D (medications) remains mostly blocked,
though less completely than M3.5 anticipated (NLEM 2022 + NNMS treatment
rates are real, new, usable inputs). Recommend resolving the two Proposed
Decisions before M4 implementation begins, since both affect config
values already in production use (the existing 81.2%/NCEP figures), not
just new fields.
