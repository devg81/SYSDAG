# M6 — Model Selection Decision Brief

**This document does not select a model. Per CLAUDE.md §11/§28 and this
task's explicit instruction, model selection is a human checkpoint.**
This assembles the evidence gathered across the two research passes
(`docs/session_logs/2026-09-27_M6-model-selection-research.md` and
`docs/session_logs/2026-09-27_M6-ecg-compatibility-audit.md`, plus
`docs/M6_SSDD_ECG_COMPATIBILITY.md`) into the specific answers the
human decision-maker asked for.

---

## Task 3 — ECG representation options (not ranked)

Context grounding this comparison: today, ECG is metadata-only
(`ECGRecord.signal_available` is always `false`; no waveform array is
generated, stored, or validated anywhere in this project).
`schemas/patient_schema.py` already declares the target shape as
`signal_shape: [1000, 12]` (samples-first) at 100Hz — this is a
existing schema field, not a new proposal. SSSD-ECG's own native
output (per `M6_SSDD_ECG_COMPATIBILITY.md`) is `(12, 1000)`
channels-first, non-standard lead order `[I,II,V1-6,III,aVR,aVL,aVF]`,
with 8 of 12 leads diffusion-sampled and 4 algebraically derived by
SSSD-ECG itself before this project would ever see the output.

### Option A — Generate and store directly in the model's native representation

Keep SSSD-ECG's raw output as-is: `(12, 1000)`, channels-first,
non-standard lead order, no post-processing.

- **Technical advantages:** Zero conversion code. Fastest to get a
  first waveform through the pipeline. No risk of introducing a bug in
  a transpose/permutation step.
