# Session Log — 2026-09-26 — M4-0A: Resolve Dyslipidemia Evidence Conflicts

**Milestone hit:** M4-0A — Dyslipidemia Evidence Conflict Research
(COMPLETE, research/documentation only). Human checkpoint from M4-0
addressed with primary-source research; **decision itself remains with
the human**, not made here.

## Objective

Resolve (via deeper research, not by picking a winner) the two evidence
conflicts M4-0 flagged: dyslipidemia prevalence (81.2% vs. "~90%") and
the LDL cutoff (NCEP ≥130 vs. LAI ≥100 mg/dL). No code, schema, or
generator changes.

## Method

Launched one deep-research fork instructed specifically to go beyond
search-result snippets (M4-0's original limitation) and attempt genuine
full-text/methods-section access via PMC mirrors, institutional
repositories, and other legitimate routes — full-text access to all
three primary sources (Lancet, ScienceDirect, Journal of Clinical
Lipidology) remained blocked (403s), but the fork cross-confirmed
specific per-component figures across multiple independent search
queries rather than relying on a single snippet, which materially
improved confidence over M4-0's original pass.

## Key Correction

M4-0's report characterized the new figure as "~90%." This pass found
the actual reported figure is **87.3%** — the "~90%"/"nearly 9 in 10"
phrasing was an imprecise paraphrase in the original source-summary
language, not the paper's own stated number. Corrected throughout the
new decision brief.

## Key Findings

1. **The 81.2% figure is confirmed to genuinely be ICMR-INDIAB-17's own
   number** (not a different, misattributed sub-study, as this session
   initially considered checking) — 14,895/18,492 complete-data
   respondents of a 25,647-person lipid sub-sample, using **NCEP/ATP
   III** criteria (TC≥200, TG≥150, HDL<40M/<50F, LDL≥130, all mg/dL).
2. **ICMR-INDIAB-25's 87.3% figure** uses **Lipid Association of India
   (LAI)** criteria — identical TC/TG/HDL cutoffs to INDIAB-17, but a
   stricter LDL cutoff (≥100 vs. ≥130 mg/dL).
3. **The dominant component (low HDL-C) is nearly identical across both
   studies** (66.9% vs. 66.8%) — this is the strongest piece of evidence
   that the ~6-point prevalence gap is driven by the LDL cutoff
   difference specifically, not a broader disagreement about the
   underlying population's lipid status.
4. **Classification: primarily "different definitions" (B), with a
   secondary, smaller contribution from "different populations/phases"
   (C)** — explicitly **not** a direct contradiction (A). Both studies
   are internally valid; they answer subtly different operational
   questions.
5. **Neither NCEP's 130 nor LAI's 100 is a treatment-initiation
   threshold** in its own source framework — both are population-
   classification/screening boundaries, repurposed by researchers for
   epidemiological prevalence reporting. Actual treatment decisions in
   both frameworks depend on overall cardiovascular risk category, not
   a single LDL number. This is an important clarification that
   prevents either cutoff from being mistaken for a clinical treatment
   rule.
6. **LAI's specific rationale for the 100 mg/dL prevalence-screening
   cutoff (as opposed to their much more aggressive treatment-target
   numbers, <50/<30 mg/dL) was not directly confirmed** — the connection
   to India-specific elevated cardiometabolic risk is this brief's
   interpretation, explicitly labeled as such, not a directly-sourced
   rationale statement.

## Dataset Design Question

Four architectural options for LDL representation were laid out with
consequences (generate-label-then-value; generate-continuous-value-then-
derive-label; both independently — not recommended; multi-threshold
category storage without a continuous value) — **none selected.** Option
B (continuous value first) remains blocked regardless of which threshold
question is resolved, since no continuous LDL distribution evidence
exists in any source examined to date (reconfirmed, not new to this
session).

## Documents Created

- `docs/M4-0A_DYSLIPIDEMIA_DECISION_BRIEF.md` — full source comparison
  tables, comparability matrix, FACT/EVIDENCE/INTERPRETATION/PROJECT-
  DESIGN-CHOICE framework, and the three explicit decisions still
  awaiting human input.
- This session log.

## What Was NOT Done

No code, schema, or `configs/indian_population.yaml` change. No new
decision recorded in `docs/DECISIONS.md` — per instructions, this stays
a proposal until a human chooses. No patients generated. M4A not begun.

## Human Decision Still Required

Three items, detailed in `docs/M4-0A_DYSLIPIDEMIA_DECISION_BRIEF.md`'s
"Decision Required" section: (1) which dyslipidemia figure/definition to
treat as canonical, (2) which LDL-representation architecture to adopt,
(3) which LDL threshold (if either) to standardize on. `docs/PROJECT_STATE.md`'s
"Human Decisions Required" section updated to reflect this remains open.

## Recommendation

Once the human resolves these three items, M4C (labs) can proceed with
HbA1c (the strongest evidence found across M4-0/M4-0A) regardless of the
outcome here, since HbA1c generation doesn't depend on the dyslipidemia/
LDL conflict. The dyslipidemia/LDL decision specifically gates any future
lipid-related generation logic, not the labs layer as a whole.
