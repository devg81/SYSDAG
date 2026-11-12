# M6 — ECG Waveform Validation Plan (DESIGN ONLY, NOT IMPLEMENTED)

**Status: design document. No code in `validation/` has been added or
changed to implement this.** Written as evidence for the M6 human
checkpoint per the user's explicit Task 4 instruction: design, do not
implement.

This plan only applies once a generative ECG model is selected and
starts producing waveforms (Stage 4). It is additive to, and follows
the same shape as, the project's existing validation layers
(`validation/structural.py`, `validation/clinical_consistency.py`),
which already return an `errors`/`warnings`/`checks_performed` result
object (see `ClinicalValidationResult` in `clinical_consistency.py`).
A future `WaveformValidationResult` would follow the identical shape —
not a new validation paradigm.

## Three-tier classification (used throughout)

- **HARD FAILURE** — the waveform is structurally or physically
  invalid; the record must not be marked `signal_available: true`.
  Equivalent to today's `errors` list.
- **WARNING** — plausible but suspicious; record is kept, flagged for
  review. Equivalent to today's `warnings` list.
- **STATISTICAL OBSERVATION** — population-level finding, not a
  per-record pass/fail; reported in aggregate (e.g. a distribution
  comparison), never blocks a single patient.

## 1. Signal-shape validation — HARD FAILURE

Check the generated array is exactly `[1000, 12]` (or whatever shape
the eventually-selected model's native output is, before/after any
conversion — see `M6_MODEL_SELECTION_DECISION_BRIEF.md` Task 3).
Wrong rank, wrong lead count, wrong sample count → hard failure.
Mirrors the existing `signal_shape` check already present in
`validation/structural.py:75`.

## 2. Sampling-rate validation — HARD FAILURE

Confirm the declared `sampling_hz` metadata matches the actual sample
count / declared duration (1000 samples at 100Hz = 10.0s). A mismatch
between stored metadata and actual array length is a hard failure —
it means the record's own metadata is lying about itself.

## 3. Lead-order validation — HARD FAILURE

Confirm the 12 leads are in the project's fixed canonical order
(standard: I, II, III, aVR, aVL, aVF, V1-V6). If the model's native
output uses a different lead order, this check runs AFTER conversion
(Task 3, Option B/C), not before — silently accepting a shuffled lead
order would corrupt every downstream morphology/inter-lead check.

## 4. Amplitude/range sanity checks — HARD FAILURE / WARNING split

- HARD FAILURE: values outside a physically-impossible range (PTB-XL
  raw units are typically mV; e.g. |amplitude| > 10mV sustained is not
  a real ECG). Exact numeric threshold: **UNKNOWN, TO BE ESTABLISHED
  DURING PILOT** — must be derived from real PTB-XL waveform statistics
  once they're available for comparison, not invented here.
  Same "TO BE ESTABLISHED DURING PILOT" flag as `docs/session_logs/
  2026-09-27_M6-model-selection-research.md` (hardware track) already
  applied to storage compression ratios — this project does not invent
  numeric thresholds without evidence.
- WARNING: values statistically unusual vs. the real PTB-XL reference
  distribution for the same lead, but not physically impossible.

## 5. Missing/NaN/Inf checks — HARD FAILURE

Any `NaN`/`Inf`/`None` in the waveform array is an unconditional hard
failure — no clinical or statistical judgment call involved.

## 6. Flatline/artifact detection — WARNING

A lead (or the whole signal) with near-zero variance for an extended
span is not impossible (a disconnected lead happens in real ECGs) but
is suspicious in a *generated* signal — flag as warning, do not
auto-reject, since a legitimately flat segment (e.g. isoelectric
baseline) is normal in short windows.

## 7. ECG morphology validation via NeuroKit2 — HARD FAILURE / WARNING split

Reuse **NeuroKit2** directly (per `docs/session_logs/2026-09-27_M6-
model-selection-research.md` Track 5 — MIT-licensed per the pending
Task 2 licensing retry, off-the-shelf, no custom implementation
needed). Run its QRS/P/T delineation:
- HARD FAILURE: no detectable QRS complex at all (delineation fails
  outright) — the signal isn't recognizable as an ECG.
- WARNING: QRS detected but P/T-wave delineation is unstable/low-
  confidence, or delineated intervals (PR, QT, QRS duration) fall
  outside NeuroKit2's own physiological reference ranges.

## 8. Heart-rate plausibility — HARD FAILURE / WARNING split

Derive HR from R-R intervals (NeuroKit2 output, reused, not
reimplemented).
- HARD FAILURE: HR outside an absolute physiological bound (e.g. <20
  or >300 bpm sustained) — not a real human heart rhythm.
  Exact bound: **UNKNOWN, TO BE ESTABLISHED DURING PILOT**.
