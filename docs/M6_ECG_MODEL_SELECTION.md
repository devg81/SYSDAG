# M6 — ECG Model Selection + Architecture Decision Brief

**Status: RESEARCH + ARCHITECTURE ONLY. No model selected. No code in
`schemas/`, `generation/`, `integration/`, `validation/`, or `configs/`
changed. No waveform generated. No dataset regenerated.** This document
supersedes nothing in `docs/M6_SSDD_ECG_COMPATIBILITY.md`,
`docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`, or
`docs/M6_ECG_VALIDATION_PLAN.md` — those remain authoritative for the
detail they contain; this document assembles them plus new evidence
gathered this session into the single decision package requested, and
corrects one specific factual point (§2).

## 1. Current baseline

Per `docs/PROJECT_STATE.md`: M1-M5 complete, Schema v0.7, a
100,000-patient baseline dataset generated and fully validated (0
structural errors, 0 clinical-consistency errors). ECG today is
**metadata-only** — `ECGRecord.signal_available` is `False` for every
patient ever generated; no waveform array is generated, stored, or
validated anywhere in this project. `ECGRecord.signal_shape` already
declares a target of `[1000, 12]` (samples-first, 100Hz) — an existing
schema field, not a new proposal.

## 2. SSSD-ECG verification — status: PARTIALLY CONFIRMED, one correction this session

Full detail remains in `docs/M6_SSDD_ECG_COMPATIBILITY.md`. Summary,
carried forward unchanged:

| Dimension | Verdict |
|---|---|
| Sample count (1000) | DIRECT MATCH |
| Sampling rate (100Hz) | DIRECT MATCH |
| Tensor axis order | REQUIRES CONVERSION (lossless transpose) |
| Lead order | REQUIRES CONVERSION (lossless permutation) — target order still undefined project-side |
| 12-lead direct generation | NO — 8 sampled + 4 algebraically derived by SSSD-ECG itself |
| Conditioning labels | see correction below |
| Pretrained-weight inference-only usability | CONFIRMED supported by the code, PENDING license |

**Correction to the conditioning-label finding, verified this session**
by fetching `clinical_ts/ecg_utils.py`'s actual `prepare_data_ptb_xl()`
logic directly (not summarized): the prior audit's phrase "71-dimensional
raw PTB-XL SCP diagnostic-code multi-hot vector" conflated two different
numbers. The code that builds SSSD-ECG's `label_diag` column explicitly
filters to only the **diagnostic-flagged** rows of `scp_statements.csv`:

```python
ptb_xl_label_diag = ptb_xl_label_df[ptb_xl_label_df.diagnostic > 0]
df_ptb_xl["label_diag"] = df_ptb_xl.scp_codes.apply(
    lambda x: [y for y in x.keys() if y in ptb_xl_label_diag.index]
)
```

`scp_statements.csv` (confirmed directly from this project's own local
copy, `syngen/SynGen/SynGen/dataset/scp_statements.csv`) has **71 total
rows, of which exactly 44 have `diagnostic == 1`**. So `label_diag`'s
vocabulary is built from **44 diagnostic codes, not 71** — while the
shipped training config's `label_embed_classes: 71` (quoted correctly
in the prior audit) allocates an embedding table sized to the *full*
71-row statement table. **This is a genuine, unresolved discrepancy**,
not a resolved one: it is not clear from the fetched preprocessing code
alone whether (a) the embedding table is simply over-allocated to 71
slots with roughly half permanently unused, or (b) a different,
non-diagnostic-filtered label construction is what the released
checkpoint was actually trained with. **Resolving this precisely
requires either the actual checkpoint's embedding-layer weight shape
(`state_dict['label_embedding.weight'].shape`) or a full trace of
`train.py`'s label-loading path — neither was done this session** (the
former needs the still-license-blocked checkpoint; the latter was out
of this session's scope). Flagged as an explicit open question (§9),
not guessed past.

## 3. Conditioning compatibility — NEW FINDING: the raw data already exists locally

Phase-2 investigation (this session) checked whether this project's
existing PTB-XL source data can recover the SCP codes SSSD-ECG needs,
before proposing any new dataset, per this milestone's explicit
instruction.

**Confirmed by direct inspection:** `syngen/SynGen/SynGen/dataset/
ptbxl_database.csv` (used today only for `age`/`sex`/`height`/`weight`/
`strat_fold` via `ingestion/ptbxl_source.py`) already has a `scp_codes`
column — e.g. row `ecg_id=1`: `{'NORM': 100.0, 'LVOLT': 0.0, 'SR': 0.0}`
— a per-record, confidence-weighted dict over SCP statement codes. The
companion `scp_statements.csv` (also already present locally) is the
full 71-row statement table with a `diagnostic` column, letting either
the 44-diagnostic-only subset or the full 71-statement set be
reconstructed deterministically, in the exact index order needed, once
the target order is known.

