"""Regenerate review sample records from scratch with the REAL build_patient()
-- -jatin, 2026-11-12 (v0.13, D027).

Unlike `rederive_review_samples.py` (an in-place upgrade that requires the RNG
stream to be unchanged), this rebuilds every field. Use it when a generator
change alters sampled values (D027 changes hypertension/diabetes, and so
treatment, BP, HbA1c, family history, onset and the LAI tier).

`--reuse-ecg-from DIR`: for machines without PTB-XL CSVs or a working pandas.
The ECG pick depends only on the seed (`pick_ecg_id(seed)`), never on patient
attributes, so the ECG metadata already stored in DIR's records for the same
patient IDs is exactly what PTB-XL would return. The flag swaps ONLY
`ingestion.ptbxl_source` for a lookup into those stored records; everything
else is the real pipeline. Without the flag, the real PTB-XL source is used.

Usage:
    python integration/regenerate_review_samples.py review_samples_v012 review_samples_v013 --reuse-ecg-from review_samples_v012
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _install_ecg_lookup(ecg_dir: Path, base_seed: int) -> None:
    """Replace ingestion.ptbxl_source with a lookup of stored ECG metadata."""
    by_seed, by_id = {}, {}
    for path in ecg_dir.glob("*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        seq = int(rec["patient_id"].split("_")[1])
        ecg = rec["ecg"]
        by_seed[base_seed + seq] = ecg["ecg_id"]
        by_id[ecg["ecg_id"]] = ecg

    module = types.ModuleType("ingestion.ptbxl_source")

    def pick_ecg_id(ptbxl_csv, folds, seed):  # noqa: ARG001 -- same signature as the real one
        if seed not in by_seed:
            raise KeyError(f"no stored ECG for seed {seed}; run with real PTB-XL instead")
        return by_seed[seed]

    def load_ptbxl_record(ecg_id, ptbxl_csv=None, scp_csv=None, threshold=50.0):  # noqa: ARG001
        e = by_id[ecg_id]
        return {
            "ecg_id": e["ecg_id"],
            "superclasses": e["superclasses"],
            "strat_fold": e["strat_fold"],
            "filename_lr": e["filename"],
            "sampling_hz": e["sampling_hz"],
            "signal_shape": e["signal_shape"],
        }

    module.pick_ecg_id = pick_ecg_id
    module.load_ptbxl_record = load_ptbxl_record
    import ingestion  # the real package

    sys.modules["ingestion.ptbxl_source"] = module
    ingestion.ptbxl_source = module


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("in_dir", help="directory whose *.json patient IDs (and file names) to regenerate")
    parser.add_argument("out_dir")
    parser.add_argument("--reuse-ecg-from", default=None)
    args = parser.parse_args()

    import yaml

    base_cfg = yaml.safe_load((_REPO_ROOT / "configs" / "base.yaml").read_text(encoding="utf-8"))
    if args.reuse_ecg_from:
        _install_ecg_lookup(Path(args.reuse_ecg_from), base_cfg["random_seed"])

    from generation.indian_population import load_config as load_indian_config
    from integration.build_patient import build_patient, load_config
    from validation.clinical_consistency import validate_clinical_consistency

    config = load_config(_REPO_ROOT / "configs" / "base.yaml")
    indian_config = load_indian_config()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for path in sorted(Path(args.in_dir).glob("*.json")):
        old = json.loads(path.read_text(encoding="utf-8"))
        seq = int(old["patient_id"].split("_")[1])
        patient = build_patient(seq, config, indian_config)
        clinical = validate_clinical_consistency(patient, indian_config)
        record = patient.to_dict()
        record["validation"]["clinical_consistency"] = {
            "valid": clinical.valid, "errors": clinical.errors, "warnings": clinical.warnings,
        }
        (out_dir / path.name).write_text(json.dumps(record, indent=2), encoding="utf-8")
        lai = next(i for i in record["lipid_interpretations"] if i["definition"] == "LAI_2020")
        summary.append({
            "file": path.name,
            "age": record["demographics"]["age"],
            "sex": record["demographics"]["sex"],
            "hypertension": f'{old["risk_factors"]["hypertension"]} -> {record["risk_factors"]["hypertension"]}',
            "diabetes": f'{old["risk_factors"]["diabetes"]} -> {record["risk_factors"]["diabetes"]}',
            "medications": [m["drug_class"] for m in record["medications"]],
            "bp": f'{record["blood_pressure"]["systolic_mm_hg"]}/{record["blood_pressure"]["diastolic_mm_hg"]}',
            "hba1c": record["labs"][0]["value"],
            "lai_tier": lai["risk_category"],
            "ecg_id_unchanged": record["ecg"] == old["ecg"],
            "structurally_valid": record["validation"]["validated"],
            "clinically_consistent": clinical.valid,
            "warnings": len(clinical.warnings),
        })
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
