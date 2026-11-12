# M7 — ECG Implementation Plan (DESIGN ONLY, NOT STARTED)

**None of the stages below have been implemented.** This is the
engineering breakdown for whichever model M6's human checkpoint
eventually selects, staged so each step produces evidence before the
next one is authorized — the same pattern this project has used for
every milestone since M1. Every "files likely to change" list is a
prediction, not a change made by this document.

Preconditions before M7-0 can start (from `docs/M6_ECG_MODEL_SELECTION.md`):
a model has been selected by a human (§6), and the representation
option (A/B/C, canonical lead order) has been decided.

---

## M7-0 — Environment / model acquisition

**Objective:** Resolve the pretrained-weight license by hand, download
the checkpoint, and get a first *real* (not estimated) parameter count
and VRAM figure.

**Inputs:** The selected model's repository and pretrained-weight host
(for SSSD-ECG: `figshare.com/s/81834b24a4711c2a5c55`).

**Outputs:** Confirmed license text (saved into `docs/`), a downloaded
checkpoint file (stored outside the repo, per the existing precedent of
excluding large PTB-XL binaries via `.gitignore`), and a real parameter
count (e.g. via SSSD-ECG's own `print_size(net)` in
`src/sssd/utils/util.py`).

**Files likely to change:** None in this repo's source — this stage is
environment setup and a documentation note recording the confirmed
license.

**Tests:** None (no project code yet).

**Stop conditions:** License is restrictive, unclear, or requires terms
this project cannot meet → **STOP, human checkpoint** (this is exactly
the currently-open blocker `docs/M6_ECG_MODEL_SELECTION.md` §4/§9-1
flags). Do not proceed to M7-1 on an unresolved license.

**Human checkpoint:** YES — this stage exists specifically to close the
license unknown.

---

## M7-1 — Source-conditioning extraction

**Objective:** Add a small, pure, additive function to read the raw
`scp_codes` column already present in this project's local
`syngen/SynGen/SynGen/dataset/ptbxl_database.csv` (confirmed present,
`docs/M6_ECG_MODEL_SELECTION.md` §3) per `ecg_id`, producing whichever
label vector shape the M7-0-confirmed checkpoint actually expects (44
diagnostic-only or 71-statement — resolved by M7-0, not guessed here).

**Files likely to change:**
- `ingestion/ptbxl_source.py` — new function (e.g. `load_scp_vector()`),
  additive, following the existing `functools.lru_cache` pattern already
  used for `_cached_ptbxl_df`/`_cached_label_map`.
- `schemas/patient_schema.py` — possibly one new optional field on
  `ECGRecord` (e.g. `scp_codes: Optional[dict[str, float]]`) to persist
  it. This is a schema touch — flag for confirmation it's additive/
  non-restructuring before merging, per the D012/D015/D016 precedent
  (proceed autonomously only if genuinely additive; STOP if not).

**Inputs:** Existing local CSVs (no new dataset).

**Outputs:** A per-`ecg_id`, deterministic label vector.

**Tests:** New unit test asserting a hand-checked `ecg_id`'s extracted
vector matches the raw CSV row exactly.

**Stop conditions:** If the exact expected index ordering cannot be
confirmed from the checkpoint/training code (only the label *set*, not
order, is knowable from the CSV alone) → flag and escalate rather than
guess an ordering.

**Human checkpoint:** Only if the schema addition is judged non-trivial
on inspection; expected to be additive and NOT require one, matching
prior precedent — confirm at implementation time, not assumed here.

---

## M7-2 — Preprocessing / conversion

**Objective:** Implement the lossless transpose + fixed lead-order
permutation identified in `docs/M6_SSDD_ECG_COMPATIBILITY.md` §8-9, as a
pure, tested function converting the selected model's native output
shape/order into this project's canonical representation (per whichever
of Options A/B/C was chosen).

**Files likely to change:** New `generation/ecg_conversion.py`.

**Inputs:** A raw model-output array (any shape the selected model
natively produces).

