# Session Log — 2026-09-27 — M5: 100K Baseline Synthetic Population Generation

**Milestone hit:** M5, COMPLETE. First large-scale dataset generation —
no architecture change, no schema change, no new decision.

## Objective

Generate and fully validate the project's first 100,000-patient
baseline synthetic Indian population dataset, using the existing
production pipeline unmodified, per M4F's confirmed 100K readiness.

## Phase 1 — Pre-generation safety check

Verified before generating anything: git status showed no unexpected
changes since M4F (same untracked file set); full suite 103/103 passing;
`configs/base.yaml`/`configs/indian_population.yaml` both `random_seed:
42` (unchanged); `docs/PROJECT_STATE.md` "Human Decisions Required"
still showed no blocking item; `docs/M4F_FINAL_CLINICAL_AUDIT.md`'s "no
RED item" conclusion still applicable (nothing changed since it was
written); `outputs/m5/100k_patients/` confirmed gitignored via
`git check-ignore -v` before writing anything there.

## Phase 2 — Reproducibility

Recorded seed (42, unchanged), schema version (0.7), git HEAD
(`4ce0e72e`), config files, and per-patient seed formula
(`config["random_seed"] + sequence`) in
`outputs/m5/dataset_manifest.json` before generation began.

## Phase 3/4 — 100K generation + monitoring

Ran a monitored wrapper around the existing, unmodified
`integration.build_patient.build_patient()` (same call M2C-M4F all
use) for sequences 1-100,000, in the background. Logged progress every
5,000 patients (elapsed time, rate, RSS, error/invalid counts).

**Result: 100,000/100,000 written, 0 generation errors, 0 invalid
patients, 100,000 unique patient IDs, 0 duplicates.** No expensive
static resource was reloaded per-patient (the existing `lru_cache`
layer, D009, held for the full run — confirmed by the flat memory
profile). No failure occurred, so no fix/rerun/human-checkpoint path
was needed.

Wall time: 1,398.2s (23.30 min). Throughput: 71.5 patients/sec, 4,291/
min. CPU utilization: 97.6% (single-process). Memory: ~266MB at
patient 5,000 → ~275MB at patient 100,000 (small ~9MB drift over the
full run — noted, not investigated further, since it caused zero
errors and remains trivial even extrapolated to 1M).

## Phase 5 — Structural validation

Reused `validation.structural.validate_patient()` unmodified via a
single-pass analysis script (streamed, not holding all 100,000 Patient
objects in memory simultaneously — memory-safe at this scale).
**100,000/100,000 valid, 0 errors.** Every check exercised: patient_id
format, schema_version, demographic ranges/vocabularies, diagnosis/
medical-history/medication controlled vocabularies, ECG structural
fields, lipid ranges, lab unit-matching, non-empty timeline.

## Phase 6 — Clinical consistency validation

Reused `validation.clinical_consistency.validate_clinical_consistency()`
unmodified, same single pass. **100,000/100,000 consistent, 0 errors, 0
warnings**, all 9 checks run for every applicable patient. Explicitly
confirmed the D014 hyperlipidemia/lipid_interpretations disagreement
(70.5% agreement, consistent with the 70-77% range already observed at
n=100/n=1,000) was never flagged as an error — the intentional
non-reconciliation held correctly at full scale.

## Phase 7 — Statistical validation

Computed exact binomial tests (demographics, risk factors, lipid
categories, treatment rates) and a chi-square test (35-category state
distribution) against `configs/indian_population.yaml`'s own cited
values. **Every variable statistically indistinguishable from its
target** (p=0.05-0.92), except the state chi-square (p=0.0549, not
significant at α=0.05 — noted, not concerning) and the composite
lipid-interpretation rates (see below).

**Investigated the composite-rate finding, per this milestone's
instruction to investigate every discrepancy**: NCEP composite
dyslipidemia 82.99% vs. cited 81.2% (p<0.0001); LAI composite 85.58%
vs. cited 87.3% (p<0.0001). Traced this to D013's own prior finding —
the composite rate is not itself sampled, it emerges mechanically from
independently-sampled TC/TG/HDL categories plus Friedewald-derived LDL;
D013 already computed that full independence would imply 86.5%
(materially above 81.2%) and chose Friedewald specifically because it
"reduces but doesn't eliminate" that gap. At n=100 (M4B) the gap was
statistically invisible (masked by sampling noise); at n=100,000 the
same, already-quantified gap is now visible because noise has shrunk.
**Classified as B (evidence/architecture limitation, previously
documented), not A (bug) — no change made**, per the milestone's
explicit "do not modify established evidence-backed generation behavior
merely to improve statistical appearance" instruction.

