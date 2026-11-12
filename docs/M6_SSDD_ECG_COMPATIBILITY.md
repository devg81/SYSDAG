# M6 — SSSD-ECG Compatibility Audit

Primary-source technical audit of `AI4HealthUOL/SSSD-ECG` (repo commit
tree `324f908`, branch `main`) against this project's existing ECG
convention. Research only — nothing in this project's `schemas/`,
`ingestion/`, `generation/`, `integration/`, or `validation/` has been
changed. No model code was executed or downloaded.

**Overall: PARTIALLY CONFIRMED compatible.** Sample count and sampling
rate match directly. Lead order and — more materially — the
conditioning label set do not match without extra work.

## 1-2. Sampling rate and waveform length: DIRECT MATCH

- Sampling rate: **100 Hz**. Source: `src/sssd/config/config_SSSD_ECG.json`
  → `trainset_config.sampling_rate: 100`; corroborated by
  `src/ptb_xl/ecg_data_preprocessing.ipynb` (`target_fs = 100`) and the
  paper's stated "ECGs were sampled at a rate of 100 Hz."
- Waveform length: **1000 samples** (10 seconds at 100Hz). Source: same
  config, `trainset_config.segment_length: 1000`; also
  `wavenet_config.s4_lmax: 1000`.
- This project's own convention (`ingestion/ptbxl_source.py:88-89`):
  `sampling_hz: 100`, `signal_shape: [1000, 12]`. **Both numbers match
  exactly** — no resampling, padding, or truncation would be needed.

## 3-4. Leads and tensor shape: PARTIAL — only 8 of 12 leads are diffusion-sampled

SSSD-ECG's diffusion model has **8 input/output channels**, not 12
(`wavenet_config.in_channels/out_channels: 8`). It directly samples
leads **I, V1, V2, V3, V4, V5, V6, aVF** (index order `[0,2,3,4,5,6,7,11]`
against its own `channel_stoi_default` mapping). The remaining 4 leads
— **II, III, aVR, aVL** — are computed *after* sampling via fixed
linear (Einthoven/Goldberger) relations in `inference.py::generate_four_leads()`:

```
leadII  = 0.5*leadI + leadaVF
leadIII = -0.5*leadI + leadaVF
leadaVR = -0.75*leadI - 0.5*leadaVF
leadaVL = 0.75*leadI - 0.5*leadaVF
```

Model I/O tensor shape: **(batch, 8, 1000)**; post-processed output:
**(batch, 12, 1000)** — channels-first. This project's declared shape
is `[1000, 12]` — samples-first. **A transpose is required regardless
of lead order.**

**Lead order SSSD-ECG produces:** `I, II, V1, V2, V3, V4, V5, V6, III,
aVR, aVL, aVF` (from `src/ptb_xl/clinical_ts/ecg_utils.py`'s
`channel_stoi_default`) — **not** the standard clinical order (I, II,
III, aVR, aVL, aVF, V1-V6).

**This project's own lead-order convention is presently UNDEFINED** —
ECG is metadata-only today (`signal_available` is always `false`;
`ingestion/ptbxl_source.py` never loads a raw waveform array). The one
piece of existing project code that *does* load raw PTB-XL signals —
`syngen/SynGen/SynGen/gan_pytorch.py:117`, via `wfdb.rdrecord(filepath)`
— reads PTB-XL's own WFDB header order, which is PTB-XL's native
standard clinical order (I, II, III, aVR, aVL, aVF, V1-V6), **not**
SSSD-ECG's order. This is evidence about the most likely default, not
a formal project decision — no Stage 4 waveform work has started, so
there is no established convention to contradict yet.

**Net: if this project's waveform pipeline uses the standard clinical
order (the likely default per the one existing precedent), a fixed
12-element index permutation is needed in addition to the transpose.
Neither is a resampling/signal-processing operation — both are
lossless re-indexing.**

## 5. Direct 12-lead generation: NO

Confirmed — only 8 of 12 leads are diffusion-sampled; 4 are derived
post-hoc via the linear relations above (item 3-4).

## 6. Sampling frequency used: CONFIRMED 100 Hz

The repo's preprocessing code is *capable* of either 100Hz or 500Hz
(`resample_data()`, parameterized `target_fs`, using the `resampy`
library) since PTB-XL ships both natively, but the shipped/released
config, notebook default, and (per the paper) the released trained
checkpoint all use 100 Hz.

## 7. Direct compatibility verdict: **REQUIRES CONVERSION** (structural, not signal-processing)

