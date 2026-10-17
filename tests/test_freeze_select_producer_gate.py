import copy

import numpy as np

from SENS_tensile.freeze_select.producer_gate import validate_producer_frame
from SENS_tensile.freeze_select.synthetic_forecast import ForecastConfig, generate_dynamic_truth


def _valid_package():
    config = ForecastConfig(nx=4, ny=3, n_times=3, n_sections=12, cutoff_index=1)
    frame = generate_dynamic_truth(config)
    combinations = [(load, temp, moisture) for load in "ABC" for temp in "LH" for moisture in "DW"]
    for section, (load, temp, moisture) in enumerate(combinations):
        mask = frame["trajectory_id"] == f"synthetic_section_{section}"
        frame.loc[mask, "load_spectrum_id"] = load
        frame.loc[mask, "temperature_level"] = temp
        frame.loc[mask, "moisture_level"] = moisture
    frame["geometry_id"] = "geometry_0"
    frame["precrack_id"] = "precrack_0"
    frame["increment_state_timing"] = "pre_refresh_to_post_update"
    frame["actual_fatigue_increment"] = 0.08 + 0.01 * frame["d"].to_numpy(float)
    frame["nominal_fixed_physics_increment"] = 0.03 + 0.005 * frame["d"].to_numpy(float)
    frame["known_residual"] = (
        frame["actual_fatigue_increment"] - frame["nominal_fixed_physics_increment"]
    )
    ids = sorted(frame["trajectory_id"].unique())
    manifest = {
        "snapshot_sha256": "a" * 64,
        "known_residual_sign": "actual_minus_nominal",
        "code_commit": "deadbeef",
        "dirty_status": "clean",
        "producer_machine": "test",
        "runtime": "test-runtime",
        "source_hashes": {"solver": "b" * 64},
        "temperature_parameter_mapping": {"L": {"Gc_scale": 1.0}, "H": {"Gc_scale": 0.7}},
        "moisture_parameter_mapping": {"D": {"fatigue_scale": 1.0}, "W": {"fatigue_scale": 1.4}},
        "load_spectrum_semantics": {
            key: {"is_physical": True, "description": f"spectrum {key}"} for key in "ABC"
        },
        "right_censored_trajectories": [ids[-1]],
        "splits": {"train": ids[:8], "validation": ids[8:10], "holdout": ids[10:]},
        "factorial_design": {
            "load_spectrum_ids": ["A", "B", "C"],
            "temperature_levels": ["L", "H"],
            "moisture_levels": ["D", "W"],
        },
    }
    return frame, manifest


def test_valid_factorial_producer_package_passes():
    frame, manifest = _valid_package()
    report = validate_producer_frame(frame, manifest, actual_snapshot_sha256="a" * 64)
    assert report.passed
    assert report.metrics["factorial_combination_count"] == 12


def test_declared_two_by_two_by_two_ferrite_design_passes():
    frame, manifest = _valid_package()
    keep = ~frame["load_spectrum_id"].eq("C")
    frame = frame.loc[keep].copy()
    ids = sorted(frame["trajectory_id"].unique())
    manifest["load_spectrum_semantics"].pop("C")
    manifest["factorial_design"]["load_spectrum_ids"] = ["A", "B"]
    manifest["right_censored_trajectories"] = [ids[-1]]
    manifest["splits"] = {
        "train": ids[:5],
        "validation": [ids[5]],
        "holdout": ids[6:],
    }
    report = validate_producer_frame(frame, manifest, actual_snapshot_sha256="a" * 64)
    assert report.passed
    assert report.metrics["factorial_combination_count"] == 8
    assert report.metrics["expected_factorial_combination_count"] == 8


def test_residual_sign_mismatch_fails():
    frame, manifest = _valid_package()
    frame["known_residual"] = -frame["known_residual"]
    report = validate_producer_frame(frame, manifest, actual_snapshot_sha256="a" * 64)
    assert not report.passed
    assert any("known_residual_identity" in error for error in report.errors)


def test_missing_factorial_combination_and_split_overlap_fail():
    frame, manifest = _valid_package()
    first = frame["trajectory_id"] == "synthetic_section_0"
    frame.loc[first, "load_spectrum_id"] = "B"
    manifest = copy.deepcopy(manifest)
    manifest["splits"]["holdout"].append(manifest["splits"]["train"][0])
    report = validate_producer_frame(frame, manifest, actual_snapshot_sha256="a" * 64)
    assert not report.passed
    assert any("factorial_coverage" in error for error in report.errors)
    assert any("overlap" in error for error in report.errors)
