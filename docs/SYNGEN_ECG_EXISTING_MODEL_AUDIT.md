# SynGen ECG Existing-Model Audit — Is the Inherited GAN Ready for the 100K Dataset?

**Read-only technical audit.** No source code, schema, config, or generation/
validation behavior was modified. No training or fine-tuning was performed.
No external model was downloaded. The 100K patient dataset was not
regenerated or touched. The only inference performed was a small (10/50/100-
sample) CPU forward-pass benchmark using the existing, already-trained
`generator_NORM.pt` checkpoint and the existing, unmodified `Generator` class
in `syngen/SynGen/SynGen/gan_pytorch.py` — outputs were held in memory and
never written to any project file. This document is the one artifact this
audit was authorized to create.

This audit builds directly on a prior read-only provenance/licensing audit
of the same GAN (same checkpoints, same `gan_pytorch.py`, same folds-1-8
training, same architecture) conducted earlier in this project. Facts
already established there are cited, not re-derived from scratch — but
several were independently re-verified this session (see each section's
labels) rather than taken on trust, per this audit's own instruction.

Labeling convention throughout: **VERIFIED** (directly confirmed from
source code, a loaded checkpoint, or a file on disk this session or the
immediately prior session), **INFERENCE** (a reasonable conclusion not
directly provable from available evidence), **UNKNOWN** (genuinely
undetermined, with the reason stated).

---

## 1. Executive Summary

The inherited `syngen/` GAN is a small (33.9M-parameter), CPU-tractable,
per-superclass DCGAN that **does** produce genuine 12-lead, 1000-sample,
100Hz-shaped synthetic waveforms — this is not metadata-only, and the output
shape matches this project's declared `[1000, 12]` @ 100Hz convention
exactly (VERIFIED). It has **no conditioning mechanism of any kind**: five
independent, unconditional generators exist, one per PTB-XL superclass
(NORM/MI/STTC/CD/HYP), each taking pure noise as its only input (VERIFIED).
There is **no denormalization step anywhere in the pipeline** — every
generated sample is a per-record z-scored, `[-1,1]`-clipped waveform with no
recorded scale to map it back to physical mV (VERIFIED, inherited finding
reconfirmed).

Three new, concrete findings from this session's deeper inspection:

1. **A real, quantified partial mode-collapse defect in the NORM checkpoint
   specifically:** of the 500 already-generated NORM samples on disk, 55
   (11%) are byte-for-byte **exact duplicates of one single waveform**
   (VERIFIED, hash-checked this session). NORM is the most heavily-used
   class in any realistic 100K generation run. The other four checkpoints
   (MI, STTC, CD, HYP) show zero exact duplicates in their existing
   500-sample batches.
2. **The model's only usable "conditioning" hook — `ecg.superclasses` —
   is itself drawn from a real PTB-XL record selected independently of a
   patient's synthetic Indian clinical profile.** `ingestion/ptbxl_source.py`
   picks one real PTB-XL row per patient by seed/fold only, and its
   `superclasses`/`age`/`sex` fields have no relationship to that patient's
   separately-generated `hypertension`/`diabetes`/`lipid_interpretations`/
   `diagnoses` (VERIFIED by reading both files). Wiring the GAN in "as-is"
   using this field would produce an ECG that looks class-coherent but is
   not actually grounded in the patient's synthetic clinical state.
3. **On CPU alone (no GPU, this machine), a full 100,000-sample generation
   run is on the order of 8-9 minutes** (measured throughput extrapolated,
   see §11) — this model does not need AWS GPU compute to be technically
   feasible at 100K scale; AWS GPU is a convenience/parallelism choice here,
   not a requirement, for the model as it currently exists.

**No Indian-specific ECG evidence exists or was ever claimed** — the model
was trained only on PTB-XL (a German/European clinical cohort). It generates
plausible-shaped generic waveforms per diagnostic superclass; it has no
mechanism to represent ethnicity, age, sex, or Indian-population-specific
morphology at all, because it has no conditioning mechanism whatsoever
(VERIFIED, §12).

## 2. Repository Inventory

All paths under `syngen/SynGen/SynGen/`. Traced by reading full file
contents this session and the immediately prior session (not names/docstrings
alone — `gan_pytorch2.py`/`visualize2.py` have known docstring/filename
mismatches, documented previously in `docs/syngen-codebase-analysis.md` §13
and reconfirmed here).

