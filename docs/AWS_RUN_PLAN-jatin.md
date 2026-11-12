# AWS run plan: pilot rebuild, 100K regeneration (current schema, v0.13), later ECG -jatin

**Author:** -jatin, 2026-11-12. **Status:** plan only. Nothing has been
launched, and nothing below runs without the team's go-ahead (Claude.md §14/§15).

## Why AWS
The human decision (2026-11-12) is to run the heavy work on AWS. Jatin's laptop
cannot run it: no PTB-XL CSVs, no GAN checkpoints or torch, and Windows Smart App
Control blocks pandas. This plan keeps the cloud footprint to one short-lived CPU
instance for phase 1. A GPU is only considered for phase 2 (ECG), once the ECG
integration code exists.

## Phase 1: CPU only (do now)

| Item | Choice / estimate |
|---|---|
| Instance | 1 × `c7i.2xlarge` (8 vCPU, 16 GB), Ubuntu 24.04, on-demand |
| Price | ~US$0.36/h (us-east-1 list price; confirm for your region, e.g. ap-south-1) |
| Runtime | ~3 h total: setup 20 min, tests 10 min, pilot 1 min, progressive scale 10→10K ~15 min, 100K ~20–120 min (v0.9 took 118 min wall-clock vs ~12 ms/record profiled; the cause is suspected, not confirmed) |
| Storage | 50 GB gp3 EBS (~US$4/month, prorated: under $1 for a day). The 100K JSON output is ~1 GB. |
| Transfer | Into AWS is free. Pulling ~1 GB of outputs back is within AWS's free monthly egress allowance. |
| **Estimated cost** | **under US$5** if the instance is stopped/terminated right after |
| GPU | None |

### Steps
1. Launch the instance. Clone the private repo using your own GitHub credentials
   (deploy key or PAT kept on the instance, never committed).
2. Environment:
   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install pandas numpy wfdb PyYAML pytest scipy
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   ```
3. PTB-XL CSVs (only these two files are needed for patient generation, about 7 MB, CC BY 4.0):
   ```bash
   mkdir -p syngen/SynGen/SynGen/dataset
   wget -P syngen/SynGen/SynGen/dataset https://physionet.org/files/ptb-xl/1.0.1/ptbxl_database.csv https://physionet.org/files/ptb-xl/1.0.1/scp_statements.csv
   ```
   Or copy them from the teammate's SynGen archive.
4. Full test suite. **This verifies D023, D024 and D027 against real PTB-XL (locally they ran only with a stubbed ECG source).**
   ```bash
   python -m pytest tests -q
   ```
5. Pilot rebuild at v0.12 (decision Q9):
   ```bash
   python validation/pilot_50_records/rebuild_v012.py
   python -m pytest validation/pilot_50_records/tests/test_pilot_v012.py -q
   ```
6. Progressive scaling (Claude.md §27), validating each level before the next:
   ```bash
   for n in 10 100 1000 10000; do
     python integration/generate_population.py $n --out-dir outputs/v013/${n}_patients
     python integration/validate_clinical_population.py outputs/v013/${n}_patients --stats --json-out outputs/v013/validation_${n}.json
   done
   ```
7. **100K: only after step 6 passes and the team approves (§15):**
   ```bash
   python integration/generate_population.py 100000 --out-dir outputs/v013/100k_patients
   python integration/validate_clinical_population.py outputs/v013/100k_patients --stats --json-out outputs/v013/validation_100k.json
   python integration/freeze_dataset_manifest.py --output-dir outputs/v013/100k_patients --validation-report outputs/v013/validation_100k.json --schema-version 0.13 --dataset-name synthetic_indian_cvd_population --dataset-version v0.13 --out outputs/v013/dataset_manifest.json
   ```
8. Copy back only the reports, manifest and metrics. The 100K records stay out of
   git, and optionally go to a private S3 bucket. Commit the pilot output, reports
   and summaries.
9. **Stop or terminate the instance.**

### Watch-outs
- At 100K, hyperlipidemia prevalence 80.9% vs the 81.2% target may fail the exact
  binomial test (z ≈ 2.4). This is a known calibration note (D023), not a defect.
- The old v0.8 pilot tests (`test_pilot_50_records.py`) will still fail. They
  describe the superseded migration and should be retired once step 5 passes.

## Phase 2: ECG (later, after the M7 integration code exists)
- Model: the inherited per-class GAN (D018). Upload `generator_{CD,HYP,MI,NORM,STTC}.pt`
  to the instance or a private S3 bucket.
- Output size: 100K × 12 leads × 1000 samples × float32 ≈ **4.8 GB** (2.4 GB as float16).
- Compute: a small GAN generator. CPU on the same instance may be enough; if not,
  one `g4dn.xlarge` (T4, ~US$0.53/h us-east-1) for an estimated 1–2 h.
  **Estimate before launching** (§14), after timing a 1K run.
- Same progressive scaling: 10 → 100 → 1K → 10K → 100K.

## Not in scope
SaaS / multi-tenant deployment, managed databases, or anything always-on.
Those belong to the later service stage (teammate's steps 12–13).
