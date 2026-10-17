"""Leakage-safe separable spatial-DCT and temporal-B-spline field adapter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import BSpline


def _bspline_knots(t_min: float, t_max: float, n_basis: int, degree: int) -> np.ndarray:
    if n_basis <= degree:
        raise ValueError("n_basis must exceed spline degree")
    n_internal = n_basis - degree - 1
    internal = np.linspace(t_min, t_max, n_internal + 2)[1:-1]
    return np.concatenate(
        [np.repeat(t_min, degree + 1), internal, np.repeat(t_max, degree + 1)]
    )


@dataclass(frozen=True)
class AdapterConfig:
    x_modes: int = 6
    y_modes: int = 4
    temporal_basis: int = 8
    spline_degree: int = 3
    ridge: float = 1e-7
    defect_center_x: float = 0.035
    defect_center_y: float = 0.0
    defect_scales: tuple[float, ...] = (0.05, 0.10, 0.20)
    wheelpath_scales: tuple[float, ...] = (0.08, 0.20)


class StructuredFieldAdapter:
    """Fit ``sum A_mk B_m(t) phi_k(x,y)`` from sparse pre-cutoff samples."""

    def __init__(self, config: AdapterConfig, *, cutoff_time: float) -> None:
        self.config = config
        self.cutoff_time = float(cutoff_time)
        self._coefficient: np.ndarray | None = None
        self._domain: tuple[float, float, float, float, float] | None = None
        self._knots: np.ndarray | None = None

    def _spatial_basis(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        if self._domain is None:
            raise RuntimeError("Adapter has not been fitted")
        x_min, x_max, y_min, y_max, _ = self._domain
        xn = (x - x_min) / max(x_max - x_min, np.finfo(float).eps)
        yn = (y - y_min) / max(y_max - y_min, np.finfo(float).eps)
        columns = []
        for ky in range(self.config.y_modes):
            for kx in range(self.config.x_modes):
                columns.append(np.cos(np.pi * kx * xn) * np.cos(np.pi * ky * yn))
        for scale in self.config.defect_scales:
            columns.append(
                np.exp(
                    -np.square((x - self.config.defect_center_x) / scale)
                    -np.square((y - self.config.defect_center_y) / (1.8 * scale))
                )
            )
        for scale in self.config.wheelpath_scales:
            columns.append(np.exp(-np.square(y / scale)))
        return np.column_stack(columns)

    def _temporal_basis(self, time: np.ndarray, derivative: bool = False) -> np.ndarray:
        if self._knots is None:
            raise RuntimeError("Adapter has not been fitted")
        coefficients = np.eye(self.config.temporal_basis)
        spline = BSpline(
            self._knots,
            coefficients,
            self.config.spline_degree,
            extrapolate=False,
        )
        if derivative:
            spline = spline.derivative()
        values = np.asarray(spline(time), dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Query time lies outside the fitted spline domain")
        return values

    def _design(self, frame: pd.DataFrame, derivative: bool = False) -> np.ndarray:
        spatial = self._spatial_basis(frame["x"].to_numpy(float), frame["y"].to_numpy(float))
        temporal = self._temporal_basis(frame["time"].to_numpy(float), derivative=derivative)
        return np.einsum("ni,nj->nij", temporal, spatial).reshape(len(frame), -1)

    def fit(self, observations: pd.DataFrame, *, value_column: str = "damage_observed") -> None:
        required = {"x", "y", "time", value_column}
        missing = sorted(required.difference(observations.columns))
        if missing:
            raise ValueError("Adapter observations lack: " + ", ".join(missing))
        if observations.empty:
            raise ValueError("Adapter observations are empty")
        if (observations["time"].to_numpy(float) > self.cutoff_time + 1e-12).any():
            raise ValueError("Field adapter cannot fit future observations beyond cutoff")
        t_min = float(observations["time"].min())
        if t_min >= self.cutoff_time:
            raise ValueError("Adapter needs observations before the cutoff")
        self._domain = (
            float(observations["x"].min()),
            float(observations["x"].max()),
            float(observations["y"].min()),
            float(observations["y"].max()),
            t_min,
        )
        self._knots = _bspline_knots(
            t_min,
            self.cutoff_time,
            self.config.temporal_basis,
            self.config.spline_degree,
        )
        design = self._design(observations)
        target = observations[value_column].to_numpy(float)
        gram = np.einsum("ni,nj->ij", design, design)
        rhs = np.einsum("ni,n->i", design, target)
        self._coefficient = np.linalg.solve(
            gram + self.config.ridge * np.eye(design.shape[1]), rhs
        )

    def predict(self, query: pd.DataFrame, *, derivative: bool = False) -> np.ndarray:
        if self._coefficient is None:
            raise RuntimeError("Adapter has not been fitted")
        times = query["time"].to_numpy(float)
        if (times > self.cutoff_time + 1e-12).any():
            raise ValueError("Field adapter cannot predict future damage beyond cutoff")
        design = self._design(query, derivative=derivative)
        values = np.einsum("ni,i->n", design, self._coefficient)
        return values if derivative else np.clip(values, 0.0, 1.0)

    def manifest(self) -> dict[str, object]:
        if self._coefficient is None or self._domain is None:
            raise RuntimeError("Adapter has not been fitted")
        return {
            "representation": "spatial_dct_x_temporal_cubic_bspline",
            "config": self.config.__dict__,
            "cutoff_time": self.cutoff_time,
            "domain": list(self._domain),
            "coefficient_sha256": hashlib.sha256(self._coefficient.tobytes()).hexdigest(),
            "future_damage_access": False,
        }


def hash_frozen_arrays(path: Path, arrays: dict[str, np.ndarray], metadata: dict[str, object]) -> str:
    np.savez_compressed(path, **arrays, metadata_json=json.dumps(metadata, sort_keys=True))
    return hashlib.sha256(path.read_bytes()).hexdigest()
