# ruff: noqa: E402
from __future__ import annotations

from collections import OrderedDict
import ast
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e014_common_direction import ARM_CANDIDATE, ARM_CONTROL
from s09_e015_trust_region import (
    NONZERO_LAMBDAS,
    actual_displacement,
    classify_grid,
    interpolate_state,
    noncollapsed,
    state_label,
    tensor_bytes_sha256,
)


def _state(nonzero: bool, local: int, global_: int, ratio: float = 1.0):
    return {
        "valid": True,
        "noncollapsed": nonzero,
        "local_pairs": {"score_2W_plus_T": local},
        "global_pairs": {"score_2W_plus_T": global_},
        "metrics": {
            "G": ratio,
            "F": ratio,
            "L_P": ratio,
            "L_judge": ratio,
            "hard_constraint_violations": 0,
        },
    }


def _grid():
    return {
        state_label(arm, fraction): _state(False, 0, 0)
        for arm in (ARM_CONTROL, ARM_CANDIDATE)
        for fraction in NONZERO_LAMBDAS
    }


def test_actual_displacement_and_direct_interior_interpolation():
    base = OrderedDict(
        (
            ("weight", torch.tensor([1.0, 2.0], dtype=torch.float64)),
            ("buffer", torch.tensor([7.0], dtype=torch.float64)),
        )
    )
    endpoint = OrderedDict(
        (
            ("weight", torch.tensor([3.0, 6.0], dtype=torch.float64)),
            ("buffer", torch.tensor([7.0], dtype=torch.float64)),
        )
    )
    displacement = actual_displacement(base, endpoint, ("weight",))
    assert torch.equal(displacement, torch.tensor([2.0, 4.0], dtype=torch.float64))
    assert tensor_bytes_sha256(displacement) == tensor_bytes_sha256(
        displacement.clone()
    )
    state = interpolate_state(base, endpoint, ("weight",), 1 / 4)
    assert torch.equal(state["weight"], torch.tensor([1.5, 3.0], dtype=torch.float64))
    assert torch.equal(state["buffer"], base["buffer"])
    assert state["buffer"].data_ptr() != base["buffer"].data_ptr()
    with pytest.raises(ValueError):
        interpolate_state(base, endpoint, ("weight",), 1.0)


def test_noncollapsed_requires_every_cycle_strictly_positive():
    rows = [
        {"cycle": index, "positive_node_count": 1, "maximum_increment": 1e-30}
        for index in range(16)
    ]
    assert noncollapsed(rows)
    rows[-1]["positive_node_count"] = 0
    assert not noncollapsed(rows)


def test_classification_levels_and_same_lambda_rule():
    states = _grid()
    assert classify_grid(states)["level"] == 2
    fraction = NONZERO_LAMBDAS[0]
    states[state_label(ARM_CONTROL, fraction)] = _state(True, 20, 20)
    assert classify_grid(states)["level"] == 3
    states[state_label(ARM_CANDIDATE, fraction)] = _state(True, 21, 20)
    assert classify_grid(states)["level"] == 5
    states[state_label(ARM_CANDIDATE, fraction)]["metrics"]["G"] = 0.0
    states[state_label(ARM_CONTROL, fraction)]["metrics"]["G"] = 0.0
    assert classify_grid(states)["level"] == 4


def test_local_gain_at_different_lambda_does_not_grant_level4():
    states = _grid()
    first, second = NONZERO_LAMBDAS[:2]
    states[state_label(ARM_CONTROL, first)] = _state(True, 20, 20)
    states[state_label(ARM_CANDIDATE, second)] = _state(True, 21, 20)
    assert classify_grid(states)["level"] == 3


def test_producer_contains_no_optimizer_or_gradient_execution_calls():
    path = ROOT / "source" / "s09_e015_producer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned = {"backward", "grad", "step", "zero_grad"}
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr
                if isinstance(func, ast.Attribute)
                else (func.id if isinstance(func, ast.Name) else "")
            )
            if name in banned:
                calls.append((name, node.lineno))
    assert calls == []
    text = path.read_text(encoding="utf-8")
    assert "torch.optim" not in text
    assert "torch.autograd" not in text


def test_bound_config_and_protocol_hashes_match_producer_constants():
    import hashlib

    from s09_e015_producer import (
        EXPECTED_PROTOCOL_SHA256,
        EXPECTED_RUN_CONFIG_SHA256,
    )

    config = ROOT / "docs" / "research" / "S09" / "S09-E015" / "run_config.json"
    protocol = ROOT / "docs" / "research" / "S09" / "S09-E015" / "experiment.md"
    assert hashlib.sha256(config.read_bytes()).hexdigest() == EXPECTED_RUN_CONFIG_SHA256
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
