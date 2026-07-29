from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_trajectory_bundle import (
    build_factorial_loco_split_lock,
    build_loto_split_lock,
    build_source_backed_bundle,
    inspect_state_shard,
    validate_bundle,
    validate_loto_split,
)


def make_source(tmp_path: Path, cycles: int = 4, cells: int = 6) -> tuple[Path, Path]:
    root = tmp_path / "case"
    states = root / "psi_fields"
    states.mkdir(parents=True)
    for cycle in range(1, cycles + 1):
        damage = np.linspace(0.0, 0.8, cells)[:, None] * cycle / cycles
        savemat(
            states / f"cycle_{cycle:04d}.mat",
            {
                "d_elem": damage,
                "alpha_bar_elem": np.full((cells, 1), 0.1 * cycle),
                "f_alpha_elem": np.full((cells, 1), 1.0 - 0.05 * cycle),
                "psi_elem": np.linspace(0.1, 1.0, cells)[:, None],
            },
        )
    graph = tmp_path / "mesh.npz"
    np.savez_compressed(
        graph,
        centroids=np.column_stack([np.arange(cells), np.zeros(cells)]),
        areas=np.ones(cells),
        connectivity=np.arange(cells * 4).reshape(cells, 4),
        edge_index=np.vstack([np.arange(cells - 1), np.arange(1, cells)]),
    )
    return root, graph


def make_bundle(
    tmp_path: Path,
    *,
    trajectory_id: str = "trajectory_a",
    family_id: str = "family_a",
    independence_class: str = "independent_physical_trajectory",
) -> dict:
    root, graph = make_source(tmp_path)
    return build_source_backed_bundle(
        trajectory_id=trajectory_id,
        family_id=family_id,
        independence_class=independence_class,
        source_root=root,
        mesh_graph_path=graph,
        umax=0.12,
        first_hit_cycle=2,
        confirmed_cycle=4,
        n_substeps=5,
    )


