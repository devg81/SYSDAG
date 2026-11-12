# Review Package — SysDag 100K Synthetic Dataset, Schema v0.9

Assembled 2026-11-10 for independent review. Every file here is a **copy**
(timestamps preserved). No project file, decision, dataset record or
manifest was changed to build this package. The 100K records themselves
(`outputs/m9/100k_patients_v09/`, ~810 MB of JSON) are **not** included.

## 1. What v0.9 is (from repository evidence only)

- **Dataset:** `sysdag_m9_100k_v09`, version 0.9.0, schema 0.9, 100,000
  records, generated fresh with `integration/generate_population.py`
  (per-record seed = `random_seed` 42 from `configs/indian_population.yaml`
  + sequence number). Source: `04_dataset_manifest/dataset_manifest.json`,
  `01_execution_logs/generation_100k_v09.log`.
- **Changes since v0.8, all bundled into this one generation:**
  - **D019:** infeasible cholesterol (TC/TG/HDL) triples are rejected and
    redrawn.
  - **D020:** family history is populated for every record. Ages 45+ use
    LASI observed rates; ages 20–44 use a calibrated parent simulation;
    family history of diabetes is conditioned on the patient's own
    diabetes.
  - **D021:** new `air_quality` field, a lookup of the 2023 CPCB state
    annual-mean AQI by state.

  Source: `02_decisions/DECISIONS.md` (D019–D021),
  `03_project_state/PROJECT_STATE.md` (M9 section).
- **Validation results:**
  - 100,000/100,000 structurally valid and clinically consistent, with 0
    errors and 0 duplicate IDs.
  - 14,206 warnings of two kinds: LDL at the 30 mg/dL clip floor (7,740)
    and empty PTB-XL superclasses (6,466).
  - Every checked distribution is within sampling error of its config
    target.

  Source: `05_validation_v09/`, `01_execution_logs/`.

## 2. Inventory

