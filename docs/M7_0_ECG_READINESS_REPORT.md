# M7-0 — ECG Implementation Readiness Report

**Status: RESEARCH + MEASUREMENT ONLY. No ECG generated. No model
selected. No schema/generation/integration/validation/configs file
changed. The existing 100K dataset (`outputs/m5/100k_patients/`) was
not touched or read for modification.** This is the human-checkpoint
decision package requested for M7-0. It builds on, and does not
duplicate, `docs/M6_ECG_MODEL_SELECTION.md`, `docs/
M7_ECG_IMPLEMENTATION_PLAN.md`, `docs/M6_SSDD_ECG_COMPATIBILITY.md`,
and `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md` — all remain
authoritative for the detail they contain. New evidence this session is
marked **NEW** throughout.

## Executive summary

- SSSD-ECG remains the only candidate with both runnable inference code
  and a real (though license-unresolved) pretrained checkpoint.
- **NEW:** the 44-vs-71 conditioning discrepancy is now resolved with
  high confidence (not full proof): the model's conditioning input is
  architecturally hard-wired to 71 dimensions (a matmul shape
  constraint, not a soft default), and the most likely source array is
  `label_all` (all 71 unfiltered SCP codes) — not `label_diag` (44
  diagnostic-only) as the prior session assumed. Full detail:
  `docs/M7_0_CONDITIONING_AUDIT.md`.
- **NEW:** this project's own local PTB-XL files can supply that
  71-dim vector directly — no new dataset required, and the
  compatibility verdict for conditioning improves from M6's "PARTIAL,
  leaning INCOMPATIBLE-AS-IS" to "content recoverable, exact index
  order not yet confirmed."
- **NEW:** a partial, code-verified parameter count was computed
  directly from the fetched architecture (~26.5M parameters excluding
  the S4 kernel internals, which are not vendored in this repository).
  The true total is estimated, not measured, but is confidently in a
  range that does not stress an 8GB GPU for inference.
- **NEW:** a real preprocessing detail was found that changes the
  amplitude-convention question from "not investigated" to "actively
  unresolved" — see §6.
- **UNCHANGED:** the pretrained-weight license remains UNKNOWN — the
  single blocking item, not resolved this session (per explicit
  instruction, no bypass of the private Figshare link was attempted).
- **No model is selected. No implementation proceeds.**

## 1. Verified facts (this session, sourced from direct fetches of SSSD-ECG's own repository files)

