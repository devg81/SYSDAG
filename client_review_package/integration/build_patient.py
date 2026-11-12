"""Assemble one structurally valid synthetic patient record (Schema v0.7).

ECG metadata is reused from a real PTB-XL record (`docs/DECISIONS.md` D003,
unchanged since M1). Demographics (age/sex/state/urban_rural) and risk
factors (BMI/smoking/hypertension/diabetes/hyperlipidemia) are generated
from Indian population evidence via `generation.indian_population`
(M2C, superseding M1's placeholder — `docs/DECISIONS.md` D004/D006).
M4B adds lipid_panel/lipid_interpretations (raw values primary, derived
interpretations computed not sampled, D011) and labs.HbA1c (conditional on
the diabetes label). M4D adds diagnoses (1:1 promotion of hypertension/
diabetes risk_factors flags) and medical_history (chronic_condition
entries referencing those diagnoses), D015. M4E adds medications
(antihypertensive/antidiabetic only, NNMS treatment-rate gated, drug_class
only -- never a specific drug name), D016. Family history, encounters, and
echo remain unset — out of current scope (`docs/PROJECT_STATE.md`).
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from schemas.patient_schema import (  # noqa: E402
    SCHEMA_VERSION,
    BloodPressure,
    Demographics,
    Diagnosis,
    ECGRecord,
    Encounter,
    Lab,
    LipidInterpretation,
    LipidPanel,
    MedicalHistoryEntry,
    Medication,
    Patient,
    Provenance,
    RiskFactors,
    TimelineEvent,
    ValidationMetadata,
)
from integration.patient_id import generate_patient_id  # noqa: E402
from ingestion.ptbxl_source import load_ptbxl_record, pick_ecg_id  # noqa: E402
from validation.structural import validate_patient  # noqa: E402
from generation.indian_population import (  # noqa: E402
    generate_indian_attributes,
    load_config as load_indian_config,
    valid_states,
)
from generation.clinical_history import (  # noqa: E402
    derive_diagnoses,
    derive_encounters,
    derive_medications,
    derive_medical_history,
    derive_timeline,
)
import numpy as np  # noqa: E402


def load_config(config_path: Path) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_patient(
    sequence: int,
    config: dict[str, Any],
    indian_config: Optional[dict[str, Any]] = None,
) -> Patient:
    """Build and structurally validate one synthetic patient.

    Deterministic given (sequence, config["random_seed"],
    indian_config["random_seed"]) — CLAUDE.md §9 (reproducibility).
    `indian_config` defaults to `configs/indian_population.yaml` if not
    supplied.
    """
    if indian_config is None:
        indian_config = load_indian_config()

    ptbxl_csv = str(_REPO_ROOT / config["ptbxl_csv"])
    scp_csv = str(_REPO_ROOT / config["scp_csv"])
    seed = config["random_seed"] + sequence

    ecg_id = pick_ecg_id(ptbxl_csv, config["training_folds"], seed)
    record = load_ptbxl_record(
        ecg_id, ptbxl_csv, scp_csv, config.get("scp_threshold", 50.0)
    )

    patient_id = generate_patient_id(sequence)

    indian_seed = indian_config["random_seed"] + sequence
    rng = np.random.default_rng(indian_seed)
    attrs = generate_indian_attributes(rng, indian_config)

    demographics = Demographics(
        age=attrs["demographics"]["age"],
        sex=attrs["demographics"]["sex"],
        # Still None after M8's evidence pass: no national mean+SD of
        # Indian adult height by sex exists in any source located across
        # 6 attempts. weight_kg is DERIVED from BMI x height, so it
        # follows height. See generation.indian_population.
        # sample_height_cm / derive_weight_kg.
        height_cm=attrs["demographics"]["height_cm"],
        weight_kg=attrs["demographics"]["weight_kg"],
        state=attrs["demographics"]["state"],
        urban_rural=attrs["demographics"]["urban_rural"],
    )
    risk_factors = RiskFactors(
        bmi=attrs["risk_factors"]["bmi"],
        smoking_status=attrs["risk_factors"]["smoking_status"],
        hypertension=attrs["risk_factors"]["hypertension"],
        diabetes=attrs["risk_factors"]["diabetes"],
        hyperlipidemia=attrs["risk_factors"]["hyperlipidemia"],
    )

    # M4B — docs/DECISIONS.md D011: raw lipid values primary, interpretations
    # computed (never sampled); HbA1c conditional on the diabetes label above.
    lv = attrs["lipid_panel"]
    lipid_panel = LipidPanel(
        ldl_mg_dl=lv["ldl_mg_dl"],
        hdl_mg_dl=lv["hdl_mg_dl"],
        triglycerides_mg_dl=lv["triglycerides_mg_dl"],
        total_cholesterol_mg_dl=lv["total_cholesterol_mg_dl"],
    )
    lipid_interpretations = [
        LipidInterpretation(
            definition=interp["definition"],
            dyslipidemia=interp["dyslipidemia"],
            components_abnormal=interp["components_abnormal"],
            source_citation=interp["source_citation"],
        )
        for interp in attrs["lipid_interpretations"]
    ]
    measured_date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    labs = None
    if attrs["hba1c"] is not None:
        labs = [Lab(analyte="HbA1c", unit="%", value=attrs["hba1c"], measured_at=measured_date)]

    # M4D — docs/DECISIONS.md D015: diagnoses are a 1:1 promotion of
    # already-generated risk_factors flags; medical_history REFERENCES
    # those diagnoses rather than re-deriving them.
    diag_dicts = derive_diagnoses(attrs["risk_factors"], patient_id)
    diagnoses = [Diagnosis(**dx) for dx in diag_dicts]
    medical_history = [
        MedicalHistoryEntry(**entry) for entry in derive_medical_history(diag_dicts)
    ]

    # M4E — docs/DECISIONS.md D016: treatment status already sampled
    # (attrs["medication_treatment"]) from an evidence-backed treatment
    # rate; medications REFERENCE diagnoses, never resample treatment.
    medications = [
        Medication(**med)
        for med in derive_medications(diag_dicts, attrs["medication_treatment"], patient_id)
    ]

    # M8 — blood pressure, conditional on the hypertension label and on
    # whether an antihypertensive was generated above (the label's own
    # published definition includes medication use). Never used to
    # re-derive hypertension.
    bp_values = attrs["blood_pressure"]
    blood_pressure = BloodPressure(
        systolic_mm_hg=bp_values["systolic_mm_hg"],
        diastolic_mm_hg=bp_values["diastolic_mm_hg"],
        measured_at=measured_date,
        age_band_source=bp_values["age_band_source"],
        extrapolated_beyond_source_age_range=bp_values[
            "extrapolated_beyond_source_age_range"
        ],
    )

    # M8 — one structural container for the single synthetic measurement
    # cross-section (NOT a healthcare visit), and a timeline that indexes
    # it by id rather than restating it.
    encounter_dicts = derive_encounters(
        patient_id,
        assessment_date=measured_date,
        has_blood_pressure=blood_pressure is not None,
        has_lipid_panel=lipid_panel is not None,
        lab_analytes=[lab.analyte for lab in (labs or [])],
    )
    encounters = [Encounter(**enc) for enc in encounter_dicts]

    ecg = ECGRecord(
        source="PTB-XL",
        ecg_id=record["ecg_id"],
        superclasses=record["superclasses"],
        strat_fold=record["strat_fold"],
        sampling_hz=record["sampling_hz"],
        signal_shape=record["signal_shape"],
        filename=record["filename_lr"],
        signal_available=False,
    )

    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    provenance = Provenance(
        schema_version=SCHEMA_VERSION,
        generated_at=generated_at,
        generator=(
            "integration/build_patient.py (M2C Indian-conditioned "
            "generation, indian_random_seed="
            f"{indian_seed}); demographics.age/state/urban_rural and "
            "risk_factors.* sampled from configs/indian_population.yaml "
            "(docs/DECISIONS.md D006); demographics.sex sampled from its "
            "Census-2011-derived national marginal; height_cm/weight_kg "
            "not modeled (out of M2C scope); ECG is metadata-only, no "
            "waveform attached (D003); family_history intentionally left "
            "unpopulated — no Indian evidence source (D004); lipid_panel "
            "TC/TG/HDL sampled (category-then-uniform, INDIAB-17), LDL "
            "DERIVED via Friedewald (never independently sampled, D011); "
            "lipid_interpretations COMPUTED per definition, never sampled "
            "(D011); labs.HbA1c generated only for non-diabetic patients, "
            "age+sex-conditioned (ICMR-INDIAB-12), conditional on the "
            "diabetes label above, never the reverse (M4-0B) — see "
            "docs/M4B_GENERATION_DESIGN.md; diagnoses are a 1:1 promotion "
            "of the hypertension/diabetes risk_factors flags, never "
            "independently sampled, diagnosed_date left null (no "
            "evidence-backed per-patient onset distribution exists); "
            "hyperlipidemia diagnosis deliberately deferred (D015); "
            "medical_history chronic_condition entries reference those "
            "diagnoses, not re-derived — see "
            "docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md; medications generated "
            "only for hypertension/diabetes diagnoses, gated on ICMR-NNMS "
            "national treatment-rate Bernoulli draws (14.5%/36.1%), "
            "drug_class only (antihypertensive/antidiabetic), never a "
            "specific drug name; statin/antiplatelet medications not "
            "generated (no population treatment-rate evidence); "
            "start_date/stop_date left null (no per-patient initiation-"
            "date evidence exists), current_status always \"active\" "
            "(D016) — see docs/M4E_MEDICATION_DESIGN.md; "
            "blood_pressure (M8) SBP/DBP drawn from NFHS-5 "
            "age-band×sex truncated normals (PLOS ONE 2025, "
            "doi:10.1371/journal.pone.0332226); per-band SDs DERIVED "
            "from that paper's published mean/95%-CI/n and "
            "cross-validated against the independently published "
            "NFHS-5 male overall SDs (PMC11068163) to within 0.8%; "
            "truncation region set by the hypertension label's OWN "
            "published definition (SBP≥140 and/or DBP≥90 and/or on "
            "antihypertensive), so BP is conditional on that "
            "already-primary label and NEVER used to re-derive it — a "
            "treated hypertensive's BP is left UNCONSTRAINED rather "
            "than forced high; ages above source coverage (men>54, "
            "women>49) hold the oldest band constant, flagged per "
            "record via blood_pressure.extrapolated_beyond_source_"
            "age_range; SBP/DBP correlation not modeled (no Indian "
            "source) — see configs/indian_population.yaml "
            "risk_factors.blood_pressure for all limitations; "
            "encounters contain ONE synthetic_baseline_assessment, a "
            "structural container for this record's single measurement "
            "cross-section — NOT an observed healthcare contact, no "
            "visit/admission/follow-up is generated (no Indian "
            "utilization evidence); clinical_timeline indexes that "
            "encounter by reference_id and emits no diagnosis-onset, "
            "medication-start or follow-up event; height_cm/weight_kg "
            "STILL null — no national mean+SD of Indian adult height "
            "by sex located in 6 research attempts (M4-0 x3, M8 x3), "
            "so BMI remains the evidence-primary anthropometric and "
            "weight stays derivable-but-underived; family_history still "
            "null — its scope is an open human decision, not an "
            "evidence gap (docs/M4F_FINAL_CLINICAL_AUDIT.md)"
        ),
        random_seed=seed,
        source_datasets=[
            "PTB-XL 1.0.1",
            "Census of India 2011",
            "ICMR-NNMS 2017-18",
            "ICMR-INDIAB-17 (2023)",
            "ICMR-INDIAB-25 (2026)",
            "ICMR-INDIAB-12 (2022)",
            "NFHS-5 2019-21 (blood pressure, via PLOS ONE 2025 doi:10.1371/journal.pone.0332226)",
        ],
    )

    timeline = [
        TimelineEvent(**event)
        for event in derive_timeline(generated_at[:10], encounter_dicts)
    ]

    patient = Patient(
        patient_id=patient_id,
        demographics=demographics,
        provenance=provenance,
        risk_factors=risk_factors,
        labs=labs,
        blood_pressure=blood_pressure,
        encounters=encounters,
        lipid_panel=lipid_panel,
        lipid_interpretations=lipid_interpretations,
        diagnoses=diagnoses,
        medical_history=medical_history,
        medications=medications,
        ecg=ecg,
        clinical_timeline=timeline,
        validation=ValidationMetadata(),
    )

    errors = validate_patient(patient, valid_states=valid_states(indian_config))
    patient.validation.validated = len(errors) == 0
    patient.validation.validation_version = "structural-0.2"
    patient.validation.errors = errors
    return patient


if __name__ == "__main__":
    config = load_config(_REPO_ROOT / "configs" / "base.yaml")
    patient = build_patient(1, config)

    out_dir = _REPO_ROOT / "outputs" / "test"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{patient.patient_id}.json"
    out_path.write_text(json.dumps(patient.to_dict(), indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Validated: {patient.validation.validated}")
    if patient.validation.errors:
        print("Errors:", patient.validation.errors)
