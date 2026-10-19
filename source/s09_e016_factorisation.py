"""Pure numerical core for the S09-E016 damage-increment factorisation audit."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np


EXPECTED_CYCLES = (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73)
GROWTH_CYCLES = (1, 58, 60, 69, 70)
NEAR_STAGNANT_CYCLES = (3, 4, 71, 72, 73)
PAIR_ORDER = tuple(
    (growth, stagnant) for growth in GROWTH_CYCLES for stagnant in NEAR_STAGNANT_CYCLES
)

CAPACITY_EPS = 0.0
FRACTION_EPS = 2.0**-53
Q_MAX = np.nextafter(np.float64(1.0), np.float64(0.0))
ZERO_AMPLITUDE_TOL = 0.0
FIELD_VALIDITY_TOL = 1.0e-12
ROUNDTRIP_RTOL = 64.0 * np.finfo(np.float64).eps
ROUNDTRIP_ATOL = 0.0
SUPPORT_THRESHOLD = 1.0e-15


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def normalised_weights(weights: np.ndarray) -> np.ndarray:
    value = np.asarray(weights, dtype=np.float64).reshape(-1)
    _require(value.size > 0, "empty nodal weights")
    _require(np.isfinite(value).all(), "nonfinite nodal weights")
    _require(np.all(value > 0.0), "nodal weights must be strictly positive")
    total = float(value.sum(dtype=np.float64))
    _require(math.isfinite(total) and total > 0.0, "invalid nodal-weight sum")
    return value / total


@dataclass(frozen=True)
class Factorisation:
    amplitude: float
    shape: np.ndarray
    shape_valid: bool
    increment: np.ndarray
    encoded_increment: np.ndarray
    reconstructed_increment: np.ndarray
    residual: np.ndarray
    clipping_residual: np.ndarray
    weighted_mean_increment: float
    maximum_increment: float
    positive_node_count: int
    saturated_fraction_count: int
    masked_capacity_positive_count: int
    maximum_roundtrip_error: float
    maximum_roundtrip_relative_error: float
    weighted_roundtrip_error: float
    maximum_clipping_residual: float
    clipping_bound_valid: bool


def factorise_increment(
    damage_pre: np.ndarray,
    damage_peak: np.ndarray,
    nodal_weight: np.ndarray,
    *,
    capacity_eps: float = CAPACITY_EPS,
    fraction_eps: float = FRACTION_EPS,
    zero_amplitude_tol: float = ZERO_AMPLITUDE_TOL,
    field_validity_tol: float = FIELD_VALIDITY_TOL,
) -> Factorisation:
    """Factorise one bounded nonnegative damage increment into hazard A and S.

    ``S`` is normalised by the supplied nodal quadrature weights. A strict zero
    event receives an all-zero sentinel and ``shape_valid=False``.
    """
    pre = np.asarray(damage_pre, dtype=np.float64).reshape(-1)
    peak = np.asarray(damage_peak, dtype=np.float64).reshape(-1)
    weights = normalised_weights(nodal_weight)
    _require(pre.shape == peak.shape == weights.shape, "damage/weight shape drift")
    _require(
        np.isfinite(pre).all() and np.isfinite(peak).all(), "nonfinite damage field"
    )
    _require(
        capacity_eps >= 0.0 and math.isfinite(capacity_eps), "invalid capacity epsilon"
    )
    _require(
        0.0 < fraction_eps < 1.0 and math.isfinite(fraction_eps),
        "invalid fraction epsilon",
    )
    _require(
        zero_amplitude_tol >= 0.0 and math.isfinite(zero_amplitude_tol),
        "invalid zero tolerance",
    )

    if (
        float(pre.min()) < -field_validity_tol
        or float(pre.max()) > 1.0 + field_validity_tol
    ):
        raise ValueError("damage_pre outside [0,1]")
    if (
        float(peak.min()) < -field_validity_tol
        or float(peak.max()) > 1.0 + field_validity_tol
    ):
        raise ValueError("damage_peak outside [0,1]")

    capacity = np.clip(1.0 - pre, 0.0, 1.0)
    raw_increment = peak - pre
    if float(raw_increment.min()) < -field_validity_tol:
        raise ValueError("material irreversibility violation")
    if float(np.max(raw_increment - capacity)) > field_validity_tol:
        raise ValueError("material remaining-capacity violation")
    increment = np.clip(raw_increment, 0.0, capacity)

    usable = capacity > capacity_eps
    masked_positive = int(np.count_nonzero((~usable) & (increment > 0.0)))
    q = np.zeros_like(increment)
    q_max = np.float64(1.0 - fraction_eps)
    _require(q_max == Q_MAX, "fraction epsilon does not map to float64 nextafter(1,0)")
    q[usable] = np.clip(increment[usable] / capacity[usable], 0.0, q_max)
    saturated = int(np.count_nonzero(q >= q_max))
    encoded_increment = capacity * q
    clipping_residual = increment - encoded_increment
    clipping_bound = capacity * (1.0 - q_max)
    clipping_bound_with_roundoff = (
        clipping_bound + 2.0 * np.finfo(np.float64).eps * capacity
    )
    clipping_lower_with_roundoff = -2.0 * np.finfo(np.float64).eps * capacity
    clipping_bound_valid = bool(
        np.all(clipping_residual >= clipping_lower_with_roundoff)
        and np.all(clipping_residual <= clipping_bound_with_roundoff)
    )
    _require(clipping_bound_valid, "saturation clipping bound violated")
    hazard = -np.log1p(-q)
    amplitude = float(np.dot(weights, hazard))
    _require(math.isfinite(amplitude) and amplitude >= 0.0, "invalid hazard amplitude")

    if amplitude == zero_amplitude_tol:
        _require(
            not np.any(increment > 0.0),
            "positive event lost by numerical factorisation",
        )
        shape = np.zeros_like(hazard)
        shape_valid = False
        reconstructed = np.zeros_like(increment)
    else:
        shape = hazard / amplitude
        shape_valid = True
        _require(
            np.isfinite(shape).all() and np.all(shape >= 0.0), "invalid hazard shape"
        )
        mass = float(np.dot(weights, shape))
        _require(
            abs(mass - 1.0) <= 64.0 * np.finfo(np.float64).eps,
            "weighted shape normalisation drift",
        )
        reconstructed = capacity * (-np.expm1(-amplitude * shape))

    residual = reconstructed - encoded_increment
    positive_encoded = encoded_increment > 0.0
    relative = np.zeros_like(residual)
    relative[positive_encoded] = (
        np.abs(residual[positive_encoded]) / encoded_increment[positive_encoded]
    )
    _require(
        np.all(residual[~positive_encoded] == 0.0),
        "zero encoded increment did not round trip exactly",
    )
    return Factorisation(
        amplitude=amplitude,
        shape=shape,
        shape_valid=shape_valid,
        increment=increment,
        encoded_increment=encoded_increment,
        reconstructed_increment=reconstructed,
        residual=residual,
        clipping_residual=clipping_residual,
        weighted_mean_increment=float(np.dot(weights, increment)),
        maximum_increment=float(increment.max(initial=0.0)),
        positive_node_count=int(np.count_nonzero(increment > 0.0)),
        saturated_fraction_count=saturated,
        masked_capacity_positive_count=masked_positive,
        maximum_roundtrip_error=float(np.max(np.abs(residual), initial=0.0)),
        maximum_roundtrip_relative_error=float(relative.max(initial=0.0)),
        weighted_roundtrip_error=float(np.dot(weights, np.abs(residual))),
        maximum_clipping_residual=float(clipping_residual.max(initial=0.0)),
        clipping_bound_valid=clipping_bound_valid,
    )


def shape_metrics(
    reference: Factorisation,
    candidate: Factorisation,
    nodal_weight: np.ndarray,
    xy: np.ndarray,
    support: np.ndarray,
) -> dict[str, float]:
    _require(reference.shape_valid and candidate.shape_valid, "undefined shape metric")
    weights = normalised_weights(nodal_weight)
    coordinates = np.asarray(xy, dtype=np.float64)
    mask = np.asarray(support, dtype=bool).reshape(-1)
    _require(coordinates.shape == (weights.size, 2), "xy shape drift")
    _require(mask.shape == weights.shape, "support shape drift")
    _require(np.isfinite(coordinates).all(), "nonfinite coordinates")

    ref = reference.shape
    pred = candidate.shape
    half_l1 = 0.5 * float(np.dot(weights, np.abs(pred - ref)))
    numerator = float(np.dot(weights, pred * ref))
    denominator = math.sqrt(
        float(np.dot(weights, pred * pred)) * float(np.dot(weights, ref * ref))
    )
    cosine = numerator / denominator if denominator > 0.0 else math.nan
    captured = float(np.dot(weights * mask, pred))
    ref_centroid = np.sum((weights * ref)[:, None] * coordinates, axis=0)
    pred_centroid = np.sum((weights * pred)[:, None] * coordinates, axis=0)
    return {
        "weighted_half_l1": half_l1,
        "weighted_cosine": cosine,
        "target_support_capture": captured,
        "background_spill": 1.0 - captured,
        "centroid_offset": float(np.linalg.norm(pred_centroid - ref_centroid)),
        "fem_centroid_x": float(ref_centroid[0]),
        "fem_centroid_y": float(ref_centroid[1]),
        "candidate_centroid_x": float(pred_centroid[0]),
        "candidate_centroid_y": float(pred_centroid[1]),
    }


def support_contrast(
    increment: np.ndarray,
    reference_increment: np.ndarray,
    nodal_weight: np.ndarray,
    *,
    support_threshold: float = SUPPORT_THRESHOLD,
) -> float:
    values = np.asarray(increment, dtype=np.float64).reshape(-1)
    reference = np.asarray(reference_increment, dtype=np.float64).reshape(-1)
    weights = np.asarray(nodal_weight, dtype=np.float64).reshape(-1)
    _require(
        values.shape == reference.shape == weights.shape, "support field shape drift"
    )
    support = reference > support_threshold
    background = ~support
    support_weight = float(weights[support].sum())
    background_weight = float(weights[background].sum())
    _require(
        support_weight > 0.0 and background_weight > 0.0, "empty support/background"
    )
    support_mean = float(np.dot(weights[support], values[support]) / support_weight)
    background_mean = float(
        np.dot(weights[background], values[background]) / background_weight
    )
    return support_mean - background_mean


def pair_score(values: Mapping[int, float]) -> dict[str, object]:
    _require(
        set(GROWTH_CYCLES + NEAR_STAGNANT_CYCLES) <= set(values), "missing pair cycle"
    )
    wins = ties = losses = 0
    rows: list[dict[str, object]] = []
    for growth, stagnant in PAIR_ORDER:
        margin = float(values[growth] - values[stagnant])
        _require(math.isfinite(margin), "nonfinite pair margin")
        outcome = "WIN" if margin > 0.0 else "LOSS" if margin < 0.0 else "TIE"
        wins += outcome == "WIN"
        ties += outcome == "TIE"
        losses += outcome == "LOSS"
        rows.append(
            {
                "growth_cycle": growth,
                "stagnant_cycle": stagnant,
                "margin": margin,
                "outcome": outcome,
            }
        )
    return {
        "score_2W_plus_T": int(2 * wins + ties),
        "wins": int(wins),
        "ties": int(ties),
        "losses": int(losses),
        "pairs": rows,
    }


def numerical_readiness(
    fem: list[Factorisation],
    b25: list[Factorisation],
    *,
    roundtrip_rtol: float = ROUNDTRIP_RTOL,
) -> dict[str, object]:
    _require(len(fem) == len(b25) == len(EXPECTED_CYCLES), "factorisation count drift")
    fem_nonzero_cycles = tuple(
        cycle for cycle, item in zip(EXPECTED_CYCLES, fem) if item.shape_valid
    )
    b25_nonzero_cycles = tuple(
        cycle for cycle, item in zip(EXPECTED_CYCLES, b25) if item.shape_valid
    )
    joint_nonzero_cycles = tuple(
        cycle for cycle in fem_nonzero_cycles if cycle in set(b25_nonzero_cycles)
    )
    zero_shape_sentinels_valid = all(
        item.shape_valid
        or (
            item.amplitude == ZERO_AMPLITUDE_TOL
            and np.array_equal(item.shape, np.zeros_like(item.shape))
        )
        for item in fem + b25
    )
    flags = {
        "at_least_one_fem_shape_target": len(fem_nonzero_cycles) > 0,
        "zero_shape_sentinels_valid": zero_shape_sentinels_valid,
        "all_roundtrips_stable": all(
            item.maximum_roundtrip_relative_error <= roundtrip_rtol
            for item in fem + b25
        ),
        "no_positive_increment_hidden_by_capacity_mask": all(
            item.masked_capacity_positive_count == 0 for item in fem + b25
        ),
        "all_metrics_finite": all(
            math.isfinite(value)
            for item in fem + b25
            for value in (
                item.amplitude,
                item.weighted_mean_increment,
                item.maximum_increment,
                item.maximum_roundtrip_error,
                item.maximum_roundtrip_relative_error,
                item.weighted_roundtrip_error,
                item.maximum_clipping_residual,
            )
        ),
        "all_clipping_bounds_valid": all(
            item.clipping_bound_valid for item in fem + b25
        ),
    }
    ready = all(flags.values())
    return {
        "ready": ready,
        "status": (
            "FACTORISATION_READY_FOR_PILOT_CARD"
            if ready
            else "DATA_OR_REPRESENTATION_REPAIR_FIRST"
        ),
        "flags": flags,
        "roundtrip_rtol": roundtrip_rtol,
        "roundtrip_atol": ROUNDTRIP_ATOL,
        "fem_nonzero_cycles": fem_nonzero_cycles,
        "b25_nonzero_cycles": b25_nonzero_cycles,
        "joint_nonzero_cycles": joint_nonzero_cycles,
    }
