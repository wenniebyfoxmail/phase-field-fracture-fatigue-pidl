"""Area/time-weighted weak residual systems built from frozen cell snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np
import pandas as pd

from .library import DEFAULT_TERM_NAMES, build_candidate_library


@dataclass(frozen=True)
class WeakSystem:
    A: np.ndarray
    b: np.ndarray
    term_names: tuple[str, ...]
    metadata: pd.DataFrame

    def as_frame(self) -> pd.DataFrame:
        frame = self.metadata.reset_index(drop=True).copy()
        frame["lhs_b"] = self.b
        for j, name in enumerate(self.term_names):
            frame[f"theta__{name}"] = self.A[:, j]
        return frame


def _compact_weight(r: np.ndarray, family: str) -> np.ndarray:
    q = np.clip(np.abs(r), 0.0, 1.0)
    if family == "hat":
        return np.maximum(1.0 - q, 0.0)
    if family == "quartic":
        return np.square(np.maximum(1.0 - q * q, 0.0))
    if family == "cosine":
        out = np.zeros_like(q)
        inside = q < 1.0
        out[inside] = np.cos(0.5 * np.pi * q[inside]) ** 2
        return out
    raise ValueError(f"Unknown test-function family {family!r}")


def _compact_weight_derivative(r: np.ndarray, family: str) -> np.ndarray:
    out = np.zeros_like(r, dtype=float)
    inside = np.abs(r) < 1.0
    q = r[inside]
    if family == "quartic":
        out[inside] = -4.0 * q * (1.0 - q * q)
        return out
    if family == "cosine":
        out[inside] = -0.5 * np.pi * np.sin(np.pi * q)
        return out
    raise ValueError("Dynamic weak derivatives require quartic or cosine tests")


def _time_step_weights(frame: pd.DataFrame) -> np.ndarray:
    unique = np.sort(frame["time"].unique().astype(float))
    if len(unique) == 1:
        return np.ones(len(frame), dtype=float)
    dt = np.gradient(unique)
    mapping = dict(zip(unique.tolist(), dt.tolist()))
    return frame["time"].map(mapping).to_numpy(dtype=float)


def assemble_weak_system(
    frame: pd.DataFrame,
    *,
    term_names: Sequence[str] = DEFAULT_TERM_NAMES,
    n_windows: int = 256,
    seed: int = 0,
    test_function_families: Sequence[str] = ("hat", "quartic", "cosine"),
    min_points: int = 12,
) -> WeakSystem:
    """Integrate ``-known_residual`` and candidate terms over compact windows.

    This first version targets algebraic residual corrections. Derivative
    transfer by integration by parts is intentionally deferred until a declared
    spatial correction slot is added.
    """

    if n_windows < 8:
        raise ValueError("n_windows must be at least 8")
    library = build_candidate_library(frame, term_names)
    work = frame.reset_index(drop=True).copy()
    library = library.reset_index(drop=True)
    work["_dt"] = 0.0
    for _, idx in work.groupby("trajectory_id", sort=False).groups.items():
        work.loc[idx, "_dt"] = _time_step_weights(work.loc[idx])

    rng = np.random.default_rng(seed)
    trajectories = tuple(sorted(work["trajectory_id"].astype(str).unique()))
    rows_a: list[np.ndarray] = []
    rows_b: list[float] = []
    metadata: list[dict[str, object]] = []
    attempts = 0
    max_attempts = n_windows * 30
    while len(rows_b) < n_windows and attempts < max_attempts:
        attempts += 1
        trajectory_id = str(rng.choice(trajectories))
        part = work[work["trajectory_id"].astype(str) == trajectory_id]
        x_min, x_max = float(part["x"].min()), float(part["x"].max())
        y_min, y_max = float(part["y"].min()), float(part["y"].max())
        t_min, t_max = float(part["time"].min()), float(part["time"].max())
        hx = max((x_max - x_min) * rng.uniform(0.22, 0.45), 1e-12)
        hy = max((y_max - y_min) * rng.uniform(0.35, 0.65), 1e-12)
        ht = max((t_max - t_min) * rng.uniform(0.20, 0.40), 1e-12)
        cx = rng.uniform(x_min, x_max)
        cy = rng.uniform(y_min, y_max)
        ct = rng.uniform(t_min, t_max)
        family = str(rng.choice(tuple(test_function_families)))
        rx = (part["x"].to_numpy(float) - cx) / hx
        ry = (part["y"].to_numpy(float) - cy) / hy
        rt = (part["time"].to_numpy(float) - ct) / ht
        weight = _compact_weight(rx, family) * _compact_weight(ry, family) * _compact_weight(rt, family)
        weight *= part["cell_area"].to_numpy(float) * part["_dt"].to_numpy(float)
        active = weight > 0.0
        if int(active.sum()) < min_points or float(weight.sum()) <= 0.0:
            continue
        normalized = weight / weight.sum()
        idx = part.index.to_numpy()
        candidate_values = library.loc[idx, list(term_names)].to_numpy(float)
        residual_values = -part["known_residual"].to_numpy(float)
        weak_a = np.sum(normalized[:, None] * candidate_values, axis=0)
        weak_b = float(np.sum(normalized * residual_values))
        active_measure = float(
            np.sum(normalized * np.maximum(part["psi_plus"].to_numpy(float), 0.0))
        )
        if not np.isfinite(weak_a).all() or not np.isfinite(weak_b):
            raise ValueError("Weak integration produced non-finite values")
        rows_a.append(weak_a)
        rows_b.append(weak_b)
        time_fraction = 0.0 if t_max == t_min else (ct - t_min) / (t_max - t_min)
        time_block = min(4, int(np.floor(5.0 * time_fraction)))
        metadata.append(
            {
                "window_id": f"w{len(rows_b) - 1:04d}",
                "trajectory_id": trajectory_id,
                "split_group": f"{trajectory_id}::tb{time_block}",
                "test_function_id": family,
                "center_x": cx,
                "center_y": cy,
                "center_time": ct,
                "halfwidth_x": hx,
                "halfwidth_y": hy,
                "halfwidth_time": ht,
                "point_count": int(active.sum()),
                "active_measure": active_measure,
                "boundary_policy": "compact_support_zero_weight",
            }
        )
    if len(rows_b) < n_windows:
        raise ValueError(f"Only assembled {len(rows_b)} of {n_windows} requested weak windows")
    return WeakSystem(
        A=np.vstack(rows_a),
        b=np.asarray(rows_b, dtype=float),
        term_names=tuple(term_names),
        metadata=pd.DataFrame(metadata),
    )


def assemble_dynamic_weak_system(
    frame: pd.DataFrame,
    *,
    term_names: Sequence[str],
    n_windows: int = 256,
    seed: int = 0,
    test_function_families: Sequence[str] = ("quartic", "cosine"),
    min_points: int = 24,
) -> WeakSystem:
    """Assemble ``weak(d_t - known_rate) = weak(candidate corrections)``.

    The time derivative is transferred to a compact test function, avoiding a
    pointwise derivative of the reconstructed field. Temporal supports are
    forced strictly inside the available pre-cutoff interval so boundary terms
    vanish.
    """

    if "known_rate" not in frame:
        raise ValueError("Dynamic weak assembly requires known_rate")
    library = build_candidate_library(frame, term_names)
    work = frame.reset_index(drop=True).copy()
    library = library.reset_index(drop=True)
    work["_dt"] = 0.0
    for _, idx in work.groupby("trajectory_id", sort=False).groups.items():
        work.loc[idx, "_dt"] = _time_step_weights(work.loc[idx])
    rng = np.random.default_rng(seed)
    trajectories = tuple(sorted(work["trajectory_id"].astype(str).unique()))
    rows_a: list[np.ndarray] = []
    rows_b: list[float] = []
    metadata: list[dict[str, object]] = []
    attempts = 0
    while len(rows_b) < n_windows and attempts < n_windows * 40:
        attempts += 1
        trajectory_id = str(rng.choice(trajectories))
        part = work[work["trajectory_id"].astype(str) == trajectory_id]
        x_min, x_max = float(part["x"].min()), float(part["x"].max())
        y_min, y_max = float(part["y"].min()), float(part["y"].max())
        t_min, t_max = float(part["time"].min()), float(part["time"].max())
        hx = max((x_max - x_min) * rng.uniform(0.22, 0.45), 1e-12)
        hy = max((y_max - y_min) * rng.uniform(0.35, 0.65), 1e-12)
        ht = max((t_max - t_min) * rng.uniform(0.18, 0.32), 1e-12)
        if 2.0 * ht >= t_max - t_min:
            continue
        cx = rng.uniform(x_min, x_max)
        cy = rng.uniform(y_min, y_max)
        ct = rng.uniform(t_min + ht, t_max - ht)
        family = str(rng.choice(tuple(test_function_families)))
        rx = (part["x"].to_numpy(float) - cx) / hx
        ry = (part["y"].to_numpy(float) - cy) / hy
        rt = (part["time"].to_numpy(float) - ct) / ht
        spatial = _compact_weight(rx, family) * _compact_weight(ry, family)
        temporal = _compact_weight(rt, family)
        temporal_derivative = _compact_weight_derivative(rt, family) / ht
        weak_weight = spatial * temporal
        quadrature = part["cell_area"].to_numpy(float) * part["_dt"].to_numpy(float)
        active = weak_weight > 0.0
        normalizer = float(np.sum(quadrature * weak_weight))
        if int(active.sum()) < min_points or normalizer <= 0.0:
            continue
        idx = part.index.to_numpy()
        candidate_values = library.loc[idx, list(term_names)].to_numpy(float)
        weak_a = np.sum(
            (quadrature * weak_weight)[:, None] * candidate_values, axis=0
        ) / normalizer
        weak_dt = -float(
            np.sum(
                quadrature
                * spatial
                * temporal_derivative
                * part["d"].to_numpy(float)
            )
            / normalizer
        )
        weak_known = float(
            np.sum(
                quadrature
                * weak_weight
                * part["known_rate"].to_numpy(float)
            )
            / normalizer
        )
        weak_b = weak_dt - weak_known
        active_measure = float(
            np.sum(
                quadrature
                * weak_weight
                * part["d"].to_numpy(float)
                * part["psi_plus"].to_numpy(float)
            )
            / normalizer
        )
        if not np.isfinite(weak_a).all() or not np.isfinite(weak_b):
            raise ValueError("Dynamic weak integration produced non-finite values")
        weighted_damage = part["d"].to_numpy(float)[active]
        damage_mean = float(np.average(weighted_damage, weights=weak_weight[active]))
        damage_std = float(
            np.sqrt(
                np.average(
                    np.square(weighted_damage - damage_mean), weights=weak_weight[active]
                )
            )
        )
        damage_max = float(np.max(weighted_damage))
        if damage_max >= 0.25 and damage_std >= 0.025:
            window_stratum = "tip"
        elif damage_mean >= 0.25:
            window_stratum = "crack_body"
        else:
            window_stratum = "background"
        rows_a.append(weak_a)
        rows_b.append(weak_b)
        time_fraction = (ct - t_min) / max(t_max - t_min, np.finfo(float).eps)
        time_block = min(4, int(np.floor(5.0 * time_fraction)))
        metadata.append(
            {
                "window_id": f"dw{len(rows_b) - 1:04d}",
                "trajectory_id": trajectory_id,
                "split_group": f"{trajectory_id}::tb{time_block}",
                "test_function_id": family,
                "center_x": cx,
                "center_y": cy,
                "center_time": ct,
                "halfwidth_x": hx,
                "halfwidth_y": hy,
                "halfwidth_time": ht,
                "point_count": int(active.sum()),
                "stratum": window_stratum,
                "damage_mean": damage_mean,
                "damage_std": damage_std,
                "active_measure": active_measure,
                "boundary_policy": "compact_temporal_support_interior_ibp",
            }
        )
    if len(rows_b) < n_windows:
        raise ValueError(f"Only assembled {len(rows_b)} of {n_windows} dynamic weak windows")
    return WeakSystem(
        A=np.vstack(rows_a),
        b=np.asarray(rows_b, dtype=float),
        term_names=tuple(term_names),
        metadata=pd.DataFrame(metadata),
    )
