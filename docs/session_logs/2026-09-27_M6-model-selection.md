# Session Log — 2026-09-27 — M6: ECG Model Selection + Architecture Decision Phase

**No milestone marked COMPLETE. No code in `schemas/`, `generation/`,
`integration/`, `validation/`, or `configs/` changed. No waveform
generated. No dataset regenerated. No model selected.** This continues
directly from the two prior M6 research sessions
(`docs/session_logs/2026-09-27_M6-model-selection-research.md`,
`docs/session_logs/2026-09-27_M6-ecg-compatibility-audit.md`) and
assembles their findings plus this session's new evidence into
`docs/M6_ECG_MODEL_SELECTION.md` and `docs/M7_ECG_IMPLEMENTATION_PLAN.md`.

## Objective

Complete the M6 decision phase per the user's explicit 10-phase
instruction: verify SSSD-ECG narrowly, investigate the 71-label
conditioning gap against this project's *own* local data, audit a small
set of realistic alternatives, consolidate hardware findings, design
(not implement) the ECG architecture/validation/leakage/storage
picture, and produce a decision brief plus an implementation plan —
without implementing anything, selecting a model, or touching
production code.

## What was newly found this session (not previously on record)

1. **A correction to the SSSD-ECG conditioning-label finding.** Fetching
   `clinical_ts/ecg_utils.py`'s actual `prepare_data_ptb_xl()` code
   directly showed `label_diag` is built by filtering
   `scp_statements.csv` to `diagnostic > 0` — **44 rows**, not the full
   71-row statement table. This project's own local copy of
   `scp_statements.csv` was checked directly and confirms `71` total
   rows / `44` with `diagnostic==1`. This conflicts with the shipped
   training config's `label_embed_classes: 71` in a way that is not
   resolved by the fetched preprocessing code alone — recorded as an
   open, unresolved discrepancy (`docs/M6_ECG_MODEL_SELECTION.md` §2),
   not guessed past.

2. **The conditioning data this project would need is already present
   locally, before any new dataset is considered.** Direct inspection
   of `syngen/SynGen/SynGen/dataset/ptbxl_database.csv` confirmed a
   `scp_codes` column already exists (e.g. `ecg_id=1` →
   `{'NORM': 100.0, 'LVOLT': 0.0, 'SR': 0.0}`), and the companion
   `scp_statements.csv` carries the full 71-statement table with a
   `diagnostic` column. Recovering either the 44-diagnostic or
   71-statement label vector is therefore a small metadata-extraction
   addition to `ingestion/ptbxl_source.py`, not a new dataset
   acquisition — directly answers the milestone's Phase-2 instruction
   to check existing project data before proposing anything new
   (`docs/M6_ECG_MODEL_SELECTION.md` §3).

3. **A dedicated research pass on the four previously-flagged-but-
   unverified alternative candidates** (DiffuSETS, FlowECG, cNVAE-ECG,
   a FEM-simulator-trained VAE), run as an isolated agent fetching
   primary sources (actual repos/license files/papers, not summaries of
   summaries). Findings, factual not ranked:
   - **DiffuSETS** — inference-only code exists, weights are
     MIT-licensed on Hugging Face, but the code repo itself has no
     LICENSE file and it conditions on free-text clinical reports + age/
     sex/HR, not any SCP/superclass label — the furthest from this
     project's existing data of any candidate reviewed.
   - **FlowECG** — paper-only; no repository or weights exist anywhere,
     despite matching SSSD-ECG's own 71-dim SCP conditioning scheme.
   - **cNVAE-ECG** — code exists but ships no pretrained weights (would
     require training from scratch) and no LICENSE file, with the paper
     text itself under CC BY-NC-ND; conditions on a bespoke 9-class
     taxonomy.
   - **FEM-simulator VAE** — the paper's promised GitHub release was
     directly checked against the named organization's repo list and
     confirmed **not present**; trained on 100% simulator-generated
     data with no real-patient provenance and a conditioning scheme
     (24-dim cardiac physiology parameters) unrelated to any label this
     project has.
   None displaces SSSD-ECG as the only candidate with both released,
   runnable inference code and a real (if incompletely licensed)
   pretrained checkpoint.

