import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path(__file__).parents[1] / "SENS_tensile" / "run_fem_pidl_cross_residual_gate.py"
SPEC = importlib.util.spec_from_file_location("cross_residual_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_payload():
    return {
        "points": np.asarray([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]),
        "cells": np.asarray([[0, 1, 2, 3]]),
        "cycles": np.asarray([89]),
        "free_phase_nodes": np.asarray([0, 1, 2, 3]),
        "fem_pfield": np.zeros((1, 4)),
        "fem_history_gp": np.zeros((1, 1, 4)),
        "fem_fatigue_gp": np.ones((1, 1, 4)),
        "pidl_pfield_on_fem_nodes": np.zeros((1, 4)),
        "pidl_raw_gp_on_fem": np.zeros((1, 1, 4)),
        "pidl_fatigue_gp_on_fem": np.ones((1, 1, 4)),
        "state_kind": np.asarray(["peak"]),
    }


def test_exchange_schema_accepts_complete_exact_assets(tmp_path):
    path = tmp_path / "exchange.npz"
    np.savez(path, **valid_payload())
    data = MODULE.load_exchange(path)
    assert data["cells"].shape == (1, 4)


def test_exchange_schema_rejects_missing_geometry(tmp_path):
    payload = valid_payload()
    del payload["points"]
    path = tmp_path / "exchange.npz"
    np.savez(path, **payload)
    with pytest.raises(ValueError, match="points"):
        MODULE.load_exchange(path)


def test_exchange_schema_rejects_unloaded_state(tmp_path):
    payload = valid_payload()
    payload["state_kind"] = np.asarray(["unloaded"])
    path = tmp_path / "exchange.npz"
    np.savez(path, **payload)
    with pytest.raises(ValueError, match="peak"):
        MODULE.load_exchange(path)
