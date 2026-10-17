from __future__ import annotations

import copy
from pathlib import Path

from scripts.synthetic_fracture_cv.render_analytic_sequence import CASES, TEXTURE_SEEDS, generate_fixture
from scripts.synthetic_fracture_cv.validate_manifest import validate_manifest, validate_records


def test_generated_manifest_is_valid_and_within_fixture_limit(tmp_path: Path) -> None:
    records = generate_fixture(tmp_path)
    assert len(records) == len(CASES) * len(TEXTURE_SEEDS) == 14
    assert validate_manifest(tmp_path / "manifest.json") == []
    assert {record["lineage_id"] for record in records} == {"analytic-straight-slit-lineage-v1"}
    assert {record["split"] for record in records} == {"verification_only"}


def test_validator_rejects_lineage_split_and_active_event_metadata(tmp_path: Path) -> None:
    records = generate_fixture(tmp_path)
    records[0]["split"] = "train"
    records[1]["split"] = "test"
    records[2]["event_first_detect"] = 4
    errors = validate_records(records, tmp_path)
    assert any("crosses splits" in error for error in errors)
    assert any("event fields are not inert" in error for error in errors)


def test_validator_rejects_incomplete_frozen_fixture(tmp_path: Path) -> None:
    records = generate_fixture(tmp_path)
    only_zero = [record for record in records if record["state_id"] == "zero"]
    errors = validate_records(only_zero, tmp_path)
    assert any("expected exactly 14 frozen records" in error for error in errors)
    assert any("frozen case/seed set mismatch" in error for error in errors)


def test_validator_rejects_ambiguous_target_promotion(tmp_path: Path) -> None:
    records = copy.deepcopy(generate_fixture(tmp_path))
    for record in records:
        if record["state_id"] == "opening_0p25px":
            record["target_status"] = "resolved"
    errors = validate_records(records, tmp_path)
    assert any("does not match frozen" in error for error in errors)


def test_validator_rejects_nonverification_split(tmp_path: Path) -> None:
    records = copy.deepcopy(generate_fixture(tmp_path))
    for record in records:
        record["split"] = "train"
    errors = validate_records(records, tmp_path)
    assert any("G1 split must be 'verification_only'" in error for error in errors)


def test_validator_rejects_missing_required_field(tmp_path: Path) -> None:
    records = generate_fixture(tmp_path)
    del records[0]["geometry_path"]
    errors = validate_records(records, tmp_path)
    assert any("missing fields" in error and "geometry_path" in error for error in errors)
