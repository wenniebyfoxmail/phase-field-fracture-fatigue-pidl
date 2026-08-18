#!/usr/bin/env python3
"""Build a fail-closed G4 centroid-containment assignment artifact.

This is a row-selection plus triangle-assignment operator.  It is deliberately
not an area-overlap or conservative projector: only FEM rows whose source
``mapping_contained`` value is true are eligible for headline comparisons.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_VERSION = "rrapinn-g4-contained-projector-v1"
METHOD = "centroid_containment_assignment"
AREA_KEYS = ("fem_element_area", "fem_areas")


class ProjectorBuildError(ValueError):
    """Raised when the source cannot satisfy the fail-closed contract."""


def _canonical_array(array: np.ndarray, dtype: str) -> np.ndarray:
    return np.ascontiguousarray(np.asarray(array, dtype=np.dtype(dtype)))


def _update_array_hash(digest: Any, name: str, array: np.ndarray) -> None:
    name_bytes = name.encode("utf-8")
    dtype_bytes = array.dtype.str.encode("ascii")
    digest.update(struct.pack("<Q", len(name_bytes)))
    digest.update(name_bytes)
    digest.update(struct.pack("<Q", len(dtype_bytes)))
    digest.update(dtype_bytes)
    digest.update(struct.pack("<Q", array.ndim))
    digest.update(struct.pack(f"<{array.ndim}q", *array.shape))
    digest.update(array.tobytes(order="C"))


def deterministic_projector_hash(
    source_fem_row_index: np.ndarray,
    pidl_triangle_assignment: np.ndarray,
    fem_centroids: np.ndarray,
    fem_element_area: np.ndarray,
) -> str:
    """Hash the canonical operator content, independent of NPZ ZIP metadata."""
    digest = hashlib.sha256()
    digest.update((SCHEMA_VERSION + "\0" + METHOD).encode("ascii"))
    for name, value in (
        ("source_fem_row_index", source_fem_row_index),
        ("pidl_triangle_assignment", pidl_triangle_assignment),
        ("fem_centroids", fem_centroids),
        ("fem_element_area", fem_element_area),
    ):
        _update_array_hash(digest, name, value)
    return digest.hexdigest()


def _load_and_validate(source_path: Path) -> tuple[dict[str, np.ndarray], str, int]:
    if not source_path.is_file():
        raise ProjectorBuildError(f"source NPZ does not exist: {source_path}")

    # Hash and parse the same immutable byte snapshot so the manifest cannot
    # describe a different file revision if the source changes during a build.
    try:
        source_bytes = source_path.read_bytes()
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        with np.load(io.BytesIO(source_bytes), allow_pickle=False) as source:
            required = {
                "pidl_triangle_assignment",
                "mapping_contained",
                "fem_centroids",
            }
            missing = sorted(required.difference(source.files))
            if missing:
                raise ProjectorBuildError(f"source NPZ missing keys: {missing}")
            present_area_keys = [key for key in AREA_KEYS if key in source.files]
            if len(present_area_keys) != 1:
                raise ProjectorBuildError(
                    "source NPZ must contain exactly one area key: "
                    f"{list(AREA_KEYS)}; found {present_area_keys}"
                )

            assignment_raw = np.asarray(source["pidl_triangle_assignment"])
            contained_raw = np.asarray(source["mapping_contained"])
            centroids_raw = np.asarray(source["fem_centroids"])
            areas_raw = np.asarray(source[present_area_keys[0]])
    except ProjectorBuildError:
        raise
    except Exception as exc:
        raise ProjectorBuildError(f"cannot read source NPZ: {exc}") from exc

    if assignment_raw.ndim != 1 or not np.issubdtype(assignment_raw.dtype, np.integer):
        raise ProjectorBuildError("pidl_triangle_assignment must be a 1-D integer array")
    if not np.can_cast(assignment_raw.dtype, np.dtype("<i8"), casting="safe"):
        raise ProjectorBuildError("pidl_triangle_assignment cannot be represented as int64")
    if contained_raw.ndim != 1 or contained_raw.dtype != np.dtype(bool):
        raise ProjectorBuildError("mapping_contained must be a 1-D bool array")
    n_rows = assignment_raw.shape[0]
    if n_rows == 0:
        raise ProjectorBuildError("source mapping has zero FEM rows")
    if contained_raw.shape != (n_rows,):
        raise ProjectorBuildError("mapping_contained length does not match assignment")
    if centroids_raw.shape != (n_rows, 2):
        raise ProjectorBuildError("fem_centroids must have shape (n_fem_rows, 2)")
    if areas_raw.shape != (n_rows,):
        raise ProjectorBuildError("FEM area array length does not match assignment")
    centroids_are_real = np.issubdtype(
        centroids_raw.dtype, np.integer
    ) or np.issubdtype(centroids_raw.dtype, np.floating)
    areas_are_real = np.issubdtype(areas_raw.dtype, np.integer) or np.issubdtype(
        areas_raw.dtype, np.floating
    )
    if not centroids_are_real:
        raise ProjectorBuildError("fem_centroids must have a real numeric dtype")
    if not areas_are_real:
        raise ProjectorBuildError("FEM areas must have a real numeric dtype")
    if not np.isfinite(centroids_raw).all():
        raise ProjectorBuildError("fem_centroids contains non-finite values")
    if not np.isfinite(areas_raw).all() or np.any(areas_raw <= 0.0):
        raise ProjectorBuildError("FEM areas must be finite and strictly positive")
    if np.any(assignment_raw < 0):
        raise ProjectorBuildError("pidl_triangle_assignment contains negative indices")

    contained = np.asarray(contained_raw, dtype=bool)
    if not np.any(contained):
        raise ProjectorBuildError("source has no mapping_contained=True rows")

    source_rows = _canonical_array(np.flatnonzero(contained), "<i8")
    headline_assignment = _canonical_array(assignment_raw[contained], "<i8")
    headline_centroids = _canonical_array(centroids_raw[contained], "<f8")
    headline_areas = _canonical_array(areas_raw[contained], "<f8")

    # Fail closed: reconstructing the source mask from output row indices must
    # select true rows only.  No fallback marker is written to the artifact.
    if not np.all(contained[source_rows]):
        raise ProjectorBuildError("internal error: fallback row entered headline output")

    return (
        {
            "source_fem_row_index": source_rows,
            "pidl_triangle_assignment": headline_assignment,
            "fem_centroids": headline_centroids,
            "fem_element_area": headline_areas,
        },
        source_sha256,
        n_rows,
    )


def build_projector(
    source_path: Path | str,
    output_path: Path | str,
    manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    if output_path.suffix != ".npz":
        raise ProjectorBuildError("output path must end in .npz")
    if manifest_path is None:
        manifest_path = output_path.with_suffix(".manifest.json")
    manifest_path = Path(manifest_path).expanduser().resolve()
    if source_path in (output_path, manifest_path):
        raise ProjectorBuildError("source and output paths must be different")
    for path in (output_path, manifest_path):
        if path.exists():
            raise ProjectorBuildError(f"refusing to overwrite existing output: {path}")
    if output_path.parent != manifest_path.parent:
        raise ProjectorBuildError("NPZ and manifest must share one output directory")

    arrays, source_sha256, n_source = _load_and_validate(source_path)
    projector_sha256 = deterministic_projector_hash(**arrays)

    n_headline = int(arrays["source_fem_row_index"].size)

    triangle_ones = np.ones(
        int(arrays["pidl_triangle_assignment"].max()) + 1,
        dtype=np.float64,
    )
    projected_constant = triangle_ones[arrays["pidl_triangle_assignment"]]
    constant_error = float(np.max(np.abs(projected_constant - 1.0)))
    constant_pass = bool(constant_error == 0.0)
    if not constant_pass:
        raise ProjectorBuildError("constant-preservation self-test failed")

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "method": METHOD,
        "claim_boundary": (
            "Centroid-containment triangle assignment only; this is not a "
            "conservative overlap projector."
        ),
        "headline_policy": "mapping_contained_true_only",
        "source": {
            "path": str(source_path),
            "sha256": source_sha256,
            "n_fem_rows": n_source,
        },
        "projector": {
            "deterministic_sha256": projector_sha256,
            "n_headline_rows": n_headline,
            "n_excluded_fallback_rows": n_source - n_headline,
            "fallback_rows_in_headline": 0,
        },
        "constant_preservation_test": {
            "input_value": 1.0,
            "expected_value": 1.0,
            "max_abs_error": constant_error,
            "tolerance": 0.0,
            "pass": constant_pass,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    npz_fd, npz_tmp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    manifest_fd, manifest_tmp_name = tempfile.mkstemp(
        prefix=f".{manifest_path.name}.", suffix=".tmp", dir=manifest_path.parent
    )
    try:
        with os.fdopen(npz_fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        installed_npz = False
        try:
            # Hard-link installation is exclusive: unlike os.replace, it can
            # never overwrite a path created concurrently after preflight.
            os.link(npz_tmp_name, output_path)
            installed_npz = True
            os.link(manifest_tmp_name, manifest_path)
        except FileExistsError as exc:
            if installed_npz:
                output_path.unlink()
            raise ProjectorBuildError(
                "output appeared during build; refusing overwrite"
            ) from exc
        except Exception:
            if installed_npz:
                output_path.unlink()
            raise
    finally:
        for temporary in (npz_tmp_name, manifest_tmp_name):
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Existing mapping NPZ")
    parser.add_argument("--output", type=Path, required=True, help="New headline-only NPZ")
    parser.add_argument("--manifest", type=Path, help="Optional manifest JSON path")
    args = parser.parse_args()
    manifest = build_projector(args.source, args.output, args.manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
