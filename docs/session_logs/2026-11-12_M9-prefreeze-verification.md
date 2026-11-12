# 2026-11-12 — M9: pre-ECG steps 1-4 (verification)

## Request
Do steps 1-4 before ECG: family-history/AQI sign-off, implement both, apply
D019 lipid fix, regenerate + validate + freeze 100K. Step 5 (ECG weight
licence) to be discussed afterwards.

## Finding
All four were already done on 2026-11-10 (that session wrote no session log).
The previous session's status answer was wrong: it relied on a stale
"Last Updated" block in PROJECT_STATE.md.
- Sign-off: D020 (family history) and D021 (AQI) are recorded as human-approved.
- Implemented: `generation/indian_population.py`, schema v0.9, validators, tests.
- D019: in the generator, active in v0.9 (0 infeasible lipid panels).
- Frozen: `outputs/m9/100k_patients_v09/`, manifest `outputs/m9/dataset_manifest.json`,
  100,000/100,000 valid, 0 errors, 14,206 known warnings (LDL clip floor 7,740;
  empty PTB-XL superclass 6,466).

No regeneration was run: it would repeat a validated 118-min run for no gain.

## Verification today
- 100,000 record files present on disk.
- The Python env had no deps. Installed pandas, numpy, scipy, wfdb, PyYAML,
  pytest and CPU torch into Python 3.14. Added scipy to requirements.txt
  (it was used but not listed).
- `pytest tests`: 174 passed.
- `validation/pilot_50_records/tests`: 5 fail. That pilot is still v0.8
  (schema mismatch, pre-D019 seed replay). It is stale, not a dataset defect.

## Open / next
- Optional: regenerate or retire the v0.8 pilot_50 package.
- Known perf issue: the generator holds all N records in memory (generate_population.py:31).
- Next: ECG discussion (step 5: SSSD-ECG weight licence, M6 model choice).
