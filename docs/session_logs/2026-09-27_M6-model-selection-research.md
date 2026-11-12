# Session Log — 2026-09-27 — M6 Pre-Work: Generative Model Selection Research

**Milestone hit:** none — research only, no code/schema/decision change.
Feeds the still-not-started M6 candidates (ECG architecture decision,
Stage 9 model selection) per `docs/PROJECT_STATE.md`'s M6 entry.

## Objective

Gather evidence for the eventual generative-model-selection checkpoint
(CLAUDE.md §11/§28: "Model selection" is an explicit human checkpoint,
not an autonomous decision). Four parallel research agents were run;
this log records what they found so the checkpoint, when raised, has
sourced evidence instead of re-deriving it.

## Track 1 — Hardware/VRAM/storage feasibility

No paper disclosed a measured peak VRAM figure. Real batch-size
evidence found: SSSD-ECG batch 4 (diffusion), ME-GAN batch 16 on an
RTX 2080 Ti/11GB (GAN). Engineering inference from that evidence: an
RTX 4060 (8GB) is not blocked for fine-tuning (batch ~4-32 depending on
architecture), only slower than a 36GB card. Inference is not
VRAM-constrained at all (1-3GB).

Storage arithmetic (waveform, additive to existing metadata-only
figures): float32 1000×12×4B = 48,000 B/patient → **4.8GB at 100K,
48GB at 1M**; float16 half that (2.4GB / 24GB). Combined with M5's
measured metadata footprint (355MB/100K, ~3.55GB/1M): ~5.15GB
(100K)/~51.5GB (1M) float32, ~2.75GB/~27.5GB float16.

**Feasibility grid conclusion: no RED cell found at any scale up to
1M on either an 8GB or 36GB local GPU.** AWS is not required by this
analysis at any stage — only useful later as a wall-clock optimization
if local GPU time becomes the bottleneck, consistent with CLAUDE.md
§14's "AWS should NOT be introduced simply because it is available."

Compression-ratio research was cut short by rate-limiting — marked
"TO BE ESTABLISHED DURING PILOT," not guessed.

## Track 2 — ECG generative model landscape (GAN/VAE/diffusion)