- WARNING: HR outside a typical-but-not-impossible range, or R-R
  variability inconsistent with the conditioning label (e.g. labeled
  NORM but HR pattern resembles a known arrhythmia morphology).

## 9. Rhythm/morphology consistency with conditioning labels — WARNING / STATISTICAL OBSERVATION

Given a record was generated conditioned on superclass label X (one of
NORM/MI/STTC/CD/HYP, this project's existing 5-class scheme), does the
morphology plausibly match X? Per-record: **WARNING** if a trained
independent classifier (see #10) strongly disagrees with the
conditioning label. In aggregate: **STATISTICAL OBSERVATION** —
report per-class classifier-agreement rate as a population metric,
not a per-patient gate. This directly reuses the cautionary finding
already recorded in Track 5 of the prior research log: self-consistency
with the generator's own conditioning is not proof of real clinical
fidelity — an *independent* classifier must be the judge, not the
generator's own training signal.

## 10. Comparison against PTB-XL reference distributions — STATISTICAL OBSERVATION

Population-level only, never a per-patient gate:
- Per-lead amplitude/interval distributions (generated vs. real PTB-XL)
- A PTB-XL-trained independent classifier's accuracy on generated
  waveforms, evaluated against the conditioning label (train-real /
  test-synthetic direction) — the standard practice already documented
  in Track 5 Section D.
- The Feature-based Fréchet Distance (FFD) concept from Track 5
  Section C, if its primary formulation is confirmed before this is
  implemented — **flagged PARTIALLY VERIFIED in the prior research,
  re-verify before use.**

## 11. Cross-patient diversity — STATISTICAL OBSERVATION

Nearest-neighbor distance distribution across the generated population,
Number-of-Modes / Mode Collapse Divergence, and/or the Vendi Score
(all from Track 5 Section E) — reported as population-level diversity
metrics. No per-record pass/fail; low diversity is a population
finding, not an individual record's fault.

## 12. Duplicate/similarity detection — HARD FAILURE (near-exact) / WARNING (near-duplicate)

- HARD FAILURE: byte-identical or near-byte-identical waveform reused
  across two different `patient_id`s — this would be a generation
  pipeline bug, not a statistical curiosity.
  (Note: this is distinct from the ALREADY-DOCUMENTED and ACCEPTED
  `ecg_id` metadata-reuse pattern from M4F/M5 — that's about which
  *source PTB-XL record's metadata* gets referenced, not about
  synthetic waveforms being duplicates of each other. A future
  waveform generator reusing the same *source* conditioning is
  expected; producing an *identical generated array* twice is not.)
- WARNING: high-similarity (e.g. small nearest-neighbor distance)
  without being exactly identical — consistent with #11's diversity
  metric, reported per-pair here, in aggregate there.

## 13. Memorization/privacy testing — STATISTICAL OBSERVATION (population-level, gates the *dataset*, not individual records)

Reuse the published health-data membership-inference method from Track
5 Section F (1-NN distance classifier: known-training vs. known-non-
training real PTB-XL records compared to their nearest synthetic
neighbor). This is a dataset-release gate, not a per-patient validation
step — a dataset with a high inferred-membership rate should not ship,
regardless of how any individual record scores.

## 14. Random-seed reproducibility — HARD FAILURE

Same `(sequence, seed)` (or whatever the selected model's own seeding
mechanism is) must deterministically reproduce the same waveform,
matching this project's existing reproducibility guarantee for the
rest of the patient record (`tests/test_stage2_foundation.py`'s
`test_reproducibility_same_seed_same_patient`). A model that cannot
be seeded deterministically is itself a Task 3/model-selection concern,
not just a validation-layer concern — flag it up if discovered.

## 15. Failure-rate reporting — STATISTICAL OBSERVATION

Aggregate, dataset-level, following the exact pattern M5's report
already established for the rest of the pipeline (0 generation errors,
0 invalid patients, out of 100,000): report generation attempts,
hard-failure count/rate, warning count/rate by type, and — once any
scale run happens — whether failure rate is stable or grows with scale
(the same kind of scale-sensitive question M4F/M5 already asked of
`ecg_id` reuse).

## What this plan deliberately does not do

- Does not implement any of the above in `validation/`.
- Does not invent numeric thresholds where no evidence exists (flagged
  "TO BE ESTABLISHED DURING PILOT" throughout, consistent with this
  project's existing standard for unresolved thresholds).
- Does not gate model selection — this plan applies to whichever model
  is eventually chosen at the M6 human checkpoint, SSSD-ECG or
  otherwise.
