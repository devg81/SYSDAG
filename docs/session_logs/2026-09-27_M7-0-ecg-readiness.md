# Session Log — 2026-09-27 — M7-0: ECG Implementation Readiness / Human Verification Spike

**No model selected. No implementation done. No schema/generation/
integration/validation/configs file changed. No ECG generated. The
existing 100K dataset was not touched.** Continues from M6
(`docs/M6_ECG_MODEL_SELECTION.md`, `docs/M7_ECG_IMPLEMENTATION_PLAN.md`).

## Objective

Execute M7-0 exactly as scoped: verify SSSD-ECG's architecture,
resolve (as far as possible without the license-blocked checkpoint) the
44-vs-71 conditioning discrepancy M6 left open, check this project's own
local PTB-XL data against what the model actually needs, measure/derive
a real parameter count, consolidate hardware/licensing/leakage findings,
and produce a decision package — without implementing anything.

## Sources inspected this session

Local repository (via `Read`/`Grep`/`Bash` with the project's Anaconda
interpreter, per D002):
- `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`, `docs/CLAUDE.md`
- `docs/M6_ECG_MODEL_SELECTION.md`, `docs/M7_ECG_IMPLEMENTATION_PLAN.md`,
  `docs/M6_SSDD_ECG_COMPATIBILITY.md`, `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`
- `ingestion/ptbxl_source.py`
- `configs/base.yaml` (`training_folds`)
- `syngen/SynGen/SynGen/dataset/ptbxl_database.csv`,
  `syngen/SynGen/SynGen/dataset/scp_statements.csv` (loaded directly via
  pandas, column/shape/value inspection)

Remote (via `WebFetch`, raw GitHub content, this session):
- `AI4HealthUOL/SSSD-ECG` repository tree (via GitHub API, `git/trees`)
- `src/sssd/config/config_SSSD_ECG.json` (full contents)
- `src/sssd/models/SSSD_ECG.py` (model class, `Residual_block`,
  `Residual_group` — fetched twice, second time targeted at the
  specific classes not returned the first time)
- `src/sssd/models/S4Model.py` (`S4Layer` class only — `Residual_block`/
  `Residual_group` are NOT here, contrary to an initial guess; corrected
  by re-fetching `SSSD_ECG.py` directly)
- `src/sssd/utils/util.py` (`print_size` function)
- `src/sssd/train.py` (fetched twice — once for label loading, once
  specifically for waveform-data normalization, which the first fetch
  did not address)
- `src/ptb_xl/ecg_data_preprocessing.ipynb` (fetched twice — once in the
  prior M6 session, once again this session with more targeted
  questions about `np.save` calls and the `ptb_xl_label` variable)
- `src/ptb_xl/clinical_ts/ecg_utils.py` (fetched twice this session —
  once for the `prepare_data_ptb_xl` label-construction detail, once
  for its normalization/mean-std computation)

## Commands run

```
find (bash) — locate ptbxl_database.csv / scp_statements.csv paths
"/c/Users/devg8/anaconda3/python.exe" -c "pandas read_csv ... scp_codes sample"
"/c/Users/devg8/anaconda3/python.exe" -c "pandas read_csv scp_statements.csv ... diagnostic sum/index"
"/c/Users/devg8/anaconda3/python.exe" -m pytest -q   (full suite, background, completed)
```

## What was newly found (not previously on record)

