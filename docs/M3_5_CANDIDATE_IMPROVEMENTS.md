# M3.5 — Candidate Improvement Audit

Each of M3's four candidate improvements was independently investigated
by reading the actual implementation (not just the M3 report summary),
per this milestone's instructions. Full reasoning for each is also
recorded in `docs/DECISIONS.md` (D009 for the one implemented, D010 for
the three deferred/preserved).

---

## 1. Urban/Rural BMI Conditioning

| Field | Answer |
|---|---|
| Current implementation | `generation/indian_population.py::sample_bmi()` conditions BMI category on **sex only**, via `configs/indian_population.yaml`'s `risk_factors.bmi.distribution.categories_by_sex` |
| Evidence supporting change | ICMR-NNMS (PLOS One 2021) reports BMI category prevalence by urban/rural (overweight urban 42.5%/rural 18.0%; obese urban 11.2%/rural 3.7%) — found during M2C-0's own research, never wired into the config |
| Expected benefit | A real, already-cited, national-level (not region-scoped) relationship currently treated as absent |
| Risk | The urban/rural figures and the sex figures come from the **same national paper but as two separate 2-way breakdowns**, not one joint sex×urban/rural×BMI table. There is no source-given method to combine them for a specific (sex, urban_rural) pair. |
| Changes the synthetic population distribution? | Yes, if implemented — BMI generation would shift for every patient based on urban_rural, not just sex |
| Changes the meaning of existing source evidence? | **Yes** — any combination method (e.g., assuming independence, multiplying odds) would be an unstated engineering assumption presented alongside genuinely-sourced sex-conditional figures, blurring the evidence-tier distinction this project has maintained throughout M2C/M2D |
| Requires a project-level decision? | **Yes** |
| **Recommendation** | **DEFER — requires project-level decision on combination methodology before implementation** (not IMPLEMENT NOW, contrary to how M3's report initially characterized this as "low-effort, high-confidence" — deeper investigation, exactly as this milestone required, found a real methodological snag M3's summary-level pass didn't surface) |

## 2. ECG-ID Reuse Policy

| Field | Answer |
|---|---|
| Current implementation | `ingestion/ptbxl_source.py::pick_ecg_id()` draws independently (with replacement) from the training-fold pool (~17,470 records) for every patient, using that patient's own seed; no cross-patient exclusion tracking exists |
| A. Intended to identify a unique synthetic ECG? | **No** — no synthetic ECG exists yet; `ECGRecord.signal_available` is always `False` |
| B. A source PTB-XL record identifier? | **Yes**, exactly — it is literally the `ecg_id` column value from `ptbxl_database.csv` |
| C. Merely metadata inherited from the source? | **Yes**, confirmed (`docs/DECISIONS.md` D003: "metadata-only, no waveform attached") |
| D. Can multiple synthetic patients legitimately reference the same source ECG? | **Depends on a Stage 4 design decision not yet made** — legitimate if source records are eventually used as conditioning templates for distinct generated waveforms; more questionable if the literal historical signal is meant to become each patient's unique permanent ECG |
| E. Would changing it affect provenance or reproducibility? | Yes — a without-replacement scheme would make each patient's ECG selection depend on generation *order* and *batch composition*, breaking today's clean per-patient-independent-of-batch determinism (a real architecture change, not a tweak) |
| F. Would a new synthetic ECG ID require schema changes? | Yes — a distinct `synthetic_ecg_id` field (alongside the existing source `ecg_id`) would be a schema addition, requiring human review under this project's own schema-change rules |
| Classification | **DEFER UNTIL ECG STAGE** |
| **Recommendation** | **DEFER — semantics are not yet unambiguous; belongs to Stage 4, out of this milestone's scope by explicit instruction** |

## 3. Generation I/O Performance

| Field | Answer |
|---|---|
| Current implementation (before fix) | `pick_ecg_id()` and `load_ptbxl_record()` each independently called `pd.read_csv`/`build_label_map()` fresh, per patient |
| Measured (before fix) | `build_label_map()` alone: **4.9s/call**; raw `pd.read_csv` alone: 0.2s/call. Confirms the bottleneck is **CPU-bound** (`ast.literal_eval` parsing inside the reused `build_label_map()`), not filesystem I/O as M3's report had imprecisely characterized it. 1,000 patients: 37 min measured (M3) / ~40 min reproduced independently this session before the fix. |
| Expected benefit | Caching the parsed result at process level (same inputs → same output, always) removes ~4 redundant expensive calls per patient |
| Risk | Low — read-only cached objects (`pd.DataFrame`, `dict`), never mutated downstream; cache keyed on the exact arguments that determine the result (path, threshold), so different inputs can't collide |
| Changes the synthetic population distribution? | **No** — verified by diffing a full 1,000-patient regeneration against M3's baseline: 0 demographics/risk_factors differences |
| Changes the meaning of existing source evidence? | No |
| Requires a project-level decision? | No — pure performance fix, doesn't touch what's generated |
| **Recommendation** | **IMPLEMENT NOW** — done. See `docs/DECISIONS.md` D009 for full detail, `tests/test_ingestion_caching.py` for regression coverage, `integration/profile_generation.py` for the measurement tooling (kept for future re-profiling). |

**Measured result:** 1,000 patients: 37min → 20.4s (~110x). Full test
suite: 265s → 11s (~24x). Projected 100K generation: ~67 hours → minutes.

## 4. State/UT Boundary Update

| Field | Answer |
|---|---|
| Current implementation | 35-entry categorical distribution using Census 2011's own state/UT definitions (pre-Telangana, pre-J&K-reorganization, pre-Daman&Diu/Dadra&NH merger) |
| Preserve source fidelity? | Changing boundaries without a matching source would **reduce** fidelity — it would require guessing a population split (e.g. Telangana's share of undivided Andhra Pradesh) not given by Census 2011 itself |
| Break source comparability? | Yes, if changed without a proper source — the weights would no longer correspond to any single coherent, citable table |
| Require a new population source? | Yes, to do correctly — no current-boundary Census-quality table was located in M2C, M2D, or this session |
| Change the meaning of existing state weights? | Any ad hoc split would, since the weights are currently exact 2011 Census counts |
| **Recommendation** | **REJECT changing now / DEFER pending a real source** — default position (preserve Census 2011 representation) upheld, no new dataset introduced per this milestone's restriction |

---

## Summary

| Candidate | Decision | Implementation | Reason |
|---|---|---|---|
| Urban/rural BMI | DEFER | Not implemented | Requires a project-level decision on combining two non-joint marginal-conditional NNMS tables — would otherwise blur sourced evidence with an invented combination rule |
| ECG-ID reuse | DEFER | Not implemented | Semantics depend on a not-yet-made Stage 4 design decision; changing now would be premature architecture work outside this milestone's scope |
| I/O performance | IMPLEMENT NOW | **Implemented** (`docs/DECISIONS.md` D009) | Pure performance fix, verified zero content change, addresses the single largest measured blocker to scaling |
| State boundaries | REJECT / DEFER | Not implemented | No current-boundary source exists; changing without one would reduce, not improve, fidelity to the cited Census 2011 source |
