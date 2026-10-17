"""Declared residual-term libraries; known phase-field terms are never selectable."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import pandas as pd


TermBuilder = Callable[[pd.DataFrame], np.ndarray]

TRAFFIC_LOG_REFERENCE = float(np.log1p(500.0))

FIXED_PHYSICS_NAMES = frozenset(
    {
        "known_residual",
        "phase_field_residual",
        "damage_laplacian",
        "fracture_shape_operator",
        "mechanical_equilibrium",
    }
)


def _hplus(frame: pd.DataFrame) -> np.ndarray:
    return np.maximum(frame["psi_plus"].to_numpy(dtype=float), 0.0)


def _centered_log_traffic(frame: pd.DataFrame) -> np.ndarray:
    if "traffic_log_reference" in frame:
        reference = frame["traffic_log_reference"].to_numpy(float)
    else:
        reference = TRAFFIC_LOG_REFERENCE
    return np.log1p(frame["traffic_esal_cum"].to_numpy(float)) - reference


TERM_BUILDERS: Mapping[str, TermBuilder] = {
    "hplus_log_traffic": lambda f: _hplus(f) * np.log1p(f["traffic_esal_cum"].to_numpy(float)),
    "hplus_traffic_rate": lambda f: _hplus(f) * f["traffic_esal_rate"].to_numpy(float),
    "hplus_low_temp": lambda f: _hplus(f) * np.maximum(20.0 - f["temperature"].to_numpy(float), 0.0),
    "hplus_abs_temp_delta": lambda f: _hplus(f) * np.abs(f["temp_delta"].to_numpy(float)),
    "hplus_moisture": lambda f: _hplus(f) * f["moisture"].to_numpy(float),
    "hplus_rain_7d": lambda f: _hplus(f) * f["rain_7d"].to_numpy(float),
    "hplus_moisture_log_traffic": lambda f: _hplus(f)
    * f["moisture"].to_numpy(float)
    * _centered_log_traffic(f),
    "hplus_low_temp_log_traffic": lambda f: _hplus(f)
    * np.maximum(20.0 - f["temperature"].to_numpy(float), 0.0)
    * _centered_log_traffic(f),
    "hplus_moisture_low_temp": lambda f: _hplus(f)
    * f["moisture"].to_numpy(float)
    * np.maximum(20.0 - f["temperature"].to_numpy(float), 0.0),
    "hplus_freeze_thaw": lambda f: _hplus(f) * f["freeze_thaw_count"].to_numpy(float),
    "damage_hplus_log_traffic": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * np.log1p(f["traffic_esal_cum"].to_numpy(float)),
    "damage_hplus_traffic_rate": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * f["traffic_esal_rate"].to_numpy(float),
    "damage_hplus_low_temp": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * np.maximum(20.0 - f["temperature"].to_numpy(float), 0.0),
    "damage_hplus_abs_temp_delta": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * np.abs(f["temp_delta"].to_numpy(float)),
    "damage_hplus_moisture": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * f["moisture"].to_numpy(float),
    "damage_hplus_rain_7d": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * f["rain_7d"].to_numpy(float),
    "damage_hplus_moisture_log_traffic": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * f["moisture"].to_numpy(float)
    * _centered_log_traffic(f),
    "damage_hplus_low_temp_log_traffic": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * np.maximum(20.0 - f["temperature"].to_numpy(float), 0.0)
    * _centered_log_traffic(f),
    "damage_hplus_moisture_low_temp": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * f["moisture"].to_numpy(float)
    * np.maximum(20.0 - f["temperature"].to_numpy(float), 0.0),
    "damage_hplus_freeze_thaw": lambda f: (1.0 - f["d"].to_numpy(float))
    * _hplus(f)
    * f["freeze_thaw_count"].to_numpy(float),
}

DEFAULT_TERM_NAMES = tuple(name for name in TERM_BUILDERS if not name.startswith("damage_"))

DYNAMIC_TERM_NAMES = tuple(name for name in TERM_BUILDERS if name.startswith("damage_"))


def build_candidate_library(
    frame: pd.DataFrame,
    term_names: Sequence[str] = DEFAULT_TERM_NAMES,
) -> pd.DataFrame:
    """Evaluate a declared correction library on already-frozen fields."""

    names = tuple(term_names)
    if len(names) != len(set(names)):
        raise ValueError("Candidate term names must be unique")
    fixed = sorted(FIXED_PHYSICS_NAMES.intersection(names))
    if fixed:
        raise ValueError("Known phase-field terms cannot be selected: " + ", ".join(fixed))
    unknown = sorted(set(names).difference(TERM_BUILDERS))
    if unknown:
        raise ValueError("Unknown candidate terms: " + ", ".join(unknown))
    if len(names) > 14:
        raise ValueError("First-pass residual libraries are capped at 14 terms")

    values = {name: np.asarray(TERM_BUILDERS[name](frame), dtype=float) for name in names}
    result = pd.DataFrame(values, index=frame.index)
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError("Candidate library contains non-finite values")
    return result
