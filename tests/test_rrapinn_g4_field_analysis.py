from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_blind_contract import BLIND_METRICS_COLUMNS, REQUIRED_METRIC_KEYS  # noqa: E402
from rrapinn_g4_field_analysis import (  # noqa: E402
    ANALYSIS_INPUT_SCHEMA,
    PROJECTOR_METHOD,
    PROJECTOR_SCHEMA,
    AnalysisError,
    _projector_content_hash,
    analyze_blind_pair,
    mirror_grid_asymmetry,
    weighted_tail_summary,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(path: Path, base: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(base)), "sha256": _sha(path)}


def _write_fem(path: Path, cycle: int, active_scale: float = 1.0) -> None:
    with h5py.File(path, "w") as handle:
        state = handle.create_group("cycle_state")
        state["cycle"] = np.asarray([[cycle]], dtype=float)
        state["substep"] = np.asarray([[4]], dtype=float)
        state["effective_load_factor"] = np.asarray([[0.999999]])
        for name in ("damage_committed", "history_committed", "cyclemax_updated"):
            state[name] = np.asarray([[1]], dtype=np.uint8)
        # Four rows are mirror-closed about y=0.
        state["element_centroid"] = np.asarray([
            [-0.4, -0.4, 0.4, 0.4], [-0.4, 0.4, -0.4, 0.4]
        ])
        state["element_area"] = np.asarray([[1.0, 2.0, 1.0, 2.0]])
        state["d_elem"] = np.asarray([[0.1, 0.3, 0.6, 0.9]])
        state["alpha_bar_elem"] = np.asarray([[1.0, 2.0, 4.0, 8.0]])
        state["f_alpha_elem"] = np.asarray([[0.9, 0.8, 0.7, 0.6]])
        state["psi_raw_peak_elem"] = np.asarray([[1.0, 10.0, 100.0, 1000.0]])
        state["psi_active_peak_elem"] = active_scale * np.asarray([[1.0, 2.0, 8.0, 16.0]])
        first = state.create_group("first_detect")
        first["triggered"] = np.asarray([[0]], dtype=np.uint8)


def _state_npzs(root: Path, cycle: int, residual_scale: float, field_scale: float):
    step = 379 if cycle == 76 else 409
    residual = root / f"residual_{cycle}.npz"
    np.savez_compressed(
        residual,
        intensive=residual_scale * np.asarray([1.0, 2.0, 4.0, 8.0]),
        dual_area=np.asarray([1.0, 2.0, 1.0, 2.0]),
        interior_free_mask=np.asarray([True, True, True, True]),
        raw_step=np.asarray(step), physical_cycle=np.asarray(cycle),
        substep_index=np.asarray(3), displacement=np.asarray(0.12),
    )
    fields = root / f"fields_{cycle}.npz"
    np.savez_compressed(
        fields,
        alpha_elem=field_scale * np.asarray([0.1, 0.3, 0.6, 0.9]),
        hist_fat_elem=field_scale * np.asarray([1.0, 2.0, 4.0, 8.0]),
        f_fatigue_elem=np.asarray([0.9, 0.8, 0.7, 0.6]),
        psi_raw_elem=field_scale * np.asarray([1.0, 10.0, 100.0, 1000.0]),
        psi_active_elem=field_scale * np.asarray([1.0, 2.0, 8.0, 16.0]),
        elem_x=np.asarray([-0.4, -0.4, 0.4, 0.4]),
        elem_y=np.asarray([-0.4, 0.4, -0.4, 0.4]),
        raw_step=np.asarray(step), physical_cycle=np.asarray(cycle),
        substep_index=np.asarray(3), displacement=np.asarray(0.12),
    )
    return residual, fields


def _event(path: Path, step: int) -> None:
    adjusted = step - 1
    substep = adjusted % 5
    path.write_text(json.dumps({
        "schema": "boundary-first-detect-v1", "raw_step": step,
        "physical_cycle": adjusted // 5 + 1, "substep_index": substep,
        "substep_displacement": (0.03, 0.06, 0.09, 0.12, 0.0)[substep],
        "qualifying_nodes": 3, "boundary_nodes": 10,
        "boundary_max_damage": 0.96, "x_min_exclusive": 0.48,
        "damage_threshold_exclusive": 0.95, "minimum_nodes": 3,
        "criterion": "right_boundary_nodes_gt_damage_threshold",
        "trigger_source": "boundary_only",
    }, sort_keys=True), encoding="utf-8")


