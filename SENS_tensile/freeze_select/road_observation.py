"""Observation-only road transitions for weak-form equation selection.

This module deliberately excludes FEM/phase-field latent mechanics. It provides
the smallest frozen transition and candidate-library contract needed to run a
real-road geometry/climate Freeze-Then-Select route without fabricating
displacement, energy, history, degradation, traffic, or moisture fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

import numpy as np


OBSERVED = "observed"
SPARSE_UNUSABLE = "sparse_unusable"
ABSENT = "absent"
UNAVAILABLE_RESOLUTION = "unavailable_resolution"
FORBIDDEN = "forbidden"


LTPP_06_1253_CANDIDATE_STATUS = {
    "low_temp_exposure": OBSERVED,
    "temp_variation_rate": OBSERVED,
    "precipitation_rate": OBSERVED,
    "traffic_rate": SPARSE_UNUSABLE,
    "cumulative_traffic": SPARSE_UNUSABLE,
    "moisture": ABSENT,
    "humidity": ABSENT,
    "rain_7d": UNAVAILABLE_RESOLUTION,
    "traffic_temperature": FORBIDDEN,
    "traffic_moisture": FORBIDDEN,
}


@dataclass(frozen=True)
class ObservedForcing:
    name: str
    values: np.ndarray
    unit: str
    source_sha256: str
    coverage_start: date
    coverage_end: date
    status: str = OBSERVED


@dataclass(frozen=True)
class FrozenRoadTransition:
    section_id: str
    transition_id: str
    start_date: date
    end_date: date
    x_m: np.ndarray
    y_m: np.ndarray
    cell_area_m2: np.ndarray
    damage_start: np.ndarray
    damage_end: np.ndarray
    valid_mask: np.ndarray
    forcing: Mapping[str, ObservedForcing]
    candidate_status: Mapping[str, str]
    field_hash_start: str
    field_hash_end: str
    adapter_hash: str
    adapter_fit_dates: tuple[date, ...]
    fields_frozen: bool
    future_geometry_used: bool
    evidence_label: str = "ltpp_observation_only_geometry_climate"

    def validate(self, *, strict_forecast: bool = False) -> None:
        if self.section_id != "06-1253":
            raise ValueError("unexpected section_id")
        if self.start_date >= self.end_date:
            raise ValueError("transition dates must be strictly increasing")
        if not self.fields_frozen:
            raise ValueError("field representation must be frozen before selection")
        if self.future_geometry_used:
            raise ValueError("future geometry leakage is prohibited")
        if not self.field_hash_start or not self.field_hash_end or not self.adapter_hash:
            raise ValueError("frozen field and adapter hashes are mandatory")
        arrays = (
            self.x_m,
            self.y_m,
            self.cell_area_m2,
            self.damage_start,
            self.damage_end,
            self.valid_mask,
        )
        if any(np.asarray(value).ndim != 1 for value in arrays):
            raise ValueError("road transition arrays must be one-dimensional")
        size = len(self.x_m)
        if size == 0 or any(len(value) != size for value in arrays):
            raise ValueError("road transition arrays must have equal non-zero length")
        for name, values in (
            ("x_m", self.x_m),
            ("y_m", self.y_m),
            ("cell_area_m2", self.cell_area_m2),
            ("damage_start", self.damage_start),
            ("damage_end", self.damage_end),
        ):
            if not np.all(np.isfinite(values)):
                raise ValueError(f"{name} contains non-finite values")
        if not np.all(self.cell_area_m2 > 0):
            raise ValueError("cell areas must be positive")
        if np.any(self.damage_start < 0) or np.any(self.damage_start > 1):
            raise ValueError("damage_start must lie in [0, 1]")
        if np.any(self.damage_end < 0) or np.any(self.damage_end > 1):
            raise ValueError("damage_end must lie in [0, 1]")
        if np.asarray(self.valid_mask).dtype != np.dtype(bool):
            raise ValueError("valid_mask must be boolean")
        latest_allowed_fit = self.start_date if strict_forecast else self.end_date
        if any(fit_date > latest_allowed_fit for fit_date in self.adapter_fit_dates):
            raise ValueError("adapter fit dates violate the declared temporal cutoff")
        for name, channel in self.forcing.items():
            if name != channel.name:
                raise ValueError("forcing mapping key/name mismatch")
            if channel.status != OBSERVED:
                raise ValueError("only observed forcing may enter a transition")
            if self.candidate_status.get(name) != OBSERVED:
                raise ValueError(f"forcing {name} is not authorized as observed")
            values = np.asarray(channel.values)
            if values.ndim != 1 or len(values) not in (1, size):
                raise ValueError(f"forcing {name} must be scalar or cell-aligned")
            if not np.all(np.isfinite(values)):
                raise ValueError(f"forcing {name} contains non-finite values")
            if channel.coverage_start > self.start_date or channel.coverage_end < self.end_date:
                raise ValueError(f"forcing {name} does not cover the transition")
            if not channel.source_sha256:
                raise ValueError(f"forcing {name} lacks source provenance")


def _broadcast(values: np.ndarray, size: int) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if len(array) == 1:
        return np.full(size, float(array[0]), dtype=np.float64)
    return array


def build_observed_candidate_library(
    transition: FrozenRoadTransition,
    requested_terms: Sequence[str],
    *,
    strict_forecast: bool = False,
) -> tuple[np.ndarray, tuple[str, ...]]:
    """Build pointwise columns that can later be integrated in a weak system."""

    transition.validate(strict_forecast=strict_forecast)
    size = len(transition.x_m)
    damage = np.asarray(transition.damage_start, dtype=np.float64)
    columns: dict[str, np.ndarray] = {
        "constant": np.ones(size, dtype=np.float64),
        "damage": damage,
        "damage_sq": damage * damage,
    }
    for name, channel in transition.forcing.items():
        if transition.candidate_status.get(name) != OBSERVED:
            continue
        values = _broadcast(channel.values, size)
        columns[name] = values
        columns[f"damage_x_{name}"] = damage * values

    selected = []
    for term in requested_terms:
        if term in columns:
            selected.append(columns[term])
            continue
        base = term.removeprefix("damage_x_")
        status = transition.candidate_status.get(base)
        if status and status != OBSERVED:
            raise ValueError(f"candidate {term} is disabled: {status}")
        raise ValueError(f"candidate {term} is unavailable or undeclared")
    if not selected:
        raise ValueError("candidate library cannot be empty")
    return np.column_stack(selected), tuple(requested_terms)