- Sample count: DIRECT match (1000 = 1000).
- Sampling rate: DIRECT match (100Hz = 100Hz).
- Tensor axis order: requires a transpose, (8 or 12, 1000) ↔ (1000, 8 or 12).
- Lead order: requires a fixed re-indexing permutation (12-element),
  assuming this project eventually adopts standard clinical order.
- **No resampling, interpolation, padding, or truncation is required** —
  every needed transformation is a lossless reshape/reindex, not a
  signal-processing operation. Item 9 below is therefore moot.

## 8-9. Conversion transform and distortion risk

**Transform required:** (1) transpose channels-first ↔ samples-first;
(2) reorder the 12-channel axis from SSSD-ECG's
`[I,II,V1-6,III,aVR,aVL,aVF]` to this project's eventual canonical
order via a fixed index map (once that order is formally decided —
currently undefined, see item 3-4).

**Distortion risk: NONE identified.** Both operations are lossless —
a transpose changes no values, and a lead re-indexing is a relabeling,
not a recomputation. This differs from the *generation-time* Einthoven/
Goldberger derivation (item 3-4), which is a real mathematical
approximation baked into SSSD-ECG's own pipeline before this project
would ever touch the output — not something this project's conversion
step introduces or could avoid by choosing a different conversion.

## 10-12. Conditioning labels: PARTIAL, leaning INCOMPATIBLE-AS-IS

**SSSD-ECG's actual conditioning label set:** PTB-XL's raw
**`label_diag`** column — **71-dimensional multi-hot diagnostic SCP
statement codes** — confirmed directly from
`ecg_data_preprocessing.ipynb` (explicit `ptb_xl_label = "label_diag"`,
selected over the same utility's also-available `label_diag_superclass`
column) and from `wavenet_config.label_embed_classes: 71` in the
shipped config. This is the code-level, executable ground truth.

*Caveat flagged by the research agent:* the paper's abstract/body (read
via an AI-summarized HTML render, not raw text) describes "71 ECG
statements comprising diagnostic, form-related, and rhythm statements
organized hierarchically" — in tension with the code's explicit
diagnostic-only column selection. The code is the authoritative,
executable source; this wording discrepancy is unresolved and would
need a raw (non-summarized) read of the paper PDF to settle.

**This project's available conditioning data:** exactly **5 PTB-XL
diagnostic SUPERCLASSES** (NORM, MI, STTC, CD, HYP) via `syngen`'s
`build_label_map()`, reused in `ingestion/ptbxl_source.py`. Raw SCP
diagnostic codes are **not currently captured or stored** anywhere in
this project's schema (`ECGRecord.superclasses: list[str]` — superclass
strings only, `schemas/patient_schema.py:173`).

**Compatibility verdict: PARTIAL, leaning INCOMPATIBLE-AS-IS.** The
mapping from raw SCP code → superclass (which `build_label_map()`
already performs) is one-directional and lossy — many raw codes
collapse onto one superclass. **You cannot reconstruct SSSD-ECG's
required 71-dim label vector from only a 5-class superclass label.**
Feeding the pretrained checkpoint's 71-class label-embedding layer a
sparse/hacked 5-populated-of-71 vector would be out-of-distribution
for that layer, not a valid use of the pretrained conditioning.

**To use the released pretrained checkpoint as intended, this project
would need to additionally capture raw PTB-XL `scp_codes` per record**
(PTB-XL provides this in its own metadata CSV — not currently ingested)
— a metadata *addition*, not a schema *redesign*, but real new work
beyond what M1-M5 built. The alternative — retraining/fine-tuning
SSSD-ECG's label-embedding layer on this project's own 5-class scheme —
is model surgery, not "pretrained inference," and would reopen the
"minimal fine-tuning only" ceiling this project's CLAUDE.md §12 sets.

## 13-14. Pretrained checkpoint availability and usability

- **Correct DOI** (the earlier research log's DOI was wrong — traced
  and corrected by this audit): model weights DOI
  `10.6084/m9.figshare.21922875` (unlisted/private Figshare share link
  `figshare.com/s/81834b24a4711c2a5c55`); the separate dataset DOI
  (SSSD-ECG's *own generated synthetic PTB-XL copy*, not training
  input) is `10.6084/m9.figshare.21922947`. The prior session's log
  entry citing `2189287`/`2192294` is **superseded — those numbers
  actually resolve to an unrelated 2015 chemistry paper**, confirmed
  by the licensing-audit agent via a direct Figshare API query. This
  document is the corrected source going forward.
