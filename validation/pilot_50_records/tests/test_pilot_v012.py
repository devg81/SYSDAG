"""Gates for the v0.12 pilot rebuild (-jatin, 2026-11-12).

Skips until `rebuild_v012.py` has been run (it needs PTB-XL + pandas). Once
the output exists, these replace the v0.8 migration gates in
test_pilot_50_records.py, which describe the superseded v0.8 artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PILOT_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PILOT_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generation.indian_population import load_config  # noqa: E402
from integration.migrate_v07_to_v08 import _dict_to_patient  # noqa: E402
from schemas.patient_schema import SCHEMA_VERSION  # noqa: E402
from validation.clinical_consistency import validate_clinical_consistency  # noqa: E402
from validation.structural import validate_patient  # noqa: E402

RECORDS = _PILOT_DIR / "output_v012" / "patient_records_50_v012.json"
MANIFEST = _PILOT_DIR / "input" / "source_manifest.json"

pytestmark = pytest.mark.skipif(not RECORDS.exists(), reason="run rebuild_v012.py first (needs PTB-XL + pandas)")


@pytest.fixture(scope="module")
def records():
    return json.loads(RECORDS.read_text(encoding="utf-8"))


def test_same_50_ids_as_manifest(records):
    ids = json.loads(MANIFEST.read_text(encoding="utf-8"))["patient_ids"]
    assert [r["patient_id"] for r in records] == ids


def test_current_schema_version(records):
    assert {r["provenance"]["schema_version"] for r in records} == {SCHEMA_VERSION}


def test_every_record_revalidates(records):
    cfg = load_config()
    from generation.indian_population import valid_states

    for r in records:
        r = json.loads(json.dumps(r))
        r["validation"].pop("clinical_consistency", None)
        p = _dict_to_patient(r)
        assert validate_patient(p, valid_states=valid_states(cfg)) == [], r["patient_id"]
        res = validate_clinical_consistency(p, cfg)
        assert res.valid, (r["patient_id"], res.errors)
        assert "hyperlipidemia_derived_from_lipid_interpretations" in res.checks_performed
        assert "lai_risk_tier_consistency" in res.checks_performed
