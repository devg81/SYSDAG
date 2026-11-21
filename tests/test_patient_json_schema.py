"""schemas/patient_schema.json must accept every generated record on disk and reject malformed ones."""

import copy
import glob
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/patient_schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
SAMPLE_FILES = sorted(glob.glob(str(ROOT / "review_samples_v0*/*.json")))


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_schema_is_valid_json_schema():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", SAMPLE_FILES, ids=lambda p: Path(p).parent.name + "/" + Path(p).name)
def test_generated_samples_conform(path):
    errors = [e.message for e in VALIDATOR.iter_errors(_load(path))]
    assert errors == []


def test_pilot_records_conform():
    pilot = ROOT / "validation/pilot_50_records/output/patient_records_50.json"
    if not pilot.exists():
        pytest.skip("pilot output not present")
    for rec in _load(pilot):
        assert list(VALIDATOR.iter_errors(rec)) == [], rec["patient_id"]


@pytest.mark.parametrize("mutate", [
    lambda r: r["demographics"].update(sex=2),
    lambda r: r.update(unexpected_field=1),
    lambda r: r["risk_factors"].update(smoking_status="sometimes"),
    lambda r: r.update(patient_id="P1"),
    lambda r: r.pop("validation"),
])
def test_malformed_record_rejected(mutate):
    rec = copy.deepcopy(_load(SAMPLE_FILES[-1]))
    mutate(rec)
    assert not VALIDATOR.is_valid(rec)
