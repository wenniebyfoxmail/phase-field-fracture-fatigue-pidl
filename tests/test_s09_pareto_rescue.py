import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "SENS_tensile"))
from run_s09_pareto_rescue import seven_metrics, validate_output_path, validate_replay


def metrics(values=(0.3, 0.2, 20.0, 0.3, 21.0, 0.4, 22.0)):
    aggregate, u76, f76, u82, f82, u83, f83 = values
    return {
        "R": aggregate,
        "states": [
            {"cycle": 76, "relative_to_affine": u76,
             "free_force_rms_ratio_to_affine": f76},
            {"cycle": 82, "relative_to_affine": u82,
             "free_force_rms_ratio_to_affine": f82},
            {"cycle": 83, "relative_to_affine": u83,
             "free_force_rms_ratio_to_affine": f83},
        ],
    }


def test_seven_metrics_has_exact_unrounded_identity():
    result = seven_metrics(metrics())
    assert result == {
        "aggregate_R": 0.3,
        "c76_R_u": 0.2, "c76_R_f": 20.0,
        "c82_R_u": 0.3, "c82_R_f": 21.0,
        "c83_R_u": 0.4, "c83_R_f": 22.0,
    }


def test_seven_metrics_rejects_wrong_cycles_and_nonfinite():
    wrong = metrics()
    wrong["states"][2]["cycle"] = 84
    with pytest.raises(RuntimeError, match="identity"):
        seven_metrics(wrong)
    nonfinite = metrics()
    nonfinite["states"][0]["relative_to_affine"] = float("nan")
    with pytest.raises(RuntimeError, match="non-finite"):
        seven_metrics(nonfinite)


def test_validate_replay_applies_elementwise_tolerance(tmp_path):
    reference = metrics()
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps({"final": {"data_only": reference}}))
    close = metrics((0.3 + 3e-6, 0.2, 20.0001, 0.3, 21.0, 0.4, 22.0))
    checks = validate_replay(close, path)
    assert len(checks) == 7
    assert all(item["pass"] for item in checks.values())
    far = metrics((0.31, 0.2, 20.0, 0.3, 21.0, 0.4, 22.0))
    with pytest.raises(RuntimeError, match="seven-value"):
        validate_replay(far, path)


def test_output_path_is_taobo_and_run_namespaced():
    accepted = validate_output_path(
        Path("/mnt/data2/drtao/wennie/S09-E006-R001_deadbee_20261012T000000CST")
    )
    assert accepted.name.startswith("S09-E006-R001")
    with pytest.raises(RuntimeError, match="contained"):
        validate_output_path(Path("/tmp/S09-E006-R001_test"))
    with pytest.raises(RuntimeError, match="Run ID"):
        validate_output_path(Path("/mnt/data2/drtao/wennie/not_a_run"))
