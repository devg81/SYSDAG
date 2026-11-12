"""Structural validation for patient records (Schema v0.2).

Generator-independent by design (`CLAUDE.md` §4) — only checks schema
compliance, not clinical plausibility.
"""

from __future__ import annotations

from typing import Optional

from schemas.patient_schema import (
    ANALYTE_UNITS,
    DIAGNOSIS_CODES,
    ENCOUNTER_TYPES,
    LIPID_COMPONENTS,
    MEDICAL_HISTORY_CATEGORIES,
    MEDICATION_DRUG_CLASSES,
    MEDICATION_STATUSES,
    SCHEMA_VERSION,
    SMOKING_STATUSES,
    TIMELINE_EVENT_TYPES,
    Patient,
)

# Outer physiological sanity bounds, NOT clinical thresholds (those are
# M4A-deferred derivation logic, not schema-level validation — see
# docs/M4_CLINICAL_ARCHITECTURE.md §10).
_LIPID_RANGE_MG_DL = (0.0, 500.0)
# Same kind of outer physiological clamp for BP and anthropometrics --
# "could a human body produce this reading", not "is this reading
# normal". Mirrors configs/indian_population.yaml's
# blood_pressure.distribution.{sbp,dbp}_bounds; kept here too so
# structural validation stays generator-independent (CLAUDE.md §4).
_SBP_RANGE_MM_HG = (70, 260)
_DBP_RANGE_MM_HG = (40, 160)
_HEIGHT_RANGE_CM = (100.0, 230.0)
_WEIGHT_RANGE_KG = (25.0, 250.0)
from integration.patient_id import is_valid_patient_id


