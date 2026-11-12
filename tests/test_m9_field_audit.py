"""M9-1: the read-only field-completeness audit counts valid/null/invalid
correctly and never touches its input directory."""

import json
from pathlib import Path

import pytest

from generation.indian_population import load_config
from integration.audit_field_completeness import audit, floor_mass_removed

_SRC = Path("outputs/m8/100k_patients_v08")


def _make_dir(tmp_path: Path) -> Path:
    # Copies one frozen v0.8 record into tmp_path -- the dataset itself is only read.
    src = _SRC / "PAT_000001.json"
    if not src.exists():
        pytest.skip("frozen v0.8 dataset (gitignored) not present")
    rec = json.loads(src.read_text(encoding="utf-8"))
    good = dict(rec, patient_id="PAT_000001")
    bad = json.loads(json.dumps(rec))
    bad["patient_id"] = "PAT_000002"
    bad["demographics"]["state"] = "Atlantis"
    bad["blood_pressure"]["diastolic_mm_hg"] = bad["blood_pressure"]["systolic_mm_hg"] - 5  # PP < 20
    for r in (good, bad):
        (tmp_path / f"{r['patient_id']}.json").write_text(json.dumps(r), encoding="utf-8")
    return tmp_path


def test_audit_counts_and_is_read_only(tmp_path):
    d = _make_dir(tmp_path)
    before = {p.name: p.read_bytes() for p in d.iterdir()}
    r = audit(d, load_config())
    assert r["n_records"] == 2
    assert r["fields"]["demographics.state"]["invalid"] == 1
    assert r["fields"]["blood_pressure.pulse_pressure(derived)"]["invalid"] == 1
    assert r["fields"]["family_history"]["null"] == 2
    assert r["fields"]["demographics.height_cm"]["null"] == 2
    assert {p.name: p.read_bytes() for p in d.iterdir()} == before


def test_floor_mass_removed_is_a_valid_percentage():
    rows = floor_mass_removed(load_config())
    assert rows and all(0.0 <= row["mass_removed_by_floor_pct"] < 100.0 for row in rows)
