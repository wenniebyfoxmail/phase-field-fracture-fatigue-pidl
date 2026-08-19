"""Locked schedules and validation helpers for the cadence c3 tooling smoke."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import gmshparser
import numpy as np


SCHEDULES = {
    "S4": (0.5, 1.0, 0.5, 0.0),
    "S8": (0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0),
    "S16": (
        0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0,
        0.875, 0.75, 0.625, 0.5, 0.375, 0.25, 0.125, 0.0,
    ),
}
REQUIRED_FIELDS = {
    "alpha_elem", "hist_alpha_elem", "hist_fat_elem", "f_fatigue_elem",
    "psi_raw_elem", "psi_active_elem", "psi_history_driver_elem",
    "psi_solver_active_elem",
    "g_alpha_elem", "g_history_driver_elem", "E_el_elem", "E_d_elem", "E_hist_elem",
    "eps_xx_elem", "eps_yy_elem", "eps_xy_elem",
    "sigma_raw_xx_elem", "sigma_raw_yy_elem", "sigma_raw_xy_elem",
    "sigma_effective_xx_elem", "sigma_effective_yy_elem",
    "sigma_effective_xy_elem", "area_elem", "elem_x", "elem_y",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_nested_schedules() -> None:
    for coarse, fine in (("S4", "S8"), ("S8", "S16")):
        coarse_path = SCHEDULES[coarse]
        fine_path = SCHEDULES[fine]
        fine_nodes = Counter(fine_path)
        for node, count in Counter(SCHEDULES[coarse]).items():
            if fine_nodes[node] < count:
                raise ValueError(f"{coarse} is not a retained-state subset of {fine}")
        h_coarse = max(abs(a - b) for a, b in zip((0.0,) + SCHEDULES[coarse], SCHEDULES[coarse]))
        h_fine = max(abs(a - b) for a, b in zip((0.0,) + SCHEDULES[fine], SCHEDULES[fine]))
        if not np.isclose(h_fine, h_coarse / 2.0):
            raise ValueError(f"{coarse}->{fine} does not halve h")
        cursor = iter(fine_path)
        if not all(any(np.isclose(value, candidate) for candidate in cursor) for value in coarse_path):
            raise ValueError(f"{coarse} is not an ordered subsequence of {fine}")
    for level, values in SCHEDULES.items():
        peak = int(np.argmax(values))
        if values.count(max(values)) != 1 or values[-1] != 0.0:
            raise ValueError(f"{level} must have one peak and end unloaded")
        if not all(a < b for a, b in zip((0.0,) + values[:peak], values[:peak + 1])):
            raise ValueError(f"{level} loading branch is not strictly increasing")
        if not all(a > b for a, b in zip(values[peak:], values[peak + 1:])):
            raise ValueError(f"{level} unloading branch is not strictly decreasing")


def state_rows(level: str, n_cycles: int = 3) -> list[dict[str, object]]:
    schedule = SCHEDULES[level]
    rows: list[dict[str, object]] = [{
        "raw_step": 0, "physical_cycle": 0, "substep": -1,
        "normalized_displacement": 0.0, "prescribed_displacement": 0.0,
        "branch": "recovery",
        "state_label": "state0_recovery_post_commit",
        "field_timing": "alpha/raw/active=pre_history_refresh;history/degradation=post_commit",
        "energy_timing": "post_commit_recomputed_from_converged_fields_not_optimization_objective",
    }]
    peak = int(np.argmax(schedule))
    for cycle in range(1, n_cycles + 1):
        for substep, value in enumerate(schedule):
            raw = 1 + (cycle - 1) * len(schedule) + substep
            branch = "loading" if substep <= peak else "unloading"
            stage = "peak" if substep == peak else ("unloaded" if substep == len(schedule) - 1 else f"{branch}_{value:g}")
            rows.append({
                "raw_step": raw, "physical_cycle": cycle, "substep": substep,
                "normalized_displacement": value,
                "prescribed_displacement": 0.12 * value, "branch": branch,
                "state_label": f"c{cycle}_{stage}",
                "field_timing": "alpha/raw/active=pre_history_refresh;history/degradation=post_commit",
                "energy_timing": "post_commit_recomputed_from_converged_fields_not_optimization_objective",
            })
    return rows


def write_state_index(path: Path, level: str, n_cycles: int = 3) -> None:
    rows = state_rows(level, n_cycles)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mesh_triangles(path: Path) -> tuple[np.ndarray, np.ndarray]:
    mesh = gmshparser.parse(str(path))
    x, y, triangles = gmshparser.helpers.get_triangles(mesh)
    return np.column_stack((np.asarray(x, dtype=float), np.asarray(y, dtype=float))), np.asarray(triangles, dtype=np.int64)


def semantic_torch_hash(path: Path) -> str:
    """Hash decoded tensor/scalar content independently of torch zip metadata."""
    import torch

    digest = hashlib.sha256()
    payload = torch.load(path, map_location="cpu", weights_only=False)

    def update(value: object, label: str) -> None:
        digest.update(label.encode("utf-8"))
        if isinstance(value, torch.Tensor):
            tensor = value.detach().cpu().contiguous()
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(str(tuple(tensor.shape)).encode("ascii"))
            digest.update(tensor.numpy().tobytes())
        elif isinstance(value, dict):
            for key in sorted(value, key=str):
                update(value[key], f"{label}/{key}")
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                update(item, f"{label}/{index}")
        else:
            digest.update(repr(value).encode("utf-8"))

    update(payload, "root")
    return digest.hexdigest()


def boundary_reactions(
    nodes: np.ndarray,
    triangles: np.ndarray,
    sigma_xx: np.ndarray,
    sigma_yy: np.ndarray,
    sigma_xy: np.ndarray,
) -> dict[str, float]:
    """Integrate P0 element stress tractions over horizontal exterior edges."""
    edge_owner: dict[tuple[int, int], int] = {}
    counts: Counter[tuple[int, int]] = Counter()
    for elem, tri in enumerate(triangles):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((int(tri[i]), int(tri[j]))))
            counts[edge] += 1
            edge_owner[edge] = elem
    ymin, ymax = float(nodes[:, 1].min()), float(nodes[:, 1].max())
    tol = max(1e-10, (ymax - ymin) * 1e-8)
    top = bottom = 0.0
    top_length = bottom_length = 0.0
    for edge, count in counts.items():
        if count != 1:
            continue
        a, b = nodes[list(edge)]
        length = float(np.linalg.norm(b - a))
        elem = edge_owner[edge]
        if abs(a[1] - ymax) <= tol and abs(b[1] - ymax) <= tol:
            top += float(sigma_yy[elem]) * length
            top_length += length
        elif abs(a[1] - ymin) <= tol and abs(b[1] - ymin) <= tol:
            bottom -= float(sigma_yy[elem]) * length
            bottom_length += length
    if top_length <= 0.0 or bottom_length <= 0.0:
        raise ValueError("could not identify both horizontal exterior boundaries")
    denom = max(abs(top), abs(bottom), 1e-30)
    return {
        "top_reaction_y": top,
        "bottom_reaction_y": bottom,
        "force_imbalance_fraction": abs(top + bottom) / denom,
        "top_boundary_length": top_length,
        "bottom_boundary_length": bottom_length,
    }


def validate_archive(archive: Path, level: str, mesh: Path, n_cycles: int = 3) -> dict[str, object]:
    expected = state_rows(level, n_cycles)
    diagnostics = archive / "element_diagnostics_probe_driver"
    nodes, triangles = mesh_triangles(mesh)
    tri_xy = nodes[triangles]
    expected_centroids = tri_xy.mean(axis=1)
    expected_area = 0.5 * np.abs(
        (tri_xy[:, 1, 0] - tri_xy[:, 0, 0]) * (tri_xy[:, 2, 1] - tri_xy[:, 0, 1])
        - (tri_xy[:, 2, 0] - tri_xy[:, 0, 0]) * (tri_xy[:, 1, 1] - tri_xy[:, 0, 1])
    )
    reaction_rows = []
    missing = []
    for row in expected:
        step = int(row["raw_step"])
        npz_path = diagnostics / f"element_fields_cycle_{step:04d}.npz"
        model_path = archive / "best_models" / f"trained_1NN_{step}.pt"
        state_path = archive / "best_models" / f"checkpoint_step_{step}.pt"
        alpha_path = archive / "alpha_snapshots" / f"alpha_cycle_{step:04d}.npy"
        for path in (npz_path, model_path, state_path, alpha_path):
            if not path.exists():
                missing.append(str(path.relative_to(archive)))
        if not npz_path.exists():
            continue
        with np.load(npz_path) as data:
            absent = REQUIRED_FIELDS.difference(data.files)
            if absent:
                missing.append(f"{npz_path.name}:fields={sorted(absent)}")
                continue
            for field in REQUIRED_FIELDS:
                values = np.asarray(data[field])
                if values.shape != (len(triangles),):
                    missing.append(f"{npz_path.name}:{field}:shape={values.shape}")
                elif not np.isfinite(values).all():
                    missing.append(f"{npz_path.name}:{field}:nonfinite")
            actual = {
                "cycle": int(np.asarray(data["physical_cycle"]).item()),
                "substep": int(np.asarray(data["substep_index"]).item()),
                "normalized": float(np.asarray(data["normalized_displacement"]).item()),
                "branch": str(np.asarray(data["loading_branch"]).item()),
                "label": str(np.asarray(data["state_label"]).item()),
                "displacement": float(np.asarray(data["prescribed_displacement"]).item()),
            }
            expected_meta = {
                "cycle": int(row["physical_cycle"]), "substep": int(row["substep"]),
                "normalized": float(row["normalized_displacement"]),
                "branch": str(row["branch"]), "label": str(row["state_label"]),
                "displacement": float(row["prescribed_displacement"]),
            }
            if (actual["cycle"], actual["substep"], actual["branch"], actual["label"]) != (
                expected_meta["cycle"], expected_meta["substep"], expected_meta["branch"], expected_meta["label"]
            ) or not np.isclose(actual["normalized"], expected_meta["normalized"], atol=1e-12) \
                    or not np.isclose(actual["displacement"], expected_meta["displacement"], atol=1e-12):
                missing.append(f"{npz_path.name}:metadata={actual}:expected={expected_meta}")
            centroids = np.column_stack((data["elem_x"], data["elem_y"]))
            if not np.allclose(centroids, expected_centroids, atol=2e-7, rtol=0.0):
                missing.append(f"{npz_path.name}:centroid_order_mismatch")
            if not np.allclose(data["area_elem"], expected_area, atol=2e-9, rtol=2e-6):
                missing.append(f"{npz_path.name}:area_order_mismatch")
            if not np.allclose(
                data["psi_solver_active_elem"],
                data["g_solver_elem"] * data["psi_raw_elem"],
                atol=1e-10, rtol=2e-5,
            ):
                missing.append(f"{npz_path.name}:solver_active_algebra_mismatch")
            if not np.allclose(
                data["psi_active_elem"],
                data["g_history_driver_elem"] * data["psi_raw_elem"],
                atol=1e-10, rtol=2e-5,
            ):
                missing.append(f"{npz_path.name}:history_active_algebra_mismatch")
            if not np.allclose(
                data["psi_history_driver_elem"], data["psi_active_elem"],
                atol=1e-10, rtol=2e-5,
            ):
                missing.append(f"{npz_path.name}:current_active_history_mismatch")
            if str(np.asarray(data["energy_export_timing"]).item()) != str(row["energy_timing"]):
                missing.append(f"{npz_path.name}:energy_timing_mismatch")
            reaction = boundary_reactions(
                nodes, triangles, data["sigma_effective_xx_elem"],
                data["sigma_effective_yy_elem"], data["sigma_effective_xy_elem"],
            )
        reaction_rows.append({**row, **reaction})
    if missing:
        raise RuntimeError(f"{level} archive incomplete: {missing[:12]}")
    reaction_path = archive / "cadence_reactions.csv"
    with reaction_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(reaction_rows[0]))
        writer.writeheader()
        writer.writerows(reaction_rows)
    write_state_index(archive / "cadence_state_index.csv", level, n_cycles)
    return {
        "level": level,
        "expected_states": len(expected),
        "diagnostic_states": len(reaction_rows),
        "state0_model_sha256": sha256(archive / "best_models" / "trained_1NN_0.pt"),
        "state0_history_sha256": sha256(archive / "best_models" / "checkpoint_step_0.pt"),
        "state0_model_semantic_sha256": semantic_torch_hash(archive / "best_models" / "trained_1NN_0.pt"),
        "state0_history_semantic_sha256": semantic_torch_hash(archive / "best_models" / "checkpoint_step_0.pt"),
        "reaction_export": str(reaction_path),
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
