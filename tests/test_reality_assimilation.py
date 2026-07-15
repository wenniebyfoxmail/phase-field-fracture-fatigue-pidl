from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from reality_assimilation import (  # noqa: E402
    OBSERVATION_TIERS,
    SensorObservationModel,
    SequentialLibraryAssimilator,
    Trajectory,
    assimilate_observation_sequence,
    empirical_crps,
    run_leave_one_trajectory_out,
    project_trajectory_to_sensor_space,
    simulate_sensor_observations,
    trajectory_from_keyframes,
    trajectory_from_observation_csv,
    trajectories_from_manifest,
    weighted_quantile,
    vision_features_from_probability_mask,
    validate_physics_library,
    validate_sensor_model_for_inference,
)
from calibrate_reality_sensor_observation_model import fit_channel_group_cv  # noqa: E402
from validate_reality_assimilation_package import validate_package  # noqa: E402
from observable_growth_baseline import (  # noqa: E402
    SequentialObservableGrowthBaseline,
    run_observable_growth_leave_one_out,
    summarize_observable_growth_stages,
)


def make_trajectory(name: str, growth: float, nf: int) -> Trajectory:
    cycles = np.arange(0, nf + 1, 5, dtype=float)
    progress = cycles / nf
    rows = pd.DataFrame(
        {
            "trajectory_id": name,
            "cycle": cycles,
            "failure_cycle": float(nf),
            "remaining_life": nf - cycles,
            "umax": growth,
            "crack_tip_x_d09": growth * progress**2,
            "damage_area_gt_0p5": growth * progress**2 * 0.2,
            "damage_area_gt_0p9": growth * progress**3 * 0.1,
            "visible_crack_width_y": growth * progress * 0.05,
            "mechanical_energy_tip_proxy": growth * (0.2 + progress),
            "mechanical_energy_strip_proxy": growth * (0.1 + 0.5 * progress),
            "ae_damage_activity_proxy": growth * progress * 0.01,
            "ae_history_activity_proxy": growth * progress * 0.02,
            "alpha_bar_p99": growth * progress * 10.0,
            "fatigue_f_tip_2l0_mean": 1.0 - 0.5 * progress,
            "psi_active_tip_2l0_mean": growth * progress * (1.0 - progress * 0.5),
        }
    )
    return Trajectory(name, Path(f"{name}.mat"), nf, growth, rows)


def test_weighted_distribution_helpers() -> None:
    values = np.array([0.0, 10.0])
    weights = np.array([0.25, 0.75])
    assert weighted_quantile(values, weights, 0.5) == 10.0
    assert empirical_crps(values, weights, 10.0) >= 0.0


def test_sequential_weights_normalize_and_update() -> None:
    a = make_trajectory("a", 0.8, 50)
    b = make_trajectory("b", 1.4, 60)
    assimilator = SequentialLibraryAssimilator(
        [a, b], OBSERVATION_TIERS["vision_plus_load"], likelihood_sigma=0.25
    )
    observation = b.row_at(20).to_dict()
    weights = assimilator.update(20, observation)
    assert np.isclose(weights.sum(), 1.0)
    assert weights[1] > weights[0]
    pred = assimilator.posterior_prediction(20, 5)
    assert pred["rul_q05"] <= pred["rul_q50"] <= pred["rul_q95"]


def test_sparse_trajectory_interpolates_at_equivalent_load() -> None:
    trajectory = make_trajectory("sparse", 1.0, 50)
    sparse = Trajectory(
        trajectory.trajectory_id,
        trajectory.source_path,
        trajectory.failure_cycle,
        trajectory.umax,
        trajectory.rows.iloc[[0, 2, 6, 10]].reset_index(drop=True),
    )
    row = sparse.row_at(15.0)
    assert row["cycle"] == 15.0
    assert row["remaining_life"] == 35.0
    assert sparse.rows["crack_tip_x_d09"].min() <= row["crack_tip_x_d09"] <= sparse.rows["crack_tip_x_d09"].max()


def test_leave_one_out_emits_probabilistic_metrics() -> None:
    trajectories = [
        make_trajectory("slow", 0.7, 60),
        make_trajectory("middle", 1.0, 50),
        make_trajectory("fast", 1.4, 40),
    ]
    predictions, summary = run_leave_one_trajectory_out(
        trajectories,
        tiers=["vision_only", "vision_load_mechanical_activity"],
        inspection_stride=2,
        forecast_horizon=5,
    )
    assert not predictions.empty
    assert not summary.empty
    assert {"rul_crps", "rul_90_coverage", "future_tip_mae"}.issubset(summary.columns)
    assert predictions["rul_interval_covers"].isin([0.0, 1.0]).all()


