from __future__ import annotations

import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from analysis.toy_road_t3_mechanism_20260819.evidence import (
    EvidencePaths,
    build_compact_evidence,
    load_json_strict,
    sha256_file,
    validate_shard_inventory,
    validate_t3_bindings,
    verify_compact_evidence,
)
from analysis.toy_road_t3_mechanism_20260819.mirror_to_onedrive import (
    mirror_verified,
    validate_source_tree,
)
from analysis.toy_road_t3_mechanism_20260819.mechanism import (
    build_comparison_pairs,
    classify_memory,
    element_geometry,
    load_mesh,
    load_peak_fields,
    process_zone,
    reduce_field,
)
from analysis.toy_road_t3_mechanism_20260819.run_analysis import run_analysis


REPO = Path(__file__).resolve().parents[1]
REAL_T3_OUTPUT = Path(r"C:\q4diag\toy-road-t3-production-7c56ff3-run1\output")
REAL_T3_RUN = REAL_T3_OUTPUT.parent
REAL_T3_SEAL = Path(r"C:\q4diag\toy-road-t3-sibling-seal-2ff8b5f")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _real_paths() -> EvidencePaths:
    return EvidencePaths(
        authenticated_terminal=REAL_T3_SEAL / "T3_AUTHENTICATED_TERMINAL.json",
        terminal_adjudication=(
            REAL_T3_SEAL
            / "terminal_evidence"
            / "T3_SIBLING_TERMINAL_ADJUDICATION.json"
        ),
        terminal_manifest=REAL_T3_OUTPUT / "TERMINAL_MANIFEST.json",
        terminal_result=REAL_T3_OUTPUT / "TERMINAL_RESULT.json",
        event_metadata=REAL_T3_OUTPUT / "EVENT_METADATA.json",
        c5_receipt=(
            REAL_T3_OUTPUT / "qualification" / "C5_NUMERICAL_GATE_RECEIPT.json"
        ),
        c5_trace=REAL_T3_OUTPUT / "qualification" / "C5_STAGGER_TRACE.csv",
        runtime_measurement=(
            REAL_T3_RUN / "receipts" / "T3_RUNTIME_MEASUREMENT.json"
        ),
        execution_input_lock=REAL_T3_OUTPUT / "EXECUTION_INPUT_LOCK.json",
        launch_receipt=REAL_T3_RUN / "receipts" / "T3_SIBLING_LAUNCH_RECEIPT.json",
    )


def test_load_json_strict_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"status":"PASS","status":"FAIL"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key: status"):
        load_json_strict(path)


def test_load_json_strict_rejects_nan(tmp_path: Path) -> None:
    path = tmp_path / "nan.json"
    path.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON constant"):
        load_json_strict(path)


def test_validate_shard_inventory_requires_71_consecutive_entries() -> None:
    files = [
        {
            "path": f"substeps/cycle_{cycle:04d}.mat",
            "sha256": f"{cycle:064x}",
            "identity": {"size": cycle},
        }
        for cycle in range(1, 72)
    ]
    records = validate_shard_inventory(files)
    assert len(records) == 71
    assert records[0].path == "substeps/cycle_0001.mat"
    assert records[-1].path == "substeps/cycle_0071.mat"

    with pytest.raises(ValueError, match="exactly 71"):
        validate_shard_inventory(files[:-1])


def test_validate_t3_bindings_rejects_manifest_tampering(tmp_path: Path) -> None:
    paths = _real_paths()
    assert validate_t3_bindings(paths)["status"] == "PASS"

    tampered_manifest = tmp_path / "TERMINAL_MANIFEST.json"
    tampered_manifest.write_bytes(paths.terminal_manifest.read_bytes() + b" ")
    tampered = EvidencePaths(
        **{
            **paths.__dict__,
            "terminal_manifest": tampered_manifest,
        }
    )
    with pytest.raises(ValueError, match="terminal manifest SHA-256 mismatch"):
        validate_t3_bindings(tampered)