**Outputs:** A `[1000, 12]`-shaped array in the project's decided
canonical lead order.

**Tests:** A round-trip test against a hand-built known array, checking
both the transpose and the 12-element permutation are exactly correct
(a wrong permutation silently mislabels leads — the highest-value test
in this stage).

**Stop conditions:** None expected — pure deterministic reshape, no
judgment calls once the canonical order is fixed.

**Human checkpoint:** NO for the code itself, but this stage cannot
start until the canonical-lead-order decision (flagged open in
`docs/M6_ECG_MODEL_SELECTION.md` §11-3/4) is made.

---

## M7-3 — Single-ECG inference prototype

**Objective:** Load the M7-0 checkpoint and run one real, conditioned
inference in an isolated script — first real (not estimated) wall-clock
and VRAM measurement on the actual target hardware (RTX 4060 8GB, and
the 36GB alternative if available).

**Files likely to change:** New isolated script, e.g.
`experiments/ecg_inference_prototype.py` — explicitly NOT wired into
`integration/build_patient.py` yet.

**Inputs:** One real conditioning vector (M7-1) and the checkpoint
(M7-0).

**Outputs:** One raw waveform array, plus measured VRAM/timing replacing
every "ESTIMATE" flag in `docs/M6_ECG_MODEL_SELECTION.md` §5.

**Tests:** Manual inspection only at this stage (correct shape, no NaN/
Inf) — this is the first real signal the project has ever produced, not
yet subject to the full validation plan.

**Stop conditions:** If VRAM exceeds the 8GB card's capacity even at
batch size 1 → escalate and report; do not silently fall back to
half-precision or CPU without documenting the tradeoff.

**Human checkpoint:** NO — this is measurement, not a new architectural
decision.

---

## M7-4 — Waveform validation

**Objective:** Implement the HARD FAILURE tier of
`docs/M6_ECG_VALIDATION_PLAN.md` (shape, sampling-rate, lead-order,
NaN/Inf, and amplitude bounds once a real threshold exists) as real,
tested code, following the existing `errors`/`warnings`/
`checks_performed` result-object shape already used by
`validation/clinical_consistency.py`.

**Files likely to change:** New `validation/waveform_validation.py`.
New dependency: NeuroKit2 (MIT-licensed, confirmed
`docs/M6_MODEL_SELECTION_DECISION_BRIEF.md` §Licensing) for the
morphology/heart-rate checks (items 7-8 of the validation plan).

**Inputs:** M7-3's prototype waveform(s), plus deliberately-corrupted
synthetic inputs for negative-path tests.

**Outputs:** A `WaveformValidationResult` object.

**Tests:** One test per check — a valid input passes, each specific
known-bad input trips exactly the right check — mirroring the existing
pattern in `tests/test_m4a_clinical_schema.py`/`tests/test_m4c_*`.

**Stop conditions:** None.

**Human checkpoint:** NO.

---

## M7-5 — Patient integration

**Objective:** Wire real ECG generation into `integration/
build_patient.py` for a small (10-patient) end-to-end run, setting
`ECGRecord.signal_available=True` and attaching the validated waveform
plus generation provenance (model name/version, checkpoint identity,
seed).

**Files likely to change:**
- `integration/build_patient.py`.
- `schemas/patient_schema.py` — new additive fields on `ECGRecord` for
  the waveform reference and generation provenance.
- `validation/structural.py` — extend the existing declared-shape check
  to also validate the real array, not just metadata.

**Inputs:** The existing 10-patient generation pipeline.

**Outputs:** 10 patients with real synthetic waveforms attached, stored
per whichever storage-location decision is made (see Stop conditions).

**Tests:** Extend the existing `tests/test_stage2_foundation.py`-style
reproducibility test to synthetic ECG: same `(sequence, seed)` →
byte-identical waveform.

**Stop conditions:** If per-patient generation time makes even 10
patients impractical on available hardware → stop and report before
attempting M7-6.