def test_source_backed_bundle_passes_deep_validation(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    report = validate_bundle(bundle, deep=True)
    assert report.valid, report.errors
    assert report.checks["deep_state_shards_checked"] == 4
    assert bundle["states"][1]["raw_step_1_based"] == 9
    assert bundle["observable_proxies"]["fwd_basin"]["mask_recipe"] == "all_false"


def test_state_shard_exports_derived_active_driver(tmp_path: Path) -> None:
    root, _ = make_source(tmp_path)
    inspected, errors = inspect_state_shard(root / "psi_fields" / "cycle_0001.mat", 6)
    assert not errors
    assert set(inspected["fields"]) == {
        "damage",
        "alpha_bar",
        "fatigue_degradation",
        "damage_degradation",
        "raw_driver",
        "active_driver",
    }


def test_solver_scale_damage_undershoot_is_retained_but_large_violation_fails(
    tmp_path: Path,
) -> None:
    root, _ = make_source(tmp_path)
    path = root / "psi_fields" / "cycle_0001.mat"
    data = {
        "d_elem": np.array([-2.3e-5, 0.0, 0.2, 0.4, 0.8, 1.0])[:, None],
        "alpha_bar_elem": np.ones((6, 1)),
        "f_alpha_elem": np.ones((6, 1)),
        "psi_elem": np.ones((6, 1)),
    }
    savemat(path, data)
    _, errors = inspect_state_shard(path, 6)
    assert not errors
    data["d_elem"][0, 0] = -1e-3
    savemat(path, data)
    _, errors = inspect_state_shard(path, 6)
    assert any("numerical tolerance" in error for error in errors)


def test_legacy_c69_is_rejected(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path, trajectory_id="legacy_c69_case")
    report = validate_bundle(bundle)
    assert not report.valid
    assert any("legacy c69" in error for error in report.errors)


def test_new_trajectory_may_legitimately_fail_at_cycle_69(tmp_path: Path) -> None:
    root, graph = make_source(tmp_path, cycles=70)
    bundle = build_source_backed_bundle(
        trajectory_id="new_independent_trajectory",
        family_id="new_independent_family",
        independence_class="independent_physical_trajectory",
        source_root=root,
        mesh_graph_path=graph,
        umax=0.12,
        first_hit_cycle=69,
        confirmed_cycle=70,
        n_substeps=5,
    )
    report = validate_bundle(bundle)
    assert report.valid, report.errors


def test_mixed_loading_step_is_rejected(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    bundle["state_semantics"]["all_fields_same_cycle_and_phase"] = False
    bundle.pop("manifest_sha256")
    report = validate_bundle(bundle)
    assert not report.valid
    assert "mixed loading-step fields are forbidden" in report.errors


def test_raw_step_mismatch_is_rejected(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    bundle["states"][0]["raw_step_1_based"] = 999
    bundle.pop("manifest_sha256")
    report = validate_bundle(bundle)
    assert not report.valid
    assert any("loading-step mapping mismatch" in error for error in report.errors)


def test_first_hit_and_confirmed_roles_cannot_be_mixed(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    bundle["event"]["confirmed"]["role"] = bundle["event"]["first_hit"]["role"]
    bundle.pop("manifest_sha256")
    report = validate_bundle(bundle)
    assert not report.valid
    assert any("roles must remain distinct" in error for error in report.errors)


def test_load_amplitude_family_cannot_unlock_loto(tmp_path: Path) -> None:
    bundles = []
    for index, umax in enumerate((0.11, 0.12, 0.13)):
        case_tmp = tmp_path / str(index)
        bundle = make_bundle(
            case_tmp,
            trajectory_id=f"u{umax}",
            family_id="same_load_amplitude_family",
            independence_class="load_amplitude_sensitivity",
        )
        bundles.append(bundle)
    split = build_loto_split_lock(bundles, [])
    report = validate_loto_split(split, bundles)
    assert report.valid, report.errors
    assert split["status"] == "blocked_by_data"
    assert split["folds"] == []
    assert not split["training_launch_allowed"]


def test_three_independent_trajectories_create_whole_trajectory_folds(
    tmp_path: Path,
) -> None:
    bundles = [
        make_bundle(
            tmp_path / str(index),
            trajectory_id=f"trajectory_{index}",
            family_id=f"independent_family_{index}",
        )
        for index in range(3)
    ]
    split = build_loto_split_lock(bundles, [])
    report = validate_loto_split(split, bundles)
    assert report.valid, report.errors
    assert split["status"] == "ready"
    assert split["training_launch_allowed"]
    assert len(split["folds"]) == 3
    for fold in split["folds"]:
        assert len(fold["test_trajectory_ids"]) == 1
        assert len(fold["train_trajectory_ids"]) == 2
        assert not set(fold["test_trajectory_ids"]) & set(fold["train_trajectory_ids"])


def test_complete_2x2_factorial_unlocks_only_scoped_loco(tmp_path: Path) -> None:
    combinations = (
        ("hard_recovery", "retained_5step", 5),
        ("hard_recovery", "explicit_8step", 8),
        ("analytic_soft_profile", "retained_5step", 5),
        ("analytic_soft_profile", "explicit_8step", 8),
    )
    bundles = []
    for index, (tip, loading, steps) in enumerate(combinations):
        root, graph = make_source(tmp_path / str(index))
        factors = (
            [0.25, 0.5, 0.75, 1.0, 0.0]
            if steps == 5
            else [0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0]
        )
        bundles.append(
            build_source_backed_bundle(
                trajectory_id=f"factorial_{index}",
                family_id="same_shared_geometry_factorial",
                independence_class="controlled_factorial_combination",
                source_root=root,
                mesh_graph_path=graph,
                umax=0.12,
                first_hit_cycle=2,
                confirmed_cycle=4,
                n_substeps=steps,
                nominal_load_factors=factors,
                initial_defect_family=tip,
                loading_family=loading,
                factorial_axes={"initial_tip_state": tip, "loading_history": loading},
            )
        )
    road_split = build_loto_split_lock(bundles, [])
    factorial_split = build_factorial_loco_split_lock(bundles)
    report = validate_loto_split(factorial_split, bundles)
    assert report.valid, report.errors
    assert road_split["status"] == "blocked_by_data"
    assert not road_split["training_launch_allowed"]
    assert factorial_split["status"] == "ready"
    assert factorial_split["training_launch_allowed"]
    assert len(factorial_split["folds"]) == 4
    assert "not independent roads" in factorial_split["claim_boundary"]


def test_split_lock_tampering_is_rejected(tmp_path: Path) -> None:
    bundles = [
        make_bundle(
            tmp_path / str(index),
            trajectory_id=f"trajectory_{index}",
            family_id=f"independent_family_{index}",
        )
        for index in range(3)
    ]
    split = build_loto_split_lock(bundles, [])
    split["folds"][0]["train_trajectory_ids"].append(
        split["folds"][0]["test_trajectory_ids"][0]
    )
    report = validate_loto_split(split, bundles)
    assert not report.valid
    assert any("train/test trajectory overlap" in error for error in report.errors)
    assert any("split lock SHA-256 mismatch" in error for error in report.errors)


def test_manifest_is_json_serializable(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    loaded = json.loads(json.dumps(bundle))
    assert loaded["trajectory_id"] == "trajectory_a"
