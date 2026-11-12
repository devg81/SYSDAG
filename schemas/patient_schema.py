"""Patient record data model — Schema v0.11 (see SCHEMA_VERSION below).

v0.9 (D020/D021): family_history populated; air_quality added.
v0.10 (D022): joint lipid model (no LDL clamp); HbA1c for every patient
(Lab.derivation/confidence); BP confidence; modeled condition onset on
Diagnosis (age_at_onset_years/onset_date, always tagged modeled) plus a
condition_onset_modeled timeline event; age rounded to 2 decimals.
v0.11 (D023, reverses D014; -jatin): risk_factors.hyperlipidemia is DERIVED from
the patient's own lipid panel (NCEP_ATP_III dyslipidemia verdict), no
longer an independent Bernoulli draw. No structural change; the version
bump marks the changed meaning of the field.

EMPTY-VALUE CONVENTION (v0.10): `None` = NOT MODELED by this generator
(e.g. height_cm, echo, diagnosed_date, medication start_date). `[]` =
modeled, and nothing applies (e.g. a patient with no diagnoses has
diagnoses == []). A list field is never None when the generator models it.

TREATMENT NOTE: medications are independent Bernoulli draws per condition
(NNMS 14.5% antihypertensive / 36.1% antidiabetic), so most hypertensives
are UNTREATED and "hypertension + diabetes" does NOT imply both treated.
Test fixtures must not assume otherwise.

Model-independent data contract for a synthetic cardiovascular patient
record. Fields not yet populated by any pipeline stage are left `None`/empty
rather than guessed (see `CLAUDE.md` §14). Do not add generator-specific
logic here (`CLAUDE.md` §4).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "0.11"

SMOKING_STATUSES = {"never", "former", "current"}  # controlled vocabulary; see RiskFactors

# Diagnosis codes this project can currently generate — a 1:1 promotion of
# an already-evidence-backed risk_factors flag, per docs/DECISIONS.md D015.
# "hyperlipidemia" is deliberately excluded: which lipid_interpretations
# definition (NCEP_ATP_III vs. LAI_2020) should drive it is an open
# question, not resolved by this project (see
# docs/M4D_DIAGNOSIS_HISTORY_DESIGN.md). Any other code is unsupported.
DIAGNOSIS_CODES = {"hypertension", "diabetes"}

# medical_history category vocabulary, per docs/CLINICAL_RECORD_DESIGN.md
# §D. Only "chronic_condition" is ever generated as of D015 — the other
# three are reserved for future, evidence-gated milestones (cv_event,
# procedure) or future diagnosis-history expansion ("diagnosis").
MEDICAL_HISTORY_CATEGORIES = {"diagnosis", "cv_event", "procedure", "chronic_condition"}

# Medication drug classes this project can currently generate — coarse
# therapeutic categories matching exactly what ICMR-NNMS's treatment-rate
# evidence measured (per diagnosed condition, not per pharmacological
# subclass), per docs/DECISIONS.md D016. No specific drug name is ever
# generated — NLEM confirms availability, not prescribing share. Statin/
# antiplatelet classes are deliberately excluded (no population
# treatment-rate evidence; see docs/M4E_MEDICATION_EVIDENCE.md).
MEDICATION_DRUG_CLASSES = {"antihypertensive", "antidiabetic"}

# "discontinued" is reserved for a future milestone with discontinuation
# evidence — never produced today (docs/M4E_MEDICATION_DESIGN.md).
MEDICATION_STATUSES = {"active", "discontinued"}

# Components a LipidInterpretation may cite as abnormal — a small, stable
# clinical vocabulary (unlike `definition` below, which is deliberately
# open — see LipidInterpretation).
LIPID_COMPONENTS = {"LDL", "HDL", "triglycerides", "total_cholesterol"}

# Encounter types this project can currently generate (M8). Exactly ONE
# value exists, and it is deliberately named for what it actually is: a
# structural container for the single synthetic cross-section of
# measurements this record holds (blood pressure, lipid panel, HbA1c --
# all carrying the same date). It is NOT a claim that a healthcare
# contact occurred. No care-seeking/utilization encounter model is
# generated: the only candidate evidence (NSS 75th Round) measures
# healthcare expenditure behaviour, not clinical encounters, and is
# classified "E — Not Used, deferred" in
# docs/INDIAN_GENERATION_STRATEGY.md. Real visit types (outpatient,
# admission, follow-up) stay unsupported until such evidence exists.
ENCOUNTER_TYPES = {"synthetic_baseline_assessment"}

# clinical_timeline event vocabulary (M8). Both values are facts about
# the synthetic record itself, not inferred clinical history: no
# diagnosis-onset, medication-start or follow-up event is ever emitted
# (no evidence-backed per-patient date distribution exists for any of
# them -- docs/M4_CLINICAL_EVIDENCE.md §7).
# v0.10: + condition_onset_modeled -- a MODELED (not observed) onset,
# referencing the Diagnosis whose onset_date it indexes.
TIMELINE_EVENT_TYPES = {"synthetic_record_created", "synthetic_baseline_assessment", "condition_onset_modeled"}

# Expected unit per known analyte, for structural (not clinical) validation
# — i.e. "is this the unit this analyte is normally reported in," not "is
# this value clinically normal." See docs/DECISIONS.md D012.
ANALYTE_UNITS = {
    "HbA1c": "%",
    "LDL": "mg/dL",
    "HDL": "mg/dL",
    "triglycerides": "mg/dL",
    "total_cholesterol": "mg/dL",
}


@dataclass
class Demographics:
    age: float
    sex: int  # PTB-XL encoding: 0 = male, 1 = female
    # Still None after M8's research pass. BMI (risk_factors.bmi) remains
    # this project's evidence-primary anthropometric variable; a national
    # mean AND SD of Indian adult height by sex was searched for 6 times
    # across M4-0 and M8 and never located, so height has no non-invented
    # dispersion to sample from. Full evidence trail and the two concrete
    # routes to unblock: configs/indian_population.yaml
    # risk_factors.anthropometrics_height_weight.
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None  # derivable as bmi * (height_cm/100)**2 once height exists
    # First-class per docs/DECISIONS.md D005. Values/sampling distributions
    # not yet implemented (docs/INDIAN_GENERATION_STRATEGY.md M2C-2/M2C-3) —
    # fields exist now so generation logic has somewhere to write to.
    state: Optional[str] = None  # Indian state/UT name
    urban_rural: Optional[str] = None  # "urban" or "rural"


@dataclass
class RiskFactors:
    """M2C scope only — see configs/indian_population.yaml for the evidence
    behind each field's generated value (or lack of one)."""

    bmi: Optional[float] = None
    smoking_status: Optional[str] = None  # one of SMOKING_STATUSES
    hypertension: Optional[bool] = None
    diabetes: Optional[bool] = None
    # D023 (v0.11): derived = lipid_interpretations[NCEP_ATP_III].dyslipidemia
    hyperlipidemia: Optional[bool] = None


