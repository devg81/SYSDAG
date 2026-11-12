# Pilot: 50 Records at Schema v0.8

A traceable 50-record validation batch, upgraded from schema v0.7 to
v0.8, intended for external review and as the proving ground for
applying the same migration to the full 100,000-record dataset.

**Verdict: ready to send with three disclosed limitations.** Read
[`reports/validation_report.md`](reports/validation_report.md) §7 first.

---

## What's here

```
validation/pilot_50_records/
├── README.md                          this file
├── run_pilot.py                       driver: select 50, back up, migrate, measure
├── input/
│   ├── source_manifest.json           ids, selection method, config, SHA-256 of every original
│   └── original_records/              verified copies of the 50 untouched v0.7 records
├── output/
│   └── patient_records_50.json        THE DELIVERABLE — exactly 50 migrated records
├── reports/
│   ├── validation_report.md           gates, results, unresolved issues, recommendation
│   ├── field_gap_assessment.md        every field: status, evidence, missingness + reason
│   ├── evidence_and_assumptions.md    every new field's source, tier and limitations
│   ├── changes_summary.md             what changed in schema / generator / validation
│   ├── validation_metrics.json        machine-readable batch metrics
│   └── full_dataset_dryrun_audit.json 100,000-record dry-run result
└── tests/
    └── test_pilot_50_records.py       37 batch gates (structural → reusability)
```

The reusable implementation deliberately does **not** live here — see
[Where the code lives](#where-the-code-lives).

---

## What the migration adds

| Field | Change |
|---|---|
| `blood_pressure` | **NEW** — SBP/DBP in whole mmHg, conditional on the already-primary hypertension label |
| `encounters` | **NEW** — one `synthetic_baseline_assessment`, a declared structural container, **not** a healthcare visit |
| `clinical_timeline` | **EXTENDED** — `TimelineEvent` gained `reference_id`; a second event indexes the encounter |
| `demographics.height_cm` / `weight_kg` | explicit `null` — still not generated, no evidence |
| `provenance`, `validation` | version bumped, generator string appended to, checks re-run |

Everything else is byte-identical, and that is **enforced in code**
(`_UNCHANGED_FIELDS` in the migration): a difference blocks the write.

Height/weight, family history and echo remain unpopulated **on purpose**.
`reports/evidence_and_assumptions.md` gives the reason and the concrete
step that would unblock each one.

---

## How the 50 were chosen

```python
numpy.random.default_rng(8).choice(100000, size=50, replace=False)
# → PAT_%06d of index+1, sorted
```

Uniform without replacement over all 100,000 records. **Not purposive,
not stratified, not hand-picked** — so rare cohorts appear only as often
as chance allows (this batch has 3 treated hypertensives and 4
diabetics). That is a deliberate trade: a hand-picked batch would look
more complete while telling a reviewer nothing about the population.
Claims that need statistical weight are asserted over hundreds of draws
in `tests/test_m8_bp_encounters.py` instead.

The seed is fixed, so the same 50 patients are selected on every run.

---

## Reproducing it

Requires the Anaconda interpreter (`docs/DECISIONS.md` D002).

```bash
# Audit without writing anything (always safe)
python validation/pilot_50_records/run_pilot.py --dry-run

# Rebuild the batch, manifest and metrics
python validation/pilot_50_records/run_pilot.py

# Batch gates
python -m pytest validation/pilot_50_records/tests -q      # 37 passed

# Full project suite (includes 38 new M8 unit tests)
python -m pytest tests/ -q                                  # 142 passed
```

`run_pilot.py` is deterministic: same seed, same config, same 50 records,
byte-identical output.

### Per-record reproducibility

Each record's blood pressure comes from **replaying**
`generation.indian_population.generate_indian_attributes()` from the seed
stored in that record's own `provenance.generator`
(`indian_random_seed=N`) — not from a new random stream. Because BP is
drawn last in the generator's order, every pre-existing field comes off
the replay identically, and the migration **verifies** that before
accepting the new field.

Two consequences:

1. `migrate_record(...)` and a fresh `build_patient(sequence)` produce
   the same blood pressure for the same patient. One source of truth.
2. The replay doubles as a provenance audit. A stored value that
   disagrees with its own seed is reported as an error, not quietly
   migrated. **This passed for all 100,000 records.**

---

## Originals are untouched

- The source dataset at `outputs/m5/100k_patients/` was opened
  **read-only**. It still holds 100,000 records, still at schema v0.7.
- Verified copies of the 50 selected records are in
  `input/original_records/`, with a SHA-256 per file in
  `input/source_manifest.json`.
- Two tests enforce this on every run:
  `test_originals_are_preserved_and_match_their_recorded_hashes` and
  `test_originals_are_still_schema_v07`.

---

## Where the code lives

Reusable logic is in the project's existing modules, not in this folder:

| Concern | Module |
|---|---|
| **Migration (entry point)** | `integration/migrate_v07_to_v08.py` |
| BP sampling, height hook, weight derivation | `generation/indian_population.py` |
| Encounter + timeline derivation | `generation/clinical_history.py` |
| Schema (v0.8 dataclasses, vocabularies) | `schemas/patient_schema.py` |
| Structural checks | `validation/structural.py` |
| Cross-field checks | `validation/clinical_consistency.py` |
| Evidence + every parameter's provenance | `configs/indian_population.yaml` |
| Fresh generation at v0.8 | `integration/build_patient.py` |

`run_pilot.py` only decides *which* 50 records to use and collects the
numbers the reports quote. Nothing in this folder is needed to migrate
the remaining 99,950 records.

---

## Applying it to the full dataset

**Not started, and it should not be until the lipid issue in
`reports/validation_report.md` §6.1 is decided.** Dry-run evidence over
all 100,000 records is already in
`reports/full_dataset_dryrun_audit.json`: 100,000/100,000 clean, zero
failures, 68.3 s (0.683 ms/record).

```bash
# Audit first — writes nothing
python integration/migrate_v07_to_v08.py \
    --input-dir outputs/m5/100k_patients \
    --output-dir outputs/m8/100k_patients_v08 --dry-run

# Then, once approved
python integration/migrate_v07_to_v08.py \
    --input-dir outputs/m5/100k_patients \
    --output-dir outputs/m8/100k_patients_v08 \
    --summary-out outputs/m8/migration_summary.json
```

Writes to a **new** directory; the v0.7 dataset is never modified in
place. The migration is idempotent, so a re-run after a config change is
safe.

---

## Git note — needs your decision

`.gitignore` excludes `outputs/` (per `CLAUDE.md` §36: do not commit
generated datasets) but **not** `validation/`, so this batch and the
backed-up originals would be committed.

**I have not changed the ignore rules and have not committed anything.**
Three options, your call:

1. Add `validation/pilot_50_records/{input/original_records,output}/` to
   `.gitignore` — consistent with the existing policy; the manifest's
   hashes still make the batch reproducible from committed code.
2. Commit the batch deliberately as a reviewed artefact (it is ~50
   records, not a dataset).
3. Move the outputs under `outputs/` and keep only code and reports here.

No credentials, API keys or secrets are in this folder.