| # | Component | File | Role |
|---|---|---|---|
| 1 | Generator architecture | `gan_pytorch.py` (`class Generator`, lines 157-203) | Noise(100) → ECG(1000,12), dense+ConvTranspose1d, VERIFIED this session (full read) |
| 2 | Discriminator architecture | `gan_pytorch.py` (`class Discriminator`, lines 220-269) | ECG(1000,12) → real/fake score; **not used at inference time**, training-only |
| 3 | Training script | `gan_pytorch.py` (`train_gan()`, lines 276-376) + `generate_ecg_all_classes.py` (driver) | Trains one Generator/Discriminator pair per class, folds 1-8, 200 epochs |
| 4 | Inference/generation script | `gan_pytorch.py` (`generate_synthetic()`, lines 384-403) | Loads a trained `Generator`, samples noise, returns `(n,1000,12)` array |
| 5 | Model checkpoints | `checkpoints/generator_{NORM,MI,STTC,CD,HYP}.pt` | 5 trained weight files, ~135MB each |
| 6 | Generated ECG outputs | `synthetic_data/{CLASS}_synthetic.npy`, `all_classes_combined.npy`, `all_classes_labels.npy` | 500 synthetic samples per class already on disk (§3) |
| 7 | Dataset loader | `gan_pytorch.py` (`PTBXLDataset`, lines 76-141) | Loads real WFDB signals for training/eval, folds-filtered |
| 8 | Label/conditioning logic | `gan_pytorch.py` (`build_label_map()`, lines 34-67) | Maps `ecg_id` → superclass list; **used only to build per-class training sets, not as a model input** |
| 9 | Preprocessing | `PTBXLDataset._load_signal()` / `._normalise()` | `wfdb.rdrecord()` → per-record per-lead z-score → clip to `[-1,1]` |
| 10 | Postprocessing | **NONE FOUND** | No denormalization / physical-unit mapping exists anywhere in this codebase (VERIFIED — `generate_synthetic()` returns raw `[-1,1]` tanh output directly) |
| 11 | Normalization/scaling | `PTBXLDataset._normalise()` | Per-record, per-lead; mean/std computed and discarded, never persisted (inherited finding, reconfirmed) |
| 12 | Report generation | `generate_report.py` | Builds `SynDataGen_Evaluation_Report.docx`; unrelated to the generation pipeline itself |
| 13 | README/documentation | **NONE** — no README exists in `syngen/SynGen/SynGen/`; this project's own `docs/syngen-codebase-analysis.md` is the closest equivalent | |
| 14 | Sample outputs | `synthetic_data/*.npy`, `eval_*/generated_ecg_sample.png`, `eval_*/*.png` | See §3 |
| 15 | ECG-to-patient-ID mapping script | **NONE FOUND** | Nothing in `syngen/` references this project's `PAT_######` patient IDs at all — `syngen/` only ever keys by PTB-XL's own `ecg_id` |

## 3. Existing ECG Output Inventory

Loaded directly this session (`numpy.load`, read-only, no modification).

| File | Shape | Dtype | Size on disk |
|---|---|---|---|
| `synthetic_data/NORM_synthetic.npy` | (500, 1000, 12) | float32 | 24,000,128 bytes |
| `synthetic_data/MI_synthetic.npy` | (500, 1000, 12) | float32 | 24,000,128 bytes |
| `synthetic_data/STTC_synthetic.npy` | (500, 1000, 12) | float32 | 24,000,128 bytes |
| `synthetic_data/CD_synthetic.npy` | (500, 1000, 12) | float32 | 24,000,128 bytes |
| `synthetic_data/HYP_synthetic.npy` | (500, 1000, 12) | float32 | 24,000,128 bytes |
| `synthetic_data/all_classes_combined.npy` | (2500, 1000, 12) | float32 | 120,000,128 bytes |
| `synthetic_data/all_classes_labels.npy` | (2500,) | `<U4` string | 40,128 bytes |
| `real_{NORM,MI,STTC,CD,HYP}.npy` | matches each class's **training-fold** (1-8) count exactly (VERIFIED this session via `ls` byte sizes, e.g. `real_NORM.npy` = 362,544,128 bytes = 7,553 records — matches the previously-established training count) | float32/float64 | up to 362MB |

**Total generated ECGs already on disk: 2,500** (500 per class × 5 classes) —
**genuine waveforms, not metadata** (VERIFIED — full `(1000,12)` float
tensors with real per-sample variance, not placeholders).

Per-file quality scan (VERIFIED this session, direct load + numpy checks):

| Class | NaN/Inf | Min/Max | Mean/Std | Flatline samples (any lead std<1e-4) | Exact-duplicate samples |
|---|---|---|---|---|---|
| NORM | 0 / 0 | -1.0 / 1.0 | -0.040 / 0.557 | 0 / 500 | **55 / 500 (11%) — all one single repeated waveform** |
| MI | 0 / 0 | -1.0 / 1.0 | -0.029 / 0.535 | 0 / 500 | 0 / 500 |
| STTC | 0 / 0 | -1.0 / 1.0 | -0.005 / 0.513 | 0 / 500 | 0 / 500 |
| CD | 0 / 0 | -1.0 / 1.0 | -0.011 / 0.556 | 0 / 500 | 0 / 500 |
| HYP | 0 / 0 | -1.0 / 1.0 | -0.017 / 0.503 | 0 / 500 | 0 / 500 |

The NORM duplicate group was inspected directly: all 55 copies are
bit-identical (MD5-matched), and the repeated waveform itself is **not**
degenerate (std ≈ 0.598, a normal-looking amplitude) — this looks like a
classic partial-mode-collapse signature (a region of the noise space
collapsing to one output point through saturated BatchNorm/ReLU units)
rather than a corrupted or flat sample. **INFERENCE** on root cause
(mode collapse); **VERIFIED** on the observed fact (55 exact duplicates).

These 2,500 samples were generated by, and correspond directly to, the 5
checkpoints in `checkpoints/` — confirmed by filename correspondence and by
this session's own re-run of `generate_synthetic()` against
`generator_NORM.pt`, which reproduces the same architecture/shape (§6).
Whether these *specific* 2,500 samples were generated by the exact
checkpoint files currently on disk (vs. some earlier/later save of the same
architecture) is **INFERENCE**, not provable without a byte-level replay —
but file mtimes cluster within seconds of each other (`synthetic_data/*.npy`
all timestamped 2026-09-16 16:45:02-04) consistent with one single
generation run using the checkpoints present at that time.

## 4. Generator Architecture

Confirmed by direct file read this session (`gan_pytorch.py` lines 157-203):