@dataclass
class Lab:
    """One laboratory measurement. Generic on purpose — reused across
    analytes (e.g. HbA1c) rather than a dedicated dataclass per analyte,
    per docs/M4_CLINICAL_ARCHITECTURE.md §2/§5 (M4A)."""

    analyte: str  # e.g. "HbA1c"
    unit: str  # e.g. "%" — see ANALYTE_UNITS for known analyte/unit pairs
    value: Optional[float] = None
    measured_at: Optional[str] = None  # ISO 8601 date; engineering-generated, not evidence-derived
    derivation: Optional[str] = None  # v0.10: which distribution produced the value (see config)
    confidence: Optional[str] = None  # v0.10: "moderate" | "low"


@dataclass
class BloodPressure:
    """One office blood-pressure measurement (M8).

    Generated CONDITIONAL on the already-primary `risk_factors.
    hypertension` label, using that label's own published definition
    (SBP>=140 and/or DBP>=90 and/or on antihypertensive medication) as
    the truncation boundary -- the same reversed, label-to-value
    direction `docs/DECISIONS.md` D011 approved for HbA1c, NOT the
    lipid raw-to-label direction. BP is therefore never used to
    re-derive hypertension, and introduces no new prevalence claim.
    Evidence and every limitation: `configs/indian_population.yaml`
    `risk_factors.blood_pressure`.

    `age_band_source` and `extrapolated_beyond_source_age_range` exist
    so the source-age-coverage gap (NFHS-5 covers men to 54, women to
    49; this project generates 20-89) is machine-filterable per record
    rather than only described in prose.
    """

    systolic_mm_hg: Optional[int] = None
    diastolic_mm_hg: Optional[int] = None
    measured_at: Optional[str] = None  # ISO 8601 date; matches the baseline-assessment encounter
    age_band_source: Optional[str] = None  # e.g. "NFHS-5 male 40-44"
    extrapolated_beyond_source_age_range: Optional[bool] = None  # True once age > source coverage
    source: str = "derived_conditional_on_hypertension_label"
    confidence: Optional[str] = None  # v0.10: "low" iff extrapolated (SBP trend-extrapolated), else "moderate"