| File name | Original path | Package path | Purpose | Version/date (file mtime) | Status |
|---|---|---|---|---|---|
| br129dosk.output | `%TEMP%/claude/…/tasks/br129dosk.output` (Claude Code background-task output, outside the repo) | `01_execution_logs/generation_100k_v09.log` | Console output of the 100K generation run: count, structural pass count, **wall time 7,089 s (118 min)** | 2026-11-10 18:09 | Found |
| bsucl6mnx.output | `%TEMP%/…/tasks/bsucl6mnx.output` | `01_execution_logs/validation_100k_v09.log` | Tail of the full validation run; wall time 776 s | 2026-11-10 18:24 | Found |
| bvlntmiyk.output | `%TEMP%/…/tasks/bvlntmiyk.output` | `01_execution_logs/distribution_check_100k_v09.log` | Console output of the distribution check (same content as the .txt in 05) | 2026-11-10 18:24 | Found |
| bn1x5m5k3.output | `%TEMP%/…/tasks/bn1x5m5k3.output` | `01_execution_logs/freeze_manifest_v09.log` | Output of the manifest freeze, plus on-disk size (948 MB allocated) and checksum | 2026-11-10 18:36 | Found |
| 2026-10-30_M9-lipid-fix-family-history-aqi-planning.md | `docs/session_logs/` | `01_execution_logs/session_log_2026-10-30_…md` | Latest session log in the repo. Covers the **D019** implementation (part of v0.9) and the family-history/AQI *planning*. It does **not** cover v0.9 generation, validation or freeze. | 2026-10-30 09:21 | Found (partial relevance, see §3) |
| DECISIONS.md | `docs/DECISIONS.md` | `02_decisions/DECISIONS.md` | Full decision history, with D021 (AQI), D020 (family history) and D019 (lipid fix) at the top | 2026-11-10 18:39 | Found |
| PROJECT_STATE.md | `docs/PROJECT_STATE.md` | `03_project_state/PROJECT_STATE.md` | Latest project state, including the "100K re-freeze at v0.9 COMPLETE" entry and the open performance issue | 2026-11-10 18:39 | Found |
| dataset_manifest.json | `outputs/m9/dataset_manifest.json` | `04_dataset_manifest/dataset_manifest.json` | Frozen manifest: name, version, schema, count, validation status, warnings, accepted limitations, directory checksum `53fcae20…d1e` | 2026-11-10 18:36 | Found |
| 100k_v09_validation_report.json | `outputs/m9/` | `05_validation_v09/` | Full structural + clinical validation report and statistics (missingness, duplicates, ECG gaps) for all 100K | 2026-11-10 18:24 | Found |
| 100k_v09_distribution_check.txt | `outputs/m9/` | `05_validation_v09/` | Marginal checks against config targets with z-scores: hypertension, diabetes, hyperlipidemia, sex, urban; family history by age tier; AQI missingness; impossible-lipid count; state χ² | 2026-11-10 18:24 | Found |
| check_v09.py | Claude Code session scratchpad (outside the repo) | `05_validation_v09/check_v09_distribution_script.py` | The script that produced the distribution check, included so the numbers can be reproduced | 2026-11-10 16:12 | Found (not a repo file) |
| pilot_1000_v09_validation.json | `outputs/m9/` | `05_validation_v09/pilots/` | Validation of the 1,000-record v0.9 pilot (family history + AQI) run before the 100K | 2026-11-10 15:58 | Found |
| pilot_1000_family_history_validation.json | `outputs/m9/` | `05_validation_v09/pilots/` | Validation of the earlier 1,000-record family-history pilot (generated at schema v0.8, before the AQI change) | 2026-11-10 15:48 | Found (pre-AQI pilot) |
| Family_history_Strategy_plan.txt | `docs/` | `06_family_history/` | Evidence trail for family history: LASI, ICMR-INDIAB, WHO STEPS, NFHS findings. Header marks it **SUPERSEDED by D020**. | 2026-11-10 15:49 | Found (superseded; context) |
| Further_Steps_for_patient-Record_complete.txt | `docs/` | `07_air_quality/` | AQI design: sources, urban-bias problem, recommended approach (§3), summary table updated to "CODE DONE" | 2026-11-10 15:59 | Found |
| cpcb_state_aqi.py | `ingestion/` | `07_air_quality/` | Script that rebuilds the per-state AQI table from the CPCB source file | 2026-11-10 15:54 | Found |
| generate_population.py | `integration/` | `08_performance/` | Generation entry point. Line 31 builds **all N `Patient` objects in a list before any file is written**. | 2026-09-25 16:27 | Found |
| indian_population.yaml | `configs/` | `09_supporting_code/configs/` | Generation config: seed, `risk_factors.family_history` (all LASI/CARRS figures, assumptions, limitations), `environment.air_quality` (per-state values, source, limitations) | 2026-11-10 15:54 | Found |
| indian_population.py | `generation/` | `09_supporting_code/generation/` | Family-history (`sample_family_history`, `family_history_marginals`) and AQI (`derive_air_quality`) implementation | 2026-11-10 15:56 | Found |
| patient_schema.py | `schemas/` | `09_supporting_code/schemas/` | Schema v0.9: `AirQuality` dataclass, `family_history` field | 2026-11-10 15:56 | Found |
| build_patient.py | `integration/` | `09_supporting_code/integration/` | Record assembly and the per-record provenance text describing D020/D021 | 2026-11-10 15:56 | Found |
| freeze_dataset_manifest.py | `integration/` | `09_supporting_code/integration/` | Manifest generator, adapted for fresh (non-migrated) datasets | 2026-11-10 16:12 | Found |
| structural.py | `validation/` | `09_supporting_code/validation/` | Structural checks, including AQI range, category and null-with-reason | 2026-11-10 15:56 | Found |
| clinical_consistency.py | `validation/` | `09_supporting_code/validation/` | Clinical checks, including the family-history shape/derivation check and the LDL < 30 clip-floor warning | 2026-11-10 15:46 | Found |
| test_m9_family_history.py | `tests/` | `09_supporting_code/tests/` | Unit tests: LASI anchor, 45 boundary continuity, CARRS cap, odds-ratio conditioning | 2026-11-10 15:46 | Found |
| test_m9_air_quality.py | `tests/` | `09_supporting_code/tests/` | Unit tests: CPCB breakpoints, determinism, null-with-reason, validator rejections | 2026-11-10 15:57 | Found |

All code files were last modified **before** the 100K run started (≈16:11
on 2026-11-10), except `freeze_dataset_manifest.py` at 16:12, which only
writes the manifest and was used afterwards. That is consistent with the
packaged code being the code that generated the dataset. Only the two docs
were edited after generation (18:39).

## 3. Requested items not found