def test_compact_locator_is_portable_and_non_authorizing(tmp_path: Path) -> None:
    destination = tmp_path / "compact"
    result = build_compact_evidence(
        _real_paths(),
        destination,
        (
            "griphfith/toy-road-evidence/T3_loading_history/"
            "manifest-455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"
        ),
    )
    assert result["status"] == "PASS"
    locator = load_json_strict(destination / "ONEDRIVE_PACKAGE.json")
    encoded = json.dumps(locator, sort_keys=True)
    assert "C:\\Users\\" not in encoded
    assert locator["authorization_capability"] is None
    assert locator["follow_on_authorized"] is False
    assert locator["cycle_shard_count"] == 71
    assert verify_compact_evidence(destination)["status"] == "PASS"


def test_verify_compact_evidence_detects_modified_file(tmp_path: Path) -> None:
    destination = tmp_path / "compact"
    build_compact_evidence(
        _real_paths(),
        destination,
        "griphfith/toy-road-evidence/T3_loading_history/manifest-455b149b",
    )
    target = destination / "TERMINAL_RESULT.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="compact evidence SHA-256 mismatch"):
        verify_compact_evidence(destination)


def test_sha256_file_matches_direct_hash(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"toy-road-t3")
    assert sha256_file(path) == _sha(path)


def _tiny_mirror_source(tmp_path: Path) -> tuple[Path, list[Path]]:
    output = tmp_path / "source-output"
    (output / "substeps").mkdir(parents=True)
    (output / "TERMINAL_MANIFEST.json").write_text("manifest", encoding="utf-8")
    (output / "substeps" / "cycle_0001.mat").write_bytes(b"cycle-one")
    evidence = tmp_path / "external.json"
    evidence.write_text('{"status":"PASS"}', encoding="utf-8")
    return output, [evidence]


def test_mirror_refuses_existing_destination(tmp_path: Path) -> None:
    output, evidence = _tiny_mirror_source(tmp_path)
    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(FileExistsError, match="destination exists"):
        mirror_verified(output, evidence, destination)


def test_validate_source_tree_rejects_symlink(tmp_path: Path) -> None:
    output, _ = _tiny_mirror_source(tmp_path)
    link = output / "linked-cycle.mat"
    try:
        link.symlink_to(output / "substeps" / "cycle_0001.mat")
    except OSError:
        pytest.skip("Windows symlink creation is unavailable")
    with pytest.raises(ValueError, match="link/reparse point"):
        validate_source_tree(output)


def test_mirror_verifies_every_source_and_destination_byte(tmp_path: Path) -> None:
    output, evidence = _tiny_mirror_source(tmp_path)
    destination = tmp_path / "destination"
    result = mirror_verified(output, evidence, destination)
    assert result["status"] == "LOCAL_MIRROR_VERIFIED"
    assert result["payload_file_count"] == 3
    assert (destination / "output" / "substeps" / "cycle_0001.mat").read_bytes() == b"cycle-one"
    assert (destination / "external_evidence" / "external.json").is_file()
    assert (destination / "ONEDRIVE_PACKAGE.json").is_file()
    assert (destination / "SHA256SUMS.txt").is_file()


