from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import deque
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis.toy_road_t3_mechanism_20260819.evidence import (
    load_json_strict,
    sha256_file,
)
from analysis.toy_road_t3_mechanism_20260819.mechanism import (
    ElementGeometry,
    Mesh,
    build_comparison_pairs,
    classify_memory,
    element_geometry,
    load_mesh,
    load_peak_fields,
    process_zone,
    reduce_field,
)


REQUESTED = [20, 30, 31, 40, 60, 61, 68, 70, 71, 73]
FIELDS = (
    "damage",
    "history",
    "fatigue_degradation_deficit",
    "ordinary_degradation_deficit",
    "raw_driver",
    "raw_cyclemax_driver",
    "active_driver",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path.name}")
    columns = list(rows[0])
    extras = sorted({key for row in rows for key in row} - set(columns))
    columns.extend(extras)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _field_arrays(peak: Any, mesh: Mesh) -> dict[str, np.ndarray]:
    damage = peak.d_node[mesh.connectivity].mean(axis=1)
    gp = {name: values.mean(axis=1) for name, values in peak.gp_fields.items()}
    return {
        "damage": damage,
        "history": gp["alpha_bar_gp"],
        "fatigue_degradation_deficit": 1.0 - gp["f_alpha_gp"],
        "ordinary_degradation_deficit": 1.0 - gp["g_gp"],
        "raw_driver": gp["psi_raw_gp"],
        "raw_cyclemax_driver": gp["psi_raw_cyclemax_gp"],
        "active_driver": gp["psi_active_gp"],
    }


def _node_graph(mesh: Mesh) -> list[set[int]]:
    graph = [set() for _ in range(len(mesh.node_coords))]
    for element in mesh.connectivity:
        for left, right in zip(element, np.roll(element, -1)):
            graph[int(left)].add(int(right))
            graph[int(right)].add(int(left))
    return graph


def _damaged_components(mask: np.ndarray, graph: list[set[int]]) -> list[list[int]]:
    pending = set(int(index) for index in np.flatnonzero(mask))
    components: list[list[int]] = []
    while pending:
        seed = pending.pop()
        component = [seed]
        queue = deque([seed])
        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if neighbor in pending:
                    pending.remove(neighbor)
                    component.append(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return components


def _crack_metrics(
    d_node: np.ndarray,
    mesh: Mesh,
    graph: list[set[int]],
    seed_nodes: set[int],
) -> dict[str, float | int | bool]:
    damaged = d_node >= 0.95
    components = _damaged_components(damaged, graph)
    seeded = [component for component in components if seed_nodes.intersection(component)]
    selected = max(seeded or components or [[]], key=len)
    tip_x = float(np.max(mesh.node_coords[selected, 0])) if selected else math.nan
    event_mask = damaged & (mesh.node_coords[:, 0] >= 0.48)
    event_components = _damaged_components(event_mask, graph)
    event_size = max((len(component) for component in event_components), default=0)
    return {
        "crack_tip_x": tip_x,
        "damaged_component_size": len(selected),
        "right_boundary_connected_size": event_size,
        "event_hit_reconstructed": event_size >= 3,
    }


def _trajectory(
    case_id: str,
    root: Path,
    terminal_cycle: int,
    mesh: Mesh,
    geometry: ElementGeometry,
) -> dict[str, Any]:
    graph = _node_graph(mesh)
    first_peak = load_peak_fields(root / "substeps" / "cycle_0001.mat", 1)
    seed_nodes = set(int(index) for index in np.flatnonzero(first_peak.d_node >= 0.95))
    invariant_names = (
        "mesh_sha256",
        "element_ordering_id",
        "gp_ordering_id",
        "runtime_lock_sha256",
        "family_contract_sha256",
    )
    expected = {name: first_peak.identities[name] for name in invariant_names}
    case_contract = first_peak.identities["case_physics_contract_sha256"]
    reductions: list[dict[str, Any]] = []
    process_rows: list[dict[str, Any]] = []
    snapshots: dict[int, dict[str, np.ndarray]] = {}
    input_files: list[dict[str, Any]] = []
    previous_damage = np.zeros(len(mesh.connectivity), dtype=float)
    for cycle in range(1, terminal_cycle + 1):
        shard_path = root / "substeps" / f"cycle_{cycle:04d}.mat"
        peak = load_peak_fields(shard_path, cycle, expected)
        if peak.identities["case_physics_contract_sha256"] != case_contract:
            raise ValueError(f"case contract changed within {case_id} at c{cycle}")
        arrays = _field_arrays(peak, mesh)
        for field_name, values in arrays.items():
            reductions.append(
                {
                    "case_id": case_id,
                    "cycle": cycle,
                    "peak_substep_ordinal": 4,
                    "load_factor": peak.load_factor,
                    "field": field_name,
                    **reduce_field(values, geometry.areas, geometry.centroids),
                }
            )
        zone = process_zone(arrays["damage"] - previous_damage, geometry)
        crack = _crack_metrics(peak.d_node, mesh, graph, seed_nodes)
        process_rows.append(
            {
                "case_id": case_id,
                "cycle": cycle,
                "load_factor": peak.load_factor,
                **zone,
                **crack,
            }
        )
        previous_damage = arrays["damage"]
        if cycle in REQUESTED or cycle == 67:
            snapshots[cycle] = {name: value.copy() for name, value in arrays.items()}
        input_files.append(
            {
                "case_id": case_id,
                "cycle": cycle,
                "path": f"substeps/cycle_{cycle:04d}.mat",
                "size": shard_path.stat().st_size,
                "sha256": sha256_file(shard_path),
            }
        )
    return {
        "reductions": reductions,
        "process": process_rows,
        "snapshots": snapshots,
        "input_files": input_files,
        "identities": {**expected, "case_physics_contract_sha256": case_contract},
    }


def _reduction_index(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, Any]]:
    return {(row["case_id"], int(row["cycle"]), row["field"]): row for row in rows}