def _fixture(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    fem76, fem82 = tmp_path / "fem76.mat", tmp_path / "fem82.mat"
    _write_fem(fem76, 76)
    _write_fem(fem82, 82)
    projector_npz = tmp_path / "projector.npz"
    arrays = {
        "source_fem_row_index": np.arange(4, dtype=np.int64),
        "pidl_triangle_assignment": np.arange(4, dtype=np.int64),
        "fem_centroids": np.asarray([
            [-0.4, -0.4], [-0.4, 0.4], [0.4, -0.4], [0.4, 0.4],
        ]),
        "fem_element_area": np.asarray([1., 2., 1., 2.]),
    }
    np.savez_compressed(projector_npz, **arrays)
    projector_manifest = tmp_path / "projector.json"
    projector_manifest.write_text(json.dumps({
        "schema_version": PROJECTOR_SCHEMA, "method": PROJECTOR_METHOD,
        "headline_policy": "mapping_contained_true_only",
        "artifact": _artifact(projector_npz, tmp_path),
        "deterministic_sha256": _projector_content_hash(arrays),
        "fem_sha256": {"76": _sha(fem76), "82": _sha(fem82)},
        "n_fem_rows": 4, "n_headline_rows": 4, "pidl_triangle_count": 4,
    }, sort_keys=True), encoding="utf-8")
    manifests = []
    for arm, residual_scale, field_scale, event_step in (
        ("arm_0123abcd", 1.0, 1.0, 444),
        ("arm_fedcba98", 0.5, 0.9, 404),
    ):
        root = tmp_path / arm
        root.mkdir()
        states = {}
        for cycle in (76, 82):
            residual, fields = _state_npzs(root, cycle, residual_scale, field_scale)
            states[str(cycle)] = {
                "cycle": cycle, "raw_step": 379 if cycle == 76 else 409,
                "residual_fields": _artifact(residual, root),
                "element_fields": _artifact(fields, root),
            }
        receipt = root / "first_detect.json"
        _event(receipt, event_step)
        manifest = root / "analysis.json"
        manifest.write_text(json.dumps({
            "schema": ANALYSIS_INPUT_SCHEMA, "opaque_arm": arm,
            "development_case": "U0.12", "states": states,
            "event": {"kind": "first_detect", "receipt": _artifact(receipt, root)},
        }, sort_keys=True), encoding="utf-8")
        manifests.append(manifest)
    return manifests, fem76, fem82, projector_manifest


def test_weighted_tail_summary_uses_fractional_one_percent_area():
    result = weighted_tail_summary(np.asarray([1.0, 10.0]), np.asarray([9.0, 1.0]))
    assert result["mean"] == pytest.approx(1.9)
    assert result["cvar99"] == pytest.approx(10.0)
    assert result["worst_1pct_area_mass"] == pytest.approx(1.0 / 19.0)


def test_mirror_grid_asymmetry_handles_nonmatching_element_sampling():
    centroids = np.asarray([
        [-0.2, -0.2], [-0.2, -0.201], [-0.2, 0.2],
        [0.2, -0.2], [0.2, 0.2], [0.2, 0.201],
    ])
    areas = np.asarray([0.5, 0.5, 1.0, 1.0, 0.5, 0.5])
    values = np.ones(6)
    asymmetry, coverage = mirror_grid_asymmetry(values, centroids, areas)
    assert asymmetry == pytest.approx(0.0)
    assert coverage == pytest.approx(1.0)


def test_mirror_grid_asymmetry_fails_on_low_paired_coverage():
    centroids = np.asarray([[-0.2, -0.2], [0.2, -0.2], [0.3, -0.3]])
    with pytest.raises(AnalysisError, match="paired-area coverage"):
        mirror_grid_asymmetry(np.ones(3), centroids, np.ones(3))


def test_blind_pair_writes_exact_grid_and_event_status(tmp_path: Path):
    manifests, fem76, fem82, projector = _fixture(tmp_path)
    output = tmp_path / "blind.csv"
    rows = analyze_blind_pair(
        arm_manifests=manifests, fem_c76=fem76, fem_c82=fem82,
        projector_manifest=projector, output_csv=output,
    )
    assert len(rows) == 2 * len(REQUIRED_METRIC_KEYS) == 72
    with output.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        disk_rows = list(reader)
        assert reader.fieldnames == list(BLIND_METRICS_COLUMNS)
    assert disk_rows == rows
    assert all("treatment" not in row and "risk" not in row for row in rows)
    status = {
        (row["opaque_arm"], row["cycle"]): row["status"]
        for row in rows if row["metric"] == "active_log_mean"
    }
    assert status[("arm_0123abcd", "82")] == "pre_first_detect"
    assert status[("arm_fedcba98", "82")] == "post_first_detect"
    assert next(
        float(row["value"]) for row in rows
        if row["opaque_arm"] == "arm_0123abcd"
        and row["metric"] == "active_log_mean" and row["cycle"] == "82"
    ) == pytest.approx(0.0)


def test_hash_state_schema_and_exclusive_create_fail_closed(tmp_path: Path):
    manifests, fem76, fem82, projector = _fixture(tmp_path)
    payload = json.loads(manifests[0].read_text())
    payload["risk_mode"] = "absent"
    manifests[0].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AnalysisError, match="schema/keys"):
        analyze_blind_pair(
            arm_manifests=manifests, fem_c76=fem76, fem_c82=fem82,
            projector_manifest=projector, output_csv=tmp_path / "out.csv",
        )

    manifests, fem76, fem82, projector = _fixture(tmp_path / "second")
    fields = manifests[0].parent / "fields_82.npz"
    fields.write_bytes(fields.read_bytes() + b"tamper")
    with pytest.raises(AnalysisError, match="SHA256"):
        analyze_blind_pair(
            arm_manifests=manifests, fem_c76=fem76, fem_c82=fem82,
            projector_manifest=projector, output_csv=tmp_path / "bad.csv",
        )

    manifests, fem76, fem82, projector = _fixture(tmp_path / "third")
    output = tmp_path / "owned.csv"
    output.write_text("owned\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        analyze_blind_pair(
            arm_manifests=manifests, fem_c76=fem76, fem_c82=fem82,
            projector_manifest=projector, output_csv=output,
        )


def test_confirmation_or_wrong_peak_semantics_cannot_replace_first_detect(tmp_path: Path):
    manifests, fem76, fem82, projector = _fixture(tmp_path)
    receipt = manifests[0].parent / "first_detect.json"
    payload = json.loads(receipt.read_text())
    payload["trigger_source"] = "confirmation"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    manifest = json.loads(manifests[0].read_text())
    manifest["event"]["receipt"]["sha256"] = _sha(receipt)
    manifests[0].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AnalysisError, match="first-detect"):
        analyze_blind_pair(
            arm_manifests=manifests, fem_c76=fem76, fem_c82=fem82,
            projector_manifest=projector, output_csv=tmp_path / "bad.csv",
        )
