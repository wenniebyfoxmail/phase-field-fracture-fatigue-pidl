import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "SENS_tensile" / "analyze_frozen_optimizer_basin_gate.py"
SPEC = importlib.util.spec_from_file_location("analyze_basin_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def row(loss, grad, iou="", mae=""):
    return {
        "loss_total": str(loss),
        "gradient_rms": str(grad),
        "active_absolute_p99_iou": str(iou),
        "active_log_mae": str(mae),
    }


def test_classifier_detects_optimizer_confounder():
    assert MODULE.classify_branch(
        row(1.0, 1.0, 0.2, 1.0), row(0.9, 0.01, 0.3, 0.8)
    ) == "optimizer_confounder_supported"


def test_classifier_detects_objective_misalignment_signal():
    assert MODULE.classify_branch(
        row(1.0, 1.0, 0.2, 1.0), row(0.9, 0.01, 0.19, 1.1)
    ) == "objective_mechanism_misalignment_signal"


def test_classifier_keeps_stationarity_only_when_fem_absent():
    assert MODULE.classify_branch(row(1.0, 1.0), row(0.9, 0.01)) == (
        "stationarity_only_no_fem_reference"
    )