## Phase 8 — Relationship validation

Confirmed both intentionally-modeled relationships strongly present
(sex×BMI χ²=1,425.85 p≈0; sex×smoking χ²=16,327.99 p≈0) — matching
their designed sex-conditioning. Checked the one relevant unmodeled
relationship, hypertension×smoking: χ²=2.43, p=0.119, **and
computed Cramér's V=0.0049** to confirm the effect size itself is
negligible (not just relying on a p-value, which alone is not
decision-useful at n=100,000) — confirms intentional independence holds
at scale, exactly as designed, without over-interpreting a borderline
p-value as evidence of a hidden relationship.

## Phase 9 — Missingness audit

`family_history`/`encounters`/`echo`: 100% missing, all
evidence-supported or deferred-domain (unchanged classifications).
`labs`: missing for exactly 11,457 patients — **exactly** the diabetes
count, confirming the "no HbA1c for diabetics" rule holds with zero
exceptions across the full dataset. `diagnoses`/`medical_history`/
`medications`: never `None` (always a list, possibly empty) — confirmed
correct, no accidental missingness anywhere.

## Phase 10 — ECG metadata audit

Quantified (not solved) the ECG-ID-reuse question at target scale:
17,386 unique ECG IDs among 100,000 patients, 341 used exactly once,
17,045 reused 2+ times, maximum single-ID reuse 17×, mean reuse 5.75×.
Empty-superclass rate 6.466% — matches PTB-XL's own ~6.5% documented
rate at the 50%-confidence threshold (M3), confirming this is inherited
from the reused metadata source, not introduced by this project. This
data is recorded as evidence for a future ECG-architecture decision,
not acted upon.

## Phase 11 — Performance + storage

Actual 100K figures (71.5 patients/sec, 355.12 MB, 3,551.2 bytes/
patient) matched M4F's 5,000-patient benchmark projections almost
exactly (71.6 patients/sec projected, 0.36 GB projected) — no surprises
between benchmark and full-scale run. Extrapolated (not generated): 1M
≈ 3.55 GB / ~3.9 hours, linear extrapolation only, not independently
verified.

## Phase 12/13 — Report and manifest

Created `docs/M5_100K_DATASET_REPORT.md` (16 sections, all requested
content) and `outputs/m5/dataset_manifest.json` (machine-readable,
patient-level-sensitive-information-free — only aggregate/config
metadata).

## Phase 14 — Final integrity check

Full suite re-run: **103/103 passing**, identical to the pre-generation
baseline — confirms this milestone made zero source-code changes.
`git status` confirms `outputs/` remains fully gitignored and no
unrelated file changed. **No behavioral code modification was
required or made.**

## Problems found

None (category A). The one investigated discrepancy (composite lipid
rates) resolved to B (previously-documented evidence limitation), not a
defect.

## Human checkpoints

**None.** No trigger condition (evidence conflict, unexpected
distribution requiring a design decision, schema restructuring,
generation-logic change, generation failure, unexplained validation
failure, ECG/model/cloud decision) occurred.

## Files Created/Modified

Created: `docs/M5_100K_DATASET_REPORT.md`, this session log,
`outputs/m5/100k_patients/*.json` (100,000 files, gitignored),
`outputs/m5/dataset_manifest.json`, `outputs/m5/generation_summary.json`,
`outputs/m5/analysis_results.json` (all gitignored, not committed).
Modified: `docs/PROJECT_STATE.md` (M5 milestone entry, Current Dataset
Counts, Stage 3/6 status, Last Completed Action, Next Action, Last
Updated).
Not modified: `docs/DECISIONS.md` (no genuine new decision made — pure
generation/validation milestone), all generation/schema/validation code
(zero behavioral changes, confirmed by the unchanged 103/103 test
result), all existing tests.

## Recommendation

The 100K baseline is ready for downstream use (pattern discovery,
future ECG work, eventual model integration). Before M6, the project
should decide: (1) the ECG-ID-reuse policy now that it's fully
quantified at target scale, and (2) whether to resolve the
hyperlipidemia-diagnosis question — both remain human decisions, not
made by this milestone.