Strongest verified lead: **SSSD-ECG** (`AI4HealthUOL/SSSD-ECG`, arXiv
2301.08227, Computers in Biology and Medicine). MIT license (confirmed
on repo), pretrained weights on Figshare (DOI 10.6084/m9.figshare.2189287),
conditions on **70+ PTB-XL SCP diagnostic statements** — directly maps
onto this project's existing `ecg.superclasses` field. Open questions
not verified this pass: exact sampling rate/signal length (must confirm
it matches or resamples to this project's 100Hz/1000-sample convention)
and real VRAM/compute cost.

Other candidates found but not deep-verified: DiffuSETS (diffusion,
conditions on clinical text + patient metadata — closer to this
project's demographic-conditioning interest, but license/weights
unconfirmed), FlowECG (flow-matching, framed as more efficient than
standard diffusion — relevant given the 8GB VRAM target), cNVAE-ECG
and a FEM-simulator-trained VAE (trains on simulated ground truth,
sidesteps real-patient-data licensing entirely — a real architectural
alternative worth a future look).

Categories 4 (transformer/autoregressive), 6 (morphology/template,
e.g. ECGSYN), and 7 (signal-processing hybrids) were **not reached** —
blocked by session-level rate-limiting, not researched to "no results
found." Do not treat as ruled out.

## Track 3 — CardioSynth/CardioSync identification audit

CLAUDE.md §11 names "CardioSynth/CardioSync" as the current placeholder
candidate, explicitly flagged as **not a final architectural decision**.
This audit confirms it should not become one on its current form:

- One real GitHub repo matches "CardioSynth" (`Abhishekkumarsingh12/cardiosynth-Ai`):
  0 stars/forks, 3 commits, self-described demo scaffold, **single-lead**
  `(batch, 187, 1)` MIT-BIH format — not 12-lead, not PTB-XL, not this
  project's `[1000, 12]` shape. No license file, no shipped pretrained
  weights, no age/sex/diagnosis conditioning.
- No paper titled "CardioSynth" exists in the ECG-generation literature.
- "CardioSync" has no ECG-generation project under that name at all —
  every real hit (a consumer health app, an ECG *display* tool, a
  Medtronic pacing algorithm) is unrelated to signal synthesis.

**Conclusion: CardioSynth/CardioSync is an unresolved placeholder, not
a usable candidate as-is.** SSSD-ECG (Track 2) is currently the only
verified, openly-licensed, weight-available, conditioning-compatible
alternative found.

## Track 4 — Broader model/dataset licensing audit

**Failed**: terminated early by a session-level API rate limit before
producing results. Not run to completion — needs a retry, not a
re-read of this log.

## Track 5 — ECG synthetic-quality validation methods (6 layers, A-F)

Research for the eventual Stage 6/6.5 (cross-modal/generative-output
validation) layer, once a model is selected and produces waveforms.

- **A. Signal-level**: established SQI methods exist (R-peak/template
  SQI, entropy-based SQIs, wavelet baseline-wander suppression).
  **Inter-lead correlation is a real, citable check** — a synthetic-ECG
  paper reports known real patterns (V1-V2/V4-V5 ~0.8 correlation,
  negative I/III correlation) a generator must reproduce
  ([arXiv:2510.05492](https://arxiv.org/pdf/2510.05492)). Einthoven's-
  triangle algebraic consistency (Lead III derivable from I/II) is
  another real check. No universal numeric threshold found — needs
  empirical calibration.
- **B. Morphology**: **NeuroKit2** (`neuropsychology/NeuroKit`, MIT-
  family license, PyPI) is a real, off-the-shelf, importable toolbox —
  QRS/P/T delineation, multiple R-peak algorithms, QT estimation. Ready
  to reuse directly, no ECG-specific research needed to adopt it.
- **C. Distribution**: no standardized "Fréchet ECG Distance" brand
  exists, but a Feature-based Fréchet Distance (FFD) concept is used in
  2024-2025 papers as an FID-analogue (mean/covariance over a feature
  space) — **PARTIALLY VERIFIED**, re-check the primary paper before
  citing a specific formula.
- **D. Clinical-label**: established practice — multiple papers use
  PTB-XL-trained classifiers to test synthetic-ECG utility. Real
  cautionary finding directly relevant to a "pretty ECG" failure mode:
  classifiers trained on synthetic-only data can score well on
  synthetic data but poorly train-synthetic/test-real — self-consistency
  metrics alone do not imply clinical fidelity.
- **E. Diversity**: nearest-neighbor distance, Number-of-Modes/Mode
  Collapse Divergence, and the general-purpose Vendi Score
  ([arXiv:2210.02410](https://arxiv.org/pdf/2210.02410)) are real,
  established methods. No ECG-specific pass/fail threshold found.
- **F. Memorization/privacy**: strongest, most directly reusable
  finding of this track — membership-inference attacks via a 1-NN
  distance classifier are documented specifically for **synthetic
  health data** ("Membership Inference Attacks Against Synthetic Health
  Data," *J. Biomedical Informatics* 2021,
  [doi:10.1016/j.jbi.2021.103977](https://dl.acm.org/doi/10.1016/j.jbi.2021.103977))
  — directly applicable given PTB-XL is real patient data underlying
  this project's ECG source.

No numeric acceptance thresholds exist anywhere in the literature for
A, C, or E — marked "TO BE ESTABLISHED DURING PILOT," not invented.

## Net effect on M6

No milestone status changed. No schema/code change. This is evidence
for the Stage 9/M6 "model selection" human checkpoint (CLAUDE.md §28),
not a selection itself — per §11, "this is NOT a final architectural
decision" until a human makes it. Recommended next step if/when M6 is
authorized: verify SSSD-ECG's exact output sampling rate and signal
length against this project's 100Hz/1000-sample convention, rerun
Track 4's licensing audit, and reuse NeuroKit2 + the health-data MIA
method directly (Track 5) rather than building custom equivalents.
