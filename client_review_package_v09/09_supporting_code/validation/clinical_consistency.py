"""Integrated clinical consistency validation (M4C, extended M4D/M4E).

Separate from `validation/structural.py`'s schema-level checks (per this
milestone's own instruction to keep them apart) — this module validates
CROSS-FIELD relationships within an already-structurally-valid patient.
See `docs/M4C_CONSISTENCY_AUDIT.md`/`docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md`/
`docs/M4E_MEDICATION_DESIGN.md` for the full dependency map and exactly
which relationships are validated here versus left unsupported
(`encounters` — not yet implemented; hyperlipidemia's own diagnosis and
statin/antiplatelet medications, deliberately deferred, D015/D016) or
intentionally left unreconciled by design (`risk_factors.hyperlipidemia`
vs. `lipid_interpretations` — two distinct variables per D014/Option B,
see docs/M4C_HYPERLIPIDEMIA_RESOLUTION.md).

Reuses `generation.indian_population.derive_lipid_interpretations()` and
`generation.clinical_history.derive_diagnoses()`/`derive_medical_history()`/
`derive_medications()` to recompute expected values rather than
duplicating logic — a second, independent implementation of the same
rules would itself become a consistency risk. Whether a patient *should*
have been treated (the treatment Bernoulli draw itself) is not
re-verifiable here — same situation as `risk_factors.hypertension` being
a sampled primitive, not a checkable derivation (docs/
M4E_MEDICATION_DESIGN.md M4E-6).

Does not modify generation behavior. Does not invent new clinical
relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from schemas.patient_schema import DIAGNOSIS_CODES, Patient
from generation.indian_population import derive_lipid_interpretations
from generation.clinical_history import (
    derive_diagnoses,
    derive_medical_history,
    derive_medications,
)

# The one controlled mapping this project's evidence supports between a
# medication's drug_class and the diagnosis code it must reference
# (docs/M4E_MEDICATION_DESIGN.md M4E-2/M4E-6).
_DRUG_CLASS_TO_DIAGNOSIS_CODE = {"antihypertensive": "hypertension", "antidiabetic": "diabetes"}


@dataclass
class ClinicalValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks_performed: list[str] = field(default_factory=list)


def validate_clinical_consistency(
    patient: Patient, indian_config: Optional[dict[str, Any]] = None
) -> ClinicalValidationResult:
    """Validate cross-field clinical consistency for one patient.

    `indian_config`: optional — enables the two checks that need to
    recompute an expected value (lipid interpretation recomputation,
    HbA1c plausibility). Without it, those checks are skipped with a
    warning rather than silently passing.
    """
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    # --- Lipids <-> lipid interpretations (hard rule, M4C-0 §4.2) ---
    lp = patient.lipid_panel
    interps = patient.lipid_interpretations
    if interps is not None and lp is None:
        errors.append(
            "lipid_interpretations present but lipid_panel is missing -- "
            "cannot have been derived from nothing"
        )
    elif lp is not None and interps is not None:
        checks.append("lipid_panel_interpretation_consistency")
        raw = {
            "total_cholesterol_mg_dl": lp.total_cholesterol_mg_dl,
            "triglycerides_mg_dl": lp.triglycerides_mg_dl,
            "hdl_mg_dl": lp.hdl_mg_dl,
            "ldl_mg_dl": lp.ldl_mg_dl,
        }
        if indian_config is None:
            warnings.append(
                "lipid_panel_interpretation_consistency check skipped -- "
                "no indian_config provided to recompute against"
            )
        elif any(v is None for v in raw.values()):
            warnings.append(
                "lipid_interpretations present but lipid_panel has missing "
                "raw values -- cannot fully re-verify derivation"
            )
        else:
            expected_by_def = {
                e["definition"]: e
                for e in derive_lipid_interpretations(indian_config, raw, patient.demographics.sex)
            }
            for interp in interps:
                expected = expected_by_def.get(interp.definition)
                if expected is None:
                    errors.append(
                        f"lipid_interpretations: definition {interp.definition!r} is not "
                        "in the configured lipid_definitions -- untraceable interpretation"
                    )
                    continue
                if interp.dyslipidemia != expected["dyslipidemia"]:
                    errors.append(
                        f"lipid_interpretations[{interp.definition}]: dyslipidemia="
                        f"{interp.dyslipidemia} does not match recomputation from raw "
                        f"values ({expected['dyslipidemia']})"
                    )
                if sorted(interp.components_abnormal) != sorted(expected["components_abnormal"]):
                    errors.append(
                        f"lipid_interpretations[{interp.definition}]: components_abnormal "
                        f"{interp.components_abnormal} does not match recomputation "
                        f"{expected['components_abnormal']}"
                    )

    # --- M8: is the RAW lipid triple internally possible at all? ---
    # Friedewald gives LDL = TC - HDL - TG/5, so a self-consistent panel
    # requires TC >= HDL + TG/5. Pre-D019, TC/TG/HDL were sampled as three
    # fully INDEPENDENT marginals (M4B), so ~2.28% of draws violated that
    # and the LDL clip_range floor of 30 mg/dL silently absorbed it.
    # D019 added reject-and-redraw to generation/indian_population.py's
    # sample_lipid_panel() for exactly this case, so `implied_ldl < 0`
    # should no longer occur in freshly-generated records -- this check is
    # kept as a regression guard, and still applies as-is to any
    # pre-D019 dataset (e.g. outputs/m8/100k_patients_v08/) re-validated
    # later. The separate, smaller clip-floor case (0 <= implied_ldl < 30,
    # a physiologically plausible low LDL, not an impossible one) is
    # unaffected by D019 and remains a WARNING below, not an error. Also
    # flagged when TG > 400 mg/dL, above which Friedewald is not
    # considered valid at all.
    if lp is not None and all(
        v is not None
        for v in (lp.total_cholesterol_mg_dl, lp.hdl_mg_dl, lp.triglycerides_mg_dl)
    ):
        checks.append("lipid_panel_internal_feasibility")
        implied_ldl = (
            lp.total_cholesterol_mg_dl - lp.hdl_mg_dl - lp.triglycerides_mg_dl / 5.0
        )
        if implied_ldl < 0:
            warnings.append(
                f"lipid_panel is internally impossible: total cholesterol "
                f"{lp.total_cholesterol_mg_dl} < HDL {lp.hdl_mg_dl} + triglycerides/5 "
                f"({lp.triglycerides_mg_dl / 5.0:.1f}), implying LDL {implied_ldl:.1f}; "
                "the stored LDL is the documented clip-range floor. Pre-existing M4B "
                "independent-marginal sampling artefact"
            )
        elif implied_ldl < 30.0:
            warnings.append(
                f"lipid_panel implies LDL {implied_ldl:.1f} mg/dL, below the documented "
                "clip floor of 30.0, so the stored LDL was clipped rather than derived"
            )
        if lp.triglycerides_mg_dl > 400.0:
            warnings.append(
                f"triglycerides {lp.triglycerides_mg_dl} mg/dL exceed 400, above which "
                "the Friedewald equation used to derive LDL is not considered valid"
            )

    # --- Diabetes <-> HbA1c (hard rule, M4C-0 §4.1) ---
    checks.append("diabetes_hba1c_consistency")
    diabetes = patient.risk_factors.diabetes if patient.risk_factors is not None else None
    hba1c_entries = [lab for lab in (patient.labs or []) if lab.analyte == "HbA1c"]

    if diabetes is True and hba1c_entries:
        errors.append(
            "labs contains an HbA1c entry for a diabetic patient -- not "
            "evidence-supported for M4B (docs/M4_CLINICAL_EVIDENCE.md)"
        )
    if diabetes is False and not hba1c_entries:
        errors.append("non-diabetic patient is missing the expected HbA1c lab entry")
    if len(hba1c_entries) > 1:
        errors.append(f"expected at most one HbA1c entry, found {len(hba1c_entries)}")
    for lab in hba1c_entries:
        if lab.value is not None and not (4.0 <= lab.value <= 6.4):
            errors.append(f"HbA1c value {lab.value} outside the documented generation range [4.0, 6.4]")
        if lab.unit != "%":
            errors.append(f"HbA1c unit {lab.unit!r} != '%'")

    if indian_config is not None and hba1c_entries and patient.demographics is not None:
        checks.append("hba1c_plausibility_given_age_sex")
        dist = indian_config["risk_factors"]["hba1c"]["distribution"]
        sex_key = "male" if patient.demographics.sex == 0 else "female"
        slope = dist["sex_decade_slope"][sex_key]
        expected_mean = dist["baseline_mean_at_age_25"] + slope * (
            patient.demographics.age - dist["reference_age"]
        ) / 10.0
        sd = dist["sd"]
        value = hba1c_entries[0].value
        if value is not None and abs(value - expected_mean) > 5 * sd:
            # Soft check -- a real Normal draw can rarely land this far out
            # (clipping makes it more likely at the bounds), so this is a
            # warning, not a hard error.
            warnings.append(
                f"HbA1c value {value} is >5 SD from the age/sex-conditioned "
                f"expected mean {expected_mean:.2f} (sd={sd}) -- statistically "
                "implausible, worth a second look"
            )

    # --- Intentionally distinct variables (docs/DECISIONS.md D014, Option B) ---
    # risk_factors.hyperlipidemia (M2C: unconditioned Bernoulli(0.812), a
    # population/background risk-factor attribute, same role as hypertension/
    # diabetes) and lipid_interpretations (M4B: computed per-patient from
    # lipid_panel) are two independently-evidenced variables describing
    # related but distinct facts -- NOT duplicate sources of truth. D014's
    # semantic audit (docs/M4C_HYPERLIPIDEMIA_RESOLUTION.md) confirmed the
    # measured 73-77% disagreement is expected, not a bug. This validator
    # never compares them and disagreement is never an error.
    checks.append("hyperlipidemia_vs_lipid_interpretations_intentionally_not_compared")

    # --- Clinical timeline / labs measured_at self-consistency (M4C-0 §4.6) ---
    checks.append("timeline_labs_date_consistency")
    if patient.clinical_timeline and hba1c_entries:
        timeline_date = patient.clinical_timeline[0].date
        for lab in hba1c_entries:
            if lab.measured_at is not None and lab.measured_at != timeline_date:
                errors.append(
                    f"labs measured_at {lab.measured_at!r} does not match "
                    f"clinical_timeline date {timeline_date!r}"
                )

    # --- Diagnoses <-> risk_factors (hard rule, M4D, docs/DECISIONS.md D015) ---
    checks.append("diagnosis_risk_factor_consistency")
    if patient.diagnoses is not None and patient.risk_factors is not None:
        rf_dict = {
            "hypertension": patient.risk_factors.hypertension,
            "diabetes": patient.risk_factors.diabetes,
        }
        expected_dx = {dx["code"] for dx in derive_diagnoses(rf_dict, patient.patient_id)}
        actual_dx = {dx.code for dx in patient.diagnoses}
        if actual_dx != expected_dx:
            errors.append(
                f"diagnoses codes {sorted(actual_dx)} do not match recomputation "
                f"from risk_factors {sorted(expected_dx)}"
            )
        unsupported = actual_dx - DIAGNOSIS_CODES
        if unsupported:
            errors.append(f"diagnoses contain unsupported codes: {sorted(unsupported)}")

    # --- medical_history <-> diagnoses (hard rule: reference, never a
    # second independent generator, docs/CLINICAL_RECORD_DESIGN.md §D) ---
    checks.append("medical_history_diagnosis_consistency")
    if patient.medical_history is not None and patient.diagnoses is not None:
        diag_dicts = [
            {
                "diagnosis_id": dx.diagnosis_id,
                "code": dx.code,
                "diagnosed_date": dx.diagnosed_date,
            }
            for dx in patient.diagnoses
        ]
        expected_history = derive_medical_history(diag_dicts)
        actual_history = [
            {
                "category": e.category,
                "description": e.description,
                "diagnosis_id": e.diagnosis_id,
                "event_date": e.event_date,
            }
            for e in patient.medical_history
        ]
        if actual_history != expected_history:
            errors.append(
                "medical_history does not match recomputation from diagnoses "
                f"(expected {expected_history}, got {actual_history})"
            )
        known_ids = {dx.diagnosis_id for dx in patient.diagnoses}
        for i, entry in enumerate(patient.medical_history):
            if entry.category != "chronic_condition":
                errors.append(
                    f"medical_history[{i}]: unsupported category {entry.category!r} "
                    "-- only chronic_condition is generated as of D015"
                )
            if entry.diagnosis_id is not None and entry.diagnosis_id not in known_ids:
                errors.append(
                    f"medical_history[{i}]: diagnosis_id {entry.diagnosis_id!r} "
                    "does not reference any of this patient's diagnoses -- orphan entry"
                )

    # --- medications <-> diagnoses (hard consistency rule, M4E, D016) ---
    # Whether a patient SHOULD have been treated is not re-verifiable here
    # (the treatment Bernoulli draw isn't stored) -- only that every
    # generated medication is well-formed relative to its diagnosis.
    checks.append("medication_diagnosis_consistency")
    if patient.medications is not None and patient.diagnoses is not None:
        diag_by_id = {dx.diagnosis_id: dx for dx in patient.diagnoses}
        seen_diagnosis_ids: set[str] = set()
        for i, med in enumerate(patient.medications):
            dx = diag_by_id.get(med.diagnosis_id)
            if dx is None:
                errors.append(
                    f"medications[{i}]: diagnosis_id {med.diagnosis_id!r} does not "
                    "reference any of this patient's diagnoses -- orphan entry"
                )
                continue
            expected_class = _DRUG_CLASS_TO_DIAGNOSIS_CODE.get(med.drug_class)
            if expected_class is None:
                errors.append(f"medications[{i}]: unsupported drug_class {med.drug_class!r}")
            elif dx.code != expected_class:
                errors.append(
                    f"medications[{i}]: drug_class {med.drug_class!r} does not match "
                    f"referenced diagnosis code {dx.code!r}"
                )
            if med.diagnosis_id in seen_diagnosis_ids:
                errors.append(
                    f"medications[{i}]: diagnosis_id {med.diagnosis_id!r} already has "
                    "a medication -- at most one medication per diagnosis is generated"
                )
            seen_diagnosis_ids.add(med.diagnosis_id)
            if med.current_status == "active" and med.stop_date is not None:
                errors.append(f"medications[{i}]: current_status='active' but stop_date is set")
            if (
                med.start_date is not None
                and med.stop_date is not None
                and med.start_date > med.stop_date
            ):
                errors.append(f"medications[{i}]: start_date {med.start_date!r} > stop_date {med.stop_date!r}")

    # --- M8: blood_pressure <-> hypertension label + medications ---
    # The hard rule is the hypertension label's OWN published definition
    # (SBP>=140 and/or DBP>=90 and/or on antihypertensive medication),
    # applied in the one direction the evidence supports: the label is
    # primary, the measurement must be consistent with it. Note the
    # treated case deliberately asserts NOTHING about the value -- a
    # treated hypertensive may be controlled, and demanding a raised
    # reading there would be requiring a fabricated confirmation.
    bp = patient.blood_pressure
    if bp is None:
        checks.append("blood_pressure_absent")
    elif patient.risk_factors is not None:
        checks.append("blood_pressure_hypertension_label_consistency")
        sbp, dbp = bp.systolic_mm_hg, bp.diastolic_mm_hg
        hypertension = patient.risk_factors.hypertension
        on_antihypertensive = any(
            med.drug_class == "antihypertensive" for med in (patient.medications or [])
        )
        if sbp is None or dbp is None:
            errors.append("blood_pressure is present but systolic/diastolic is null")
        else:
            if sbp <= dbp:
                errors.append(f"blood_pressure: systolic {sbp} must exceed diastolic {dbp}")
            raised = sbp >= 140 or dbp >= 90
            if hypertension is False and raised:
                errors.append(
                    f"blood_pressure {sbp}/{dbp} meets the hypertension definition "
                    "(SBP>=140 or DBP>=90) but risk_factors.hypertension is False"
                )
            if hypertension is True and not raised and not on_antihypertensive:
                errors.append(
                    f"blood_pressure {sbp}/{dbp} is below the hypertension threshold and "
                    "no antihypertensive medication is present, so the hypertension=True "
                    "label has no route to being satisfied under its own definition"
                )
        if bp.measured_at and patient.clinical_timeline:
            if bp.measured_at != patient.clinical_timeline[0].date:
                errors.append(
                    f"blood_pressure.measured_at {bp.measured_at!r} does not match "
                    f"clinical_timeline date {patient.clinical_timeline[0].date!r}"
                )

    # --- M8: BMI <-> height/weight arithmetic ---
    # Only asserted when all three are populated. Today height/weight are
    # always null (no evidence), so this records itself as skipped rather
    # than silently passing on absent data.
    demo = patient.demographics
    bmi = patient.risk_factors.bmi if patient.risk_factors is not None else None
    if (
        demo is not None
        and demo.height_cm is not None
        and demo.weight_kg is not None
        and bmi is not None
    ):
        checks.append("bmi_height_weight_arithmetic")
        expected_bmi = demo.weight_kg / (demo.height_cm / 100.0) ** 2
        # Tolerance covers the rounding already applied to each stored
        # value (BMI 1dp, weight 1dp), not modelling slack.
        if abs(expected_bmi - bmi) > 0.15:
            errors.append(
                f"BMI {bmi} disagrees with weight {demo.weight_kg} kg / height "
                f"{demo.height_cm} cm (implies {expected_bmi:.2f})"
            )
    elif bmi is not None:
        checks.append("bmi_height_weight_arithmetic_skipped_height_weight_unpopulated")

    # --- M8: encounters <-> timeline <-> measurements referential integrity ---
    if patient.encounters is not None:
        checks.append("encounter_timeline_referential_integrity")
        encounter_ids = {enc.encounter_id for enc in patient.encounters}
        for i, enc in enumerate(patient.encounters):
            if enc.patient_id != patient.patient_id:
                errors.append(
                    f"encounters[{i}]: patient_id {enc.patient_id!r} does not match "
                    f"the record's own {patient.patient_id!r}"
                )
            # Every measurement the encounter claims to contain must
            # actually exist on the record -- an encounter must never
            # assert a measurement that was not generated.
            for name in enc.recorded_measurements:
                if name == "blood_pressure":
                    present = patient.blood_pressure is not None
                elif name == "lipid_panel":
                    present = patient.lipid_panel is not None
                elif name.startswith("labs."):
                    present = any(
                        lab.analyte == name.split(".", 1)[1] for lab in (patient.labs or [])
                    )
                else:
                    errors.append(
                        f"encounters[{i}]: recorded_measurements entry {name!r} is not a "
                        "known record field"
                    )
                    continue
                if not present:
                    errors.append(
                        f"encounters[{i}]: claims measurement {name!r} which is not "
                        "present on this record"
                    )
            # The encounter's date must agree with the dates its
            # measurements actually carry.
            for lab in patient.labs or []:
                if lab.measured_at is not None and lab.measured_at != enc.date:
                    errors.append(
                        f"encounters[{i}]: date {enc.date!r} does not match labs "
                        f"measured_at {lab.measured_at!r}"
                    )
            if (
                patient.blood_pressure is not None
                and patient.blood_pressure.measured_at is not None
                and patient.blood_pressure.measured_at != enc.date
            ):
                errors.append(
                    f"encounters[{i}]: date {enc.date!r} does not match "
                    f"blood_pressure.measured_at {patient.blood_pressure.measured_at!r}"
                )

        # Timeline references must resolve, and must not duplicate.
        seen_refs: set[str] = set()
        for i, event in enumerate(patient.clinical_timeline):
            if event.reference_id is None:
                continue
            if event.reference_id not in encounter_ids:
                errors.append(
                    f"clinical_timeline[{i}]: reference_id {event.reference_id!r} does "
                    "not resolve to any encounter on this record -- dangling reference"
                )
            if event.reference_id in seen_refs:
                errors.append(
                    f"clinical_timeline[{i}]: reference_id {event.reference_id!r} appears "
                    "in more than one timeline event -- duplicate representation"
                )
            seen_refs.add(event.reference_id)
        unindexed = encounter_ids - seen_refs
        if unindexed:
            errors.append(
                f"encounters {sorted(unindexed)} have no clinical_timeline event "
                "referencing them"
            )
        created = next(
            (
                e.date
                for e in patient.clinical_timeline
                if e.event_type == "synthetic_record_created"
            ),
            None,
        )
        if created is not None:
            for i, event in enumerate(patient.clinical_timeline):
                if event.date < created:
                    errors.append(
                        f"clinical_timeline[{i}]: date {event.date!r} precedes "
                        f"synthetic_record_created {created!r}"
                    )

    # --- D020: family history shape, and its derivation tag must match
    # the patient's age tier (observed 45+, model-derived below) ---
    fh = patient.family_history
    if fh is not None:
        checks.append("family_history_shape_and_derivation")
        if set(fh) != {"diabetes", "cardiovascular_disease", "derivation"}:
            errors.append(f"family_history: unexpected keys {sorted(fh)}")
        elif not all(isinstance(fh[k], bool) for k in ("diabetes", "cardiovascular_disease")):
            errors.append("family_history: diabetes/cardiovascular_disease must be bool")
        else:
            expected = (
                "lasi_observed_45_plus" if patient.demographics.age >= 45
                else "parent_simulation_calibrated"
            )
            if fh["derivation"] != expected:
                errors.append(
                    f"family_history.derivation {fh['derivation']!r} does not match "
                    f"age {patient.demographics.age} (expected {expected!r})"
                )

    # --- Confirm still-unimplemented domains remain absent ---
    # `encounters` left this list in M8 and `family_history` in D020;
    # echo's scope is entirely open.
    checks.append("unimplemented_domains_confirmed_absent")
    for field_name in ("echo",):
        if getattr(patient, field_name) is not None:
            warnings.append(
                f"{field_name} is populated, but no generation logic for it "
                "exists yet in this codebase -- unexpected, worth investigating"
            )

    # --- ECG boundary (docs/DECISIONS.md D003): metadata only, never a
    # waveform. M8 must not have disturbed it. ---
    if patient.ecg is not None:
        checks.append("ecg_remains_metadata_only")
        if patient.ecg.signal_available:
            errors.append(
                "ecg.signal_available is True but no waveform generation workflow has "
                "been approved (docs/DECISIONS.md D003)"
            )
        if not patient.ecg.superclasses:
            warnings.append(
                "ecg.superclasses is empty -- a missing PTB-XL label, not something to "
                "guess at (docs/M7_0_ECG_READINESS_REPORT.md)"
            )

    return ClinicalValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        checks_performed=checks,
    )


def validate_population_clinical_consistency(
    patients: list[Patient], indian_config: Optional[dict[str, Any]] = None
) -> list[ClinicalValidationResult]:
    """O(N) — one independent validate_clinical_consistency() call per
    patient; no cross-patient comparison is needed for any rule here, so
    there is no O(N^2) risk to guard against."""
    return [validate_clinical_consistency(p, indian_config) for p in patients]
