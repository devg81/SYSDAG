"""Canonical synthetic patient-ID generation.

One format, defined once, so every pipeline stage (ingestion, generation,
export) references the same ID scheme instead of inventing its own.
"""

from __future__ import annotations

import re

_ID_FORMAT = "PAT_{:06d}"
ID_PATTERN = re.compile(r"^PAT_\d{6}$")


def generate_patient_id(sequence: int) -> str:
    """Return the canonical patient ID for a 1-based sequence number."""
    if sequence < 1:
        raise ValueError(f"sequence must be >= 1, got {sequence}")
    return _ID_FORMAT.format(sequence)


def is_valid_patient_id(patient_id: str) -> bool:
    return bool(ID_PATTERN.match(patient_id))
