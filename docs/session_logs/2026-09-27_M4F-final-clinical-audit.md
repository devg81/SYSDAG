# Session Log — 2026-09-27 — M4F: Final Clinical Completeness + Pre-Scale Audit

**Milestone hit:** M4F, COMPLETE. Pure audit + benchmark milestone — no
behavioral generation change, no schema change, no new dataset, no
human decision resolved.

## Objective

Determine whether the current patient architecture is internally
coherent enough to scale to 100K, and whether any Category-A
implementation defect must be fixed before scaling.

## Phase 1 — Domain matrix

Built a full field-by-field matrix (`docs/M4F_FINAL_CLINICAL_AUDIT.md`)
evaluating *actual generation + validation behavior*, not schema field
presence. Fully complete: demographics, all 5 risk factors, lipid
panel/interpretations, HbA1c (NGT), ECG metadata. Correctly partial
(evidence-bounded): diagnoses, medical_history, medications, temporal
information. Correctly unimplemented: family history, ECG waveform,
echo, procedures, stroke, heart failure, general CVD.

## Phase 2 — Human-decision audit

Reviewed every open item across `docs/DECISIONS.md`/
`docs/PROJECT_STATE.md`/M4 documentation. **No new category-C or
category-B item was found** — the hyperlipidemia-diagnosis-definition
question remains the sole open human decision (unchanged from M4D/M4E);
three narrower items (`TimelineEvent.reference_id`, `birth_date`,
family-history scope) were already known, restated not rediscovered.
Everything else classified D (intentionally deferred, evidence
genuinely absent) — preserved unchanged, per instruction.

## Phase 3 — Clinical consistency audit

Full suite: 103/103 passing (unchanged — nothing needed fixing).
Generated fresh 10/100/1,000-patient populations with the existing
seeds (no override): 0 structural errors, 0 clinical-consistency
errors/warnings at all three scales, every check running for every
applicable patient.

Statistical spot-checks at n=1,000: hypertension/diabetes/
hyperlipidemia prevalence and antihypertensive treatment rate all
statistically indistinguishable from cited rates (p=0.37-0.96).
**One borderline finding investigated**: antidiabetic treatment rate
45.1% observed vs. 36.1% cited among the 113 diabetic patients in this
particular run (p=0.050). Ran an isolated 50,000-draw check of the same
Bernoulli in isolation (35.88% observed, p=0.308) — confirms the
sampler is unbiased; the borderline result is sampling variation at a
small conditional sub-sample (113), not a defect. Same investigative
method M2C used for its own borderline age p-value. **Zero Category-A
bugs found across the entire audit.**

Duplicate `ecg_id` reuse at n=1,000 (30 groups, 61 occurrences) exactly
reproduces M3's original finding — same seed, same pool, same
birthday-paradox math, not a new issue.

## Phase 4 — Large-scale readiness benchmark

Ran a 5,000-patient benchmark (not committed, `outputs/m4f/
benchmark_5000/`, gitignored) using the existing, unmodified
`lru_cache`-based PTB-XL caching layer: 69.9s wall time, 71.6
patients/sec, 97.0% CPU utilization (single-process, no parallelism),
memory flat at ~265MB steady-state from patient 1,000 through 5,000 (no
leak). **Estimated 100K runtime: ~23 minutes.** No bottleneck requiring
a code change was found.

## Phase 5 — Storage estimate

Measured directly (not guessed) from the 5,000-patient benchmark:
3,551 bytes/patient average → **100K ≈ 0.36 GB** at the current
metadata-only schema. A future waveform representation, using the
schema's already-declared `[1000, 12]` float32 shape as a rough
upper-bound estimate (not a committed format), would add ~4.8 GB at
100K — explicitly labeled as an estimate, not an implementation.
Recommended working-space margin: 15-20 GB.

## Phase 6 — ECG readiness check

Audited `ingestion/ptbxl_source.py` and `schemas/patient_schema.py`'s
`ECGRecord`. Metadata-only architecture (D003) is internally consistent
and additively extensible for a future waveform — no restructuring
needed, `signal_available` already exists as the toggle. **Found
existing, previously-trained, unused per-superclass GAN checkpoints**
(`syngen/SynGen/SynGen/checkpoints/generator_{CD,HYP,MI,NORM,STTC}.pt`,
with a `generate_synthetic()` function already defined in
`gan_pytorch.py`) — a real "reuse before rebuild" candidate distinct
from the CardioSynth/CardioSync candidate named in
`docs/PROJECT_STATE.md` Stage 9. Not evaluated for currency/validity,
not selected — this is an audit finding, not a decision. Two design
decisions identified as required before any waveform work: which
checkpoint(s) generate a multi-label or zero-label patient's waveform,
and whether/how to evaluate the existing checkpoints' validity.
Duplicate `ecg_id` reuse (Phase 3) will become pervasive at 100K
against the fixed ~17,470-record training-fold pool — flagged as the
one real, quantified scale concern (not blocking, not decided here).

## Phase 7 — 100K readiness checklist

14 areas assessed; **zero RED**, two YELLOW (medication scope — a
documented evidence boundary, not a defect; ECG-ID reuse at scale — a
quantified, not-yet-decided policy question), everything else GREEN.
**Answer: YES, conditionally** — every correctness/reproducibility/
performance/storage dimension is ready; the open human decision
(hyperlipidemia-diagnosis) does not block a 100K run of the currently-
implemented schema, since it only gates a future third diagnosis/
statin medication, not anything already generated.

## Phase 8 — Implementation

No Category-A bugs found → no behavior-changing modification made.
Tests unchanged (103/103, same as M4E's ending count). Only new
artifacts: the audit document, this session log, and gitignored
benchmark/validation output (not committed).

## Problems found

None (category A). Every investigated discrepancy resolved to C
(expected sampling variation) or was already a known, documented D
(intentional engineering choice/evidence gap).

## Human checkpoints

**None raised by this milestone.** The one pre-existing open item
(hyperlipidemia-diagnosis definition choice) is unchanged — not
resolved, not escalated further, exactly as it stood entering M4F.

## Files Created/Modified

Created: `docs/M4F_FINAL_CLINICAL_AUDIT.md`, this session log.
Modified: `docs/PROJECT_STATE.md` (M4F milestone entry, Current Dataset
Counts, Last Completed Action, Next Action, Last Updated).
Not modified: `docs/DECISIONS.md` (no genuine new decision was made,
per this milestone's own instruction), all generation/schema/validation
code (zero behavioral changes), all existing tests.

## Recommendation

100K readiness is confirmed at the current schema/architecture level.
Before authorizing a 100K run (or any milestone beyond this one), the
project should decide: (1) whether to resolve the hyperlipidemia-
diagnosis question now or continue deferring it into the 100K dataset,
and (2) the ECG-ID-reuse policy at scale (accept pervasive reuse as a
documented limitation vs. expand the training-fold pool vs. change fold
discipline) — both are human decisions, not made by this audit.
