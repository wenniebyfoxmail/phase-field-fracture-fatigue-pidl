#!/usr/bin/env python3
"""Fail-closed data and lineage contracts for S01-E002."""

from __future__ import annotations

from typing import Mapping, Sequence


PROTOCOL = "S01-E002-v1"
LOCATION_KEYS = (
    "train_locations",
    "validation_locations",
    "confirmatory_test_locations",
    "consumed_or_excluded_locations",
    "reserve_test_locations",
)


def validate_data_lock(lock: Mapping[str, object]) -> None:
    missing = set(LOCATION_KEYS) - set(lock)
    if missing:
        raise ValueError(f"data lock lacks location partitions: {sorted(missing)}")
    observed: dict[str, str] = {}
    for key in LOCATION_KEYS:
        values = lock[key]
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise ValueError(f"data lock {key} must be a sequence")
        normalized = [str(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"data lock {key} contains duplicate locations")
        for location in normalized:
            if location in observed:
                raise ValueError(
                    f"data lock location {location} overlaps {observed[location]} and {key}"
                )
            observed[location] = key
    if lock.get("independence_unit") != "reid":
        raise ValueError("data lock independence unit must be reid")
    if lock.get("selection_uses_pixels") is not False:
        raise ValueError("confirmatory selection must not use image pixels")


def validate_tile_manifest_contract(
    manifest: Mapping[str, object],
    *,
    data_lock_sha256: str,
    run_config_sha256: str,
    workbook_sha256: str,
    source_manifest_sha256: str | None,
) -> None:
    expected = {
        "protocol": PROTOCOL,
        "data_lock_sha256": data_lock_sha256,
        "run_config_sha256": run_config_sha256,
        "workbook_sha256": workbook_sha256,
    }
    if source_manifest_sha256 is not None:
        expected["source_manifest_sha256"] = source_manifest_sha256
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(f"tile manifest mismatch at {field}")