def _difference_row(
    label: str,
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    metrics = (
        "area_weighted_mean",
        "area_weighted_integral",
        "support_area_abs_1e15",
        "support_area_rel_1pct",
        "weighted_centroid_x",
        "weighted_centroid_y",
        "weighted_rms_width_x",
        "weighted_rms_width_y",
    )
    result: dict[str, Any] = {"comparison": label, "field": left["field"]}
    for metric in metrics:
        result[f"left_{metric}"] = left[metric]
        result[f"right_{metric}"] = right[metric]
        result[f"right_minus_left_{metric}"] = right[metric] - left[metric]
    return result


def _grid(values: np.ndarray, geometry: ElementGeometry, bins: int = 80) -> np.ndarray:
    x = geometry.centroids[:, 0]
    y = geometry.centroids[:, 1]
    sums, _, _ = np.histogram2d(x, y, bins=bins, weights=values)
    counts, _, _ = np.histogram2d(x, y, bins=bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (sums / counts).T


def _save_trajectory_figures(
    destination: Path,
    all_reductions: list[dict[str, Any]],
    process_rows: list[dict[str, Any]],
    p0_snapshots: dict[int, dict[str, np.ndarray]],
    t3_snapshots: dict[int, dict[str, np.ndarray]],
    geometry: ElementGeometry,
) -> list[str]:
    figure_files: list[str] = []
    cases = ("P0_parent", "T3_loading_history")
    colors = {"P0_parent": "#1f77b4", "T3_loading_history": "#d62728"}
    index = _reduction_index(all_reductions)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for case in cases:
        cycles = sorted({row["cycle"] for row in all_reductions if row["case_id"] == case})
        loads = [index[(case, cycle, "damage")]["load_factor"] for cycle in cycles]
        ax.plot(cycles, loads, label=case, color=colors[case])
    for cycle, label in ((68, "T3 first"), (71, "T3 confirmed"), (70, "P0 first"), (73, "P0 confirmed")):
        ax.axvline(cycle, color="0.5", linewidth=0.7, linestyle="--")
        ax.text(cycle, ax.get_ylim()[1], label, rotation=90, va="top", fontsize=7)
    ax.set(xlabel="cycle", ylabel="peak load factor", title="Loading amplitude and sealed events")
    ax.legend()
    fig.tight_layout()
    name = "01_loading_and_events.png"
    fig.savefig(destination / name, dpi=150)
    plt.close(fig)
    figure_files.append(name)

    fig, axes = plt.subplots(4, 2, figsize=(12, 12), sharex=True)
    for ax, field in zip(axes.ravel(), FIELDS):
        for case in cases:
            rows = [row for row in all_reductions if row["case_id"] == case and row["field"] == field]
            ax.plot([row["cycle"] for row in rows], [row["area_weighted_mean"] for row in rows], label=case, color=colors[case])
        ax.set_title(field)
    axes.ravel()[-1].axis("off")
    axes[0, 0].legend()
    fig.suptitle("Area-weighted field trajectories")
    fig.tight_layout()
    name = "02_field_trajectories.png"
    fig.savefig(destination / name, dpi=150)
    plt.close(fig)
    figure_files.append(name)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for case in cases:
        history = [row for row in all_reductions if row["case_id"] == case and row["field"] == "history"]
        active = [row for row in all_reductions if row["case_id"] == case and row["field"] == "active_driver"]
        axes[0].plot([row["cycle"] for row in history], [row["support_area_abs_1e15"] for row in history], label=case, color=colors[case])
        axes[1].plot([row["cycle"] for row in active], [row["support_area_rel_1pct"] for row in active], label=case, color=colors[case])
    axes[0].set_title("History support area (>0)")
    axes[1].set_title("Active-driver support area (1% max)")
    for ax in axes:
        ax.set_xlabel("cycle")
        ax.legend()
    fig.tight_layout()
    name = "03_support_area_trajectories.png"
    fig.savefig(destination / name, dpi=150)
    plt.close(fig)
    figure_files.append(name)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    for case in cases:
        rows = [row for row in process_rows if row["case_id"] == case]
        cycles = [row["cycle"] for row in rows]
        for ax, metric in zip(axes.ravel(), ("crack_tip_x", "centroid_x", "support_area", "rms_width_x")):
            ax.plot(cycles, [row[metric] for row in rows], label=case, color=colors[case])
            ax.set_title(metric)
    axes[0, 0].legend()
    fig.suptitle("Crack-tip and incremental process-zone trajectories")
    fig.tight_layout()
    name = "04_crack_process_zone.png"
    fig.savefig(destination / name, dpi=150)
    plt.close(fig)
    figure_files.append(name)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, (start, end) in zip(axes, ((30, 31), (60, 61))):
        for case in cases:
            values = [index[(case, cycle, "history")]["area_weighted_mean"] for cycle in (start, end)]
            ax.plot((start, end), values, marker="o", label=case, color=colors[case])
        ax.set_title(f"Block transition c{start}→c{end}")
        ax.set_xlabel("cycle")
    axes[0].legend()
    fig.tight_layout()
    name = "05_block_transitions.png"
    fig.savefig(destination / name, dpi=150)
    plt.close(fig)
    figure_files.append(name)

    same_cycles = build_comparison_pairs()["same_cycle"]
    for field in FIELDS:
        values = [p0_snapshots[cycle][field] for cycle in same_cycles] + [t3_snapshots[cycle][field] for cycle in same_cycles]
        vmin = min(float(np.nanmin(value)) for value in values)
        vmax = max(float(np.nanmax(value)) for value in values)
        fig, axes = plt.subplots(2, len(same_cycles), figsize=(2.2 * len(same_cycles), 5))
        for column, cycle in enumerate(same_cycles):
            for row, (case, snapshots) in enumerate((("P0", p0_snapshots), ("T3", t3_snapshots))):
                axes[row, column].imshow(_grid(snapshots[cycle][field], geometry), origin="lower", vmin=vmin, vmax=vmax, aspect="auto")
                axes[row, column].set_title(f"{case} c{cycle}", fontsize=8)
                axes[row, column].axis("off")
        fig.suptitle(f"Same-cycle maps: {field}; common limits [{vmin:.3e}, {vmax:.3e}]")
        fig.tight_layout()
        name = f"06_same_cycle_maps_{field}.png"
        fig.savefig(destination / name, dpi=120)
        plt.close(fig)
        figure_files.append(name)

    event_pairs = (("first_hit", 70, 68), ("confirmed", 73, 71))
    for field in FIELDS:
        values = [p0_snapshots[p0_cycle][field] for _, p0_cycle, _ in event_pairs] + [t3_snapshots[t3_cycle][field] for _, _, t3_cycle in event_pairs]
        vmin = min(float(np.nanmin(value)) for value in values)
        vmax = max(float(np.nanmax(value)) for value in values)
        fig, axes = plt.subplots(2, 2, figsize=(8, 7))
        for column, (label, p0_cycle, t3_cycle) in enumerate(event_pairs):
            axes[0, column].imshow(_grid(p0_snapshots[p0_cycle][field], geometry), origin="lower", vmin=vmin, vmax=vmax)
            axes[1, column].imshow(_grid(t3_snapshots[t3_cycle][field], geometry), origin="lower", vmin=vmin, vmax=vmax)
            axes[0, column].set_title(f"P0 c{p0_cycle} {label}")
            axes[1, column].set_title(f"T3 c{t3_cycle} {label}")
            axes[0, column].axis("off")
            axes[1, column].axis("off")
        fig.suptitle(f"Own-event maps: {field}; T3 c73 unavailable")
        fig.tight_layout()
        name = f"07_own_event_maps_{field}.png"
        fig.savefig(destination / name, dpi=140)
        plt.close(fig)
        figure_files.append(name)
    return figure_files


def run_analysis(p0_root: Path, t3_root: Path, destination: Path) -> dict[str, Any]:
    p0_root, t3_root, destination = Path(p0_root), Path(t3_root), Path(destination)
    if destination.exists():
        raise FileExistsError(f"results destination exists: {destination}")
    p0_terminal = load_json_strict(p0_root / "TERMINAL_RESULT.json")
    t3_terminal = load_json_strict(t3_root / "TERMINAL_RESULT.json")
    if (p0_terminal.get("first_hit_cycle"), p0_terminal.get("confirmed_cycle")) != (70, 73):
        raise ValueError("P0 sealed event mismatch")
    if (t3_terminal.get("first_hit_cycle"), t3_terminal.get("confirmed_cycle")) != (68, 71):
        raise ValueError("T3 sealed event mismatch")
    p0_mesh = load_mesh(p0_root / "mesh_geometry.mat")
    t3_mesh = load_mesh(t3_root / "mesh_geometry.mat")
    if p0_mesh.identities != t3_mesh.identities:
        raise ValueError("P0/T3 mesh or ordering identity mismatch")
    if not np.array_equal(p0_mesh.node_coords, t3_mesh.node_coords) or not np.array_equal(p0_mesh.connectivity, t3_mesh.connectivity):
        raise ValueError("P0/T3 numerical mesh mismatch")
    geometry = element_geometry(p0_mesh)

    p0 = _trajectory("P0_parent", p0_root, 73, p0_mesh, geometry)
    t3 = _trajectory("T3_loading_history", t3_root, 71, t3_mesh, geometry)
    for identity in ("mesh_sha256", "element_ordering_id", "gp_ordering_id", "runtime_lock_sha256", "family_contract_sha256"):
        if p0["identities"][identity] != t3["identities"][identity]:
            raise ValueError(f"P0/T3 identity mismatch: {identity}")

    destination.mkdir(parents=True, exist_ok=False)
    reductions = p0["reductions"] + t3["reductions"]
    process_rows = p0["process"] + t3["process"]
    index = _reduction_index(reductions)
    pairs = build_comparison_pairs()

    same_rows: list[dict[str, Any]] = []
    for cycle in pairs["same_cycle"]:
        for field in FIELDS:
            row = _difference_row(
                f"same_cycle_c{cycle}",
                index[("P0_parent", cycle, field)],
                index[("T3_loading_history", cycle, field)],
            )
            row.update({"p0_cycle": cycle, "t3_cycle": cycle})
            same_rows.append(row)

    own_rows: list[dict[str, Any]] = []
    for label, p0_cycle, t3_cycle in pairs["own_event"]:
        for field in FIELDS:
            row = _difference_row(
                label,
                index[("P0_parent", p0_cycle, field)],
                index[("T3_loading_history", t3_cycle, field)],
            )
            row.update({"p0_cycle": p0_cycle, "t3_cycle": t3_cycle})
            own_rows.append(row)

    transition_rows: list[dict[str, Any]] = []
    for start, end in pairs["transitions"]:
        for case in ("P0_parent", "T3_loading_history"):
            for field in FIELDS:
                row = _difference_row(
                    f"{case}_c{start}_to_c{end}",
                    index[(case, start, field)],
                    index[(case, end, field)],
                )
                row.update({"case_id": case, "start_cycle": start, "end_cycle": end})
                transition_rows.append(row)

    alpha_c60 = t3["snapshots"][60]["history"] - p0["snapshots"][60]["history"]
    alpha_c61 = t3["snapshots"][61]["history"] - p0["snapshots"][61]["history"]
    alpha_c68 = t3["snapshots"][68]["history"] - p0["snapshots"][68]["history"]
    delta_t3_c68 = np.maximum(
        t3["snapshots"][68]["damage"] - t3["snapshots"].get(67, t3["snapshots"][68])["damage"],
        0.0,
    )
    difference_floor = max(1e-14, 0.01 * float(np.max(np.abs(alpha_c68), initial=0.0)))
    zone_floor = max(1e-8, 0.01 * float(delta_t3_c68.max(initial=0.0)))
    overlap = (np.abs(alpha_c68) >= difference_floor) & (delta_t3_c68 >= zone_floor)
    memory_evidence = {
        "departure": bool(np.max(np.abs(alpha_c60), initial=0.0) > 1e-14),
        "persistence": bool(np.max(np.abs(alpha_c61), initial=0.0) > 1e-14 and np.max(np.abs(alpha_c68), initial=0.0) > 1e-14),
        "spatial_colocation": bool(np.any(overlap)),
    }
    memory_status = classify_memory(memory_evidence)

    _write_csv(destination / "cycle_field_reductions.csv", reductions)
    _write_csv(destination / "same_cycle_differences.csv", same_rows)
    _write_csv(destination / "own_event_differences.csv", own_rows)
    _write_csv(destination / "block_transition_differences.csv", transition_rows)
    _write_csv(destination / "process_zone_trajectory.csv", process_rows)

    summary = {
        "schema_version": "toy_road_p0_t3_mechanism_summary_v1",
        "status": "PASS_OFFLINE_ANALYSIS",
        "p0_first_hit": 70,
        "p0_confirmed": 73,
        "t3_first_hit": 68,
        "t3_confirmed": 71,
        "delta_n_first": -2,
        "delta_n_confirmed": -2,
        "t3_c73_status": "UNAVAILABLE",
        "memory_classification": memory_status,
        "memory_evidence": memory_evidence,
        "mechanism_claim_boundary": "Observed field persistence is not proof that the constitutive mechanism is correct.",
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    (destination / "mechanism_summary.json").write_bytes(_canonical_bytes(summary) + b"\n")

    figures = _save_trajectory_figures(
        destination,
        reductions,
        process_rows,
        p0["snapshots"],
        t3["snapshots"],
        geometry,
    )
    figure_metadata = {
        "schema_version": "toy_road_p0_t3_figure_metadata_v1",
        "common_color_limits": True,
        "t3_c73_status": "UNAVAILABLE",
        "figure_files": figures,
    }
    (destination / "FIGURE_METADATA.json").write_bytes(_canonical_bytes(figure_metadata) + b"\n")

    report = f"""# P0–T3 mechanism comparison

## Evidence qualification

This is a read-only offline analysis of the sealed P0 and numerically qualified T3 packages. No FEM trajectory was started, resumed, or modified.

## Sealed event result

P0 first hit/confirmation are c70/c73. T3 first hit/confirmation are c68/c71. Therefore **ΔN_first=-2** and **ΔN_confirmed=-2**. The synchronous shift is a qualified trajectory observation; event timing alone cannot establish that a physical mechanism is correct.

## Loading-block transitions

The compact tables and figures compare T3 c30→c31 and c60→c61 against the same P0 constant-loading transitions.

## History/degradation persistence

Predeclared classification: **{memory_status}**. Evidence flags: departure={str(memory_evidence['departure']).lower()}, persistence={str(memory_evidence['persistence']).lower()}, spatial_colocation={str(memory_evidence['spatial_colocation']).lower()}.

## Process-zone and crack-tip response

Incremental damage support uses `max(1e-8, 0.01*max(Δd))`. Centroid, area, and RMS widths are Δd×element-area weighted. Crack-tip values use the connected d≥0.95 damaged-node component seeded by c1 damage.

## Same-cycle versus own-event comparison

Same-cycle nodes are c20, c30, c31, c40, c60, c61, c68, c70, and c71. Own-event pairs are P0 c70/T3 c68 and P0 c73/T3 c71. T3 c73 is unavailable and is never extrapolated.

## Mechanism boundary and next discriminator

The analysis can support persistent stored-field memory and spatial co-location, but not constitutive correctness. A dose-matched reversed-order T3 sibling remains the direct future discriminator and requires separate authorization.
"""
    (destination / "P0_T3_MECHANISM_REPORT.md").write_text(report, encoding="utf-8", newline="\n")

    inventory = {
        "schema_version": "toy_road_p0_t3_analysis_input_inventory_v1",
        "p0_terminal_result_sha256": sha256_file(p0_root / "TERMINAL_RESULT.json"),
        "t3_terminal_result_sha256": sha256_file(t3_root / "TERMINAL_RESULT.json"),
        "p0_mesh_sha256": sha256_file(p0_root / "mesh_geometry.mat"),
        "t3_mesh_sha256": sha256_file(t3_root / "mesh_geometry.mat"),
        "files": p0["input_files"] + t3["input_files"],
    }
    (destination / "ANALYSIS_INPUT_INVENTORY.json").write_bytes(_canonical_bytes(inventory) + b"\n")
    output_files = [path for path in destination.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt"]
    (destination / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in sorted(output_files, key=lambda item: item.name)),
        encoding="ascii",
        newline="\n",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the sealed offline P0–T3 mechanism comparison.")
    parser.add_argument("--p0-root", type=Path, required=True)
    parser.add_argument("--t3-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = run_analysis(args.p0_root, args.t3_root, args.destination)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
