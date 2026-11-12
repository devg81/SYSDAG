"""M3.5 Step 4: regression tests for ingestion/ptbxl_source.py's
process-level caching (added purely for performance — these tests confirm
it doesn't silently return stale/wrong data for different inputs).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration.build_patient import load_config  # noqa: E402
from ingestion.ptbxl_source import (  # noqa: E402
    _cached_label_map,
    _cached_ptbxl_df,
    load_ptbxl_record,
    pick_ecg_id,
)

CONFIG = load_config(REPO_ROOT / "configs" / "base.yaml")
PTBXL_CSV = str(REPO_ROOT / CONFIG["ptbxl_csv"])
SCP_CSV = str(REPO_ROOT / CONFIG["scp_csv"])


def test_cached_label_map_distinguishes_thresholds():
    strict = _cached_label_map(PTBXL_CSV, SCP_CSV, 90.0)
    loose = _cached_label_map(PTBXL_CSV, SCP_CSV, 10.0)
    # A stricter confidence threshold must yield fewer (or equal) total
    # superclass assignments than a looser one -- if the cache wrongly
    # conflated the two calls, these would be identical.
    strict_total = sum(len(v["superclasses"]) for v in strict.values())
    loose_total = sum(len(v["superclasses"]) for v in loose.values())
    assert strict_total < loose_total


def test_cached_label_map_same_args_returns_consistent_content():
    a = _cached_label_map(PTBXL_CSV, SCP_CSV, 50.0)
    b = _cached_label_map(PTBXL_CSV, SCP_CSV, 50.0)
    assert a == b


def test_cached_ptbxl_df_reused_across_calls():
    df1 = _cached_ptbxl_df(PTBXL_CSV)
    df2 = _cached_ptbxl_df(PTBXL_CSV)
    assert df1 is df2  # same cached object, not re-read from disk


def test_load_ptbxl_record_and_pick_ecg_id_still_agree_with_config_threshold():
    ecg_id = pick_ecg_id(PTBXL_CSV, CONFIG["training_folds"], seed=999)
    record = load_ptbxl_record(ecg_id, PTBXL_CSV, SCP_CSV, CONFIG.get("scp_threshold", 50.0))
    assert record["ecg_id"] == ecg_id
    assert record["strat_fold"] in CONFIG["training_folds"]
