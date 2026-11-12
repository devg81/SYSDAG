"""Re-derive review sample records under the current generator (D023, v0.11)
WITHOUT PTB-XL or pandas.

Why this exists: `build_patient()` needs the PTB-XL CSVs (for ECG metadata)
and pandas. Neither is available on every development machine. D023 only
changes how `risk_factors.hyperlipidemia` is produced, and the D023
placeholder draw keeps the RNG stream aligned. So a stored v0.10 record can
be upgraded exactly by:

1. re-running `generate_indian_attributes()` with the record's own seed,
2. ASSERTING that every generated field the record already holds is
   identical (demographics, risk-factor flags, lipids, interpretations,
   HbA1c, treatment, BP, family history, AQI, onset), so the RNG stream is
   proven unchanged,
3. replacing only `risk_factors.hyperlipidemia`, `schema_version` and the
   provenance text, and
4. re-running the real structural and clinical-consistency validators.

ECG metadata, IDs, diagnoses, medications and the timeline are carried over
unchanged (they do not depend on the hyperlipidemia flag).

Usage:
    python integration/rederive_review_samples.py review_samples_v010 review_samples_v011
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import (  # noqa: E402
    generate_indian_attributes,
    load_config as load_indian_config,
    valid_states,
)
from integration.migrate_v07_to_v08 import _dict_to_patient  # noqa: E402
from schemas.patient_schema import SCHEMA_VERSION  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from validation.structural import validate_patient  # noqa: E402

_OLD_PROVENANCE = (
    "risk_factors.* sampled from configs/indian_population.yaml "
    "(docs/DECISIONS.md D006); "
)
_NEW_PROVENANCE = (
    "risk_factors.* sampled from configs/indian_population.yaml "
    "(docs/DECISIONS.md D006), except risk_factors.hyperlipidemia, "
    "which is DERIVED (v0.11, D023) as the NCEP_ATP_III "
    "dyslipidemia verdict of this patient's own lipid_panel, never "
    "sampled; "
)


def _expect(field: str, stored: Any, regenerated: Any, mismatches: list[str]) -> None:
    if stored != regenerated:
        mismatches.append(f"{field}: stored={stored!r} regenerated={regenerated!r}")


def check_alignment(record: dict[str, Any], attrs: dict[str, Any]) -> list[str]:
    """Every field D023 must NOT change, compared stored vs regenerated."""
    m: list[str] = []
    d = record["demographics"]
    for k in ("age", "sex", "state", "urban_rural", "height_cm", "weight_kg"):
        _expect(f"demographics.{k}", d[k], attrs["demographics"][k], m)
    rf = record["risk_factors"]
    for k in ("bmi", "smoking_status", "hypertension", "diabetes"):
        _expect(f"risk_factors.{k}", rf[k], attrs["risk_factors"][k], m)
    for k, v in attrs["lipid_panel"].items():
        _expect(f"lipid_panel.{k}", record["lipid_panel"][k], v, m)
    _expect("lipid_interpretations", record["lipid_interpretations"], attrs["lipid_interpretations"], m)
    lab = record["labs"][0]
    for k in ("value", "derivation", "confidence"):
        _expect(f"labs[HbA1c].{k}", lab[k], attrs["hba1c"][k], m)
    classes = {med["drug_class"] for med in record["medications"]}
    _expect("medications.antihypertensive", "antihypertensive" in classes,
            attrs["medication_treatment"].get("hypertension", False), m)
    _expect("medications.antidiabetic", "antidiabetic" in classes,
            attrs["medication_treatment"].get("diabetes", False), m)
    for k, v in attrs["blood_pressure"].items():
        _expect(f"blood_pressure.{k}", record["blood_pressure"][k], v, m)
    _expect("family_history", record["family_history"], attrs["family_history"], m)
    for k, v in attrs["air_quality"].items():
        _expect(f"air_quality.{k}", record["air_quality"][k], v, m)
    onset_by_code = {dx["code"]: dx.get("age_at_onset_years") for dx in record["diagnoses"]}
    for code, o in attrs["onset"].items():
        _expect(f"diagnoses[{code}].age_at_onset_years", onset_by_code.get(code), o["age_at_onset_years"], m)
    return m


def rederive(record: dict[str, Any], indian_config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    seq = int(record["patient_id"].split("_")[1])
    rng = np.random.default_rng(indian_config["random_seed"] + seq)
    attrs = generate_indian_attributes(rng, indian_config)

    mismatches = check_alignment(record, attrs)
    if mismatches:
        raise RuntimeError(f"{record['patient_id']}: RNG stream not aligned with stored record: {mismatches}")

    out = copy.deepcopy(record)
    old_flag = out["risk_factors"]["hyperlipidemia"]
    out["risk_factors"]["hyperlipidemia"] = attrs["risk_factors"]["hyperlipidemia"]

    prov = out["provenance"]
    if _OLD_PROVENANCE not in prov["generator"]:
        raise RuntimeError(f"{record['patient_id']}: provenance text to replace not found")
    prov["generator"] = prov["generator"].replace(_OLD_PROVENANCE, _NEW_PROVENANCE)
    prov["schema_version"] = SCHEMA_VERSION
    new_generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if new_generated_at[:10] != prov["generated_at"][:10]:
        # measured_at / timeline dates are derived from generated_at's date;
        # keep the original so they stay consistent.
        new_generated_at = prov["generated_at"]
    prov["generated_at"] = new_generated_at

    out["validation"].pop("clinical_consistency", None)
    patient = _dict_to_patient(out)
    errors = validate_patient(patient, valid_states=valid_states(indian_config))
    clinical = validate_clinical_consistency(patient, indian_config)
    out["validation"] = {
        "validated": not errors,
        "validation_version": "structural-0.2",
        "errors": errors,
        "clinical_consistency": {
            "valid": clinical.valid,
            "errors": clinical.errors,
            "warnings": clinical.warnings,
        },
    }
    change = {
        "patient_id": record["patient_id"],
        "hyperlipidemia_v010": old_flag,
        "hyperlipidemia_v011": out["risk_factors"]["hyperlipidemia"],
        "ncep_dyslipidemia": next(
            i["dyslipidemia"] for i in out["lipid_interpretations"] if i["definition"] == "NCEP_ATP_III"
        ),
        "structurally_valid": not errors,
        "clinically_consistent": clinical.valid,
        "clinical_warnings": len(clinical.warnings),
        "checks_include_d023": "hyperlipidemia_derived_from_lipid_interpretations" in clinical.checks_performed,
    }
    return out, change


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("in_dir")
    parser.add_argument("out_dir")
    args = parser.parse_args()

    indian_config = load_indian_config()
    in_dir, out_dir = Path(args.in_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    changes = []
    for path in sorted(in_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        out, change = rederive(record, indian_config)
        (out_dir / path.name).write_text(json.dumps(out, indent=2), encoding="utf-8")
        changes.append({"file": path.name, **change})
    print(json.dumps(changes, indent=2))
