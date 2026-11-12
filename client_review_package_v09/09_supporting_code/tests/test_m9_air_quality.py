"""D021 -- state-level CPCB air quality lookup."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import (
    aqi_category,
    derive_air_quality,
    generate_indian_attributes,
    load_config,
    validate_config,
)
from integration.build_patient import build_patient, load_config as load_base_config
from schemas.patient_schema import AirQuality
from validation.structural import validate_patient

CONFIG = load_config()
BASE_CONFIG = load_base_config(_REPO_ROOT / "configs" / "base.yaml")


def test_config_is_valid_and_covers_every_state():
    assert validate_config(CONFIG) == []


@pytest.mark.parametrize(
    "aqi,category",
    [(0, "Good"), (50, "Good"), (50.1, "Satisfactory"), (100, "Satisfactory"),
     (200, "Moderate"), (212.3, "Poor"), (400, "Very Poor"), (401, "Severe"), (500, "Severe")],
)
def test_cpcb_category_breakpoints(aqi, category):
    assert aqi_category(CONFIG, aqi) == category


def test_lookup_is_deterministic_and_matches_config():
    aq = derive_air_quality(CONFIG, "Delhi")
    assert aq == derive_air_quality(CONFIG, "Delhi")
    assert (aq["aqi"], aq["category"], aq["reference_year"]) == (212.3, "Poor", 2023)


def test_unmonitored_state_is_null_with_a_reason():
    aq = derive_air_quality(CONFIG, "Goa")
    assert aq["aqi"] is None and aq["category"] is None and aq["unavailable_reason"]


def test_lookup_consumes_no_rng():
    # Two draws from the same seed must agree on every field, and the
    # state's AQI must be exactly the config value -- never sampled.
    a = generate_indian_attributes(np.random.default_rng(7), CONFIG)
    b = generate_indian_attributes(np.random.default_rng(7), CONFIG)
    assert a == b
    assert a["air_quality"] == derive_air_quality(CONFIG, a["demographics"]["state"])


def test_built_patient_carries_air_quality_and_validates():
    patient = build_patient(1, BASE_CONFIG)
    assert patient.air_quality.geographic_resolution == "state"
    assert patient.air_quality.monitoring_bias == "state_mean_is_urban_station_weighted"
    assert patient.validation.validated, patient.validation.errors


@pytest.mark.parametrize(
    "air_quality,fragment",
    [
        (AirQuality(aqi=120.0, category="Good", reference_year=2023), "does not match"),
        (AirQuality(aqi=None, category=None, reference_year=2023), "unavailable_reason"),
        (AirQuality(aqi=612.0, category="Severe", reference_year=2023), "out of CPCB"),
    ],
)
def test_structural_validation_rejects_inconsistent_air_quality(air_quality, fragment):
    patient = build_patient(1, BASE_CONFIG)
    patient.air_quality = air_quality
    assert any(fragment in e for e in validate_patient(patient))
