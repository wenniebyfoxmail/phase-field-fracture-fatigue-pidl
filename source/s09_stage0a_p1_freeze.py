"""Deterministic in-memory P1 selection and scale freeze for S09-E008.

No file reader is provided: scientific payload access remains separately gated.
"""
from __future__ import annotations

import math
import numpy as np


def require_float64(name: str, value) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != np.float64:
        raise ValueError(f"{name} must be stored float64")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains nonfinite values")
    return array


def half_ulp_float64(value) -> np.ndarray:
    """Representable half-ULP convention with a subnormal lower clamp."""
    x = require_float64("half_ulp input", value)
    upper = np.nextafter(x, np.inf) - x
    lower = x - np.nextafter(x, -np.inf)
    spacing = np.minimum(upper, lower)
    smallest = np.nextafter(np.float64(0), np.float64(1))
    return np.maximum(spacing * np.float64(0.5), smallest)


def weighted_mean_per_sample(value: np.ndarray, weight: np.ndarray) -> np.ndarray:
    axes = tuple(range(1, value.ndim))
    expanded = weight
    while expanded.ndim < value.ndim:
        expanded = expanded[None]
    denominator = weight.sum()
    return (value * expanded).sum(axis=axes) / denominator


def weighted_rms(value: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """RMS over sample and support axes, retaining a final channel axis."""
    if value.ndim == weight.ndim + 1:
        scale = np.max(np.abs(value))
        if scale == 0:
            return np.float64(0)
        scaled = value / scale
        return scale * np.sqrt((np.square(scaled) * weight[None]).sum() /
                               (value.shape[0] * weight.sum()))
    if value.ndim == weight.ndim + 2:
        reduce_axes = tuple(range(value.ndim - 1))
        scale = np.max(np.abs(value), axis=reduce_axes)
        safe_scale = np.where(scale == 0, np.float64(1), scale)
        expanded = weight[None, ..., None]
        scaled = value / safe_scale
        rms = safe_scale * np.sqrt((np.square(scaled) * expanded).sum(reduce_axes) /
                                   (value.shape[0] * weight.sum()))
        return np.where(scale == 0, np.float64(0), rms)
    raise ValueError("unsupported weighted RMS shapes")


def _median(values: np.ndarray) -> float:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    n = len(ordered)
    if n == 0:
        raise ValueError("median of empty group")
    if n % 2:
        return float(ordered[n // 2])
    return float((ordered[n // 2 - 1] + ordered[n // 2]) / 2)


def freeze_p1_contract(
    *,
    cycles,
    d_pre,
    d_peak,
    history_pre,
    history_peak,
    u_peak,
    nodal_weight,
    gp_weight,
) -> dict:
    """Freeze the reviewed 16-cycle selection and fixed teacher normalisers."""
    cycles = np.asarray(cycles)
    if cycles.dtype.kind not in "iu" or tuple(cycles.tolist()) != tuple(range(1, 74)):
        raise ValueError("eligible cycles must be exact integers 1..73")
    d_pre = require_float64("d_pre", d_pre)
    d_peak = require_float64("d_peak", d_peak)
    history_pre = require_float64("history_pre", history_pre)
    history_peak = require_float64("history_peak", history_peak)
    u_peak = require_float64("u_peak", u_peak)
    nodal_weight = require_float64("nodal_weight", nodal_weight)
    gp_weight = require_float64("gp_weight", gp_weight)
    if d_pre.shape != d_peak.shape or d_pre.shape[0] != 73:
        raise ValueError("damage arrays must be [73,node]")
    if history_pre.shape != history_peak.shape or history_pre.shape != (73, *gp_weight.shape, 4):
        raise ValueError("history arrays must be [73,element,4GP,4]")
    if u_peak.shape != (73, d_pre.shape[1], 2):
        raise ValueError("u_peak must be [73,node,2]")
    if nodal_weight.shape != (d_pre.shape[1],) or np.any(nodal_weight <= 0):
        raise ValueError("invalid nodal weights")
    if gp_weight.ndim != 2 or gp_weight.shape[1] != 4 or np.any(gp_weight <= 0):
        raise ValueError("invalid GP weights")

    delta_d = d_peak - d_pre
    g = (np.abs(delta_d) * nodal_weight[None]).sum(axis=1) / nodal_weight.sum()
    export = half_ulp_float64(d_pre) + half_ulp_float64(d_peak)
    eta = float(np.max((export * nodal_weight[None]).sum(axis=1) / nodal_weight.sum()))
    order = np.lexsort((cycles, g))
    upper_count = math.ceil(len(cycles) / 4)
    d_scale = _median(g[order[-upper_count:]])
    if not np.isfinite(d_scale) or d_scale <= 0:
        raise ValueError("detectable-growth scale D must be positive")
    near_limit = max(10 * eta, 0.05 * d_scale)

    selected: set[int] = set()
    for start, stop in ((1, 24), (25, 49), (50, 73)):
        band = np.flatnonzero((cycles >= start) & (cycles <= stop))
        ranked = band[np.lexsort((cycles[band], g[band]))]
        selected.update(cycles[ranked[:2]].tolist())
        selected.update(cycles[ranked[-2:]].tolist())
    remaining = np.array([i for i in order if int(cycles[i]) not in selected], dtype=np.int64)
    selected.update(cycles[remaining[:2]].tolist())
    selected.update(cycles[remaining[-2:]].tolist())
    chosen = np.array(sorted(selected), dtype=np.int64)
    if len(chosen) != 16:
        raise ValueError("deterministic selection must contain exactly 16 cycles")
    chosen_index = chosen - 1
    growth = chosen[g[chosen_index] >= d_scale]
    stagnant = chosen[g[chosen_index] <= near_limit]
    if len(growth) < 4 or len(stagnant) < 4:
        raise ValueError("P1_NOT_READY: insufficient growth or near-stagnant selected cycles")

    tiny = np.finfo(np.float64).tiny
    dd = delta_d[chosen_index]
    dh = (history_peak - history_pre)[chosen_index]
    uu = u_peak[chosen_index]
    dd_floor = half_ulp_float64(d_pre[chosen_index]) + half_ulp_float64(d_peak[chosen_index])
    dh_floor = half_ulp_float64(history_pre[chosen_index]) + half_ulp_float64(history_peak[chosen_index])
    uu_floor = half_ulp_float64(uu)
    normalisers = {
        "damage_increment": float(max(weighted_rms(dd, nodal_weight), weighted_rms(dd_floor, nodal_weight), tiny)),
        "history_increment": np.maximum.reduce((
            weighted_rms(dh, gp_weight), weighted_rms(dh_floor, gp_weight), np.full(4, tiny)
        )).tolist(),
        "displacement": np.maximum.reduce((
            weighted_rms(uu, nodal_weight), weighted_rms(uu_floor, nodal_weight), np.full(2, tiny)
        )).tolist(),
    }
    flat = np.array([normalisers["damage_increment"], *normalisers["history_increment"],
                     *normalisers["displacement"]])
    if not np.isfinite(flat).all() or np.any(flat <= 0):
        raise ValueError("all P1 normalisers must be finite and positive")
    return {
        "verdict": "P1_CONTRACT_FROZEN",
        "eligible_cycles": cycles.tolist(),
        "selected_cycles": chosen.tolist(),
        "growth_cycles": growth.tolist(),
        "near_stagnant_cycles": stagnant.tolist(),
        "eta": eta,
        "D": d_scale,
        "near_stagnant_limit": near_limit,
        "normalisers": normalisers,
        "scientific_execution_authorized": False,
    }
