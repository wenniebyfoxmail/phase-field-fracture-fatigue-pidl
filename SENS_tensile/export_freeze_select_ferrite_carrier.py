from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from pathlib import Path

import numpy as np
import pandas as pd


STATE_SEQUENCE = ["state0"] + [f"c{cycle}_{phase}" for cycle in range(1, 6) for phase in ("peak", "unload")]
TRUE_BETA = {
    "damage_hplus_log_traffic": 0.08,
    "damage_hplus_low_temp": 0.005,
    "damage_hplus_moisture": 0.06,
}
CANDIDATE_TERMS = (
    "damage_hplus_log_traffic",
    "damage_hplus_traffic_rate",
    "damage_hplus_low_temp",
    "damage_hplus_abs_temp_delta",
    "damage_hplus_moisture",
    "damage_hplus_rain_7d",
    "damage_hplus_moisture_log_traffic",
    "damage_hplus_low_temp_log_traffic",
    "damage_hplus_moisture_low_temp",
    "damage_hplus_freeze_thaw",
)
TRAFFIC_LOG_REFERENCE = float(np.log1p(500.0))
CARRIER_TIMES = np.asarray([0.0, 4.0, 5.0, 9.0, 10.0, 14.0, 15.0, 19.0, 20.0, 24.0, 25.0])
CARRIER_TRAFFIC_LOG_REFERENCE = float(
    np.mean([np.log1p(rate * time) for rate in (0.8, 1.0) for time in CARRIER_TIMES])
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_mesh(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nodes: dict[int, tuple[float, float]] = {}
    elements: dict[int, tuple[int, int, int, int]] = {}
    mode = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("*"):
            upper = line.upper()
            mode = "node" if upper.startswith("*NODE") else "element" if upper.startswith("*ELEMENT") else None
            continue
        values = [value.strip() for value in line.split(",")]
        if mode == "node":
            nodes[int(values[0])] = (float(values[1]), float(values[2]))
        elif mode == "element":
            elements[int(values[0])] = tuple(int(value) for value in values[1:5])
    element_ids = np.asarray(sorted(elements), dtype=int)
    connectivity = np.asarray([elements[index] for index in element_ids], dtype=int)
    max_node = max(nodes)
    coordinates = np.full((max_node + 1, 2), np.nan, dtype=float)
    for node_id, coordinate in nodes.items():
        coordinates[node_id] = coordinate
    polygons = coordinates[connectivity]
    x = polygons[:, :, 0]
    y = polygons[:, :, 1]
    area = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    if not np.isfinite(polygons).all() or np.any(area <= 0.0):
        raise ValueError(f"Invalid mesh geometry in {path}")
    return element_ids, connectivity, coordinates


def aggregation_map(connectivity: np.ndarray, coordinates: np.ndarray, stride: int) -> dict[str, np.ndarray]:
    polygons = coordinates[connectivity]
    centroids = polygons.mean(axis=1)
    x_unique = np.unique(np.round(centroids[:, 0], 12))
    y_unique = np.unique(np.round(centroids[:, 1], 12))
    hx = float(np.min(np.diff(x_unique)))
    hy = float(np.min(np.diff(y_unique)))
    bx = np.floor((centroids[:, 0] - x_unique.min()) / (stride * hx) + 1e-9).astype(int)
    by = np.floor((centroids[:, 1] - y_unique.min()) / (stride * hy) + 1e-9).astype(int)
    _, inverse = np.unique(np.column_stack([by, bx]), axis=0, return_inverse=True)
    x = polygons[:, :, 0]
    y = polygons[:, :, 1]
    area = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    group_area = np.bincount(inverse, weights=area)
    return {
        "inverse": inverse,
        "area": area,
        "group_area": group_area,
        "x": np.bincount(inverse, weights=centroids[:, 0] * area) / group_area,
        "y": np.bincount(inverse, weights=centroids[:, 1] * area) / group_area,
    }


def aggregate(values: np.ndarray, mapping: dict[str, np.ndarray]) -> np.ndarray:
    return np.bincount(
        mapping["inverse"], weights=np.asarray(values, dtype=float) * mapping["area"]
    ) / mapping["group_area"]


def node_to_cell(nodes: pd.DataFrame, connectivity: np.ndarray, column: str) -> np.ndarray:
    size = int(max(int(nodes["node_id"].max()), int(connectivity.max()))) + 1
    values = np.full(size, np.nan, dtype=float)
    values[nodes["node_id"].to_numpy(int)] = nodes[column].to_numpy(float)
    result = values[connectivity].mean(axis=1)
    if not np.isfinite(result).all():
        raise ValueError(f"Non-finite {column} after node-to-cell projection")
    return result


def state_time(name: str) -> tuple[int, int, float]:
    if name == "state0":
        return 0, 0, 0.0
    match = re.fullmatch(r"c([1-5])_(peak|unload)", name)
    if not match:
        raise ValueError(name)
    cycle = int(match.group(1))
    substep = 4 if match.group(2) == "peak" else 5
    time = float((cycle - 1) * 5 + substep)
    return cycle, substep, time


def injected_residual(frame: pd.DataFrame) -> np.ndarray:
    hplus = np.maximum(frame["psi_plus"].to_numpy(float), 0.0)
    log_traffic = np.log1p(frame["traffic_esal_cum"].to_numpy(float))
    low_temp = np.maximum(20.0 - frame["temperature"].to_numpy(float), 0.0)
    moisture = frame["moisture"].to_numpy(float)
    damage_weight = 1.0 - frame["d"].to_numpy(float)
    reference = (
        frame["traffic_log_reference"].to_numpy(float)
        if "traffic_log_reference" in frame
        else TRAFFIC_LOG_REFERENCE
    )
    return (
        damage_weight * TRUE_BETA["damage_hplus_log_traffic"] * hplus * log_traffic
        + damage_weight * TRUE_BETA["damage_hplus_low_temp"] * hplus * low_temp
        + damage_weight * TRUE_BETA["damage_hplus_moisture"] * hplus * moisture
    )


def load_sections(corpus_decision: Path) -> dict[str, list[dict[str, object]]]:
    corpus = json.loads(corpus_decision.read_text())
    if corpus.get("passed") is not True:
        raise ValueError("The 24-cell corpus decision is not passed")
    sections: dict[str, list[dict[str, object]]] = {}
    for section, record in corpus["sections"].items():
        evidence = json.loads(Path(record["evidence_path"]).read_text())
        sections[section] = evidence.get("cells", evidence.get("results", []))
    return sections


def resolve_run_root(section: str, result: dict[str, object], corpus_decision: Path) -> Path:
    if result.get("evidence_root"):
        return Path(str(result["evidence_root"]))
    return corpus_decision.parent / "runs" / str(result["cell_id"])


def export_trajectory(
    section: str,
    result: dict[str, object],
    corpus_decision: Path,
    stride: int,
) -> tuple[pd.DataFrame, dict[str, str]]:
    run_root = resolve_run_root(section, result, corpus_decision)
    run_manifest = json.loads((run_root / "run_manifest.json").read_text())
    factors = result["factors"]
    load_level = int(factors["load_level"])
    temperature_level = int(factors["stiffness_proxy_level"])
    moisture_level = int(factors["toughness_proxy_level"])
    trajectory_id = f"{section}_L{load_level}_T{temperature_level}_M{moisture_level}"
    mesh_path = run_root / "hard5_native_q4.inp"
    element_ids, connectivity, coordinates = read_mesh(mesh_path)
    mapping = aggregation_map(connectivity, coordinates, stride)
    n_groups = len(mapping["group_area"])
    previous_alpha = np.zeros(n_groups, dtype=float)
    rows: list[pd.DataFrame] = []
    for snapshot_index, state in enumerate(STATE_SEQUENCE):
        state_root = run_root / state
        nodes = pd.read_csv(state_root / "nodes.csv").sort_values("node_id")
        cells = pd.read_csv(state_root / "cells.csv").sort_values("cell_id")
        if not np.array_equal(cells["cell_id"].to_numpy(int), element_ids):
            raise ValueError(f"Cell identity mismatch in {state_root}")
        damage = aggregate(node_to_cell(nodes, connectivity, "damage"), mapping)
        u = aggregate(node_to_cell(nodes, connectivity, "ux"), mapping)
        v = aggregate(node_to_cell(nodes, connectivity, "uy"), mapping)
        alpha = aggregate(cells["alpha_bar"].to_numpy(float), mapping)
        nominal_increment = np.maximum(alpha - previous_alpha, 0.0)
        previous_alpha = alpha
        cycle, substep, time = state_time(state)
        traffic_rate = 0.8 if load_level == 0 else 1.0
        temperature = 0.0 if temperature_level == 0 else 20.0
        moisture = float(moisture_level)
        frame = pd.DataFrame(
            {
                "trajectory_id": trajectory_id,
                "source_kind": "qualified_ferrite_semisynthetic_correction",
                "physics_family": "ferrite_at1_history_fatigue_revised_v1",
                "protocol_id": "hard5_r0_5cycle_11state_semisynthetic_v1",
                "snapshot_id": f"{trajectory_id}::{state}",
                "time": time,
                "cycle": cycle,
                "substep": substep,
                "cell_id": [f"{section}_g{index:04d}" for index in range(n_groups)],
                "x": mapping["x"],
                "y": mapping["y"],
                "cell_area": mapping["group_area"],
                "d": damage,
                "u": u,
                "v": v,
                "psi_plus": aggregate(cells["psi_raw"].to_numpy(float), mapping),
                "psi_active": aggregate(cells["active_driver"].to_numpy(float), mapping),
                "alpha_bar": alpha,
                "f_alpha": aggregate(cells["fatigue_f"].to_numpy(float), mapping),
                "g_stiffness": np.square(1.0 - damage),
                "ell": 0.01,
                "Gc_base": float(run_manifest.get("Gc", 0.008 if moisture_level else 0.01)),
                "traffic_esal_cum": traffic_rate * time,
                "traffic_esal_rate": traffic_rate,
                "traffic_log_reference": CARRIER_TRAFFIC_LOG_REFERENCE,
                "temperature": temperature,
                "temp_delta": 0.0,
                "temp_gradient": 0.0,
                "moisture": moisture,
                "rain_7d": 0.0,
                "freeze_thaw_count": 0.0,
                "field_uncertainty": 0.0,
                "missingness_flags": "{}",
                "actual_fatigue_increment": nominal_increment,
                "nominal_fixed_physics_increment": nominal_increment,
                "load_spectrum_id": "load_low" if load_level == 0 else "load_high",
                "temperature_level": "temperature_cold" if temperature_level == 0 else "temperature_warm",
                "moisture_level": "moisture_dry" if moisture_level == 0 else "moisture_wet",
                "geometry_id": section,
                "precrack_id": f"{section}_independent_precrack",
                "increment_state_timing": "previous_saved_state_to_current_saved_state",
                "known_rate": nominal_increment / max(time - state_time(STATE_SEQUENCE[max(0, snapshot_index - 1)])[2], 1.0),
            }
        )
        correction = injected_residual(frame)
        frame["actual_fatigue_increment"] = nominal_increment + correction
        frame["known_residual"] = correction
        rows.append(frame)
    source_hashes = {
        "run_manifest": sha256(run_root / "run_manifest.json"),
        "convergence": sha256(run_root / "convergence.csv"),
        "mesh": sha256(mesh_path),
        "solver": sha256(run_root / "pfm_independent_mesh_5cycle_v2.jl"),
    }
    return pd.concat(rows, ignore_index=True), source_hashes


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a qualified Ferrite carrier with sealed semi-synthetic correction support")
    parser.add_argument("--corpus-decision", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=4)
    args = parser.parse_args()
    if args.stride < 1:
        raise ValueError("stride must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sections = load_sections(args.corpus_decision)
    section_packages: dict[str, dict[str, object]] = {}
    for section, results in sections.items():
        frames: list[pd.DataFrame] = []
        hashes: dict[str, dict[str, str]] = {}
        for result in sorted(results, key=lambda item: str(item["cell_id"])):
            frame, source_hashes = export_trajectory(section, result, args.corpus_decision, args.stride)
            frames.append(frame)
            hashes[str(frame["trajectory_id"].iloc[0])] = source_hashes
        combined = pd.concat(frames, ignore_index=True)
        snapshot_path = args.output_dir / f"{section}_frozen_carrier.csv"
        combined.to_csv(snapshot_path, index=False)
        ids = sorted(combined["trajectory_id"].unique())
        manifest = {
            "snapshot_sha256": sha256(snapshot_path),
            "known_residual_sign": "actual_minus_nominal",
            "code_commit": "uncommitted_mac_snapshot_20260804",
            "dirty_status": "dirty",
            "producer_machine": platform.node(),
            "runtime": f"Python {platform.python_version()}, pandas {pd.__version__}, numpy {np.__version__}",
            "source_hashes": {
                "corpus_decision": sha256(args.corpus_decision),
                "exporter": sha256(Path(__file__)),
                "trajectories": hashes,
            },
            "temperature_parameter_mapping": {
                "temperature_cold": {"parameter": "E_proxy", "value": 1.0, "calibrated_road_temperature": False},
                "temperature_warm": {"parameter": "E_proxy", "value": 0.9, "calibrated_road_temperature": False},
            },
            "moisture_parameter_mapping": {
                "moisture_dry": {"parameter": "Gc_proxy", "value": 0.01, "calibrated_road_moisture": False},
                "moisture_wet": {"parameter": "Gc_proxy", "value": 0.008, "calibrated_road_moisture": False},
            },
            "load_spectrum_semantics": {
                "load_low": {"is_physical": True, "description": "Normalized five-cycle displacement spectrum with Umax=0.08; not calibrated ESAL."},
                "load_high": {"is_physical": True, "description": "Normalized five-cycle displacement spectrum with Umax=0.10; not calibrated ESAL."},
            },
            "right_censored_trajectories": ids,
            "splits": {"train": ids[:5], "validation": [ids[5]], "holdout": ids[6:]},
            "factorial_design": {
                "load_spectrum_ids": ["load_low", "load_high"],
                "temperature_levels": ["temperature_cold", "temperature_warm"],
                "moisture_levels": ["moisture_dry", "moisture_wet"],
            },
            "claim_class": "tooling-only_semisynthetic_ferrite_carrier",
            "field_feedback_of_injected_correction": False,
            "injected_support": list(TRUE_BETA),
            "injected_beta": TRUE_BETA,
            "aggregation_stride": args.stride,
            "aggregation_policy": "area-conservative regular supercells",
            "traffic_log_reference": CARRIER_TRAFFIC_LOG_REFERENCE,
            "traffic_log_reference_policy": "mean log1p(cumulative normalized load) over the locked two spectra and eleven saved times",
        }
        manifest_path = args.output_dir / f"{section}_FROZEN_EXPORT_MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        section_packages[section] = {
            "snapshot": str(snapshot_path),
            "snapshot_sha256": manifest["snapshot_sha256"],
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
            "trajectory_ids": ids,
            "row_count": len(combined),
        }
    ordered_sections = list(section_packages)
    folds = []
    for holdout_index, holdout in enumerate(ordered_sections):
        validation = ordered_sections[(holdout_index + 1) % len(ordered_sections)]
        train = [section for section in ordered_sections if section not in {holdout, validation}]
        folds.append({"fold": holdout_index, "train_geometry_ids": train, "validation_geometry_id": validation, "holdout_geometry_id": holdout})
    truth_path = args.output_dir / "SEALED_TRUTH.json"
    truth_path.write_text(json.dumps({"term_names": list(CANDIDATE_TERMS), "declared_support": list(TRUE_BETA), "beta": TRUE_BETA}, indent=2) + "\n")
    handoff = {
        "claim_class": "tooling-only_semisynthetic_ferrite_carrier",
        "corpus_decision": str(args.corpus_decision),
        "corpus_decision_sha256": sha256(args.corpus_decision),
        "section_packages": section_packages,
        "geometry_folds": folds,
        "sealed_truth": str(truth_path),
        "sealed_truth_sha256": sha256(truth_path),
        "field_feedback_of_injected_correction": False,
        "authorizations": {
            "support_stability_comparison": True,
            "crack_geometry_improvement_claim": False,
            "road_mechanism_claim": False,
        },
    }
    (args.output_dir / "HANDOFF_MANIFEST.json").write_text(json.dumps(handoff, indent=2) + "\n")
    print(json.dumps({"output_dir": str(args.output_dir), "sections": section_packages, "folds": folds}, indent=2))


if __name__ == "__main__":
    main()
