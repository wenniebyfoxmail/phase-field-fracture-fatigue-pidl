from __future__ import annotations

import importlib.util
from pathlib import Path


RUNNER = (
    Path(__file__).resolve().parents[1]
    / "SENS_tensile"
    / "run_kan_rbf_production_umax.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location("kan_rbf_producer", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_capture_steps_use_same_cycle_peak_and_unload() -> None:
    module = _load_runner()
    assert module._capture_steps(1) == [3, 4]
    assert module._capture_steps(3) == [3, 4, 13, 14]
    assert module._capture_steps(120)[-2:] == [598, 599]


def test_capture_steps_do_not_exceed_requested_trajectory() -> None:
    module = _load_runner()
    assert max(module._capture_steps(80)) == 399
