"""Observable-conditioned damage-amplitude inversion helpers.

The functions in this module deliberately operate on one declared source
cycle.  They do not know about c87/c89 targets, neural-operator checkpoints, or
FEM truth fields beyond the sealed binary crack observation supplied by the
caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class LoadDisplacementCycle:
    cycle: int
    step: np.ndarray
    ux: np.ndarray
    fx: np.ndarray
    uy: np.ndarray
    fy: np.ndarray


def parse_load_displacement_cycles(
    path: str | Path,
    *,
    steps_per_cycle: int,
) -> list[LoadDisplacementCycle]:
    """Parse the GRIPHFiTH ``load_displ`` table into verified cycle blocks."""
    if steps_per_cycle < 1:
        raise ValueError("steps_per_cycle must be positive")
    rows: list[list[float]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields or fields[0].lower() == "step":
            continue
        if len(fields) != 5:
            raise ValueError(f"expected five load-displacement columns, got: {line}")
        try:
            rows.append([float(value) for value in fields])
        except ValueError as error:
            raise ValueError(f"non-numeric load-displacement row: {line}") from error
    if not rows or len(rows) % steps_per_cycle:
        raise ValueError("load-displacement rows do not form complete cycles")
    table = np.asarray(rows, dtype=np.float64)
    if not np.all(np.isfinite(table)):
        raise ValueError("load-displacement table contains non-finite values")
    expected_steps = np.arange(1, steps_per_cycle + 1, dtype=np.int64)
    cycles: list[LoadDisplacementCycle] = []
    for offset in range(0, len(table), steps_per_cycle):
        block = table[offset : offset + steps_per_cycle]
        steps = np.rint(block[:, 0]).astype(np.int64)
        if not np.array_equal(steps, expected_steps):
            raise ValueError(
                "load-displacement step sequence mismatch in cycle "
                f"{len(cycles) + 1}: {steps.tolist()}"
            )
        cycles.append(
            LoadDisplacementCycle(
                cycle=len(cycles) + 1,
                step=steps,
                ux=block[:, 1].copy(),
                fx=block[:, 2].copy(),
                uy=block[:, 3].copy(),
                fy=block[:, 4].copy(),
            )
        )
    return cycles


def amplify_damage(base_damage: np.ndarray, beta: float) -> np.ndarray:
    """Strengthen or weaken a fixed damage geometry without moving its support.

    ``d_beta = 1 - (1 - d0)**beta`` implies
    ``g_beta = (1 - d0)**(2*beta)`` for eta=0.
    """
    base = np.asarray(base_damage, dtype=np.float64)
    if beta <= 0.0 or not np.isfinite(beta):
        raise ValueError("beta must be finite and positive")
    if not np.all(np.isfinite(base)) or np.min(base) < 0.0 or np.max(base) > 1.0:
        raise ValueError("base damage must be finite and lie in [0, 1]")
    amplified = 1.0 - np.power(1.0 - base, float(beta))
    amplified[base == 0.0] = 0.0
    amplified[base == 1.0] = 1.0
    return np.clip(amplified, 0.0, 1.0)


def merge_irreversible_damage(
    prior: np.ndarray,
    observed_profile: np.ndarray,
    beta: float,
) -> np.ndarray:
    """Merge an amplified observation profile without healing prior damage.

    Both inputs are damage fields on the same support.  A fresh array is
    returned so callers can safely retain the historical prior and visible-profile
    reconstruction as immutable provenance artifacts.
    """
    prior_array = np.asarray(prior, dtype=np.float64)
    profile_array = np.asarray(observed_profile, dtype=np.float64)
    if prior_array.shape != profile_array.shape:
        raise ValueError("prior and observed profile must have matching shapes")
    if prior_array.size == 0:
        raise ValueError("damage fields must not be empty")
    if (
        not np.all(np.isfinite(prior_array))
        or np.min(prior_array) < 0.0
        or np.max(prior_array) > 1.0
    ):
        raise ValueError("prior damage must be finite and lie in [0, 1]")
    amplified = amplify_damage(profile_array, beta)
    return np.maximum(prior_array, amplified)


def relative_reaction_error(predicted: float, observed: float) -> float:
    """Return an absolute reaction error normalized by the observed magnitude."""
    if not np.isfinite(predicted) or not np.isfinite(observed) or observed == 0.0:
        raise ValueError("finite non-zero observed reaction is required")
    return abs(float(predicted) - float(observed)) / abs(float(observed))


def feasible_reaction_brackets(
    beta: np.ndarray,
    reaction: np.ndarray,
    observed: float,
    feasible: np.ndarray,
) -> list[tuple[float, float]]:
    """Find adjacent feasible sign-change brackets without crossing failures."""
    beta = np.asarray(beta, dtype=np.float64).reshape(-1)
    reaction = np.asarray(reaction, dtype=np.float64).reshape(-1)
    feasible = np.asarray(feasible, dtype=bool).reshape(-1)
    if beta.shape != reaction.shape or beta.shape != feasible.shape:
        raise ValueError("beta, reaction and feasible arrays must have matching shapes")
    if len(beta) < 2 or np.any(np.diff(beta) <= 0.0):
        raise ValueError("beta values must be strictly increasing")
    if observed == 0.0 or not np.isfinite(observed):
        raise ValueError("finite non-zero observed reaction is required")
    brackets: list[tuple[float, float]] = []
    residual = reaction - float(observed)
    for index in range(len(beta) - 1):
        if not feasible[index] or not feasible[index + 1]:
            continue
        if not np.isfinite(residual[index]) or not np.isfinite(residual[index + 1]):
            continue
        if residual[index] == 0.0:
            brackets.append((float(beta[index]), float(beta[index])))
        elif residual[index] * residual[index + 1] < 0.0:
            brackets.append((float(beta[index]), float(beta[index + 1])))
    if feasible[-1] and np.isfinite(residual[-1]) and residual[-1] == 0.0:
        brackets.append((float(beta[-1]), float(beta[-1])))
    return brackets


def log_midpoint(lower: float, upper: float) -> float:
    """Return the geometric midpoint of a positive bracket."""
    if lower <= 0.0 or upper <= lower:
        raise ValueError("a positive increasing bracket is required")
    return float(np.sqrt(lower * upper))