**Human checkpoint:** YES — **waveform storage: inline (embedded in each
patient's JSON) vs. external file (`.npy`/`.h5`) referenced by path** is
an open, consequential decision (`docs/M6_ECG_MODEL_SELECTION.md` §7)
affecting every downstream consumer's I/O pattern; flag for sign-off
before this stage writes its first real patient record.

---

## M7-6 — Deterministic batch generation

**Objective:** Extend generation to support checkpointed, resumable
batches (e.g. N patients per batch), reusing the existing per-patient
seed/sequence determinism rather than inventing a new scheme.

**Files likely to change:** `integration/build_patient.py`, or a new
thin batch-runner script alongside it.

**Inputs/outputs:** Configurable batch size; same schema as M7-5's
single-patient output, at scale.

**Tests:** Interrupting a batch partway through and resuming produces
output byte-identical to an uninterrupted run of the same size/seed.

**Stop conditions:** None expected.

**Human checkpoint:** NO.

---

## M7-7 — 100 / 1,000 ECG validation

**Objective:** Generate 100, then 1,000 patients with real synthetic
ECGs (progressive scaling, `CLAUDE.md` §7/§27 — never jump straight to
a large number), running the *full* validation plan including the
STATISTICAL OBSERVATION tier (NeuroKit2 morphology agreement,
distributional comparison against the untouched PTB-XL folds 9/10
reference set — see `docs/M6_ECG_MODEL_SELECTION.md` §9's leakage
finding — diversity metrics, and the membership-inference/privacy
check). This is the first real evidence for every "TO BE ESTABLISHED
DURING PILOT" threshold `docs/M6_ECG_VALIDATION_PLAN.md` flagged.

**Files likely to change:** None new expected beyond M7-4/M7-6's code;
possibly a small aggregation/reporting script under `integration/`,
matching the pattern of `integration/analyze_m3_population.py`.

**Inputs:** 100- and 1,000-patient batches from M7-6.

**Outputs:** A report matching the shape of `docs/M3_DATA_QUALITY_REPORT.md`/
`docs/M5_100K_DATASET_REPORT.md`.

**Tests:** Full existing suite plus every new test from M7-1 through
M7-6, still passing.

**Stop conditions:** Any non-negligible HARD FAILURE rate, or a
membership-inference result indicating a real privacy/leakage concern →
**STOP, report, do not proceed to M7-8/100K.**

**Human checkpoint:** YES, conditionally — only if the membership-
inference or distributional checks raise a genuine concern; otherwise
proceeds autonomously to M7-8.

---

## M7-8 — Scale-readiness audit

**Objective:** Same shape as M4F's pre-100K audit for the metadata
pipeline — a full domain matrix, a mid-scale benchmark (e.g. 5,000
patients, matching M4F's own precedent), and an explicit RED/YELLOW/
GREEN call on 100K-ECG readiness. **Does not itself generate 100K
waveforms.**

**Files likely to change:** None — audit/report only.

**Inputs:** M7-7's outputs and benchmark run.

**Outputs:** `docs/M7_ECG_SCALE_READINESS_AUDIT.md`.

**Tests:** Full suite passing.

**Stop conditions:** Any RED cell → do not proceed to actual 100K
generation.

**Human checkpoint:** YES — actual 100K ECG generation is a materially
larger "expensive operation" than M5's metadata-only run was (diffusion
inference measured in low-single-digit *hours*, not minutes, per
`docs/M6_ECG_MODEL_SELECTION.md` §5/§10, plus several GB of new
storage) and requires its own explicit STOP-and-report before it runs,
per `CLAUDE.md` §15 — this audit is the report that precedes that
approval request, not the approval itself.

---

## What this plan deliberately does not do

- Does not select a model (M6's own open human checkpoint).
- Does not implement any stage above.
- Does not authorize 100K ECG generation, AWS usage, or model
  fine-tuning/training at any stage — every stage that would touch one
  of those is marked as its own explicit human checkpoint above.
- Does not resolve the `docs/M6_ECG_MODEL_SELECTION.md` §11 open
  questions — M7-0/M7-1 are where several of them get resolved, not
  this document.