| Requested | Finding |
|---|---|
| Session log covering v0.9 generation, validation, manifest and freeze | **Not found.** No session log was written for this work; the latest in `docs/session_logs/` is 2026-10-30, which predates v0.9 generation. The v0.9 work is recorded in `PROJECT_STATE.md` (M9 section) and `DECISIONS.md` (D020, D021), plus the raw run logs in `01_execution_logs/`. |
| Profiling output for the 118-minute run | **Not found as a file.** A 300-record cProfile run was executed in the Claude Code session, but its output was not saved. Its summary (≈12 ms per record, dominated by `pick_ecg_id`; new code ≈0.6 ms) exists only as a sentence in `PROJECT_STATE.md`. |
| Memory measurements during generation | **Not found as a file.** One mid-run reading (≈1.06 GB working set, ≈566 s CPU at 12.5 min) was observed in the session and not saved. |
| Analysis confirming the memory-bottleneck cause | **Does not exist.** The cause is unconfirmed (see §5). |
| A dedicated family-history validation report | **Not found.** Family-history validation evidence is spread across `100k_v09_distribution_check.txt`, the pilot reports, the D020 "Verification" paragraph and `test_m9_family_history.py`. |
| CARRS source document | **Not in the repository.** CARRS figures (diabetes 22.2%, heart disease 7.1%, stroke 1.9%; PMC9453056) are cited in the config and D020 only. |
| Explicit random seed / generation-config hash in the manifest | **Not present.** The manifest records the seed rule only as text ("seed = random_seed + sequence"); the seed value 42 is in `configs/indian_population.yaml`. No config hash is recorded. |

## 4. Conflicting, outdated or erroneous content found

1. **D021 says "8 states rest on a single station"; the config shows 7**
   (Arunachal Pradesh, Himachal Pradesh, Jammu and Kashmir, Meghalaya,
   Mizoram, Sikkim, Tripura). This is an error in D021's Limitations line.
   It was not corrected, per this task's no-edit rule.
2. **`PROJECT_STATE.md` header still reads "Current Stage: Stage 2 —
   Foundation"**, which is outdated relative to its own M5–M9 content.
3. **The manifest's `code_state.git_head_commit` (4ce0e72) predates all
   v0.9 work.** The v0.9 code exists only as uncommitted/untracked working
   tree files; the manifest's own note says so.
4. **`Family_history_Strategy_plan.txt`** recommends a 45+-only approach
   and cites an odds ratio of "~3.13". Both are superseded: D020 uses a
   parent simulation for 20–44 and LASI's verified crude OR 3.80. Its
   header flags this.
5. **`Further_Steps_for_patient-Record_complete.txt` §3.5/§3.6** still say
   "not implemented / pilot on 50 records". The implementation used a
   1,000-record pilot; only the §4 summary table was updated.
6. **`pilot_1000_family_history_validation.json`** comes from a schema
   v0.8 run (before AQI). Records in that pilot folder would now fail v0.9
   structural validation on version alone.
7. **The v0.8 frozen dataset (`outputs/m8/`) and its reports** describe the
   previous release. They are not included, and their figures (e.g. 2,283
   impossible lipid panels) should not be read as v0.9 results.

## 5. Information that could not be verified

- **Cause of the 118-minute generation time.** Evidence available:
  - Supporting the in-memory hypothesis: `generate_population.py` line 31
    keeps all 100,000 `Patient` objects in memory until generation ends,
    and only then writes files. This is a fact about the code, not proof
    of the cause.
  - Against "new code is slow": per-record build cost was profiled at
    ≈12 ms (unsaved, see §3), projecting ≈20 min of compute; the M5 run of
    the same script took 23.3 min (`PROJECT_STATE.md`, M5).
  - Untested alternatives: Python garbage-collection cost growing with
    live objects, Windows file-write/antivirus overhead for 100,000 files,
    and other machine load. **None has been measured; the cause is
    unconfirmed.**
- **External figures (LASI, CARRS, CPCB/CAAQM Delhi 204)** are cited with
  sources in the config and decisions. The source documents themselves
  are not part of the repository and were not re-checked for this package.
- **The directory checksum was not recomputed for this package.**
  Unchanged state was confirmed by file count, total bytes and newest
  modification time before and after packaging (see §6).

## 6. Package integrity checks

Recorded at packaging time:
- SHA-256 of every original file matched before and after copying.
- Dataset folder: 100,000 files, 810,416,240 bytes, unchanged.
- Manifest unchanged.

The final verification results are reported alongside this package.
