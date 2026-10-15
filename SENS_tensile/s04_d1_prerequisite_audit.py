#!/usr/bin/env python3
"""Read-only S04-E017 prerequisite audit; no fit, training, or confirmation access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat


LOCK_SHA256 = "cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c"
FIELDS = ("damage", "alpha_bar", "psi_raw_direct")
MONOTONE_FIELDS = ("damage", "alpha_bar")
EPSILON = 1e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(data_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else data_root / path


def weighted(values: list[float], weights: list[float]) -> float:
    mass = sum(weights)
    assert mass > 0
    return sum(v * w for v, w in zip(values, weights)) / mass


def audit_targets(lock: dict, data_root: Path, ids: np.ndarray) -> list[dict]:
    results = []
    for item in lock["trajectories"]:
        assert item["id"] in {"u011", "u0115", "u012", "u013"}
        path = resolve(data_root, item["fem_path"])
        assert sha256(path) == item["fem_sha256"]
        n_cycle = item["common_pre_cycle_end_candidate"]
        payload = loadmat(path, variable_names=[*FIELDS, "cycles"])
        assert np.array_equal(payload["cycles"].ravel()[:n_cycle], np.arange(1, n_cycle + 1))
        record = {"holdout": item["id"], "cycles": n_cycle, "fields": {}}
        for field in FIELDS:
            values = np.asarray(payload[field][:n_cycle, ids], dtype=np.float64)
            assert values.shape == (n_cycle, len(ids)) and np.isfinite(values).all()
            lower = np.maximum(-values, 0.0)
            upper = np.maximum(values - 1.0, 0.0) if field == "damage" else np.zeros_like(values)
            info = {
                "minimum": float(values.min()),
                "maximum": float(values.max()),
                "strict_lower_count": int(np.count_nonzero(values < 0.0)),
                "epsilon_lower_count": int(np.count_nonzero(values < -EPSILON)),
                "strict_upper_count": int(np.count_nonzero(values > 1.0)) if field == "damage" else 0,
                "epsilon_upper_count": int(np.count_nonzero(values > 1.0 + EPSILON)) if field == "damage" else 0,
                "maximum_bound_magnitude": float(np.maximum(lower, upper).max()),
            }
            if field in MONOTONE_FIELDS:
                delta = np.diff(values, axis=0)
                info.update(
                    minimum_temporal_increment=float(delta.min()),
                    strict_decrease_count=int(np.count_nonzero(delta < 0.0)),
                    epsilon_decrease_count=int(np.count_nonzero(delta < -EPSILON)),
                )
            record["fields"][field] = info
        results.append(record)
    return results


def audit_d0(percycle_path: Path) -> list[dict]:
    rows = list(csv.DictReader(percycle_path.open(newline="")))
    assert len(rows) == 357 * 3
    results = []
    for holdout in ("u011", "u0115", "u012", "u013"):
        for field in FIELDS:
            group = [row for row in rows if row["holdout"] == holdout and row["field"] == field]
            assert group
            weights = [float(row["cycle_weight"]) for row in group]
            b0_area = [float(row["B0_bound_area"]) for row in group]
            b1_area = [float(row["bound_violation_area"]) for row in group]
            results.append(
                {
                    "holdout": holdout,
                    "field": field,
                    "B0_mean_bound_area": weighted(b0_area, weights),
                    "B1_mean_bound_area": weighted(b1_area, weights),
                    "B0_max_bound_area": max(b0_area),
                    "B1_max_bound_area": max(b1_area),
                    "B0_minimum": min(float(row["B0_min"]) for row in group),
                    "B0_maximum": max(float(row["B0_max"]) for row in group),
                    "B1_minimum": min(float(row["B1_min"]) for row in group),
                    "B1_maximum": max(float(row["B1_max"]) for row in group),
                }
            )
    return results


def run(lock_path: Path, data_root: Path, d0_output: Path, output: Path) -> None:
    assert sha256(lock_path) == LOCK_SHA256
    lock = json.loads(lock_path.read_text())
    assert set(lock["excluded_amplitudes"]) == {0.1175, 0.125}
    mapping_path = resolve(data_root, lock["geometry"]["path"])
    assert sha256(mapping_path) == lock["geometry"]["sha256"]
    with np.load(mapping_path) as geometry:
        ids = np.flatnonzero(geometry["contained"])
    assert len(ids) == 85112
    target_audit = audit_targets(lock, data_root, ids)
    d0_audit = audit_d0(d0_output / "percycle.csv")
    target_valid = all(
        field["epsilon_lower_count"] == 0
        and field["epsilon_upper_count"] == 0
        and field.get("epsilon_decrease_count", 0) == 0
        for case in target_audit
        for field in case["fields"].values()
    )
    result = {
        "status": "prerequisite_validated" if target_valid else "target_validity_failed",
        "experiment_id": "S04-E017",
        "scope": "read-only development prerequisite; no fit or training",
        "lock_sha256": LOCK_SHA256,
        "admitted_cells": int(len(ids)),
        "epsilon": EPSILON,
        "excluded_amplitudes_not_accessed": [0.1175, 0.125],
        "target_audit": target_audit,
        "d0_boundary_context": d0_audit,
        "decision": (
            "target state semantics support strict future D1 bounds/non-decrease audits; "
            "D0 area alone is insufficient because B0 signed tails and B1 magnitudes differ"
            if target_valid
            else "stop before D1 implementation"
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "experiment_id", "admitted_cells", "epsilon", "decision"
    )}, indent=2))
    if not target_valid:
        raise SystemExit(1)


def tests() -> None:
    assert weighted([1.0, 3.0], [1.0, 1.0]) == 2.0
    assert weighted([1.0, 3.0], [1.0, 3.0]) == 2.5
    assert resolve(Path("/tmp/a"), "b") == Path("/tmp/a/b")
    assert resolve(Path("/tmp/a"), "/tmp/c") == Path("/tmp/c")
    print("PASS prerequisite helper tests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--d0-output", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        tests()
    else:
        assert all((args.lock, args.data_root, args.d0_output, args.output))
        run(args.lock, args.data_root, args.d0_output, args.output)
