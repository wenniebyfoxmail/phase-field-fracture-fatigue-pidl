"""Schema and claim-boundary checks for frozen field snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = (
    "trajectory_id",
    "source_kind",
    "physics_family",
    "protocol_id",
    "snapshot_id",
    "time",
    "cycle",
    "substep",
    "cell_id",
    "x",
    "y",
    "cell_area",
    "known_residual",
    "d",
    "u",
    "v",
    "psi_plus",
    "psi_active",
    "alpha_bar",
    "f_alpha",
    "g_stiffness",
    "ell",
    "Gc_base",
    "traffic_esal_cum",
    "traffic_esal_rate",
    "temperature",
    "temp_delta",
    "temp_gradient",
    "moisture",
    "rain_7d",
    "freeze_thaw_count",
    "field_uncertainty",
    "missingness_flags",
)

NUMERIC_COLUMNS = tuple(
    name
    for name in REQUIRED_COLUMNS
    if name
    not in {
        "trajectory_id",
        "source_kind",
        "physics_family",
        "protocol_id",
        "snapshot_id",
        "cell_id",
        "missingness_flags",
    }
)

REALITY_FORBIDDEN_COLUMNS = (
    "oracle_alpha_bar",
    "oracle_psi_active",
    "true_support_json",
    "true_beta_json",
    "manufactured_residual_id",
)


@dataclass(frozen=True)
class SnapshotSchemaReport:
    row_count: int
    trajectory_count: int
    snapshot_count: int
    physics_families: tuple[str, ...]
    claim_class: str


def _missing(columns: Iterable[str], required: Iterable[str]) -> list[str]:
    present = set(columns)
    return sorted(name for name in required if name not in present)


def validate_frozen_snapshots(
    frame: pd.DataFrame,
    *,
    claim_class: str,
    allow_mixed_physics_family: bool = False,
) -> SnapshotSchemaReport:
    """Validate frozen snapshots before any candidate library is evaluated.

    ``claim_class`` must be explicit so a manufactured or FEM diagnostic cannot
    silently become road evidence.
    """

    allowed_claims = {"tooling-only", "diagnostic", "road-observation"}
    if claim_class not in allowed_claims:
        raise ValueError(f"claim_class must be one of {sorted(allowed_claims)}")
    missing = _missing(frame.columns, REQUIRED_COLUMNS)
    if missing:
        raise ValueError("Frozen snapshot table lacks required columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("Frozen snapshot table is empty")
    if claim_class == "road-observation":
        forbidden = sorted(set(frame.columns).intersection(REALITY_FORBIDDEN_COLUMNS))
        if forbidden:
            raise ValueError("Road-observation mode forbids oracle/truth columns: " + ", ".join(forbidden))

    numeric = frame.loc[:, NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        bad = [name for name in NUMERIC_COLUMNS if not np.isfinite(numeric[name]).all()]
        raise ValueError("Non-finite numeric snapshot columns: " + ", ".join(bad))
    if (numeric["cell_area"] <= 0.0).any():
        raise ValueError("cell_area must be strictly positive")
    if (numeric["ell"] <= 0.0).any() or (numeric["Gc_base"] <= 0.0).any():
        raise ValueError("ell and Gc_base must be strictly positive")
    if ((numeric["moisture"] < 0.0) | (numeric["moisture"] > 1.0)).any():
        raise ValueError("moisture must lie in [0, 1]")

    identity = ["trajectory_id", "snapshot_id", "cell_id"]
    if frame.duplicated(identity).any():
        raise ValueError("Duplicate trajectory_id/snapshot_id/cell_id rows")
    families = tuple(sorted(str(value) for value in frame["physics_family"].unique()))
    if len(families) > 1 and not allow_mixed_physics_family:
        raise ValueError("Frozen snapshots mix physics_family values: " + ", ".join(families))

    return SnapshotSchemaReport(
        row_count=len(frame),
        trajectory_count=int(frame["trajectory_id"].nunique()),
        snapshot_count=int(frame[["trajectory_id", "snapshot_id"]].drop_duplicates().shape[0]),
        physics_families=families,
        claim_class=claim_class,
    )