**This means: recovering the label vector SSSD-ECG needs is a metadata
*addition* to `ingestion/ptbxl_source.py` (a new, small, pure function
reading a column this project's own files already ship), not a new
external dataset download and not a redesign.** This directly resolves
the open question `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md` §Task-3
left open ("Option A: recover and preserve the original PTB-XL SCP-code
representation") from "would require new work" to "the data exists
today; only the extraction code doesn't." The §2 embedding-size
discrepancy above means the *exact* target vector shape (44 vs 71,
and in what index order) is still not fully nailed down — that remains
open, but the *source data availability* question is now answered:
**yes, without any new dataset.**

Options A/B/C for what to actually *do* with this (evaluated, not
selected, per `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`'s existing
Task-3 analysis for the tensor-shape question, and newly for the
labeling question):

- **Option A** — capture and store the raw SCP/diagnostic vector as new
  ECG metadata (additive schema field, e.g. `ECGRecord.scp_codes:
  Optional[dict[str, float]]`), keeping the public 5-superclass field
  unchanged. Now confirmed low-cost given §3's finding.
- **Option B** — do not capture raw SCP codes; adapt/retrain SSSD-ECG's
  label-embedding layer around the existing 5-superclass scheme. This is
  model surgery, not pretrained inference — a materially larger
  undertaking, reopening the "minimal fine-tuning only" ceiling
  (`CLAUDE.md` §12).
- **Option C** — pick a different model whose native conditioning
  already matches the 5-superclass scheme. No such candidate was found
  in either research pass (§6) — every real candidate audited conditions
  on something else entirely (71/44-dim SCP vectors, free text, or a
  bespoke pathology taxonomy).

**Not selected here.** Option A is the only one of the three that adds
no new external dependency and no model-surgery risk, but adopting it is
still a schema change (however small) and depends on §2's discrepancy
being resolved first (so the stored vector's shape/order actually
matches what a checkpoint expects) — left as a human-checkpoint item
(§9) plus M7-1 in the implementation plan.

## 4. Weight/license findings — unchanged, still the single blocking unknown

From `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`, not re-litigated:

| Item | Status |
|---|---|
| SSSD-ECG code license | MIT — CONFIRMED |
| SSSD-ECG pretrained-weight license | **UNKNOWN** — Figshare share link (`figshare.com/s/81834b24a4711c2a5c55`, DOI `10.6084/m9.figshare.21922875`) returns HTTP 403 on every automated fetch; needs a human with an authenticated browser session |
| PTB-XL license | CC BY 4.0 — CONFIRMED |
| NeuroKit2 license | MIT — CONFIRMED |

No new attempt was made this session to access the Figshare link — it
remains a manual-verification task for a human, not something an
automated fetch can resolve (already attempted twice previously).

## 5. Hardware findings — estimates, not measurements

Carried forward, no new measurement taken this session (would require
downloading the license-blocked checkpoint):

- **RTX 4060 (8GB): ESTIMATE — practical.** SSSD-ECG is an 8-channel,
  36-residual-layer WaveNet/S4 hybrid over a short (8×1000) tensor —
  not large by parameter-count conventions in this space. No VRAM figure
  is stated anywhere in SSSD-ECG's own sources.
- **36GB alternative machine: ESTIMATE — more clearly practical**, same
  reasoning, more headroom for larger inference batches. No distinct new
  evidence beyond the same architecture-size reasoning.
- **The three alternative candidates (§6) are, if anything, less
  characterized for an 8GB card**: DiffuSETS states only its *training*
  hardware (RTX 3090, batch 512) with no inference-alone VRAM figure;
  FlowECG and cNVAE-ECG state training cost only (batch 6; ~134h on an
  A100) with nothing about inference memory.
- **To resolve for real:** run `print_size(net)` (already present in
  SSSD-ECG's own `src/sssd/utils/util.py`) against a loaded checkpoint,
  or benchmark `inference.py` directly — both blocked on the same
  license/access step as §4, and both deferred to M7-0/M7-3 in the
  implementation plan, not attempted here (`CLAUDE.md` §15 — no code
  execution/download this milestone).
- **AWS: NOT REQUIRED**, per every hardware estimate gathered across
  both this session and the prior research pass — no RED (impractical)
  cell was found for local hardware at any scale up to 1M waveforms.

## 6. Alternative candidates — factual comparison, not ranked

Beyond SSSD-ECG, four candidates flagged (not deep-verified) in the
prior research pass were audited this session by a dedicated research
pass fetching primary sources (actual repos, actual license files,
actual papers — not summaries of summaries).

| Candidate | Paper | Repo/weights | Conditioning | Shape/rate | PTB-XL role | Bucket |
|---|---|---|---|---|---|---|
| **SSSD-ECG** | arXiv:2301.08227 | MIT code; weights license UNKNOWN | 44-or-71-dim SCP vector (see §2) | (12,1000) native, non-standard order, 100Hz | Sole training data | VIABLE WITH ADAPTATION, pending weight license |
| **DiffuSETS** | arXiv:2501.05932 (*Patterns*) | Code repo has **no LICENSE file** (terms unclear); HF weights `Laiyf/DiffuSETS_KT` are **MIT** | Free-text clinical report + age/sex/HR — **no SCP/superclass conditioning at all** | 500Hz, 5000 samples native, downsampled to a 1024-step latent, 12-lead | Trained on MIMIC-IV-ECG; externally validated on PTB-XL (not primary training data) | VIABLE WITH ADAPTATION — inference-only code + MIT weights exist, but needs a label→text bridge since it doesn't accept SCP/superclass labels at all |
| **FlowECG** | arXiv:2509.10491 | **No repository or weights found anywhere** | Full 71-dim SCP vector (SSSD-ECG-derived design) | Same as SSSD-ECG (8 sampled + 4 derived leads, 100Hz, 1000 samples) | PTB-XL, full dataset | RESEARCH-ONLY — paper-only, nothing released to run |
| **cNVAE-ECG** | arXiv:2503.13469 | `github.com/univanxx/cNVAE_ECG`, **no LICENSE file**; paper text itself CC BY-NC-ND (non-commercial, no-derivatives) if that governs code use; **no pretrained weights** | Bespoke 9-class pathology taxonomy — partial overlap with, but not equal to, either this project's 5 superclasses or SCP codes | 500Hz, 5000 samples, 8 channels generated + 4 derived, 12-lead | 2,183 PTB-XL records used (small subset) + two other databases | VIABLE WITH ADAPTATION — code exists but no weights (training required) and an unclear/restrictive license |
| **FEM-simulator VAE** | *Cardiovasc Digital Health J.*, Dec 2023 (PMC10879006) | Promised `nttcslab` GitHub release **confirmed NOT present** in that org today | 24-dim cardiac-simulator physiology parameters — no relationship to SCP codes or PTB-XL labels at all | 500Hz, 500 samples/beat (per-beat, not a 10s strip), 12-lead | **Zero real patient data** — 100% FEM-simulator-generated training set | REJECTED / INCOMPATIBLE — no released code, no weights, no real-data provenance, incompatible representation |

**No winner is declared, per instruction.** The one candidate with both
released, runnable inference code AND a real (if incompletely licensed)
pretrained checkpoint remains SSSD-ECG. DiffuSETS is the only other
candidate with both code and openly-licensed weights, but its
conditioning scheme (free text) is the furthest from anything this
project currently stores — using it would mean generating synthetic
clinical-report text from structured labels as a new translation layer,
not a small adapter.

## 7. Architecture options — design only, not implemented

Pipeline (none of this exists yet; every arrow below is a future stage,
not current behavior):

```text
Existing Patient (risk_factors, diagnoses, demographics — already generated)
    ↓
ECG conditioning source: superclasses (existing, 5-class)
                          + scp_codes (NEW metadata field, §3 — not yet added)
    ↓
Condition representation: model-specific vector (shape/order per §2's
    still-open discrepancy — must be pinned down before this stage)
    ↓
ECG generative model (not selected — §6's evidence, no choice made)
    ↓
Raw model output: native shape/lead-order (e.g. SSSD-ECG's (12,1000),
    non-standard order)
    ↓
Conversion step (Option B, `docs/M6_MODEL_SELECTION_DECISION_BRIEF.md`
    §Task-3 — lossless transpose + lead permutation; NOT ranked against
    A/C, no choice made)
    ↓
Canonical [1000, 12] waveform, standard clinical lead order (matches
    the schema's existing declared field)
    ↓
Waveform validation (`docs/M6_ECG_VALIDATION_PLAN.md` — designed,
    not implemented)
    ↓
Patient ECG attachment (`ECGRecord.signal_available = True`,
    provenance recording model/checkpoint/seed — additive schema fields,
    not yet added)
    ↓
Dataset validation (existing `validation/clinical_consistency.py`
    pattern, extended)
```

Specific open design points, decided/undecided status:

- **Conditioning source** — DECIDED this session (§3): recoverable
  locally, no new dataset. **Not yet implemented.**
- **patient_id → ECG mapping** — UNCHANGED from today: `pick_ecg_id()`'s
  existing deterministic `(seed, folds)` selection already assigns a
  source PTB-XL `ecg_id` per patient; a future waveform generator would
  condition on that same already-selected record's labels, not add a
  second independent selection.
- **Random seeds / reproducibility** — the existing per-patient
  `(sequence, seed)` determinism (`tests/test_stage2_foundation.py`)
  must extend to the model's own generation seed; NOT designed in
  code yet, but the existing precedent is the pattern to reuse, not a
  new scheme to invent.
- **Waveform shape/lead-order/rate validation** — fully designed
  already, `docs/M6_ECG_VALIDATION_PLAN.md` items 1-3.
- **Invalid-waveform rejection** — designed already, same document's
  HARD FAILURE tier.
- **Storage — inline vs. external** — **UNDECIDED**, flagged as a human
  checkpoint in the M7 plan (M7-5): storing a `[1000,12]` float array
  inline in each patient's JSON record would make every JSON file ~48KB
  (float32) larger — a ~1.4x size increase over M5's measured
  3,551 bytes/patient metadata baseline — versus an external file
  (`.npy`/`.h5`) referenced by path, matching how large binary PTB-XL
  assets are already excluded from git today (`.gitignore`). Not decided
  in this document.
- **Metadata reference to the waveform** — depends on the storage
  decision above; not designed further until that decision is made.
- **Preventing PTB-XL source records from being mistaken for synthetic
  waveforms** — already structurally provided for: `ECGRecord.
  signal_available` exists precisely to distinguish "metadata only"
  (today, always `False`) from "has an attached waveform" (future,
  `True`), and the source `ecg_id` field is documented (D003) as
  metadata provenance, never a synthetic-content identifier. No new
  field is needed for this distinction — reusing the existing one is
  sufficient.

## 8. Validation plan — reference, not redesigned

`docs/M6_ECG_VALIDATION_PLAN.md` already covers all 15 requested
validation dimensions (shape, sampling rate, lead order, amplitude
sanity, NaN/Inf, flatline, NeuroKit2 morphology, heart-rate
plausibility, label-consistency, PTB-XL distributional comparison,
diversity, duplicate/similarity, membership-inference/privacy,
reproducibility, failure-rate reporting) in the same three-tier (HARD
FAILURE / WARNING / STATISTICAL OBSERVATION) shape as this project's
existing `ClinicalValidationResult`. **That document remains
authoritative and is not modified or reproduced here.** Nothing new was
added this session; it is referenced, not redesigned, per this
milestone's instruction not to re-do settled work.

## 9. Leakage considerations — NEW, this session

**Existing, already-in-place protection:** `configs/base.yaml`'s
`training_folds: [1, 2, 3, 4, 5, 6, 7, 8]` already restricts every
synthetic patient's ECG-metadata conditioning to PTB-XL's own designated
training folds (`ingestion/ptbxl_source.py::pick_ecg_id`). PTB-XL's
stratified folds are patient-level (Wagner et al. 2020's own
methodology keeps all of one real patient's records in one fold), so
this project's synthetic population has never, at any milestone,
sampled from PTB-XL's official validation fold (9) or test fold (10).
**This means folds 9/10 are already a clean, never-conditioned-on
reference set today** — directly usable for `docs/M6_ECG_VALIDATION_PLAN.md`
item #10 (train-real/test-synthetic classifier) and item #13
(membership-inference check) without carving out a new held-out split.

**New risk this session identifies, specific to using a third-party
pretrained model:** if SSSD-ECG's own released checkpoint was trained
on *all* of PTB-XL (its own paper does not document restricting to
folds 1-8 the way this project does), then generating waveforms with
that checkpoint and evaluating them against "held-out" fold 9/10 real
data is **not** a leakage-free test from the *model's* perspective, even
though it is from *this project's own* conditioning-sampling
perspective. This is a real, concrete distinction the prior research
passes did not separate out: this project's own fold discipline
protects its *own* label-selection process, but says nothing about what
the *external pretrained model itself* was exposed to during its own
training. **Not resolved here** — would need either training SSSD-ECG
from scratch on a fold-1-8-only split (a large undertaking, contrary to
the "pretrained inference, minimal fine-tuning" principle,
`CLAUDE.md` §12), or explicitly documenting this as an accepted
limitation of using any third-party-pretrained generator, rather than
silently treating fold 9/10 evaluation as if it were leakage-free.

**ecg_id-reuse interaction (existing, already-documented finding,
M3/M4F/M5 — not newly discovered):** at 100K scale, 17,386 unique
`ecg_id`s are referenced across 100,000 patients (max reuse 17×). This
is fine for metadata-only conditioning (many synthetic patients
legitimately sharing one real record's diagnostic labels is not itself
a leak). **The new implication for actual waveform generation:** the
eventual generation seed must incorporate the synthetic `patient_id`/
sequence, not just the shared source `ecg_id`, or two patients
conditioned on the same source record would receive a byte-identical
generated waveform — a real generation-pipeline bug per
`docs/M6_ECG_VALIDATION_PLAN.md` item #12's HARD FAILURE tier, not a
statistical curiosity. Not implemented; flagged for M7-3/M7-6.

## 10. Storage and scale estimates

Per-waveform, `[1000, 12]`:

| Precision | Bytes/waveform | 100,000 waveforms | 1,000,000 waveforms |
|---|---|---|---|
| float32 | 48,000 B (46.9 KiB) | 4.8 GB | 48 GB |
| float16 | 24,000 B (23.4 KiB) | 2.4 GB | 24 GB |

Combined with M5's **measured** metadata footprint (355.12 MB at 100K;
linearly ~3.55 GB projected at 1M, not independently verified at that
scale):

| Precision | Total at 100K | Total at 1M |
|---|---|---|
| float32 | ≈ 5.15 GB | ≈ 51.5 GB |
| float16 | ≈ 2.75 GB | ≈ 27.5 GB |

No compression evaluated — per this milestone's instruction not to
introduce it without evaluation.

**Single run vs. deterministic batches:** M5's metadata-only 100K run
took 23.3 minutes; every ECG-generation estimate gathered (§5, this
session and prior) puts waveform generation at "low single-digit hours"
for 100K — over an order of magnitude longer, and diffusion-model
inference failure partway through a multi-hour run is a real risk this
project has not had to plan for yet. **Recommendation (not a decision):
generate in deterministic, checkpointed batches** (e.g. 1,000 or 10,000
patients per batch, matching this project's own existing
10→100→1,000→10,000→100,000 progressive-scaling pattern, `CLAUDE.md`
§7/§27), not as one monolithic run — allows resuming after a failure
without regenerating from scratch, and matches every prior scale-up in
this project's own history.

## 11. Explicit unresolved questions

1. **SSSD-ECG pretrained-weight license** — UNKNOWN, needs a human with
   an authenticated Figshare session (§4).
2. **The 44-vs-71 label_diag/label_embed_classes discrepancy** — needs
   either the actual checkpoint's embedding-layer shape or a full
   `train.py` label-path trace (§2).
3. **Canonical ECG lead order for this project** — still formally
   undecided; no Stage-4 waveform pipeline exists yet to have decided it
   (carried forward from `docs/M6_SSDD_ECG_COMPATIBILITY.md`).
4. **Representation option A/B/C** (where the shape/order conversion
   happens) — not ranked, not chosen (§7).
5. **Whether to add the raw `scp_codes` metadata field at all** — now
   confirmed cheap/local (§3), but still an actual schema change
   requiring the same kind of sign-off `docs/DECISIONS.md` D012/D015/
   D016 record for past additive changes.
6. **Waveform storage: inline vs. external file** — not decided (§7).
7. **The external-pretrained-model leakage question** (§9) — not
   resolved, and not resolvable without either retraining or an
   explicit accepted-limitation decision.
8. **DiffuSETS's label→text conditioning bridge** — if pursued, an
   entirely new translation-layer design question this document does
   not attempt (§6).
9. All of `docs/M6_ECG_VALIDATION_PLAN.md`'s "TO BE ESTABLISHED DURING
   PILOT" numeric thresholds — unchanged, still open, still deferred to
   real pilot data (M7-7).

## 12. Recommended next implementation milestone

See `docs/M7_ECG_IMPLEMENTATION_PLAN.md` for the full staged breakdown.
In short: the next defensible step is a narrow verification spike
(M7-0) — resolve the weight license by hand, get a real parameter/VRAM
number, and pin down the §2 label-vocabulary discrepancy — **before**
any conversion, schema, or generation code is written. Nothing in this
document authorizes skipping that spike or selecting SSSD-ECG outright.

---

**This document does not select a model.** Per `CLAUDE.md` §11/§28 and
this milestone's explicit instruction, model selection remains a human
checkpoint. Candidates are classified by verified capability (§6), not
ranked or scored.