AQI_CATEGORIES = ("Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe")


@dataclass
class AirQuality:
    """State-level annual ambient AQI (D021) -- a deterministic lookup by
    demographics.state, CPCB National AQI scale. Evidence and every
    limitation: `configs/indian_population.yaml` `environment.air_quality`.

    `monitoring_bias` and `geographic_resolution` are per-record so a
    consumer cannot mistake an urban-station state mean for a rural
    patient's own exposure; `aqi` is None (with `unavailable_reason`)
    where the state has no adequately reporting station.
    """

    aqi: Optional[float] = None
    category: Optional[str] = None  # one of AQI_CATEGORIES, None iff aqi is None
    reference_year: Optional[int] = None
    stations: Optional[int] = None
    cities: Optional[int] = None
    unavailable_reason: Optional[str] = None
    geographic_resolution: str = "state"
    monitoring_bias: str = "state_mean_is_urban_station_weighted"
    source: str = "CPCB CAAQMS hourly AQI via github.com/Vonter/india-cpcb-aqi (ODbL-1.0)"


@dataclass
class Encounter:
    """A structural container for this record's single synthetic
    measurement cross-section (M8) -- NOT an observed healthcare
    contact. See ENCOUNTER_TYPES for why no real visit type is
    generated. `recorded_measurements` names the already-generated
    fields this encounter anchors; it REFERENCES them rather than
    holding copies, following the same no-duplicate-representation rule
    as MedicalHistoryEntry."""

    encounter_id: str  # e.g. "PAT_000001_ENC01"
    encounter_type: str  # one of ENCOUNTER_TYPES
    date: str  # ISO 8601 date
    patient_id: str  # canonical owner -- never floating
    recorded_measurements: list[str] = field(default_factory=list)
    source: str = "synthetic_structural_container"


@dataclass
class LipidPanel:
    """Raw/continuous lipid measurements — the PRIMARY data, per
    docs/DECISIONS.md D011. Field-name unit suffixes match this schema's
    existing convention (Demographics.height_cm/weight_kg)."""

    ldl_mg_dl: Optional[float] = None
    hdl_mg_dl: Optional[float] = None
    triglycerides_mg_dl: Optional[float] = None
    total_cholesterol_mg_dl: Optional[float] = None


@dataclass
class LipidInterpretation:
    """A DERIVED label from a LipidPanel — never independently sampled
    (D011). `definition` is a free-text reference key, deliberately not a
    closed vocabulary (unlike LIPID_COMPONENTS/SMOKING_STATUSES) because
    new clinical guidelines must be addable without a schema change."""

    definition: str  # e.g. "NCEP_ATP_III" | "LAI_2020"
    dyslipidemia: Optional[bool] = None
    components_abnormal: list[str] = field(default_factory=list)  # subset of LIPID_COMPONENTS
    source_citation: Optional[str] = None


@dataclass
class Diagnosis:
    """A DERIVED entry — a 1:1 promotion of an already-generated
    risk_factors flag, never independently sampled (D015, mirroring
    D011's rule for lipid interpretations). `code` is a plain-text
    condition name from DIAGNOSIS_CODES; ICD-coding is a future decision
    (docs/CLINICAL_RECORD_DESIGN.md §E), not made here."""

    diagnosis_id: str  # e.g. "PAT_000001_DX01"
    code: str  # one of DIAGNOSIS_CODES
    diagnosed_date: Optional[str] = None  # ISO 8601; None -- diagnosis timing is not modeled (onset is, below; ~half of cases are undiagnosed)
    source: str = "derived_from_risk_factors"
    # v0.10 -- MODELED, never observed: onset sampled from a prevalence-by-age
    # curve (configs/indian_population.yaml onset_model). Always <= current age.
    age_at_onset_years: Optional[float] = None
    onset_date: Optional[str] = None  # assessment date minus (age - age_at_onset_years)
    onset_derivation: Optional[str] = None
    onset_confidence: Optional[str] = None