- `SSSD_ECG.py`'s label-conditioning mechanism is `label @
  self.embedding.weight`, where `self.embedding = nn.Embedding(
  label_embed_classes=71, label_embed_dim=128)` — a matrix multiply,
  **not** an index lookup. This requires `label` to be shape `[B, 71]`.
- `ecg_utils.py`'s `prepare_data_ptb_xl()` builds **six** label arrays
  (`label_all`, `label_diag`, `label_form`, `label_rhythm`,
  `label_diag_subclass`, `label_diag_superclass`), not just the one
  (`label_diag`, 44 diagnostic codes) the prior session's audit
  inspected.
- `train.py` loads `ptbxl_train_data.npy` and `labels_ptbxl` (not
  computed live from the fetched preprocessing notebook — that notebook
  contains no `np.save()` call at all) and applies **no normalization**
  to the waveform array before training.
- Full residual-block architecture (`fc_t`, `conv_layer`, `res_conv`,
  `skip_conv`, `fc_label`, two `S4Layer` instances) quoted verbatim in
  `docs/M7_0_ECG_READINESS_REPORT.md` §5 below.
- `scp_statements.csv` (this project's own local file) has exactly 71
  rows, 44 flagged `diagnostic==1` — independently confirmed by direct
  inspection this session (`pandas.read_csv`, this project's Anaconda
  interpreter per D002).
- `ptbxl_database.csv` (this project's own local file) has a `scp_codes`
  column already present, per-record, e.g. `{'NORM': 100.0, 'LVOLT':
  0.0, 'SR': 0.0}` for `ecg_id=1`.
- `configs/base.yaml`'s `training_folds: [1..8]` already restricts this
  project's synthetic sampling away from PTB-XL's official folds 9/10
  (carried forward from `docs/M6_ECG_MODEL_SELECTION.md` §9, re-verified
  present this session, unchanged).
- Full test suite: 103/103 passing (re-run this session, see §14).

## 2. Unresolved facts

1. **Pretrained-weight license** — UNKNOWN. Not attempted to bypass.
2. **Exact conditioning vector index order** — plausibly
   `sorted(unique codes)` per `map_and_filter_labels()`'s described
   behavior, not confirmed.
3. **Whether the conditioning vector is confidence-weighted (raw
   `scp_codes` values) or binarized** at the point it enters training.
4. **True total parameter count** — a verified partial count (~26.5M,
   excluding S4 kernels) plus an unverified but bounded estimate for
   the S4 layers themselves (§7).
5. **Amplitude/normalization convention of the actual training data**
   (§6) — a genuinely new open question this session surfaced, not
   previously flagged.
6. **Whether the checkpoint dict's `model_state_dict` shapes actually
   match what's described in the fetched source** (only a manual
   checkpoint load, blocked by the license issue, would fully confirm
   this).

## 3. SSSD-ECG architecture — verified from source

| Component | Value | Source |
|---|---|---|
| Diffusion steps (T) | 200 | `config_SSSD_ECG.json` |
| Residual layers | 36 | same |
| Residual/skip channels | 256 / 256 | same |
| In/out channels | 8 / 8 | same |
| Diffusion-step embed dims | 128 → 512 → 512 | same |
| S4 state dim (N) | 64 | same |
| S4 bidirectional/layernorm | both on | same |
| Label embed classes / dim | 71 / 128 | same |
| Segment length / sampling rate | 1000 / 100Hz | same |
| Per-block layers | `fc_t: Linear(512,256)`, `conv_layer: Conv(256,512,k=3)`, `S41/S42: S4Layer(features=512, N=64)`, `res_conv: Conv1d(256,256,k=1)`, `skip_conv: Conv1d(256,256,k=1)`, `fc_label: Linear(128,512)` | `SSSD_ECG.py`, quoted verbatim in `docs/M7_0_CONDITIONING_AUDIT.md`-adjacent research this session |
| Top-level layers | Initial `Conv(8,256,k=1)`+ReLU; `nn.Embedding(71,128)`; `fc_t1: Linear(128,512)`, `fc_t2: Linear(512,512)`; output `Conv(256,256,k=1)`+ReLU + `ZeroConv1d(256,8,k=1)` | same |

## 4. Conditioning analysis

See `docs/M7_0_CONDITIONING_AUDIT.md` for the complete investigation.
Summary: 71-dim conditioning is a hard architectural requirement;
`label_all` (unfiltered, all 71 SCP codes) is the high-confidence, not
fully proven, candidate; this project's own local files already contain
the source data (`scp_codes` column, 71-row `scp_statements.csv`)
needed to build it; the exact index order and binarization convention
remain unconfirmed without the checkpoint or the original
label-producing script.

## 5. 44-vs-71 investigation

Fully covered in `docs/M7_0_CONDITIONING_AUDIT.md` — not duplicated
here per this milestone's instruction to keep the conditioning
deep-dive in its own document.

## 6. PTB-XL / waveform representation compatibility

Carrying forward `docs/M6_SSDD_ECG_COMPATIBILITY.md`'s verdicts
(sample count and rate: DIRECT MATCH; axis order and lead order:
REQUIRES lossless conversion), plus one **NEW** finding this session:

| Dimension | Project | SSSD-ECG | Classification |
|---|---|---|---|
| Sampling rate | 100Hz | 100Hz | IDENTICAL |
| Duration | 10s | 10s | IDENTICAL |
| Sample count | 1000 | 1000 | IDENTICAL |
| Lead count | 12 | 12 (8 sampled + 4 derived) | LOSSLESS CONVERSION (the 4-lead derivation is SSSD-ECG's own internal step, happens before this project would ever see the output) |
| Lead order | undefined (likely standard clinical, per the one existing `wfdb` precedent) | `[I,II,V1-6,III,aVR,aVL,aVF]` | LOSSLESS CONVERSION (fixed permutation) once this project's own order is formally decided |
| Tensor orientation | `[1000, 12]` samples-first | `(12, 1000)` / `(8,1000)` internally, channels-first | LOSSLESS CONVERSION (transpose) |
| dtype | not yet defined for waveforms (schema declares shape only) | float32 (no fp16 path found in fetched training code) | Recommend float32, matches |
| Amplitude convention | undefined — no waveform generated yet | **UNRESOLVED, NEW FINDING** | See below |

**NEW finding on amplitude convention:** `prepare_data_ptb_xl()` computes
`mean_ptb_xl, std_ptb_xl` (per-channel dataset statistics) and passes
them to `save_dataset(...)`, but the raw `.npy` files it writes are
**not** themselves normalized — `np.save()` is called directly on the
resampled signal with no `(x-mean)/std` step in the fetched code. A
direct fetch of `train.py`'s data-loading section confirms this
independently: the loaded `ptbxl_train_data.npy` array is used with
**no normalization applied anywhere in the training script** — only
channel selection (`torch.index_select`) and a dtype cast to float.
**This means the amplitude scale of the file `ptbxl_train_data.npy` —
whatever it is — is what the model was trained on directly.** That
file's own provenance (whether it's raw PTB-XL mV values, or was
pre-scaled by some step not present in the fetched files, e.g. a
separate script that ran once and isn't in this repo) **could not be
confirmed this session.** Consequence: whether a future conversion step
needs an amplitude rescale is genuinely unknown until a real generated
sample can be compared against real PTB-XL amplitude ranges (deferred
to M7-3, per `docs/M7_0_ECG_IMPLEMENTATION_CONTRACT.md`'s Process
step 4). No resampling is needed in any case (rate/length already match
exactly) — this is strictly an amplitude-scale question, separate from
the already-settled shape/rate compatibility.

**No filtering (bandpass, baseline-wander removal) is applied by
SSSD-ECG's own preprocessing** — confirmed directly; `resample_data()`
performs only frequency conversion via `resampy.resample()`.

## 7. Parameter count / VRAM analysis

**Verified-from-source-code component** (every layer explicitly quoted
from the fetched `SSSD_ECG.py`, excluding the two `S4Layer` instances
per residual block):

| Component | Params |
|---|---|
| Initial `Conv(8,256,k=1)` + bias | 2,304 |
| `nn.Embedding(71,128)` | 9,088 |
| `fc_t1: Linear(128,512)` | 66,048 |
| `fc_t2: Linear(512,512)` | 262,656 |
| Output `Conv(256,256,k=1)` + `ZeroConv1d(256,8,k=1)` | 67,848 |
| **Top-level subtotal** | **407,944** |
| Per residual block: `fc_t`(512→256) + `conv_layer`(256→512,k=3) + `res_conv`(256→256) + `skip_conv`(256→256) + `fc_label`(128→512) + 2×LayerNorm(512) | 724,736 |
| **× 36 residual blocks** | **26,090,496** |
| **TOTAL VERIFIED (excl. S4 kernels)** | **≈ 26.50M parameters** |

**Unverified component:** each of the 72 `S4Layer` instances (36 blocks
× 2) wraps an upstream `state-spaces/s4` HiPPO SSM kernel whose own
parameter-defining source file is **not vendored in the SSSD-ECG
repository** and was not fetched this session (a further external
dependency, out of this narrow spike's scope). **This audit will not
report a fabricated precise figure for this component.** Based on
publicly documented S4 layer parameter scaling at this size (features≈
512, state N=64), each instance plausibly contributes on the order of
several hundred thousand to a few million parameters (dominated by its
own internal output projection, not the state-space kernel itself,
which is typically small). **Bounded estimate: the true total parameter
count is plausibly in the 50M-150M range** — still, by any measure,
a small-to-moderate diffusion model, not a large one.

**Parameter count status: PARTIALLY MEASURED.** ~26.5M is a real,
code-derived figure; the remainder is an explicitly-labeled estimate,
not a guess presented as fact.

**Memory footprint implications:**
- Weights alone: even at the high end of the estimate (150M params),
  fp32 weights are ≈ 600MB, fp16 ≈ 300MB — a small fraction of an 8GB
  card's capacity.
- Activation memory for single-sample or small-batch inference at this
  channel width (256-512) and length (1000) is on the order of a few MB
  per intermediate tensor — not a GB-scale concern.
- **Conclusion: 8GB VRAM is very likely SUFFICIENT for inference**, with
  materially stronger grounding than the prior session's pure
  architecture-based guess (this session ties it to an actual
  parameter-count derivation, not just "the layer counts look modest").
  **Still not independently measured** — the checkpoint itself remains
  license-blocked, so this is DERIVED, not MEASURED.

## 8. Licensing analysis — unchanged, not bypassed

| Item | Status |
|---|---|
| SSSD-ECG code license | MIT — CONFIRMED (unchanged from M6) |
| SSSD-ECG pretrained-weight license | **UNKNOWN — HUMAN VERIFICATION REQUIRED.** Not attempted to bypass the private Figshare link this session, per explicit instruction. |
| PTB-XL dataset license | CC BY 4.0 — CONFIRMED (unchanged) |
| NeuroKit2 license | MIT — CONFIRMED (unchanged) |
| Commercial use / modification / redistribution / attribution for the checkpoint specifically | Cannot be determined without the weight license itself |
| Generated-output restrictions | Cannot be determined without the weight license itself |

**Code license and weight license are explicitly treated as separate
facts, not conflated**, per this milestone's instruction.

## 9. Leakage analysis

Carrying forward and sharpening `docs/M6_ECG_MODEL_SELECTION.md` §9:

1. **The risk:** SSSD-ECG was trained on PTB-XL (confirmed — `trainset_config.
   finetune_dataset: "ptbxl_all"`, and no other dataset is referenced
   anywhere in the fetched code). This project's own synthetic
   population also derives its ECG *metadata* from PTB-XL. If the
   released checkpoint was trained on all of PTB-XL (its own repo shows
   no fold-1-8 restriction the way this project's `configs/base.yaml`
   applies to its own sampling), a waveform generated by that checkpoint
   for a given conditioning vector could, in principle, closely resemble
   or reproduce a real training-set record's waveform — a memorization
   risk inherent to any pretrained generator trained on a public,
   relatively small (~21,837-record) dataset.
2. **Why it matters:** this project's own PTB-XL-derived `ecg_id`s are
   already real identifiers pointing at real patients (anonymized, but
   real recordings). Publishing a "synthetic" waveform that is in fact a
   near-exact reproduction of one specific real recording would
   undermine the synthetic-data claim this project's `CLAUDE.md` §10
   requires ("synthetic data must not be represented as real patient
   data" cuts both ways — it also must not accidentally *be* real
   patient data under a synthetic label).
3. **What future validation should test:** `docs/M6_ECG_VALIDATION_PLAN.md`
   item #13 (membership-inference / 1-NN distance check against real
   PTB-XL) already covers this — not re-designed here. **This project's
   own fold-1-8 discipline (`configs/base.yaml`) does not protect
   against this risk**, because the risk is about the *external
   pretrained model's* training exposure, not this project's own
   conditioning-sampling process — a distinction `docs/
   M6_ECG_MODEL_SELECTION.md` §9 already drew and this report reaffirms.
4. **Implementation guardrails (recommended, not implemented):** (a) run
   the membership-inference check (already designed) before any
   generated batch is treated as final; (b) never present a generated
   waveform's `ecg_id` field as if it denotes the *generated content's*
   identity — it denotes only the *conditioning source*, per
   `docs/M7_0_ECG_IMPLEMENTATION_CONTRACT.md`'s ECG-ID-policy section;
   (c) if the membership-inference check ever flags a high reproduction
   risk for a specific conditioning vector, that generation should be
   rejected/regenerated with a different seed, not silently accepted.

## 10. Hardware analysis — by stage

| Stage | Hardware needed | Why |
|---|---|---|
| Model/checkpoint inspection (M7-0 itself, once license permits) | CPU sufficient, or either GPU | Loading a ~26.5M-150M-param checkpoint and calling `print_size(net)` needs no meaningful compute |
| Checkpoint loading | 8GB sufficient | Weights alone ≈ 100-600MB (§7) |
| Single-sample inference | 8GB sufficient | Activation memory is MB-scale at this channel width/length |
| Small-batch inference (e.g. 4-16) | 8GB likely sufficient | Batch scales activation memory linearly; still small relative to 8GB given single-sample headroom |
| Large-batch generation | 36GB gives headroom | Larger batches trade wall-clock for memory; 8GB may cap batch size before 36GB would, but neither is "insufficient" for correctness — only throughput |
| 100K generation | 8GB sufficient in principle; 36GB reduces wall-clock via larger batches | No VRAM ceiling identified either way — a throughput/time tradeoff, not a feasibility gate |
| 1M generation | Same as 100K, more pronounced | Same reasoning, larger absolute time savings from bigger batches on the 36GB machine |
| Waveform validation (NeuroKit2, distributional checks) | CPU-only, no GPU needed | NeuroKit2 and statistical comparisons are not GPU-bound operations |

**8GB (RTX 4060): SUFFICIENT for every stage's correctness; not
independently measured, DERIVED from a partially-verified parameter
count (§7) — materially stronger grounding than M6's estimate, still
not a substitute for an actual benchmark once the license permits one.**

**36GB machine: not required for correctness at any stage; useful only
for wall-clock throughput at the 100K/1M generation stages via larger
batch sizes.** No stage was found where 8GB is insufficient.

## 11. Alternative model check — reviewed, not re-researched

Per this milestone's instruction not to re-run the model survey,
`docs/M6_ECG_MODEL_SELECTION.md` §6's comparison table (SSSD-ECG,
DiffuSETS, FlowECG, cNVAE-ECG, FEM-simulator VAE) is reviewed and
reaffirmed unchanged — nothing this session's SSSD-ECG-specific deep
dive found changes any of those four alternatives' classification.
**If SSSD-ECG's weight license turns out to be unusable, DiffuSETS
remains the documented fallback** — it is the only other candidate with
both runnable inference code and openly-licensed (MIT, via Hugging
Face) pretrained weights, at the cost of a conditioning mismatch (free
text, not SCP/superclass labels) that would need its own translation
layer, not evaluated further here.

## 12. Implementation contract

See `docs/M7_0_ECG_IMPLEMENTATION_CONTRACT.md` — the full input/process/
output design, storage/dtype/compression recommendations, and the
ECG-ID/reproducibility policy, none of it implemented.

## 13. Human decision checklist

Only decisions genuinely requiring human authorization — none made here:

1. **SSSD-ECG selection:** SUITABLE (technically, pending the license)
   / UNSUITABLE / INSUFFICIENT EVIDENCE — **not decided by this
   document.**
2. **44-vs-71 conditioning:** this session provides a high-confidence
   (not proven) resolution (`label_all`, all 71 codes) — human must
   decide whether "high confidence, not proven" is sufficient to proceed
   with implementation, or whether further verification (e.g. obtaining
   the checkpoint to inspect its embedding shape directly) is required
   first.
3. **Whether raw SCP codes should ever enter the patient schema** — now
   confirmed cheap and locally available (`docs/
   M7_0_CONDITIONING_AUDIT.md` §5), but still a real schema decision.
4. **Whether the pretrained-model leakage risk (§9) is acceptable** with
   the proposed guardrails (membership-inference gating, ECG-ID
   labeling discipline), or requires training from scratch instead.
5. **Inline vs. external waveform storage** — not decided
   (`docs/M7_0_ECG_IMPLEMENTATION_CONTRACT.md`).
6. **Whether 8GB hardware is sufficient to proceed with implementation,
   or whether to wait for/use the 36GB machine** — this report's finding
   is "8GB sufficient for correctness at every stage," but the human may
   still prefer 36GB for throughput; not decided here.
7. **Whether to authorize M7-1** (source-conditioning extraction) — the
   next concrete implementation step, contingent on decisions 1-3 above.
8. **Whether the pretrained-weight license (§8) is worth pursuing
   further** (e.g. contacting the authors directly) if the Figshare
   link remains inaccessible, or whether to treat SSSD-ECG as blocked
   and move to the DiffuSETS fallback (§11).

## 14. Testing / scope verification

Full suite re-run this session under the project's Anaconda interpreter
(D002): **103/103 passing**, no failures. No file under `schemas/`,
`generation/`, `integration/`, `validation/`, or `configs/` was
modified this session — confirmed by this session's own edit log
(only `docs/` files were created). `outputs/m5/100k_patients/` was not
read or modified. No new dependency was installed (NeuroKit2 remains a
documented future dependency, not installed this session).

## 15. Recommended next steps

1. **A human manually confirms the SSSD-ECG pretrained-weight license**
   via an authenticated Figshare session (unchanged blocker, §8).
2. **If and only if** the license permits use: load the checkpoint
   (read-only, no training) and inspect `embedding.weight.shape` to
   settle `docs/M7_0_CONDITIONING_AUDIT.md`'s remaining open item
   directly, and run `print_size(net)` to convert §7's estimate into a
   real measurement.
3. Decide the human-checklist items in §13 before any code is written.
4. Only then does `docs/M7_ECG_IMPLEMENTATION_PLAN.md`'s M7-1 become
   actionable.

---

**M7-0 STATUS: HUMAN CHECKPOINT.**

Research: COMPLETE (within this spike's narrow scope — S4-kernel-level
parameter precision and the label-array producing script remain
explicitly out of reach without the checkpoint itself).

Implementation: NOT STARTED.

Schema changed: NO. Generation changed: NO. Validation changed: NO.
Configs changed: NO. 100K dataset modified: NO.

Tests: 103/103 passing.

SSSD-ECG: UNRESOLVED (technically promising, license-blocked).

44-vs-71: RESOLVED WITH HIGH CONFIDENCE (not definitively proven without
the checkpoint).

Weight license: UNKNOWN.

Parameter count: PARTIALLY MEASURED (~26.5M verified from source code;
remainder ESTIMATED at 50M-150M total, pending the S4-kernel component).

8GB: SUFFICIENT (derived from partial parameter count, not independently
benchmarked).

36GB: SUFFICIENT, with more throughput headroom than 8GB; not required
for correctness at any stage.

Leakage risk: HUMAN DECISION (guardrails proposed, not yet a project
policy).

Human decisions required: see §13 (8 items).

Recommended next milestone: **M7-0 continuation (manual license check +
checkpoint-based confirmation) — not yet M7-1.**