```
noise (batch, 100)
   ↓ Linear(100→256) + BatchNorm + ReLU
   ↓ Linear(256→512) + BatchNorm + ReLU
   ↓ Linear(512→64000) + BatchNorm + ReLU
   ↓ reshape → (batch, 512, 125)
   ↓ ConvTranspose1d(512→256, k4 s2 p1) + BatchNorm + ReLU   → (batch,256,250)
   ↓ ConvTranspose1d(256→128, k4 s2 p1) + BatchNorm + ReLU   → (batch,128,500)
   ↓ ConvTranspose1d(128→12,  k4 s2 p1) + Tanh                → (batch,12,1000)
   ↓ permute(0,2,1)
output (batch, 1000, 12), range [-1,1]
```

**33,911,953 parameters** (VERIFIED, previously counted directly from the
loaded checkpoint's state_dict; re-confirmed this session by loading the
checkpoint again and running a live forward pass, §6/§11). No conditioning
input of any kind — `forward(self, noise)` takes exactly one tensor
(VERIFIED, direct code read this session).

The Discriminator exists only for training; `generate_synthetic()` never
constructs or calls it (VERIFIED).

## 5. Checkpoint Audit

| Checkpoint | Params | Format | Loadable read-only | Matches current `Generator` class |
|---|---|---|---|---|
| `generator_NORM.pt` | 33,911,953 | bare `OrderedDict` state_dict | YES — loaded and run this session | YES, exact key/shape match |
| `generator_MI.pt` | 33,911,953 (same arch) | same | YES (loaded, not run this session) | YES (key/shape match confirmed in the prior audit) |
| `generator_STTC.pt` | 33,911,953 | same | YES | YES |
| `generator_CD.pt` | 33,911,953 | same | YES | YES |
| `generator_HYP.pt` | 33,911,953 | same | YES | YES |

No optimizer state, epoch, or training metadata is embedded in any
checkpoint (VERIFIED, prior session). No checkpoint shows any sign of
truncation/corruption — all loaded cleanly with `torch.load(...,
map_location='cpu')` and, for NORM, a live forward pass this session
produced correctly-shaped output with no NaN/Inf.

## 6. PTB-XL Relationship

- **Trained on PTB-XL:** YES (VERIFIED — `PTBXLDataset` loads via
  `wfdb.rdrecord()` from the local `dataset/` folder).
- **Version:** PTB-XL 1.0.1 (VERIFIED, folder name).
- **Folds:** training strictly folds 1-8 (VERIFIED, `train_gan()` hardcodes
  `folds=list(range(1,9))`); evaluation's "real" comparison data uses the
  **same** folds 1-8, not held-out 9/10 — a confirmed leakage bug in the
  *evaluation metrics only*, not in training itself (inherited finding,
  cited from the prior audit, not re-derived byte-for-byte this session but
  the underlying `real_*.npy` file sizes were independently re-observed
  this session and are consistent with that finding).
- **Are generated ECGs copies of source waveforms, or learned/generated?**
  **Learned/generated, structurally guaranteed.** The Generator's only
  input is `torch.randn(batch, 100)` — random noise with no reference to
  any specific real record (VERIFIED, direct code read). It is
  architecturally impossible for this network to "copy" a specific PTB-XL
  waveform on a per-sample basis; it can only have learned a *distribution*
  during training. Whether it has memorized specific training examples
  (a distinct concern from "copying by construction") was **not** tested
  this session — that would require a nearest-neighbor search against all
  ~21,837 real training waveforms, out of scope for this audit's
  benchmark-only mandate. **UNKNOWN**, flagged rather than assumed.
- **Does the code use PTB-XL metadata, waveforms, or both?** Both — metadata
  (`ptbxl_database.csv`, `scp_statements.csv`) for the label map, and raw
  waveforms for training data (VERIFIED).

## 7. Conditioning Mechanism

**What the model actually accepts:** nothing but noise. There is no label,
class index, or embedding vector consumed anywhere in `Generator.forward()`
(VERIFIED, §4). "Conditioning" is achieved only at the *training-set*
level — five separate models are trained, each on a different filtered
subset of PTB-XL (one per superclass) — not at the *model-input* level.

**Can a current 100K patient JSON record be mapped to this model's required
conditioning input?** There is no conditioning input to map to in the
formal sense — but there is exactly one usable **model-selection** hook:
which of the 5 trained `Generator` objects to load and sample from.

- **What field could drive that selection today:** `ECGRecord.superclasses`
  (schema field, populated today via `ingestion/ptbxl_source.py`'s
  `load_ptbxl_record()`, itself sourced from `build_label_map()`'s per-
  record SCP-code classification of one real, seed-selected PTB-XL row).
  This field already exists on every one of the 100K patients (VERIFIED,
  read `ingestion/ptbxl_source.py` this session).
- **What is NOT used, and why this matters:** `load_ptbxl_record()` pulls
  exactly `ecg_id`, `superclasses`, `strat_fold`, `filename_lr`,
  `sampling_hz`, `signal_shape`, `age`, `sex`, `height`, `weight` from the
  **real** PTB-XL row it happened to draw by seed — nothing else (VERIFIED,
  full function read). It does **not** read, and has no path to read, this
  patient's separately-generated Indian-population `hypertension`,
  `diabetes`, `lipid_panel`, `lipid_interpretations`, `diagnoses`,
  `medications`, or `bmi`/`smoking_status` fields (all produced by
  `generation/indian_population.py` and `generation/clinical_history.py` on
  an entirely separate, unrelated random draw). **There is currently no
  code path connecting a patient's synthetic clinical state to which ECG
  superclass gets attached to them.**