@dataclass
class MedicalHistoryEntry:
    """A REFERENCE to an existing Diagnosis, never an independent
    generator (docs/CLINICAL_RECORD_DESIGN.md §D) — avoids two
    separately-random representations of the same fact."""

    category: str  # one of MEDICAL_HISTORY_CATEGORIES
    description: str  # mirrors the referenced Diagnosis.code
    diagnosis_id: Optional[str] = None  # points at a Diagnosis.diagnosis_id
    event_date: Optional[str] = None  # mirrors the referenced Diagnosis.diagnosed_date


@dataclass
class Medication:
    """A DERIVED entry — treatment is sampled per-diagnosis from an
    evidence-backed treatment rate (D016), but the Medication record
    itself is a deterministic construction from that outcome, never a
    second independent generator. `drug_class` is a coarse therapeutic
    category, not a specific drug name (docs/M4E_MEDICATION_DESIGN.md
    M4E-1) — no Indian source reports drug-name-level prescribing
    share."""

    medication_id: str  # e.g. "PAT_000001_MED01"
    drug_class: str  # one of MEDICATION_DRUG_CLASSES
    diagnosis_id: str  # references the Diagnosis this treats -- never floating
    current_status: str = "active"  # one of MEDICATION_STATUSES; only "active" is ever produced
    start_date: Optional[str] = None  # ISO 8601; None -- no per-patient initiation-date evidence exists
    stop_date: Optional[str] = None  # None while current_status == "active" (always, today)
    source: str = "derived_from_diagnosis_treatment_rate"


@dataclass
class ECGRecord:
    source: str
    ecg_id: int
    superclasses: list[str]
    strat_fold: int
    sampling_hz: int
    signal_shape: list[int]
    filename: str
    signal_available: bool = False  # True once a waveform is attached (Stage 4)


@dataclass
class TimelineEvent:
    """`reference_id` added in M8 — the reference mechanism
    docs/CLINICAL_RECORD_DESIGN.md §H proposed (an additive change, as
    that document anticipated). It points at an already-generated
    record's id (today: an Encounter.encounter_id), so the timeline
    indexes other records instead of restating them."""

    event_type: str  # one of TIMELINE_EVENT_TYPES
    date: str  # ISO 8601 date
    reference_id: Optional[str] = None


@dataclass
class Provenance:
    schema_version: str
    generated_at: str
    generator: str
    random_seed: int
    source_datasets: list[str]


@dataclass
class ValidationMetadata:
    validated: bool = False
    validation_version: Optional[str] = None
    errors: list[str] = field(default_factory=list)


@dataclass
class Patient:
    patient_id: str
    demographics: Demographics
    provenance: Provenance
    risk_factors: Optional[RiskFactors] = None  # M2C — see docs/DECISIONS.md D006
    family_history: Optional[dict[str, Any]] = None  # D020 — {diabetes, cardiovascular_disease, derivation}; LASI 45+, model-derived 20-44
    medical_history: Optional[list[MedicalHistoryEntry]] = None  # M4D — derived from diagnoses, docs/DECISIONS.md D015
    diagnoses: Optional[list[Diagnosis]] = None  # M4D — derived from risk_factors, docs/DECISIONS.md D015
    medications: Optional[list[Medication]] = None  # M4E — derived from diagnoses + treatment rate, docs/DECISIONS.md D016
    labs: Optional[list[Lab]] = None  # v0.10: always a list (HbA1c for every patient); [] would mean modeled-but-none
    blood_pressure: Optional[BloodPressure] = None  # M8 — conditional on the hypertension label, see BloodPressure
    air_quality: Optional[AirQuality] = None  # D021 — state lookup, see AirQuality
    encounters: Optional[list[Encounter]] = None  # M8 — structural baseline-assessment container only, see ENCOUNTER_TYPES
    lipid_panel: Optional[LipidPanel] = None  # M4A — raw/primary, per D011; not yet populated
    lipid_interpretations: Optional[list[LipidInterpretation]] = None  # M4A — derived from lipid_panel, per D011; not yet populated
    ecg: Optional[ECGRecord] = None
    echo: Optional[dict[str, Any]] = None  # scope open — spec §2.1/§7
    clinical_timeline: list[TimelineEvent] = field(default_factory=list)
    validation: ValidationMetadata = field(default_factory=ValidationMetadata)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
