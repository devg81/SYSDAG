"""M1 milestone checks: patient ID, schema validation, ECG reuse,
reproducibility, and duplicate-ID detection (CLAUDE.md §8).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import build_patient, load_config  # noqa: E402
from integration.patient_id import generate_patient_id, is_valid_patient_id  # noqa: E402
from validation.structural import check_duplicate_ids  # noqa: E402

CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")


def test_patient_id_format():
    assert generate_patient_id(1) == "PAT_000001"
    assert is_valid_patient_id("PAT_000001")
    assert not is_valid_patient_id("PAT_1")
    assert not is_valid_patient_id("pat_000001")


def test_build_one_patient_is_structurally_valid():
    patient = build_patient(1, CONFIG)
    assert patient.patient_id == "PAT_000001"
    assert patient.validation.validated, patient.validation.errors
    assert patient.ecg is not None
    assert patient.ecg.signal_shape == [1000, 12]
    assert 0 <= patient.demographics.age <= 89


def test_reproducibility_same_seed_same_patient():
    p1 = build_patient(1, CONFIG)
    p2 = build_patient(1, CONFIG)
    assert p1.ecg.ecg_id == p2.ecg.ecg_id
    assert p1.demographics.age == p2.demographics.age
    assert p1.demographics.sex == p2.demographics.sex


def test_different_sequence_can_pick_different_record():
    p1 = build_patient(1, CONFIG)
    p2 = build_patient(2, CONFIG)
    assert p1.patient_id != p2.patient_id


def test_duplicate_id_detection():
    p1 = build_patient(1, CONFIG)
    p2 = build_patient(1, CONFIG)
    errors = check_duplicate_ids([p1, p2])
    assert errors