1. **The 71-dim conditioning requirement is architecturally hard, not
   a loose config default.** `SSSD_ECG.py`'s `label @
   self.embedding.weight` matmul requires the label input's last
   dimension to exactly equal `label_embed_classes` (71) or the
   operation fails outright. This is a stronger form of evidence than
   the prior session's config-value citation alone.
2. **`prepare_data_ptb_xl()` builds six label arrays, not one** —
   `label_all`, `label_diag`, `label_form`, `label_rhythm`,
   `label_diag_subclass`, `label_diag_superclass`. The prior session's
   audit had only traced the notebook's `ptb_xl_label = "label_diag"`
   variable and concluded the model's conditioning was 44-diagnostic
   codes; this session found that conclusion was based on an incomplete
   trace — the notebook's own `np.save()`-free structure means it isn't
   even the script that produces `train.py`'s actual loaded array, and
   `label_all` (unfiltered, all 71 codes) is the far more parsimonious
   match for a hard 71-dim requirement.
3. **This project's own local PTB-XL files (already present, no new
   dataset) can supply the 71-dim vector directly** — `scp_statements.csv`
   independently confirmed at exactly 71 rows / 44 diagnostic-flagged,
   `ptbxl_database.csv`'s `scp_codes` column confirmed present with
   real per-record values. Upgrades the M6 conditioning-compatibility
   verdict from "PARTIAL, leaning INCOMPATIBLE-AS-IS" to "content
   recoverable locally, exact index order unconfirmed."
4. **A real, code-verified partial parameter count**: ~26.5M parameters
   from every layer that could be fully traced from the fetched source
   (convs, linears, embeddings, layer norms across all 36 residual
   blocks plus top-level layers), with the remaining S4-kernel
   contribution explicitly bounded as an estimate (50M-150M total)
   rather than fabricated as measured. This is a materially stronger
   basis for the "8GB VRAM sufficient" conclusion than the prior
   session's pure architecture-size hand-waving.
5. **A new, previously unflagged amplitude-convention question**:
   `train.py` applies no normalization to the loaded waveform array
   before training, and the preprocessing notebook/utils code that
   computes `mean_ptb_xl`/`std_ptb_xl` never applies them to the saved
   `.npy` files either — meaning the actual amplitude scale of
   `ptbxl_train_data.npy` (a file not present in the fetched repository)
   cannot be confirmed this session. Recorded as unresolved, not
   assumed either way.
6. **A sharpened leakage finding**: this project's own PTB-XL
   fold-1-8 sampling discipline protects its own conditioning-selection
   process, but says nothing about whether SSSD-ECG's own pretrained
   checkpoint was itself trained on all of PTB-XL (no fold restriction
   found in its own repository) — a distinct risk not fully separated
   out in the prior M6 session's leakage discussion.

## What was explicitly NOT done, per this milestone's stop conditions

- Did not attempt to access the private/authenticated Figshare weight
  link by any method (no scraping, no auth bypass).
- Did not download or install any model weights.
- Did not fetch the upstream `state-spaces/s4` library (the source of
  the unverified S4-kernel parameter component) — flagged as a further
  narrowing step, not attempted, kept within this spike's scope.
- Did not add `scp_codes` (or any field) to `schemas/patient_schema.py`.
- Did not write any conversion, generation, or validation code.
- Did not modify `configs/base.yaml` or any other config.
- Did not touch `outputs/m5/100k_patients/`.

## Verification run this session

Full test suite: **103/103 passed**, under the project's Anaconda
interpreter (D002). Confirms zero behavioral regression, consistent
with no production file having been touched this session (only files
under `docs/` were created).

## Net effect on M7

M7-0 remains a human checkpoint, not a completed implementation stage.
Deliverables: `docs/M7_0_ECG_READINESS_REPORT.md` (main decision
package), `docs/M7_0_CONDITIONING_AUDIT.md` (44-vs-71 deep dive),
`docs/M7_0_ECG_IMPLEMENTATION_CONTRACT.md` (design-only interface),
this log. `docs/PROJECT_STATE.md` updated with a pointer only. No entry
added to `docs/DECISIONS.md` — this session made no actual decision;
every judgment call it could have made (model selection, conditioning
resolution acceptance, schema change, storage format, leakage-risk
acceptance) is recorded as a pending human decision instead
(`docs/M7_0_ECG_READINESS_REPORT.md` §13). D011-D016 were read for
context and are unmodified.

## Recommended next step

A human manually confirms the SSSD-ECG pretrained-weight license via an
authenticated Figshare session. If and only if permitted, load the
checkpoint read-only to confirm `embedding.weight.shape == (71, 128)`
(settling the conditioning question directly) and run `print_size(net)`
for a real parameter count. Nothing past that point should proceed
before those two checks and the §13 human-decision checklist are
resolved.