- **Format:** standard PyTorch checkpoint dict (`torch.save({'model_state_dict':
  ..., 'optimizer_state_dict': ...}, ...)`), filename pattern
  `<iteration>.pkl` (e.g. `100000.pkl`) — a `.pkl` extension on an
  ordinary PyTorch state-dict save, not a raw pickle of arbitrary
  Python objects.
- **Inference without training: YES, supported by the code.**
  `inference.py` is a standalone script — loads a checkpoint
  (`ckpt_iter='max'` auto-selects the highest iteration), runs
  `generate()`/`sampling_label()` directly. No training step is
  required if a checkpoint file is present. This workflow is only
  documented by reading `inference.py` itself — the top-level README
  is citation/badges only, no prose walkthrough.

## 15. Inference/scale estimates for 1K / 100K / 1M waveforms

**No throughput, GPU model, or VRAM figure is stated anywhere in the
primary sources** (README, config, code comments, or the paper text as
summarized) — every number below is this audit's own **ESTIMATE**,
not a citation.

Measured/stated facts available to ground the estimate: 200 sequential
diffusion reverse steps (`T=200`, both config and paper); training
`batch_size=8` in the shipped config but the actual `train.py`
DataLoader hardcodes `batch_size=6` (an unresolved minor inconsistency
between shipped config and shipped script, noted not resolved);
`inference.py`'s own default batches inference in chunks of 400 labels;
the authors report generating one full synthetic-PTB-XL-sized dataset
(~21,837 records) but do not report the time or hardware that took.

**ESTIMATE (architecture-based reasoning, not benchmarked):** each
waveform needs 200 sequential forward passes of a moderate WaveNet/S4
hybrid (36 residual layers, 256 channels) over a short (8×1000) tensor.
On a single modern GPU, this class of model plausibly processes a
batch of several hundred sequences through all 200 steps in the tens-
of-seconds range.

| Scale | Estimated wall-clock (single modern GPU, order-of-magnitude) |
|---|---|
| 1,000 | under a few minutes |
| 100,000 | low single-digit hours |
| 1,000,000 | roughly a day |

Model parameter count / VRAM was **not disclosed** in any fetched
source (the code calls `print_size(net)` but that runtime output isn't
captured in a static file); given the channel/layer counts this is
very unlikely to be a multi-billion-parameter model, so single-GPU
inference — plausibly even on the 8GB RTX 4060 — looks feasible, but
this is inference from architecture size, not a measured figure. **To
resolve for real: run `print_size(net)` against the loaded model, or
benchmark `inference.py` directly on target hardware** — no shortcut
exists in the published materials.

## 16. Explicit UNKNOWNs and what would resolve each

| # | Unknown | What would resolve it |
|---|---|---|
| 1 | This project's own eventual lead-order convention | A formal Stage-4 decision — not yet made (no waveform pipeline exists) |
| 2 | Exact SSSD-ECG parameter count / VRAM footprint | Run `print_size(net)` in `src/sssd/utils/util.py`, or inspect checkpoint file size once accessible |
| 3 | Real GPU/wall-clock generation benchmarks | Actually run `inference.py` on target hardware (RTX 4060 or the 36GB alternative) |
| 4 | Paper-vs-code "71 diagnostic" vs. "71 diagnostic+form+rhythm" wording discrepancy | Direct raw read of the PDF/HTML paper text (not an AI-summarized fetch), specifically its labeling section |
| 5 | Exact Figshare-hosted checkpoint file layout/sizes, and whether a label-index↔SCP-code mapping file ships with it | A human opening the private share link (`figshare.com/s/81834b24a4711c2a5c55`) in an authenticated browser — automated fetch returned HTTP 403 twice |
| 6 | `train.py` batch_size=6 vs. config's batch_size=8 discrepancy | Not investigated further — low priority (affects training reproduction only, not inference) |

## Compatibility summary (for the decision brief)

| Dimension | Verdict |
|---|---|
| Sample count (1000) | DIRECT MATCH |
| Sampling rate (100Hz) | DIRECT MATCH |
| Tensor axis order | REQUIRES CONVERSION (lossless transpose) |
| Lead order | REQUIRES CONVERSION (lossless permutation) — target order itself still undefined project-side |
| 12-lead direct generation | NO — 8 sampled + 4 algebraically derived by SSSD-ECG itself, before this project ever sees the output |
| Conditioning labels | PARTIAL, leaning INCOMPATIBLE-AS-IS — pretrained checkpoint expects 71-dim raw SCP codes, project has only 5-class superclasses |
| Pretrained-weight inference-only usability | CONFIRMED supported by the code, PENDING license confirmation (see `M6_MODEL_SELECTION_DECISION_BRIEF.md` §Licensing) |