- **Practical consequence:** using `ecg.superclasses` to select which of the
  5 generators to sample from is mechanically straightforward (a
  dictionary lookup + `if/elif`), but it would select a generator based on
  a real PTB-XL patient's original diagnosis — a patient who is not this
  project's synthetic patient and whose demographic/clinical profile this
  project's Indian-population synthetic patient does not share. This is not
  a code limitation; it is an evidence limitation, and it should not be
  silently glossed over as "the model is conditioned on the patient's
  clinical state" — it isn't. **This is this audit's single most important
  finding for Phase 9/14 design purposes.**

## 8. Waveform Specification

| Property | Declared project convention (`ingestion/ptbxl_source.py`) | Verified from `Generator` output |
|---|---|---|
| Leads | 12 | 12 (VERIFIED, `ConvTranspose1d(128, n_leads=12, ...)` and live forward-pass output shape `(batch,12,1000)`) |
| Samples per lead | 1000 | 1000 (VERIFIED, both from the architecture's reshape math — 125→250→500→1000 — and a live run this session) |
| Sampling rate | 100 Hz | **INFERENCE, not independently re-derivable from the tensor itself** — 1000 samples "is" 100Hz only because the training data (`sampling="lr"`, PTB-XL's own 100Hz release) was 100Hz; the Generator has no explicit sample-rate parameter. Consistent with, not contradicted by, the project's convention. |
| Duration | 10s | Follows directly from 1000 samples @ 100Hz (same caveat as above) |
| Dtype | float32 | float32 (VERIFIED) |
| Amplitude/units | undefined for this project (Stage 4 not started) | `[-1, 1]`, **not physical mV** — no denormalization exists (VERIFIED, §1/§2) |
| Tensor axis order | `[1000, 12]` (samples-first) | `(batch, 1000, 12)` after the explicit `.permute(0,2,1)` in `forward()` — **matches directly, no transpose needed** (VERIFIED) — this is a materially better fit than the SSSD-ECG alternative audited previously, which required a channels-first-to-samples-first transpose |
| Lead order | undefined for this project (Stage 4 not started); the one existing precedent (`wfdb.rdrecord` in this same codebase) is PTB-XL's native clinical order (I, II, III, aVR, aVL, aVF, V1-V6) | Generator's output channel order is whatever order `PTBXLDataset` fed it during training — i.e., the same native `wfdb` clinical order, since no reordering occurs anywhere in `PTBXLDataset`/`Generator` (VERIFIED by code read) — **consistent with the one existing precedent, no permutation needed if that convention is adopted** |

**Bottom line: shape (1000,12), dtype, and axis order all match this
project's stated intent directly with zero conversion needed** — a
materially simpler integration than the SSSD-ECG path audited previously
(which needed a transpose and a lead-order permutation). Amplitude
calibration is the one real gap (§9/§15).

## 9. Waveform Quality Findings

Performed without NeuroKit2 (confirmed **not installed** in the project's
Anaconda environment this session — `import neurokit2` raised
`ModuleNotFoundError`; not installed, per this audit's constraint).
Quality checks therefore limited to shape/NaN/flatline/amplitude/variance
analysis plus one naive `scipy.signal.find_peaks`-based heart-rate estimate
(the same library/technique already used by `evaluate_class.py` in this
codebase, reused rather than reinvented).

1. **Shape correctness:** 100% — all 2,500 existing samples are exactly
   `(1000,12)` (VERIFIED).
2. **NaN/Inf:** zero across all 2,500 samples, all 5 classes (VERIFIED).
3. **Flatline rate:** zero samples with any lead's std below 1e-4 across
   all 2,500 samples (VERIFIED) — no dead/corrupted channels.
4. **Amplitude range:** exactly `[-1.0, 1.0]` for every class (VERIFIED,
   Tanh output, as designed).
5. **Signal variance:** healthy and comparable across classes (std
   0.50-0.56 per class, VERIFIED) — no evidence of global mode collapse
   (only the localized NORM-specific issue in §3/§10).
6. **Per-lead statistics vs. real data (NORM):** the existing
   `eval_NORM/metrics_summary.txt` (already on disk, not regenerated this
   session — **inherited, not independently re-verified figure-by-figure**)
   reports per-lead std within ~0.01-0.03 of the real training-fold data
   and an overall KS statistic of 0.0972 / KL divergence 0.0843 — both
   under the script's own "excellent"/"very similar" thresholds. **Caveat
   carried forward unchanged from the prior audit: this comparison is
   against training-fold data, not held-out data (§6), so it should be
   read as "reproduces the training distribution reasonably well," not as
   "generalizes well to unseen data."**
7. **Heart-rate plausibility (naive check, this session):** a simple
   prominence-based peak detector (`scipy.signal.find_peaks`, distance=0.3s,
   prominence=0.3) on lead II of the first 20 NORM samples detected ≥2
   peaks in all 20, giving estimated rates of **71-122 BPM (mean ≈105
   BPM)**. This is a broadly physiologically plausible range, though
   skewed slightly high of typical resting 60-100 BPM — **INFERENCE**, not
   a clinical-grade R-peak detector (no NeuroKit2 available; this naive
   method is known to sometimes double-count T-waves as beats, which would
   bias the estimate upward). Should not be over-interpreted as validated
   heart-rate accuracy.
8. **Lead-to-lead relationship, obvious artifacts, detailed morphology
   plausibility:** not deeply assessed this session beyond the amplitude/
   variance/peak checks above — doing so properly would need NeuroKit2 or
   a cardiology-informed manual review, neither available/in scope here.
   **UNKNOWN** at that level of detail.
9. **The one concrete, quantified defect:** the 55/500 (11%) exact-duplicate
   NORM samples (§3) — a real, specific finding, not a general verdict on
   all five classes.

## 10. Uniqueness / Reuse Analysis

**The generator produces genuinely new waveforms, not reused PTB-XL
signals** — this follows structurally from the architecture (noise-only
input, no lookup table, no retrieval mechanism anywhere in `Generator` or
`generate_synthetic()`), not just from observation (VERIFIED by code read,
§4/§6).

Distinguishing the two senses of "reuse" the audit brief asked about:

- **"Referencing PTB-XL metadata":** YES, and by design — every patient
  already references a specific real PTB-XL `ecg_id` today (metadata-only,
  no waveform) via `ingestion/ptbxl_source.py`. This is expected, existing
  project behavior, unrelated to the GAN.
- **"Using the same generated waveform for multiple synthetic patients":**
  **Quantified problem exists, but only for NORM.** If the existing
  500-sample NORM batch were used as-is to serve, say, ~34,000 NORM-class
  patients in a 100K population (proportional to PTB-XL's own ~35% NORM
  share), the current batch's 11% duplicate rate would mean roughly 1 in 9
  NORM patients could receive an identical waveform to another — **but this
  is a symptom of reusing a small pre-generated batch, not an inherent
  property of the generator.** Freshly generating one new noise-conditioned
  sample per patient (rather than reusing this pre-made 500-sample batch)
  would not carry this specific duplicate forward in the same proportion,
  though it does not fix the underlying partial-mode-collapse tendency in
  the NORM checkpoint itself — repeated fresh sampling from that checkpoint
  will still statistically land in the collapsed noise region some
  fraction of the time. **INFERENCE:** re-running `generate_synthetic()`
  fresh for each of the ~34K NORM patients (rather than reusing this
  500-sample file) is a partial mitigation, not a fix for the underlying
  checkpoint defect.
- **No fixed random seed exists inside `generate_synthetic()`** (VERIFIED —
  no `torch.manual_seed()` call anywhere in the function); every call uses
  fresh `torch.randn(...)`. This means, unlike the rest of this project's
  generation pipeline (`configs/base.yaml`'s `random_seed: 42`, respected
  everywhere else per the project's own reproducibility convention), the
  GAN's output is **not currently reproducible run-to-run** unless a caller
  wraps it with an explicit seed — a real integration gap if this
  project's reproducibility standard (D032/CLAUDE.md §32) is to be
  preserved.

## 11. 100K Scalability

**Benchmark performed this session** (read-only, CPU-only — this machine
has no CUDA GPU, confirmed via `torch.cuda.is_available()` → `False`):
loaded `generator_NORM.pt` into the unmodified `Generator` class, ran
`.eval()` + `torch.no_grad()` forward passes at batch sizes matching
`generate_synthetic()`'s own internal batching (64), for n=10/50/100
samples, all held in memory only (nothing written to disk).

| n | Wall time | Per-sample (steady-state) |
|---|---|---|
| 10 | 0.32s | ~32ms (cold-start overhead dominates at this size) |
| 50 | 0.22s | ~4.4ms |
| 100 | 0.56s | ~5.6ms |

**Steady-state estimate: ~5ms/sample on ordinary CPU** (8 torch threads,
this machine), taking the 50/100-sample runs as representative and
discounting the n=10 cold-start outlier.

**Extrapolation (explicit assumptions stated — INFERENCE, not measured at
these scales):**

| Scale | Estimated time (single CPU, no GPU) | Estimated storage (float32, `(n,1000,12)`) |
|---|---|---|
| 1,000 | ~5 seconds | ~45.8 MB |
| 10,000 | ~50 seconds | ~458 MB |
| 100,000 | **~8-9 minutes** | **~4.58 GB** |

This storage estimate is consistent with, and cross-checks, this project's
own earlier independent estimate ("~4.8GB at 100K for a future waveform
representation," from the prior SSSD-ECG-focused audit work) — two
different estimation methods landing on the same number is a useful sanity
check (**VERIFIED-consistent**, not independently re-derived by a different
formula this session, but the arithmetic — `100,000 × 1000 × 12 × 4 bytes`
— is a direct, simple calculation, not a guess).

- **GPU/VRAM requirement:** effectively none for feasibility — the model
  has 33.9M parameters (~136MB in fp32) and runs comfortably on CPU at the
  measured rate. A GPU would help mainly with wall-clock convenience
  (larger batch parallelism) rather than making an otherwise-infeasible
  job feasible.
- **Batch inference:** supported natively — `generate_synthetic()` already
  batches internally (default batch_size=64).
- **Per-superclass independence:** YES — each of the 5 generators is a
  fully separate model; generating for different classes is embarrassingly
  parallel (could run 5 processes/GPUs simultaneously with zero shared
  state) — VERIFIED, no shared parameters or state between the 5
  `Generator` instances.
- **Obvious bottleneck:** none at the model-inference level. The real
  bottleneck for a 100K run would be orchestration/I-O (writing 100K
  waveform files or one large array, assigning them to patient records) —
  not GAN inference itself.
- **Is AWS GPU necessary for this specific model?** **No, not for
  feasibility.** It would still be reasonable to use AWS for convenience
  (a bigger/idle machine, parallel batch jobs, or because AWS is being
  provisioned anyway for other heavier project needs), but this
  particular ~34M-parameter DCGAN does not by itself require it.

## 12. Indian-Population Compatibility

Distinguishing the three layers the audit brief asked to separate:

- **A. Demographic generation** (age/sex/state/urban-rural/BMI/smoking/
  hypertension/diabetes/lipids): already implemented, entirely separately,
  in `generation/indian_population.py`, evidence-sourced from Indian
  national health surveys (Census 2011, ICMR-NNMS, ICMR-INDIAB) — **the
  syngen GAN plays no role in this layer and never did.**
- **B. Clinical-state generation** (diagnoses, medications, lipid
  interpretations): also implemented separately in
  `generation/clinical_history.py`, deterministically derived from the
  demographic/risk-factor layer — **again, no interaction with the GAN.**
- **C. ECG waveform generation:** this is the GAN's only role, and it
  operates on a **completely disconnected** input (pure noise) with no
  demographic or clinical conditioning of any kind (§7).

**Does having Indian-conditioned synthetic patients mean a new ECG
generator must be trained?** Not automatically, and this audit does not
conclude that. What can be said with evidence:

- The GAN was trained exclusively on PTB-XL, a dataset collected at a
  German clinical site (Physikalisch-Technische Bundesanstalt) —
  **VERIFIED as the sole training source** (§6), with **no ethnicity, age,
  or sex conditioning of any kind built into the model** (§7) — so there is
  no mechanism by which it *could* represent Indian-specific morphology
  even if such morphology exists in reality.
- This audit found **no evidence anywhere in this codebase or its
  documentation of ethnicity-specific ECG morphology being modeled,
  measured, or claimed** — consistent with this project's own standing
  principle (`CLAUDE.md` §4) of not inventing population-specific
  relationships without evidence.
- Whether real, clinically-established Indian-population-specific ECG
  morphology differences exist in the medical literature at all is
  **UNKNOWN to this audit** — that question was out of scope (this is a
  repository audit, not a literature review) and was not investigated.
- **Practical conclusion:** the existing GAN can generate a plausible
  *generic* PTB-XL-style waveform per diagnostic superclass. It cannot,
  and does not claim to, represent any Indian-specific morphological
  signal — not because it was deliberately excluded, but because the
  model has no demographic conditioning input of any kind to represent
  *any* population's specific morphology, Indian or otherwise. Using it
  is a "generic-shape, class-labeled waveform" choice, not an "Indian ECG"
  claim, and the resulting patient records should not be described as
  containing Indian-specific ECG morphology.

## 13. AWS Readiness

Grounded directly in the measurements in §11 (33.9M parameters, ~5ms/sample
CPU, no CUDA available locally to benchmark a GPU-accelerated number
directly this session — **UNKNOWN** for an actual measured GPU number, all
GPU statements below are INFERENCE from the model's size/CPU throughput,
not a direct GPU benchmark).

- **Minimum practical GPU VRAM:** effectively any CUDA GPU with a few GB
  free would run this model many times over — even a ~4GB entry-level GPU
  is generously sufficient for a ~136MB model plus batch activations at
  this signal size (INFERENCE, not benchmarked on this session's CPU-only
  machine).
- **Recommended VRAM:** 8GB is comfortably more than enough headroom;
  larger (16GB+) buys only larger-batch convenience, not a capability this
  model needs.
- **Expected generation time (GPU, INFERENCE):** likely well under the
  ~8-9 minute CPU estimate for 100K, plausibly low single-digit minutes
  with batched GPU inference — not independently measured this session
  (no local GPU).
- **Storage requirement:** ~4.58GB at 100K (§11, direct arithmetic).
- **Is one GPU sufficient?** Yes — nothing about this workload benefits
  meaningfully from multi-GPU given the model's small size and the
  embarrassingly-parallel per-class structure (§11); multiple GPUs would
  mainly help by running the 5 class-generators concurrently rather than
  needing more VRAM per generator.
- **Is AWS necessary, or merely convenient, for this specific model?**
  **Convenient, not necessary** — this model runs adequately on ordinary
  CPU already (§11). AWS GPU makes sense if it's being provisioned for
  other heavier project work anyway, or for orchestration/parallelism
  convenience, not because this GAN demands it.
- No specific AWS instance type or price is recommended here, per this
  audit's own instruction not to cite a price/instance that can't be
  verified from this session's evidence.

## 14. 100K Integration Proposal

**Architectural options only — no schema change made or chosen here.**

- **Option A — embed waveform directly in patient JSON:** would add
  ~48KB of raw float data per patient (100K × 48KB ≈ 4.58GB spread across
  100K JSON files) — inflates every patient record by roughly an order of
  magnitude versus today's ~3.5KB/patient metadata-only footprint (M5's own
  measured figure), hurts JSON readability, and duplicates a pattern this
  project has not used for any other large array-shaped data.
- **Option B — store waveforms externally, reference by ID:** e.g. one
  waveform file (or a small number of batched array files) under
  `outputs/`, keyed by `patient_id` or `ecg_id`, referenced from the
  patient JSON by path/ID only (mirroring how `outputs/` is already used
  for pipeline artifacts, and how `ecg_id` already exists as a join key
  today). This keeps JSON records lightweight, matches the project's
  existing `outputs/` convention, and avoids repeating the same 48KB
  blob inside every downstream JSON copy/diff/git operation.
- **Option C — another already-supported approach:** none found in this
  repository — there is no existing precedent here for embedding or
  externally storing large binary arrays per patient; Option B is a new
  but incremental extension of existing conventions, not an invented one.

**This audit's non-binding read:** Option B looks like the better fit
against every listed criterion (dataset size, portability, JSON
readability, downstream ML use, which typically wants raw arrays anyway,
not JSON-embedded floats) — but this is offered as an architectural
observation, not a decision, per the brief's explicit instruction not to
auto-select a schema change.

```
PAT_000001
    ↓ existing: demographics, risk_factors, diagnoses, ECG metadata (superclass, ecg_id)
    ↓ [NEW, not yet built] ECG conditioning decision — currently only
      "which of 5 unconditional generators to sample from," driven by the
      PRE-EXISTING (real-PTB-XL-sourced) superclass field, not by this
      patient's own synthetic clinical state (§7 caveat applies)
    ↓ existing syngen Generator (noise → waveform, no other input)
    ↓ synthetic (1000,12) float32 waveform, range [-1,1], no physical units
    ↓ [NOT YET DESIGNED] storage decision (Option A/B above)
    ↓ PAT_000001's ECG record gains either an embedded array or a reference
```

## 15. Risks / Limitations

1. **No conditioning-to-clinical-state linkage exists** (§7) — the most
   significant architectural gap for "coherent" synthetic records.
2. **No amplitude/physical-unit calibration** — output stays in per-record
   z-scored `[-1,1]` space, not recoverable to mV (§8/§9, inherited).
3. **Confirmed partial mode collapse in the NORM checkpoint** (11% exact
   duplicates in the existing batch) — NORM is typically the
   plurality/majority class in any realistic population, making this the
   single highest-impact quality issue found (§3/§9/§10).
4. **No built-in reproducibility/seeding** in `generate_synthetic()` —
   breaks from this project's otherwise-consistent `random_seed`
   convention unless a caller adds it (§10).
5. **Confirmed evaluation-metric leakage** (inherited finding) — existing
   quality metrics (§9 point 6) describe fit to training data, not
   generalization to unseen data; should not be over-cited as proof of
   quality.
6. **No license/ownership resolution for this code or its checkpoints**
   (inherited finding from the prior audit — unchanged, not re-litigated
   here since this audit's scope was technical, not legal/ownership).
7. **Memorization of specific training examples was not tested** (§6) —
   a real, unresolved gap for anyone treating "these are definitely novel
   waveforms" as a settled fact rather than a structural likelihood.
8. **No Indian-specific morphology representation of any kind** (§12) —
   not a defect exactly, but a real limitation that should be stated
   plainly in any downstream documentation of the resulting dataset.
9. **Detailed morphology/lead-relationship plausibility was not deeply
   assessed** (no NeuroKit2 available this session) — only a coarse
   engineering-level check was possible (§9).

## 16. GREEN/YELLOW/RED Decision

# **YELLOW**

The generator works, produces correctly-shaped, non-corrupted, genuinely
novel (by construction) 12-lead waveforms that match this project's
declared convention with no conversion needed, and is trivially cheap to
run at 100K scale even without a GPU. It is not disqualified by
architecture, shape mismatch, or scale. But it should not proceed straight
to a 100K production run without addressing: the NORM mode-collapse defect
(§3), the missing conditioning-to-clinical-state linkage (§7), the missing
amplitude calibration (§8), and the missing reproducibility seeding (§10).
None of these require a new model or a redesign — they are scoped,
addressable engineering gaps.

## 17. Recommended Next Steps

1. Decide (human decision, not a technical one) whether attaching ECGs via
   the existing, clinically-disconnected superclass field is acceptable as
   an interim step, or whether the project wants to wait for/design a real
   clinical-state-to-superclass mapping first (§7).
2. Before generating at any real scale, re-run `check_mode_collapse()`
   (already present in `gan_pytorch.py`) against a fresh, larger NORM
   sample batch to characterize the duplicate-producing region more
   precisely, and decide whether to accept, filter, or retrain-fix NORM
   specifically.
3. Add explicit seeding to a wrapper around `generate_synthetic()` before
   any patient-linked generation, to preserve this project's
   reproducibility convention.
4. Decide the storage architecture (§14, Option A vs. B) before writing any
   integration code.
5. Generate a small (1,000-patient) trial batch first, per this project's
   own progressive-scaling convention (`CLAUDE.md` §27), before committing
   to 10K/100K.
6. If deeper waveform-morphology validation is wanted, install NeuroKit2
   (a genuine new dependency decision, not made by this audit) and repeat
   §9's checks with proper R-peak/QRS-duration detection.

## 18. Exact Files Inspected

`syngen/SynGen/SynGen/gan_pytorch.py` (full read, this session),
`ingestion/ptbxl_source.py` (full read, this session),
`syngen/SynGen/SynGen/checkpoints/generator_{NORM,MI,STTC,CD,HYP}.pt`
(loaded read-only; NORM additionally run through a live forward pass this
session), `syngen/SynGen/SynGen/synthetic_data/{NORM,MI,STTC,CD,
HYP}_synthetic.npy`, `all_classes_combined.npy`, `all_classes_labels.npy`
(all loaded and inspected this session), `syngen/SynGen/SynGen/real_
{NORM,MI,STTC,CD,HYP}.npy` (sizes inspected via `ls`, not loaded this
session), `syngen/SynGen/SynGen/eval_NORM/metrics_summary.txt` (read this
session), `docs/syngen-codebase-analysis.md`, `docs/M6_SSDD_ECG_
COMPATIBILITY.md`, `docs/M7_0_CONDITIONING_AUDIT.md`, `docs/DECISIONS.md`
(D001-D003, D015, D016) — all consulted for cited, not re-derived, prior
findings from this project's own earlier audit work.

## 19. Exact Commands/Tests/Benchmarks Performed

- `ls -la --time-style=full-iso` on `synthetic_data/`, `real_*.npy`,
  `checkpoints/`, and `eval_NORM/` (file inventory/sizes/mtimes).
- `torch.cuda.is_available()` → `False`; `torch.get_num_threads()` → `8`;
  `import neurokit2` → `ModuleNotFoundError` (all this session).
- `numpy.load()` on all 7 `synthetic_data/*.npy` files, with NaN/Inf/min/
  max/mean/std/flatline/MD5-duplicate checks computed directly (this
  session).
- A CPU-only, read-only benchmark: loaded `generator_NORM.pt` into the
  unmodified `Generator` class, `.eval()`, `torch.no_grad()`, generated
  n=10/50/100 samples via fresh `torch.randn` noise at batch_size=64 (same
  batching `generate_synthetic()` itself uses), timed with
  `time.perf_counter()`. **No output was written to any file** — the
  generated tensors existed only in the Python process's memory during
  this benchmark.
- A naive heart-rate plausibility check on the first 20 existing NORM
  samples using `scipy.signal.find_peaks` (lead II, distance=0.3s,
  prominence=0.3) — this session.

## 20. Anything That Could Not Be Verified

- Whether the generator has memorized specific PTB-XL training waveforms
  (would require a nearest-neighbor search against all training records;
  not performed, out of scope for a benchmark-only mandate) — **UNKNOWN**.
- The root technical cause of the NORM checkpoint's partial mode collapse
  (inferred as a saturated-BatchNorm/ReLU noise-space collapse, not
  confirmed by gradient/activation inspection) — **INFERENCE only**.
- Actual GPU throughput/VRAM usage (no CUDA GPU available on this
  machine this session) — **UNKNOWN, all GPU figures in §13 are
  INFERENCE** from the CPU benchmark and parameter count.
- Whether the exact 2,500 samples on disk in `synthetic_data/` were
  produced by precisely the checkpoint files currently present (vs. some
  earlier save of the same architecture) — **INFERENCE** from matching
  mtimes, not a byte-level replay.
- Detailed clinical/morphological plausibility (T-wave, ST-segment, P-wave
  shape correctness) beyond coarse amplitude/variance/naive-peak checks —
  **UNKNOWN**, would need NeuroKit2 or expert review, neither available/
  in scope here.
- Whether real Indian-population-specific ECG morphology differences exist
  in the broader medical literature at all (a literature-review question,
  not a repository-audit question) — **UNKNOWN, not investigated**.

---

## RECOMMENDATION FOR CHATGPT REVIEW

- The inherited `syngen/` model is a small (33.9M-parameter) DCGAN, not a
  diffusion model — five independent, unconditional generators, one per
  PTB-XL superclass (NORM/MI/STTC/CD/HYP).
- It genuinely generates novel synthetic 12-lead waveforms (noise-only
  input, structurally cannot copy a specific real record) — verified by
  reading the architecture directly, not inferred from output alone.
- Output shape is exactly `(1000, 12)` float32, matching this project's
  declared 100Hz/1000-sample/samples-first convention with **zero
  conversion needed** — a simpler fit than the previously-researched
  external SSSD-ECG alternative, which required a transpose and lead
  reorder.
- Output amplitude is `[-1, 1]` (per-record z-scored, then clipped) —
  **not physical mV**, and there is no denormalization step anywhere in
  this codebase to recover real units.
- The model has **zero conditioning mechanism** — no demographic, disease,
  or label vector is ever fed into it; "conditioning" only exists as
  "which of 5 separately-trained models to load."
- The only field in this project's schema that could plausibly select
  which of the 5 generators to use (`ecg.superclasses`) comes from a real
  PTB-XL record picked independently by seed — **it has no relationship to
  this project's own synthetic Indian-population clinical fields**
  (hypertension, diabetes, lipids, diagnoses). Wiring it in today would
  look coherent but would not actually be clinically grounded.
- A direct, quantified defect was found: **11% of the existing 500 NORM
  samples on disk are exact byte-for-byte duplicates of one waveform** —
  a partial mode-collapse signature, specific to the NORM checkpoint only
  (the other four classes show zero exact duplicates).
- No NaN/Inf/flatline samples exist across any of the 2,500 already-
  generated waveforms.
- A naive (non-NeuroKit2) heart-rate check on 20 NORM samples found
  physiologically plausible rates (71-122 BPM), with the caveat that the
  detection method is basic and may over-count beats.
- CPU-only benchmark (this session, no GPU available locally): ~5ms per
  sample steady-state → **~8-9 minutes for 100,000 samples on ordinary
  CPU alone.**
- Estimated storage for 100K raw waveforms: **~4.58GB** (float32,
  cross-consistent with this project's own earlier independent estimate).
- **AWS GPU is not technically required for this specific model** to be
  feasible at 100K scale — it would only add convenience/parallelism, not
  capability, given the model's small size.
- If a GPU is used anyway, even a modest (~4-8GB VRAM) card is inferred to
  be more than sufficient — not independently benchmarked on GPU this
  session (none available locally).
- No evidence exists, and none is claimed, that this generator can
  represent Indian-specific ECG morphology — it was trained solely on a
  German clinical cohort (PTB-XL) with no ethnicity/demographic
  conditioning of any kind.
- Evaluation metrics already on disk for this model describe fit to
  **training-fold data**, not held-out generalization — a known, inherited
  leakage caveat on the existing `.docx`/`metrics.json` quality claims.
- No built-in random seeding exists in the generation function — output is
  not currently reproducible run-to-run, unlike the rest of this project's
  pipeline.
- Whether the model has memorized specific training waveforms was not
  tested this session (would need a nearest-neighbor search) — flagged as
  unknown, not assumed either way.
- **Overall verdict: YELLOW** — technically usable, shape/scale/cost are
  not blockers, but the clinical-conditioning gap, the NORM mode-collapse
  defect, the missing amplitude calibration, and the missing seeding
  should be addressed (or explicitly accepted as known limitations) before
  a full 100K production run.