def test_mirror_fails_when_copy_is_corrupted(tmp_path: Path) -> None:
    output, evidence = _tiny_mirror_source(tmp_path)
    destination = tmp_path / "destination"

    def corrupt_copy(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = bytearray(Path(source).read_bytes())
        payload[0] ^= 1
        target.write_bytes(payload)

    with pytest.raises(ValueError, match="copied payload SHA-256 mismatch"):
        mirror_verified(output, evidence, destination, copier=corrupt_copy)
    assert not (destination / "ONEDRIVE_PACKAGE.json").exists()


def _matlab_string(value: str) -> np.ndarray:
    return np.asarray([ord(char) for char in value], dtype=np.uint16)[:, None]


def _write_synthetic_mesh(path: Path) -> None:
    nodes = np.asarray(
        [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]
    )
    connectivity = np.asarray([[1, 2, 5, 4], [2, 3, 6, 5]], dtype=float)
    with h5py.File(path, "w") as handle:
        group = handle.create_group("mesh_geometry")
        group.create_dataset("node_coords", data=nodes.T)
        group.create_dataset("connectivity", data=connectivity.T)
        for key, value in {
            "mesh_sha256": "a" * 64,
            "connectivity_sha256": "b" * 64,
            "element_ordering_id": "element-order",
            "gp_ordering_id": "gp-order",
        }.items():
            group.create_dataset(key, data=_matlab_string(value))


def _write_synthetic_shard(
    path: Path,
    *,
    cycle: int = 31,
    ordinals: tuple[int, ...] = (1, 2, 3, 4, 5),
    nan_field: bool = False,
    field_scale: float = 1.0,
    peak_load: float = 1.0,
    case_contract_sha: str = "e" * 64,
) -> None:
    nstep, nelem, nnode = len(ordinals), 2, 6
    peak_index = ordinals.index(4) if 4 in ordinals else 0
    d_node = np.zeros((nstep, nnode), dtype=float)
    d_node[peak_index, :] = np.linspace(0.0, 1.0, nnode)
    gp = np.zeros((nstep, 4, nelem), dtype=float)
    gp[peak_index, :, 0] = 1.0 * field_scale
    gp[peak_index, :, 1] = 3.0 * field_scale
    with h5py.File(path, "w") as handle:
        group = handle.create_group("shard")
        group.create_dataset("cycle", data=np.asarray([[cycle]], dtype=float))
        group.create_dataset("substep_ordinal", data=np.asarray(ordinals, dtype=float)[:, None])
        loads = np.linspace(0.25, 0.0, nstep)
        loads[peak_index] = peak_load
        group.create_dataset("load_factor", data=loads[:, None])
        group.create_dataset("d_node", data=d_node)
        for key in (
            "d_gp",
            "alpha_bar_gp",
            "f_alpha_gp",
            "g_gp",
            "psi_raw_gp",
            "psi_active_gp",
        ):
            values = gp.copy()
            if nan_field and key == "alpha_bar_gp":
                values[peak_index, 0, 0] = np.nan
            group.create_dataset(key, data=values)
        group.create_dataset("psi_raw_cyclemax_gp", data=gp[peak_index])
        for key, value in {
            "mesh_sha256": "a" * 64,
            "element_ordering_id": "element-order",
            "gp_ordering_id": "gp-order",
            "runtime_lock_sha256": "c" * 64,
            "family_contract_sha256": "d" * 64,
            "case_physics_contract_sha256": case_contract_sha,
            "execution_input_lock_sha256": "f" * 64,
        }.items():
            group.create_dataset(key, data=_matlab_string(value))


def test_load_mesh_converts_one_based_connectivity_and_computes_area(tmp_path: Path) -> None:
    path = tmp_path / "mesh_geometry.mat"
    _write_synthetic_mesh(path)
    mesh = load_mesh(path)
    assert mesh.connectivity.tolist() == [[0, 1, 4, 3], [1, 2, 5, 4]]
    geometry = element_geometry(mesh)
    np.testing.assert_allclose(geometry.areas, [1.0, 1.0])
    np.testing.assert_allclose(geometry.centroids, [[0.5, 0.5], [1.5, 0.5]])


def test_load_peak_fields_selects_stored_ordinal_four(tmp_path: Path) -> None:
    path = tmp_path / "cycle_0031.mat"
    _write_synthetic_shard(path)
    fields = load_peak_fields(path, 31)
    assert fields.cycle == 31
    assert fields.substep_ordinal == 4
    np.testing.assert_allclose(fields.d_node, np.linspace(0.0, 1.0, 6))
    np.testing.assert_allclose(fields.gp_fields["alpha_bar_gp"].mean(axis=1), [1.0, 3.0])


def test_loader_rejects_missing_s4_and_nan(tmp_path: Path) -> None:
    missing = tmp_path / "missing.mat"
    _write_synthetic_shard(missing, ordinals=(1, 2, 3, 5))
    with pytest.raises(ValueError, match="exactly one stored substep ordinal 4"):
        load_peak_fields(missing, 31)

    invalid = tmp_path / "nan.mat"
    _write_synthetic_shard(invalid, nan_field=True)
    with pytest.raises(ValueError, match="non-finite dataset: alpha_bar_gp"):
        load_peak_fields(invalid, 31)


def test_reduce_field_matches_known_weighted_integral_and_percentiles() -> None:
    values = np.asarray([1.0, 3.0])
    areas = np.asarray([1.0, 1.0])
    centroids = np.asarray([[0.5, 0.5], [1.5, 0.5]])
    reduced = reduce_field(values, areas, centroids)
    assert reduced["area_weighted_integral"] == pytest.approx(4.0)
    assert reduced["area_weighted_mean"] == pytest.approx(2.0)
    assert reduced["p50"] == pytest.approx(1.0)
    assert reduced["p95"] == pytest.approx(3.0)
    assert reduced["weighted_centroid_x"] == pytest.approx(1.25)


def test_process_zone_uses_predeclared_threshold(tmp_path: Path) -> None:
    path = tmp_path / "mesh_geometry.mat"
    _write_synthetic_mesh(path)
    geometry = element_geometry(load_mesh(path))
    result = process_zone(np.asarray([0.0, 0.02]), geometry)
    assert result["threshold"] == pytest.approx(0.0002)
    assert result["support_area"] == pytest.approx(1.0)
    assert result["centroid_x"] == pytest.approx(1.5)
    assert result["centroid_y"] == pytest.approx(0.5)


def test_comparison_pairs_include_p0_only_c73_without_t3_extrapolation() -> None:
    pairs = build_comparison_pairs()
    assert pairs["same_cycle"] == [20, 30, 31, 40, 60, 61, 68, 70, 71]
    assert pairs["own_event"] == [("first_hit", 70, 68), ("confirmed", 73, 71)]
    assert pairs["transitions"] == [(30, 31), (60, 61)]
    assert pairs["p0_only"] == [73]


def test_memory_requires_persistence_and_spatial_colocation() -> None:
    assert (
        classify_memory(
            {"departure": True, "persistence": True, "spatial_colocation": True}
        )
        == "PERSISTENT_MEMORY_OBSERVED"
    )
    for missing in ("departure", "persistence", "spatial_colocation"):
        evidence = {"departure": True, "persistence": True, "spatial_colocation": True}
        evidence[missing] = False
        assert classify_memory(evidence) == "MEMORY_NOT_ESTABLISHED"


def _write_synthetic_trajectory(root: Path, *, case_id: str, terminal_cycle: int) -> None:
    root.mkdir(parents=True)
    _write_synthetic_mesh(root / "mesh_geometry.mat")
    substeps = root / "substeps"
    substeps.mkdir()
    is_t3 = case_id == "T3_loading_history"
    for cycle in range(1, terminal_cycle + 1):
        if is_t3:
            peak_load = 0.108 if cycle <= 30 else 0.126 if cycle <= 60 else 0.120
            field_scale = 1.0 if cycle <= 30 else 1.1
            case_sha = "9" * 64
        else:
            peak_load = 0.120
            field_scale = 1.0
            case_sha = "8" * 64
        _write_synthetic_shard(
            substeps / f"cycle_{cycle:04d}.mat",
            cycle=cycle,
            field_scale=field_scale,
            peak_load=peak_load,
            case_contract_sha=case_sha,
        )
    if is_t3:
        first_hit, confirmed = 68, 71
    else:
        first_hit, confirmed = 70, 73
    (root / "TERMINAL_RESULT.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "terminal_reason": "confirmed_penetration",
                "terminal_cycle": confirmed,
                "first_hit_cycle": first_hit,
                "confirmed_cycle": confirmed,
            }
        ),
        encoding="utf-8",
    )
    (root / "EVENT_METADATA.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "terminal_cycle": confirmed,
                "first_hit_cycle": first_hit,
                "confirmed_cycle": confirmed,
                "peak_substep_ordinal": 4,
            }
        ),
        encoding="utf-8",
    )