def test_versioned_external_observation_sequence() -> None:
    library = [make_trajectory("a", 0.8, 50), make_trajectory("b", 1.2, 60)]
    library[0].parameters = {"alpha_T": 10.0}
    library[1].parameters = {"alpha_T": 20.0}
    source = library[0].rows.iloc[[1, 3]].copy()
    observations = source[list(OBSERVATION_TIERS["vision_plus_load"]) + ["cycle"]].copy()
    observations.insert(0, "observation_space_version", "reality_obs_v1")
    observations.insert(1, "asset_id", "lab_coupon_01")
    observations.insert(2, "inspection_id", ["inspection_01", "inspection_02"])
    observations.insert(3, "timestamp", ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"])
    observations.insert(5, "coordinate_frame", "registered_specimen_xy_m")
    observations.insert(6, "registration_id", "registration_v1")
    posterior = assimilate_observation_sequence(
        observations,
        library,
        tier="vision_plus_load",
        forecast_horizon=5,
    )
    assert len(posterior) == 2
    assert {"rul_q05", "rul_q50", "rul_q95", "model_weight__a", "model_weight__b"}.issubset(
        posterior.columns
    )
    assert np.allclose(posterior[["model_weight__a", "model_weight__b"]].sum(axis=1), 1.0)
    assert {
        "parameter__umax__mean",
        "parameter__alpha_T__mean",
        "parameter__alpha_T__q05",
        "parameter__alpha_T__q95",
    }.issubset(posterior.columns)


def test_sparse_mat_keyframe_import(tmp_path: Path) -> None:
    nodes = np.array(
        [[0.0, 0.0], [0.5, 0.0], [1.0, 0.0], [0.0, 1.0], [0.5, 1.0], [1.0, 1.0]]
    )
    conn = np.array([[1, 2, 5, 4], [2, 3, 6, 5]])
    centroids = np.array([[0.25, 0.5], [0.75, 0.5]])
    mesh = tmp_path / "mesh_geometry.mat"
    savemat(mesh, {"node_coords": nodes, "connectivity": conn, "element_centroids": centroids})
    paths = []
    for cycle, damage in [(1, [0.0, 0.0]), (5, [0.95, 0.0]), (10, [1.0, 0.95])]:
        path = tmp_path / f"u10_cycle_{cycle:04d}.mat"
        savemat(
            path,
            {
                "d_elem": np.asarray(damage),
                "alpha_bar_elem": np.asarray(damage) * cycle,
                "f_alpha_elem": 1.0 - 0.5 * np.asarray(damage),
                "psi_elem": 0.1 + np.asarray(damage),
            },
        )
        paths.append(path)
    trajectory = trajectory_from_keyframes(
        paths,
        mesh_path=mesh,
        trajectory_id="sparse_u10",
        umax=0.10,
        failure_cycle=10,
    )
    assert trajectory.rows["cycle"].tolist() == [1.0, 5.0, 10.0]
    assert trajectory.rows["remaining_life"].tolist() == [9.0, 5.0, 0.0]
    assert trajectory.rows["ae_damage_activity_proxy"].iloc[-1] > 0.0

    manifest = tmp_path / "trajectory_manifest.csv"
    pd.DataFrame(
        [
            {
                "trajectory_id": "sparse_u10",
                "source_kind": "keyframes",
                "source_path": "u10_cycle_*.mat",
                "mesh_path": "mesh_geometry.mat",
                "umax": 0.10,
                "failure_cycle": 10,
                "censored": False,
                "censor_cycle": np.nan,
                "physics_family": "unit_test_family",
                "parameter_alpha_T": 12.5,
            }
        ]
    ).to_csv(manifest, index=False)
    loaded = trajectories_from_manifest(manifest)
    assert len(loaded) == 1
    assert loaded[0].trajectory_id == "sparse_u10"
    assert loaded[0].parameters == {"alpha_T": 12.5}
    assert loaded[0].physics_family == "unit_test_family"


def test_right_censored_candidate_produces_auditable_tail_distribution() -> None:
    failed = make_trajectory("failed", 0.8, 50)
    source = make_trajectory("censored_source", 1.2, 60)
    censored_rows = source.rows[source.rows["cycle"] <= 40].copy()
    censored_rows["failure_cycle"] = np.nan
    censored_rows["censored"] = 1.0
    censored_rows["censor_cycle"] = 40.0
    censored_rows["remaining_life"] = np.nan
    censored_rows["remaining_life_lower_bound"] = 40.0 - censored_rows["cycle"]
    censored = Trajectory(
        "censored",
        Path("censored.mat"),
        None,
        1.2,
        censored_rows,
        censored=True,
        censor_cycle=40,
    )
    assimilator = SequentialLibraryAssimilator(
        [failed, censored],
        OBSERVATION_TIERS["vision_plus_load"],
        likelihood_sigma=0.25,
        censor_tail_scale=30.0,
        censor_quadrature_points=21,
    )
    assimilator.update(20, censored.row_at(20).to_dict())
    pred = assimilator.posterior_prediction(20, 5)
    lower_bound = censored.censor_cycle - 20
    assert pred["censored_posterior_mass"] > 0.0
    assert pred["rul_q95"] > lower_bound
    assert np.isclose(np.sum(pred["rul_crps_weights"]), 1.0)
    assert pred["censor_tail_scale"] == 30.0


def test_explicit_dic_ae_observation_model_projects_noise_and_missingness() -> None:
    model = SensorObservationModel(
        model_id="lab_calibration_test",
        calibration_status="lab_calibrated",
        channels={
            "dic_tip_response": {
                "sources": {"mechanical_energy_tip_proxy": 2.0},
                "offset": 0.1,
                "sigma": 0.02,
            },
            "ae_log_event_rate": {
                "sources": {
                    "ae_damage_activity_proxy": 0.7,
                    "ae_history_activity_proxy": 0.3,
                },
                "offset": -0.2,
                "sigma": 0.05,
            },
        },
    )
    trajectory = make_trajectory("sensor_source", 1.0, 50)
    projected = project_trajectory_to_sensor_space(trajectory, model)
    expected = 0.1 + 2.0 * trajectory.rows["mechanical_energy_tip_proxy"]
    assert np.allclose(projected.rows["dic_tip_response"], expected)
    observed = simulate_sensor_observations(
        trajectory,
        model,
        noise_multiplier=1.0,
        missing_probability=0.25,
        random_seed=7,
    )
    assert observed.rows["dic_tip_response"].isna().any()
    assert not np.allclose(
        observed.rows["ae_log_event_rate"].fillna(0.0),
        projected.rows["ae_log_event_rate"].fillna(0.0),
    )


def test_leave_one_out_uses_censored_library_member_without_scoring_it_as_failure() -> None:
    a = make_trajectory("a", 0.8, 50)
    b = make_trajectory("b", 1.0, 60)
    source = make_trajectory("censored_source", 1.2, 70)
    rows = source.rows[source.rows["cycle"] <= 40].copy()
    rows["remaining_life"] = np.nan
    rows["remaining_life_lower_bound"] = 40.0 - rows["cycle"]
    censored = Trajectory(
        "censored",
        Path("censored.mat"),
        None,
        1.2,
        rows,
        censored=True,
        censor_cycle=40,
    )
    predictions, summary = run_leave_one_trajectory_out(
        [a, b, censored],
        tiers=["vision_only"],
        inspection_stride=2,
        censor_tail_scale=25.0,
    )
    assert set(predictions["heldout_trajectory"]) == {"a", "b"}
    assert (predictions["censored_posterior_mass"] > 0.0).any()
    assert summary["mean_censored_posterior_mass"].notna().all()


def test_registered_probability_mask_maps_to_physical_vision_features() -> None:
    mask = np.zeros((4, 6), dtype=float)
    mask[1:3, 1:5] = 0.6
    mask[1, 1:4] = 0.95
    features = vision_features_from_probability_mask(
        mask,
        pixel_size_x=0.1,
        pixel_size_y=0.2,
        origin_x=1.0,
        origin_y=-0.4,
    )
    assert np.isclose(features["crack_tip_x_d09"], 1.35)
    assert np.isclose(features["damage_area_gt_0p5"], 8 * 0.1 * 0.2)
    assert np.isclose(features["damage_area_gt_0p9"], 3 * 0.1 * 0.2)
    assert np.isclose(features["visible_crack_width_y"], 0.4)
    assert features["vision_tip_x_threshold_upper"] > features["vision_tip_x_threshold_lower"]


def test_physics_family_guard_rejects_confounded_library_by_default() -> None:
    a = make_trajectory("a", 0.8, 50)
    b = make_trajectory("b", 1.0, 60)
    a.physics_family = "legacy_fem5"
    b.physics_family = "reverse_bc"
    with np.testing.assert_raises_regex(ValueError, "mixes physics_family"):
        validate_physics_library([a, b])
    assert validate_physics_library([a, b], allow_mixed=True) == (
        "legacy_fem5",
        "reverse_bc",
    )


def test_grouped_sensor_calibration_uses_heldout_groups_for_uncertainty() -> None:
    x = np.linspace(0.0, 3.0, 20)
    frame = pd.DataFrame(
        {
            "calibration_group": np.repeat(["a", "b", "c", "d"], 5),
            "mechanical_energy_tip_proxy": x,
            "dic_tip_response": 0.5 + 2.0 * x + 0.01 * np.sin(4.0 * x),
        }
    )
    channel, report = fit_channel_group_cv(
        frame,
        output_name="dic_tip_response",
        source_names=["mechanical_energy_tip_proxy"],
        group_column="calibration_group",
        min_groups=3,
    )
    assert np.isclose(channel["sources"]["mechanical_energy_tip_proxy"], 2.0, atol=0.02)
    assert np.isclose(channel["offset"], 0.5, atol=0.02)
    assert channel["sigma"] > 0.0
    assert report["n_groups"] == 4.0
    with np.testing.assert_raises_regex(ValueError, "need at least 5"):
        fit_channel_group_cv(
            frame,
            output_name="dic_tip_response",
            source_names=["mechanical_energy_tip_proxy"],
            group_column="calibration_group",
            min_groups=5,
        )


def test_real_sensor_inference_requires_separate_approval_gate() -> None:
    channels = {
        "dic_tip_response": {
            "sources": {"mechanical_energy_tip_proxy": 1.0},
            "offset": 0.0,
            "sigma": 0.1,
        }
    }
    candidate = SensorObservationModel(
        model_id="candidate",
        calibration_status="lab_calibrated",
        channels=channels,
        approved_for_inference=False,
    )
    with np.testing.assert_raises_regex(ValueError, "not approved_for_inference"):
        validate_sensor_model_for_inference(candidate)
    approved = SensorObservationModel(
        model_id="approved",
        calibration_status="lab_calibrated",
        channels=channels,
        approved_for_inference=True,
    )
    validate_sensor_model_for_inference(approved)
    with np.testing.assert_raises_regex(ValueError, "lacks channels"):
        validate_sensor_model_for_inference(approved, "vision_load_dic")


def test_result_package_validator_enforces_quarantine_and_constant_parameters(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text(
        '{"training_launched": false, "physics_families": ["a", "b"], '
        '"mixed_physics_family": true, "claim_quarantined": true, '
        '"sensor_calibration_status": "synthetic_only", '
        '"sensor_approved_for_inference": false, '
        '"observable_growth_baseline": false}\n',
        encoding="utf-8",
    )
    (package / "decision.md").write_text("- **Quarantine:** mixed families.\n", encoding="utf-8")
    pd.DataFrame(
        {
            "tier": ["vision_only"],
            "rul_q05": [1.0],
            "rul_q50": [2.0],
            "rul_q95": [3.0],
            "future_tip_q05": [0.1],
            "future_tip_q95": [0.2],
            "rul_interval_covers": [1.0],
        }
    ).to_csv(package / "reality_assimilation_predictions.csv", index=False)
    pd.DataFrame(
        {"heldout_trajectory": ["ALL"], "rul_90_coverage": [1.0]}
    ).to_csv(package / "reality_assimilation_summary.csv", index=False)
    pd.DataFrame(
        {
            "n_unique_truth": [1.0],
            "identifiable_from_holdout": [False],
            "mae": [np.nan],
            "rmse": [np.nan],
            "90_coverage": [np.nan],
            "90_width": [np.nan],
        }
    ).to_csv(package / "reality_assimilation_parameter_summary.csv", index=False)
    pd.DataFrame({"feature": ["crack_tip_x_d09"]}).to_csv(
        package / "sensor_observability_catalog.csv", index=False
    )
    pd.DataFrame(
        {
            "transition_model": ["direct_fem_library"],
            "observation_contract": ["crack_tip_x_d09_only"],
        }
    ).to_csv(package / "transition_model_comparison.csv", index=False)
    assert validate_package(package) == []
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest["claim_quarantined"] = False
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert "mixed physics family package must set claim_quarantined=true" in validate_package(package)


def test_observable_growth_baseline_emits_probabilistic_same_holdout_metrics() -> None:
    trajectories = [
        make_trajectory("slow", 0.7, 60),
        make_trajectory("middle", 1.0, 50),
        make_trajectory("fast", 1.4, 40),
    ]
    model = SequentialObservableGrowthBaseline(
        trajectories[:2],
        rate_particles=51,
        tip_sigma=0.002,
    )
    model.update(5.0, float(trajectories[2].row_at(5.0)["crack_tip_x_d09"]))
    model.update(10.0, float(trajectories[2].row_at(10.0)["crack_tip_x_d09"]))
    pred = model.posterior_prediction(
        float(trajectories[2].row_at(10.0)["crack_tip_x_d09"]),
        5,
    )
    assert pred["rul_q05"] <= pred["rul_q50"] <= pred["rul_q95"]
    predictions, summary = run_observable_growth_leave_one_out(
        trajectories,
        inspection_stride=2,
        rate_particles=51,
    )
    assert not predictions.empty
    assert set(predictions["transition_model"]) == {"observable_growth_particles"}
    assert predictions["rul_interval_covers"].isin([0.0, 1.0]).all()
    assert {"rul_crps", "future_tip_mae"}.issubset(summary.columns)
    stages = summarize_observable_growth_stages(predictions)
    assert set(stages["observation_stage"]) == {
        "no_detected_extension",
        "detected_extension",
    }


def test_historical_observation_csv_can_be_an_empirical_transition_trajectory(
    tmp_path: Path,
) -> None:
    observation_path = tmp_path / "history.csv"
    pd.DataFrame(
        {
            "observation_space_version": ["reality_obs_v1"] * 3,
            "asset_id": ["asset_1"] * 3,
            "inspection_id": ["i0", "i1", "i2"],
            "timestamp": [
                "2026-01-01T00:00:00Z",
                "2026-01-02T00:00:00Z",
                "2026-01-03T00:00:00Z",
            ],
            "cycle": [0.0, 5.0, 10.0],
            "coordinate_frame": ["asset_xy_m"] * 3,
            "registration_id": ["registration_v1"] * 3,
            "crack_tip_x_d09": [0.0, 0.1, 0.5],
        }
    ).to_csv(observation_path, index=False)
    trajectory = trajectory_from_observation_csv(
        observation_path,
        trajectory_id="historical_asset_1",
        umax=1.0,
        failure_cycle=10,
        physics_family="road_family_v1",
        observation_tier="tip_only",
    )
    assert trajectory.rows["remaining_life"].tolist() == [10.0, 5.0, 0.0]
    assert trajectory.physics_family == "road_family_v1"
    manifest = tmp_path / "historical_manifest.csv"
    pd.DataFrame(
        [
            {
                "trajectory_id": "historical_asset_1",
                "source_kind": "observation_csv",
                "source_path": "history.csv",
                "mesh_path": np.nan,
                "umax": 1.0,
                "failure_cycle": 10,
                "censored": False,
                "censor_cycle": np.nan,
                "physics_family": "road_family_v1",
                "observation_tier": "tip_only",
            }
        ]
    ).to_csv(manifest, index=False)
    loaded = trajectories_from_manifest(manifest)
    assert len(loaded) == 1
    assert loaded[0].source_path == observation_path

    historical_library = []
    for index, failure_cycle in enumerate((10, 12, 14)):
        path = tmp_path / f"history_{index}.csv"
        history = pd.read_csv(observation_path)
        history["asset_id"] = f"asset_{index}"
        history["inspection_id"] = [f"asset_{index}_i{j}" for j in range(3)]
        history["cycle"] = [0.0, failure_cycle / 2.0, float(failure_cycle)]
        history.to_csv(path, index=False)
        historical_library.append(
            trajectory_from_observation_csv(
                path,
                trajectory_id=f"historical_{index}",
                umax=1.0 + 0.1 * index,
                failure_cycle=failure_cycle,
                physics_family="road_family_v1",
                observation_tier="tip_only",
            )
        )
    predictions, summary = run_leave_one_trajectory_out(
        historical_library,
        tiers=["tip_only"],
        inspection_stride=1,
    )
    assert not predictions.empty
    assert set(summary["tier"]) == {"tip_only"}
    with np.testing.assert_raises_regex(ValueError, "Selected observation tiers are unavailable"):
        run_leave_one_trajectory_out(
            historical_library,
            tiers=["vision_only"],
            inspection_stride=1,
        )
