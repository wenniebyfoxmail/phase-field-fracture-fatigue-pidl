import json
from pathlib import Path

import numpy as np
import pytest

from scripts.build_rrapinn_g4_contained_projector import (
    METHOD,
    ProjectorBuildError,
    build_projector,
)


def _write_source(path: Path, **overrides: np.ndarray) -> None:
    arrays = {
        "pidl_triangle_assignment": np.array([3, 8, 1, 7], dtype=np.int64),
        "mapping_contained": np.array([True, False, True, False], dtype=bool),
        "fem_centroids": np.array(
            [[0.0, 0.0], [5.0, 5.0], [0.2, -0.1], [-6.0, 4.0]],
            dtype=np.float64,
        ),
        "fem_element_area": np.array([0.2, 0.3, 0.4, 0.5], dtype=np.float64),
    }
    arrays.update(overrides)
    np.savez(path, **arrays)


def test_build_keeps_only_contained_headline_rows_and_records_contract(tmp_path: Path) -> None:
    source = tmp_path / "source.npz"
    output = tmp_path / "projector.npz"
    _write_source(source)

    manifest = build_projector(source, output)

    with np.load(output, allow_pickle=False) as built:
        assert set(built.files) == {
            "source_fem_row_index",
            "pidl_triangle_assignment",
            "fem_centroids",
            "fem_element_area",
        }
        np.testing.assert_array_equal(built["source_fem_row_index"], [0, 2])
        np.testing.assert_array_equal(built["pidl_triangle_assignment"], [3, 1])
        np.testing.assert_allclose(built["fem_centroids"], [[0.0, 0.0], [0.2, -0.1]])
        np.testing.assert_allclose(built["fem_element_area"], [0.2, 0.4])

    disk_manifest = json.loads(output.with_suffix(".manifest.json").read_text())
    assert disk_manifest == manifest
    assert manifest["method"] == METHOD
    assert manifest["projector"]["n_headline_rows"] == 2
    assert manifest["projector"]["n_excluded_fallback_rows"] == 2
    assert manifest["projector"]["fallback_rows_in_headline"] == 0
    assert manifest["constant_preservation_test"] == {
        "input_value": 1.0,
        "expected_value": 1.0,
        "max_abs_error": 0.0,
        "tolerance": 0.0,
        "pass": True,
    }
    assert "not a conservative overlap projector" in manifest["claim_boundary"]
    assert len(manifest["source"]["sha256"]) == 64
    assert len(manifest["projector"]["deterministic_sha256"]) == 64


def test_projector_hash_is_deterministic_and_area_alias_is_supported(tmp_path: Path) -> None:
    source = tmp_path / "source.npz"
    _write_source(source)
    with np.load(source, allow_pickle=False) as original:
        arrays = {key: np.asarray(original[key]) for key in original.files}
    arrays["fem_areas"] = arrays.pop("fem_element_area")
    np.savez(source, **arrays)

    first = build_projector(source, tmp_path / "first.npz")
    second = build_projector(source, tmp_path / "second.npz")

    assert (
        first["projector"]["deterministic_sha256"]
        == second["projector"]["deterministic_sha256"]
    )


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"mapping_contained": np.array([False] * 4, dtype=bool)}, "no mapping_contained"),
        ({"mapping_contained": np.array([1, 0, 1, 0], dtype=np.int8)}, "must be a 1-D bool"),
        ({"pidl_triangle_assignment": np.array([3, 8, -1, 7])}, "negative indices"),
        ({"fem_element_area": np.array([0.2, 0.3, 0.0, 0.5])}, "strictly positive"),
        ({"fem_centroids": np.zeros((4, 3))}, "shape"),
    ],
)
def test_invalid_sources_fail_closed(
    tmp_path: Path, overrides: dict[str, np.ndarray], match: str
) -> None:
    source = tmp_path / "source.npz"
    _write_source(source, **overrides)

    with pytest.raises(ProjectorBuildError, match=match):
        build_projector(source, tmp_path / "projector.npz")


def test_refuses_ambiguous_area_keys_and_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.npz"
    _write_source(source, fem_areas=np.ones(4, dtype=np.float64))
    with pytest.raises(ProjectorBuildError, match="exactly one area key"):
        build_projector(source, tmp_path / "ambiguous.npz")

    source.unlink()
    _write_source(source)
    output = tmp_path / "existing.npz"
    output.write_bytes(b"do not overwrite")
    with pytest.raises(ProjectorBuildError, match="refusing to overwrite"):
        build_projector(source, output)
    assert output.read_bytes() == b"do not overwrite"