def test_run_analysis_refuses_existing_results(tmp_path: Path) -> None:
    p0 = tmp_path / "p0"
    t3 = tmp_path / "t3"
    _write_synthetic_trajectory(p0, case_id="P0_parent", terminal_cycle=73)
    _write_synthetic_trajectory(t3, case_id="T3_loading_history", terminal_cycle=71)
    destination = tmp_path / "results"
    destination.mkdir()
    with pytest.raises(FileExistsError, match="results destination exists"):
        run_analysis(p0, t3, destination)


def test_run_analysis_emits_required_tables_and_summary(tmp_path: Path) -> None:
    p0 = tmp_path / "p0"
    t3 = tmp_path / "t3"
    _write_synthetic_trajectory(p0, case_id="P0_parent", terminal_cycle=73)
    _write_synthetic_trajectory(t3, case_id="T3_loading_history", terminal_cycle=71)
    destination = tmp_path / "results"
    summary = run_analysis(p0, t3, destination)
    assert summary["delta_n_first"] == -2
    assert summary["delta_n_confirmed"] == -2
    assert summary["t3_c73_status"] == "UNAVAILABLE"
    for name in (
        "cycle_field_reductions.csv",
        "same_cycle_differences.csv",
        "own_event_differences.csv",
        "block_transition_differences.csv",
        "process_zone_trajectory.csv",
        "mechanism_summary.json",
        "P0_T3_MECHANISM_REPORT.md",
        "ANALYSIS_INPUT_INVENTORY.json",
        "SHA256SUMS.txt",
        "FIGURE_METADATA.json",
    ):
        assert (destination / name).is_file(), name