4. **A leakage-safety finding specific to using a third-party pretrained
   model.** `configs/base.yaml`'s existing `training_folds: [1..8]`
   already means this project's synthetic population has never sampled
   PTB-XL's official validation (9) or test (10) folds for ECG-metadata
   conditioning — a real, already-in-place protection, not new. But this
   session identified a distinct risk the prior passes didn't separate
   out: if SSSD-ECG's own pretrained checkpoint was trained on *all* of
   PTB-XL (its paper does not document a fold-1-8 restriction the way
   this project does), then generating from that checkpoint and
   evaluating against folds 9/10 is not leakage-free *from the model's
   training history*, even though it is from this project's own
   conditioning-sampling process. Recorded as unresolved
   (`docs/M6_ECG_MODEL_SELECTION.md` §9), not silently assumed safe.

5. **A concrete storage/scale table and a batching recommendation**
   (not a decision) — generating 100K ECG waveforms is estimated at
   "low single-digit hours," over an order of magnitude longer than
   M5's 23-minute metadata-only run, so deterministic checkpointed
   batches (matching this project's own existing progressive-scaling
   pattern) are recommended over one monolithic run — not implemented.

## What was reused, not redone

`docs/M6_SSDD_ECG_COMPATIBILITY.md` (shape/rate/lead-order compatibility
verdicts) and `docs/M6_ECG_VALIDATION_PLAN.md` (the full 15-item
validation design) are referenced as-is — neither was reproduced or
modified, per this session's instruction not to redo settled work. The
Option A/B/C representation analysis from `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`
is carried forward unranked, as it already was.

## Verification run this session

Full test suite: **103/103 passed**, 180.74s, 0 failures — confirms no
behavioral regression, consistent with the fact that no file under
`schemas/`, `generation/`, `integration/`, `validation/`, or `configs/`
was touched this session. Anaconda interpreter used per `docs/DECISIONS.md`
D002.

## Net effect on M6

Still not started as a coded milestone — this remains research and
architecture design. The decision package requested is complete:
`docs/M6_ECG_MODEL_SELECTION.md`, `docs/M7_ECG_IMPLEMENTATION_PLAN.md`,
this log. `docs/PROJECT_STATE.md` updated with a pointer only. No entry
added to `docs/DECISIONS.md` — no model, architecture, or schema
decision was actually made this session (per this milestone's own
instruction, every real choice — model, representation option A/B/C,
storage inline/external, the scp_codes schema addition, the weight
license — is recorded as an open human-checkpoint item instead,
`docs/M6_ECG_MODEL_SELECTION.md` §9/§11).

## Human decisions required (unchanged set, restated for this session's record)

1. Model selection itself (SSSD-ECG vs. an alternative vs. deferring
   further) — this document classifies candidates, does not choose one.
2. Whether/how to resolve the 44-vs-71 label discrepancy (§2) before
   committing to SSSD-ECG specifically.
3. Whether to add the `scp_codes` metadata field (§3) — now confirmed
   cheap, but still a real schema touch needing the same sign-off
   pattern as D012/D015/D016.
4. Representation option A/B/C (where shape/lead-order conversion
   happens) and the canonical lead order itself.
5. Waveform storage: inline JSON vs. external file.
6. Whether the third-party-pretrained-model leakage risk (§9) is an
   acceptable, documented limitation or a reason to require training
   from scratch on a fold-1-8-only split.
7. Authorization for M7-0 (manual license verification + a real
   parameter/VRAM measurement) — the recommended next concrete step.

## Recommended next step

`docs/M7_ECG_IMPLEMENTATION_PLAN.md` M7-0: a human manually confirms the
SSSD-ECG pretrained-weight license via an authenticated Figshare
session, and — if the license permits use — a real parameter count/VRAM
figure is obtained by loading (not training) the checkpoint. Nothing
past that point should proceed until that license question is closed.