- **Disadvantages:** Breaks the schema's existing `signal_shape:
  [1000, 12]` contract immediately — either the schema is silently
  wrong for every future waveform, or every consumer of `ECGRecord`
  must special-case "is this SSSD-ECG's shape or the declared one?"
  Locks the project's *stored* representation to one specific model's
  implementation detail — a future second model (or SSSD-ECG's own
  next version) may use a different native shape, forcing a rewrite of
  every stored record, not just the generator.
- **Information loss:** None at generation time — nothing is
  discarded. But standard clinical lead order is never established,
  so every downstream consumer (validation, visualization, a future
  independent classifier trained on real PTB-XL clinical-order data)
  must itself know and undo SSSD-ECG's specific ordering.
- **Validation implications:** `M6_ECG_VALIDATION_PLAN.md`'s lead-order
  check (#3) and any check that compares against real PTB-XL reference
  distributions (#10) must be written against SSSD-ECG's order, not
  clinical order — validation code becomes coupled to this one model.
- **Storage implications:** Identical byte volume to any other option
  (same 1000×12 float values) — shape/order is metadata, not size.
- **Reproducibility implications:** None distinct from other options —
  reproducibility depends on seeding, not storage shape.
- **Compatibility with PTB-XL:** Real PTB-XL raw files (via `wfdb`, the
  only precedent in this codebase — `syngen/SynGen/SynGen/gan_pytorch.py`)
  are in standard clinical order. Storing SSSD-ECG's non-standard order
  means synthetic and real-reference waveforms are never directly
  comparable without a downstream permutation anyway — this option just
  moves that permutation from "generation time" to "every time anyone
  compares to real PTB-XL," including every validation-plan check.
- **Effect on downstream ML/model training:** Any future model or
  classifier trained/evaluated using standard-order references (e.g.
  the PTB-XL benchmark classifiers referenced in the validation plan's
  #10) would need its own adapter for this project's stored order.

### Option B — Generate natively, convert to canonical `[1000, 12]` clinical order afterward

Run SSSD-ECG as designed, then apply the transpose + fixed lead
permutation identified in `M6_SSDD_ECG_COMPATIBILITY.md` §8-9 before
storing, so every stored `ECGRecord` matches the schema's existing
declared shape and (once decided) a standard clinical lead order.

- **Technical advantages:** Preserves the schema's existing contract
  (`signal_shape: [1000, 12]`) without a schema change. Every
  downstream consumer — validation, visualization, comparison to real
  PTB-XL — can assume one consistent, standard representation
  regardless of which generative model produced a given waveform.
  Matches the one existing precedent in this codebase (`wfdb.rdrecord`
  in `syngen/SynGen/SynGen/gan_pytorch.py` reads clinical order).
- **Disadvantages:** Requires writing and testing a conversion step
  (transpose + 12-element permutation) — small, but it is new code
  that doesn't exist today, and per `M6_ECG_VALIDATION_PLAN.md` #1/#3
  that conversion step itself becomes something the hard-failure shape
  check must run *after*, not before.
- **Information loss:** None — both operations (transpose, lead
  reindex) are confirmed lossless (`M6_SSDD_ECG_COMPATIBILITY.md` §8-9).
  No values are recomputed or discarded; only axis order and channel
  order change.
- **Validation implications:** Validation plan can be written once,
  against one canonical representation, reusable regardless of which
  model generated a given waveform (a real advantage if a second model
  is ever added later, e.g. after CardioSynth/CardioSync-style
  candidates mature, or a future SSSD-ECG version changes its own
  native shape).
- **Storage implications:** Identical to Option A.
- **Reproducibility implications:** None distinct — but the conversion
  step itself must be deterministic (a fixed index map, not a learned
  or randomized step) to preserve this project's existing
  seed-reproducibility guarantee end-to-end.
- **Compatibility with PTB-XL:** Direct — synthetic and real waveforms
  end up in the same representation, so any comparison (validation
  plan #10, #12, #13) doesn't need a per-source special case.
- **Effect on downstream ML/model training:** A future classifier
  trained on real PTB-XL (standard order) can be applied to generated
  waveforms without an adapter.

### Option C — Change the project's canonical ECG representation to match the selected model

Redefine `ECGRecord.signal_shape`'s intended meaning (or the array
convention it implies) to SSSD-ECG's native `(12, 1000)`
channels-first, non-standard-order layout, instead of converting to
match it.

- **Technical advantages:** Same as Option A (no conversion code) but
  formalized as the project's actual documented convention rather than
  an ad hoc exception — avoids Option A's "silently wrong schema"
  problem by making the schema *correctly* describe what's stored.
- **Disadvantages:** This is a genuine schema/convention change (the
  kind CLAUDE.md §8 says "do not casually redesign," and §25 says any
  such decision belongs in `docs/DECISIONS.md`). It retroactively
  couples the project's canonical representation to one specific
  external model's implementation detail — the same lock-in risk as
  Option A, except now formalized into the schema itself rather than
  left as an inconsistency. If a differently-shaped model is chosen
  instead of SSSD-ECG (or a future SSSD-ECG version changes shape),
  this option requires a second schema change, not just a new
  generator.
- **Information loss:** None at generation time — same as Option A.
  Same downstream cost: every comparison to real PTB-XL (which is
  naturally in clinical order via `wfdb`) needs its own conversion at
  comparison time instead of once at generation time.
- **Validation implications:** Same coupling problem as Option A —
  validation code written against this model's specific order, not a
  model-independent canonical order.
- **Storage implications:** Identical byte volume to A/B.
- **Reproducibility implications:** None distinct.
- **Compatibility with PTB-XL:** Same mismatch as Option A — real
  PTB-XL reference data (via `wfdb`) is naturally clinical-order;
  formalizing a different canonical order doesn't remove that mismatch,
  it just makes the mismatch the documented, intended state.
- **Effect on downstream ML/model training:** Same as Option A.

**Not ranked, per instruction.** The one fact all three options share:
none requires resampling or interpolation (§8-9 of the compatibility
audit already established every needed transform is lossless), so the
*cost* difference between them is entirely about where representation-
consistency work happens (once at generation time, vs. repeatedly at
every future comparison/validation/training use) and how much of that
cost is made an explicit, documented decision (Option C) versus an
implicit inconsistency (Option A).

---

## Licensing audit summary (Task 2 — see full detail in the session log)

| Item | License/terms | Status |
|---|---|---|
| A. SSSD-ECG code | MIT (repo root `LICENCE` file, GitHub API confirms `spdx_id: MIT`) | CONFIRMED |
| B. SSSD-ECG pretrained weights | Unresolved — hosted at an unlisted/private Figshare share link, HTTP 403 on every automated fetch attempt | **UNKNOWN — needs a human to open the link in an authenticated browser** |
| C. Training data used by SSSD-ECG | PTB-XL exclusively (no separate/additional dataset found) | CONFIRMED — same as D |
| D. PTB-XL license | **CC BY 4.0**, Open Access, no credentialing/DUA required (physionet.org/content/ptb-xl) | CONFIRMED |
| E. Figshare platform terms vs. item content license | Could not determine whether they diverge for these specific items — both item pages 403'd | **UNKNOWN** |
| F. NeuroKit2 license | **MIT** (plain, not a variant — repo LICENSE file confirmed) | CONFIRMED |
| G. SSSD-ECG's own dependencies | No requirements.txt/setup.py/pyproject.toml exists in the repo at all; deps identified from imports (torch, numpy, scipy, pytorch_lightning, einops, opt_einsum, tqdm, pyyaml) | Dependency **list** CONFIRMED; each dependency's own license stated from general knowledge, **not independently re-verified this pass** |

**Also corrected in this pass:** the earlier research log's Figshare
DOIs (`2189287`/`2192294`) were wrong — they resolve to an unrelated
2015 chemistry paper. Correct DOIs: weights `10.6084/m9.figshare.21922875`,
SSSD-ECG's own generated synthetic dataset `10.6084/m9.figshare.21922947`.
`M6_SSDD_ECG_COMPATIBILITY.md` uses the corrected DOIs; treat the
original 2026-09-27 research-track log's DOIs as superseded.

**Overall licensing status: PARTIAL.** The one unresolved item (weight
license, B/E) is exactly the item that matters most for a "can we
actually use the pretrained checkpoint" decision — it is not a minor
gap.

---

## Final Report

**1. SSSD-ECG compatibility: PARTIALLY CONFIRMED.**
Sample count and sampling rate match directly; tensor axis order and
lead order need a (lossless) conversion; conditioning labels do not
match without new metadata work; pretrained-weight license is
unresolved.

**2. 100 Hz × 1000 × 12 compatibility: REQUIRES CONVERSION.**
Rate and length are direct matches. Axis order and lead order require
a lossless transpose + fixed permutation (Options A/B/C above address
*where* that conversion happens, not whether it's needed for a
clinical-order comparison). No resampling/interpolation is needed.

**3. Conditioning-label compatibility: PARTIAL, leaning INCOMPATIBLE-AS-IS.**
SSSD-ECG's released checkpoint expects a 71-dim raw PTB-XL SCP
diagnostic-code multi-hot vector (`label_diag`). This project has only
5-class superclass labels. The superclass mapping is one-directional
and lossy — cannot reconstruct the 71-dim vector from it. Using the
pretrained checkpoint as intended would require this project to
additionally capture raw `scp_codes` per record (new metadata work,
not a redesign) — or accept a model-surgery-level retrain of the
label-embedding layer, which is a materially different (and more
expensive) undertaking than "pretrained inference."

**4. Pretrained-weight usability: PARTIAL.**
The code confirms inference-only usage is fully supported (no training
required if a checkpoint is present) — CONFIRMED at the code level.
Whether it's *legally* usable is UNKNOWN — the weight-hosting Figshare
item's license could not be fetched (HTTP 403, twice) and needs a
human to check via an authenticated browser session.

**5. Licensing audit: PARTIAL.**
Unresolved items: (a) SSSD-ECG pretrained-weight Figshare item license/
terms (B), (b) whether Figshare platform terms diverge from item
content license for these specific items (E), (c) individual license
verification for SSSD-ECG's 8 identified dependencies (G) — currently
stated from general knowledge, not re-fetched from each project's own
LICENSE file.

**6. 8GB GPU (RTX 4060): PRACTICAL for inference, per architecture-
based estimate — NOT independently measured.**
No source states a VRAM figure for SSSD-ECG. Evidence used: 8-channel,
36-residual-layer WaveNet/S4 hybrid over a short (8×1000) tensor is not
a large model by parameter-count conventions in this space; the
project's earlier hardware-feasibility research (prior session log)
independently concluded GAN/diffusion inference in this signal-size
regime needs only 1-3GB VRAM. Treat "practical" as an estimate pending
an actual `print_size(net)` run or a real benchmark.

**7. 36GB GPU: PRACTICAL, more clearly so than the 8GB case.**
Same reasoning as #6, with more headroom — removes any batch-size
ceiling the 8GB card might have for larger inference batches. No
distinct new evidence beyond the general hardware-feasibility research
already on record.

**8. 100K generation: ESTIMATED runtime "low single-digit hours";
storage 4.8GB (float32) / 2.4GB (float16), additive to the existing
355MB metadata footprint (per M5's actual measured figure) → combined
~5.15GB (float32) / ~2.75GB (float16).** Runtime figure is this audit's
architecture-based estimate, not a citation — no source states SSSD-ECG
throughput.

**9. 1M generation: ESTIMATED runtime "roughly a day" (order of
magnitude); storage 48GB (float32) / 24GB (float16), additive to
~3.55GB metadata → combined ~51.5GB (float32) / ~27.5GB (float16).**
Same estimate caveat as #8.

**10. AWS: NOT REQUIRED, per current evidence.**
Nothing in this audit or the prior hardware-feasibility research shows
a RED (impractical) cell for local hardware at any scale up to 1M
waveforms, on either the 8GB or 36GB option. AWS remains, at most, a
future wall-clock optimization if local GPU time becomes the
bottleneck once real (not estimated) throughput is measured —
consistent with CLAUDE.md §14.

**11. Human decisions required (genuinely require your input — nothing
below has been decided or acted on):**

- **Model selection itself** — SSSD-ECG vs. any other candidate vs.
  deferring Stage 4 further. This brief provides evidence, not a
  choice.
- **Whether the conditioning-label gap (item 3) is acceptable** — i.e.,
  whether to (a) add raw SCP-code capture to this project's metadata
  to use SSSD-ECG's pretrained checkpoint as intended, (b) accept
  degraded/approximate conditioning from only 5 superclasses, or (c)
  treat this as a reason to look further at alternatives (DiffuSETS,
  the FEM-simulator VAE, etc. — from the prior research track).
- **Which representation option (A/B/C, Task 3) to adopt**, if/when a
  model is selected — this brief deliberately does not rank them.
- **Whether to wait for the pretrained-weight license (item 5/B) to be
  manually confirmed before any further SSSD-ECG-specific work**, given
  it is currently the single unresolved item most likely to block or
  permit actual reuse.
- **Whether to authorize the small amount of manual-verification work
  this audit could not complete itself** (opening the private Figshare
  share link in an authenticated session; running `print_size(net)`
  against a loaded — not trained — checkpoint purely to read off a
  parameter count) — both are verification steps, not implementation,
  but this audit's own scope ("no code execution, no downloads")
  stopped short of them.

**12. Recommended next milestone (described, not begun):**
If M6 is authorized to proceed toward SSSD-ECG specifically, the
logical next step would be a narrow verification spike: confirm the
pretrained-weight license by hand, run `print_size(net)` for a real
parameter count, and decide the conditioning-label question (item 3)
before writing any conversion or validation code. If M6 instead
broadens to compare SSSD-ECG against the other candidates surfaced in
the prior research (DiffuSETS, FlowECG, the FEM-simulator VAE), the
next step would be a matching compatibility audit for whichever
alternative the human decision-maker wants evaluated next. Neither has
been started.