def test_report_separates_event_result_from_mechanism_claim(tmp_path: Path) -> None:
    p0 = tmp_path / "p0"
    t3 = tmp_path / "t3"
    _write_synthetic_trajectory(p0, case_id="P0_parent", terminal_cycle=73)
    _write_synthetic_trajectory(t3, case_id="T3_loading_history", terminal_cycle=71)
    destination = tmp_path / "results"
    run_analysis(p0, t3, destination)
    report = (destination / "P0_T3_MECHANISM_REPORT.md").read_text(encoding="utf-8")
    assert "ΔN_first=-2" in report
    assert "ΔN_confirmed=-2" in report
    assert "event timing alone" in report
    assert (
        "PERSISTENT_MEMORY_OBSERVED" in report
        or "MEMORY_NOT_ESTABLISHED" in report
    )


def test_figures_use_common_limits_and_label_missing_t3_c73(tmp_path: Path) -> None:
    p0 = tmp_path / "p0"
    t3 = tmp_path / "t3"
    _write_synthetic_trajectory(p0, case_id="P0_parent", terminal_cycle=73)
    _write_synthetic_trajectory(t3, case_id="T3_loading_history", terminal_cycle=71)
    destination = tmp_path / "results"
    run_analysis(p0, t3, destination)
    metadata = load_json_strict(destination / "FIGURE_METADATA.json")
    assert metadata["common_color_limits"] is True
    assert metadata["t3_c73_status"] == "UNAVAILABLE"
    assert len(metadata["figure_files"]) >= 7
    assert all((destination / name).is_file() for name in metadata["figure_files"])


def test_analysis_code_does_not_import_or_invoke_fem_launcher() -> None:
    source = (
        REPO
        / "analysis"
        / "toy_road_t3_mechanism_20260819"
        / "run_analysis.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "main_toy_road_family_case",
        "run_toy_road_runtime_bridge",
        "launch_t3_sibling",
        "subprocess",
        "matlab.engine",
    ):
        assert forbidden not in source
