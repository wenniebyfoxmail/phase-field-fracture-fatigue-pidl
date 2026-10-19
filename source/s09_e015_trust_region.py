# ruff: noqa: E721
"""Pure state construction and classification helpers for S09-E015."""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import math
from typing import Any, Mapping

import torch

from s09_e014_common_direction import ARM_CANDIDATE, ARM_CONTROL, ARM_ORDER


LAMBDA_GRID = (0.0, 1 / 1024, 1 / 256, 1 / 64, 1 / 16, 1 / 4, 1.0)
NONZERO_LAMBDAS = LAMBDA_GRID[1:]
PROTECTED_METRICS = ("G", "F", "L_P", "L_judge")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def tensor_bytes_sha256(value: torch.Tensor) -> str:
    array = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()


def parameter_order(model: torch.nn.Module) -> tuple[str, ...]:
    order = tuple(name for name, _ in model.named_parameters())
    _require(bool(order) and len(order) == len(set(order)), "invalid parameter order")
    return order


def actual_displacement(
    base_state: Mapping[str, torch.Tensor],
    endpoint_state: Mapping[str, torch.Tensor],
    order: tuple[str, ...],
) -> torch.Tensor:
    _require(
        set(order).issubset(base_state) and set(order).issubset(endpoint_state),
        "parameter missing from checkpoint state",
    )
    values = []
    for name in order:
        base = base_state[name].detach().cpu().to(torch.float64)
        endpoint = endpoint_state[name].detach().cpu().to(torch.float64)
        _require(
            base.shape == endpoint.shape
            and torch.isfinite(base).all().item()
            and torch.isfinite(endpoint).all().item(),
            f"invalid parameter tensor: {name}",
        )
        values.append((endpoint - base).reshape(-1))
    return torch.cat(values)


def interpolate_state(
    base_state: Mapping[str, torch.Tensor],
    endpoint_state: Mapping[str, torch.Tensor],
    order: tuple[str, ...],
    fraction: float,
) -> OrderedDict[str, torch.Tensor]:
    """Build one interior state directly in float64; exact endpoints stay external."""
    _require(
        fraction in NONZERO_LAMBDAS[:-1],
        "interpolation requires frozen interior lambda",
    )
    parameter_names = set(order)
    _require(
        set(base_state) == set(endpoint_state), "checkpoint state membership drift"
    )
    result: OrderedDict[str, torch.Tensor] = OrderedDict()
    for name, base_value in base_state.items():
        endpoint_value = endpoint_state[name]
        _require(
            base_value.shape == endpoint_value.shape
            and base_value.dtype == endpoint_value.dtype,
            f"checkpoint tensor metadata drift: {name}",
        )
        if name in parameter_names:
            value = base_value.detach().to(torch.float64) + fraction * (
                endpoint_value.detach().to(torch.float64)
                - base_value.detach().to(torch.float64)
            )
            _require(
                torch.isfinite(value).all().item(), f"nonfinite interpolation: {name}"
            )
            result[name] = value.to(dtype=base_value.dtype)
        else:
            _require(
                torch.equal(base_value.detach().cpu(), endpoint_value.detach().cpu()),
                f"buffer drift: {name}",
            )
            result[name] = base_value.detach().clone()
    return result


def state_label(arm: str, fraction: float) -> str:
    _require(arm in ARM_ORDER, "unknown arm")
    mapping = {
        1 / 1024: "1of1024",
        1 / 256: "1of256",
        1 / 64: "1of64",
        1 / 16: "1of16",
        1 / 4: "1of4",
        1.0: "1",
    }
    _require(fraction in mapping, "unknown lambda")
    prefix = "CG25" if arm == ARM_CONTROL else "CL25"
    return f"{prefix}_lambda_{mapping[fraction]}"


def noncollapsed(cycle_rows: list[Mapping[str, Any]]) -> bool:
    _require(len(cycle_rows) == 16, "NONCOLLAPSED requires all 16 cycles")
    cycles = [int(row["cycle"]) for row in cycle_rows]
    _require(len(cycles) == len(set(cycles)), "duplicate cycle in collapse evidence")
    return all(
        type(row["positive_node_count"]) is int
        and row["positive_node_count"] > 0
        and math.isfinite(float(row["maximum_increment"]))
        and float(row["maximum_increment"]) > 0.0
        for row in cycle_rows
    )


def classify_grid(states: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        state_label(arm, fraction) for arm in ARM_ORDER for fraction in NONZERO_LAMBDAS
    }
    _require(set(states) == expected, "incomplete fixed grid")
    for label, state in states.items():
        _require(state.get("valid") is True, f"invalid state: {label}")

    witnesses = []
    any_noncollapsed = False
    for fraction in NONZERO_LAMBDAS:
        control = states[state_label(ARM_CONTROL, fraction)]
        candidate = states[state_label(ARM_CANDIDATE, fraction)]
        any_noncollapsed = (
            any_noncollapsed
            or bool(control["noncollapsed"])
            or bool(candidate["noncollapsed"])
        )
        ratios: dict[str, float | None] = {}
        for name in PROTECTED_METRICS:
            numerator = float(candidate["metrics"][name])
            denominator = float(control["metrics"][name])
            ratios[name] = (
                numerator / denominator
                if math.isfinite(numerator)
                and math.isfinite(denominator)
                and denominator > 0.0
                else None
            )
        both = bool(control["noncollapsed"] and candidate["noncollapsed"])
        local_gain = int(candidate["local_pairs"]["score_2W_plus_T"]) - int(
            control["local_pairs"]["score_2W_plus_T"]
        )
        global_gain = int(candidate["global_pairs"]["score_2W_plus_T"]) - int(
            control["global_pairs"]["score_2W_plus_T"]
        )
        level4 = both and local_gain >= 1
        protected = all(
            value is not None and math.isfinite(value) and value <= 1.10
            for value in ratios.values()
        )
        level5 = (
            level4
            and global_gain >= 0
            and int(candidate["metrics"]["hard_constraint_violations"]) == 0
            and protected
        )
        witnesses.append(
            {
                "lambda": fraction,
                "both_noncollapsed": both,
                "local_pair_score_gain": local_gain,
                "global_pair_score_gain": global_gain,
                "protected_ratios": ratios,
                "protected_ratios_ok": protected,
                "level4": level4,
                "level5": level5,
            }
        )
    if any(row["level5"] for row in witnesses):
        return {
            "level": 5,
            "status": "BALANCED_TRUST_REGION_SIGNAL",
            "witnesses": witnesses,
        }
    if any(row["level4"] for row in witnesses):
        return {
            "level": 4,
            "status": "LOCAL_COMPONENT_SIGNAL_AT_MATCHED_LAMBDA",
            "witnesses": witnesses,
        }
    if any_noncollapsed:
        return {
            "level": 3,
            "status": "NONZERO_TRUST_REGION_FOUND",
            "witnesses": witnesses,
        }
    return {
        "level": 2,
        "status": "NO_NONZERO_TRUST_REGION_ON_GRID",
        "witnesses": witnesses,
    }