def validate_patient(
    patient: Patient, valid_states: Optional[set[str]] = None
) -> list[str]:
    """Return a list of structural error strings (empty = valid).

    `valid_states`: the canonical Indian state/UT set (e.g. from
    `generation.indian_population.valid_states(config)`). Optional — pass
    None to skip state-membership checking (e.g. for a patient with no
    Indian conditioning applied).
    """
    errors: list[str] = []

    if not is_valid_patient_id(patient.patient_id):
        errors.append(f"invalid patient_id format: {patient.patient_id!r}")

    if patient.provenance is None:
        errors.append("missing provenance")
    elif patient.provenance.schema_version != SCHEMA_VERSION:
        errors.append(
            f"schema_version mismatch: expected {SCHEMA_VERSION!r}, "
            f"got {patient.provenance.schema_version!r}"
        )

    d = patient.demographics
    if d is None:
        errors.append("missing demographics")
    else:
        if not (0 <= d.age <= 120):
            errors.append(f"age out of range: {d.age}")
        if d.sex not in (0, 1):
            errors.append(f"invalid sex code: {d.sex}")
        if d.urban_rural is not None and d.urban_rural not in ("urban", "rural"):
            errors.append(f"invalid urban_rural value: {d.urban_rural!r}")
        if d.state is not None and valid_states is not None and d.state not in valid_states:
            errors.append(f"invalid state: {d.state!r}")
        # M8: both are still None for every generated patient (no height
        # evidence -- see Demographics). Bounds-checked anyway so the
        # validator is already correct when they start being populated.
        if d.height_cm is not None and not (
            _HEIGHT_RANGE_CM[0] <= d.height_cm <= _HEIGHT_RANGE_CM[1]
        ):
            errors.append(f"height_cm out of plausible range: {d.height_cm}")
        if d.weight_kg is not None and not (
            _WEIGHT_RANGE_KG[0] <= d.weight_kg <= _WEIGHT_RANGE_KG[1]
        ):
            errors.append(f"weight_kg out of plausible range: {d.weight_kg}")

    rf = patient.risk_factors
    if rf is not None:
        if rf.bmi is not None and not (10.0 <= rf.bmi <= 80.0):
            errors.append(f"BMI out of plausible range: {rf.bmi}")
        if rf.smoking_status is not None and rf.smoking_status not in SMOKING_STATUSES:
            errors.append(f"invalid smoking_status: {rf.smoking_status!r}")

    if patient.ecg is not None:
        if patient.ecg.signal_shape != [1000, 12]:
            errors.append(f"unexpected ECG signal_shape: {patient.ecg.signal_shape}")
        if patient.ecg.strat_fold not in range(1, 11):
            errors.append(f"invalid strat_fold: {patient.ecg.strat_fold}")

    lp = patient.lipid_panel
    if lp is not None:
        for field_name, value in (
            ("ldl_mg_dl", lp.ldl_mg_dl),
            ("hdl_mg_dl", lp.hdl_mg_dl),
            ("triglycerides_mg_dl", lp.triglycerides_mg_dl),
            ("total_cholesterol_mg_dl", lp.total_cholesterol_mg_dl),
        ):
            if value is not None and not (_LIPID_RANGE_MG_DL[0] <= value <= _LIPID_RANGE_MG_DL[1]):
                errors.append(f"lipid_panel.{field_name} out of plausible range: {value}")

    if patient.lipid_interpretations is not None:
        for i, interp in enumerate(patient.lipid_interpretations):
            if not interp.definition:
                errors.append(f"lipid_interpretations[{i}]: missing definition")
            unknown = set(interp.components_abnormal) - LIPID_COMPONENTS
            if unknown:
                errors.append(f"lipid_interpretations[{i}]: unknown components_abnormal {unknown}")

    if patient.labs is not None:
        for i, lab in enumerate(patient.labs):
            if not lab.analyte:
                errors.append(f"labs[{i}]: missing analyte")
            if not lab.unit:
                errors.append(f"labs[{i}]: missing unit")
            expected_unit = ANALYTE_UNITS.get(lab.analyte)
            if expected_unit is not None and lab.unit != expected_unit:
                errors.append(
                    f"labs[{i}]: analyte {lab.analyte!r} expects unit "
                    f"{expected_unit!r}, got {lab.unit!r}"
                )

    if patient.diagnoses is not None:
        for i, dx in enumerate(patient.diagnoses):
            if dx.code not in DIAGNOSIS_CODES:
                errors.append(f"diagnoses[{i}]: unsupported code {dx.code!r}")

    if patient.medical_history is not None:
        for i, entry in enumerate(patient.medical_history):
            if entry.category not in MEDICAL_HISTORY_CATEGORIES:
                errors.append(f"medical_history[{i}]: unknown category {entry.category!r}")

    if patient.medications is not None:
        seen_med_ids: set[str] = set()
        for i, med in enumerate(patient.medications):
            if med.drug_class not in MEDICATION_DRUG_CLASSES:
                errors.append(f"medications[{i}]: unsupported drug_class {med.drug_class!r}")
            if med.current_status not in MEDICATION_STATUSES:
                errors.append(f"medications[{i}]: unknown current_status {med.current_status!r}")
            if med.medication_id in seen_med_ids:
                errors.append(f"medications[{i}]: duplicate medication_id {med.medication_id!r}")
            seen_med_ids.add(med.medication_id)

    # --- M8: blood_pressure ---
    bp = patient.blood_pressure
    if bp is not None:
        for field_name, value, (lo, hi) in (
            ("systolic_mm_hg", bp.systolic_mm_hg, _SBP_RANGE_MM_HG),
            ("diastolic_mm_hg", bp.diastolic_mm_hg, _DBP_RANGE_MM_HG),
        ):
            if value is None:
                errors.append(f"blood_pressure.{field_name} is null on a populated blood_pressure")
            elif not isinstance(value, int) or isinstance(value, bool):
                errors.append(
                    f"blood_pressure.{field_name} must be a whole-mmHg int, got {type(value).__name__}: {value!r}"
                )
            elif not (lo <= value <= hi):
                errors.append(f"blood_pressure.{field_name} out of plausible range: {value}")
        # Definitional, not clinical: a systolic reading is by definition
        # the higher of the pair.
        if (
            isinstance(bp.systolic_mm_hg, int)
            and isinstance(bp.diastolic_mm_hg, int)
            and bp.systolic_mm_hg <= bp.diastolic_mm_hg
        ):
            errors.append(
                f"blood_pressure: systolic {bp.systolic_mm_hg} must exceed "
                f"diastolic {bp.diastolic_mm_hg}"
            )
        if not bp.measured_at:
            errors.append("blood_pressure.measured_at is missing")
        # Provenance of the age-band extrapolation must never be silent.
        if not bp.age_band_source:
            errors.append("blood_pressure.age_band_source is missing (evidence provenance)")
        if bp.extrapolated_beyond_source_age_range is None:
            errors.append("blood_pressure.extrapolated_beyond_source_age_range is missing")

    # --- M8: encounters ---
    if patient.encounters is not None:
        seen_encounter_ids: set[str] = set()
        for i, enc in enumerate(patient.encounters):
            if enc.encounter_type not in ENCOUNTER_TYPES:
                errors.append(f"encounters[{i}]: unsupported encounter_type {enc.encounter_type!r}")
            if enc.encounter_id in seen_encounter_ids:
                errors.append(f"encounters[{i}]: duplicate encounter_id {enc.encounter_id!r}")
            seen_encounter_ids.add(enc.encounter_id)
            if enc.patient_id != patient.patient_id:
                errors.append(
                    f"encounters[{i}]: patient_id {enc.patient_id!r} does not match "
                    f"the record's own {patient.patient_id!r}"
                )
            if not enc.date:
                errors.append(f"encounters[{i}]: missing date")
            if not enc.recorded_measurements:
                errors.append(
                    f"encounters[{i}]: empty recorded_measurements -- an encounter "
                    "containing nothing should not have been emitted"
                )

    if not patient.clinical_timeline:
        errors.append("empty clinical_timeline")
    for i, event in enumerate(patient.clinical_timeline):
        if event.event_type not in TIMELINE_EVENT_TYPES:
            errors.append(f"clinical_timeline[{i}]: unsupported event_type {event.event_type!r}")
        if not event.date:
            errors.append(f"clinical_timeline[{i}]: missing date")

    return errors


def check_duplicate_ids(patients: list[Patient]) -> list[str]:
    """Return error strings for any patient_id appearing more than once."""
    seen: dict[str, int] = {}
    for p in patients:
        seen[p.patient_id] = seen.get(p.patient_id, 0) + 1
    return [f"duplicate patient_id: {pid} (x{n})" for pid, n in seen.items() if n > 1]
