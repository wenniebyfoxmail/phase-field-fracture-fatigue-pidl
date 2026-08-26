#!/usr/bin/env python3
"""Build the frozen three-amplitude Hard-5 LOAO GNO dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import meshio
import numpy as np
from scipy.io import loadmat


CASES = {
    "hard5_u011": {"subdir": "u011", "umax": 0.11, "first_hit": 122, "confirmed": 125, "pidl": "u011_c121_peak_step604_on_fem.npz"},
    "hard5_u012": {"subdir": "u012", "umax": 0.12, "first_hit": 83, "confirmed": 86, "pidl": "u012_c82_peak_step409_on_fem.npz"},
    "hard5_u013": {"subdir": "u013", "umax": 0.13, "first_hit": 59, "confirmed": 62, "pidl": "u013_c55_peak_step274_on_fem.npz"},
}
FIELDS = ("d_elem", "alpha_bar_elem", "f_alpha_elem", "psi_elem")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_states(case_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    files = sorted(
        (case_dir / "psi_fields").glob("cycle_*.mat"),
        key=lambda path: int(re.fullmatch(r"cycle_(\d+)\.mat", path.name).group(1)),
    )
    cycles = np.asarray([int(re.fullmatch(r"cycle_(\d+)\.mat", path.name).group(1)) for path in files], dtype=np.int16)
    if not np.array_equal(cycles, np.arange(1, len(cycles) + 1)):
        raise ValueError(f"nonconsecutive cycle files in {case_dir}")
    states = []
    for path in files:
        payload = loadmat(path)
        arrays = [np.asarray(payload[name], dtype=np.float64).reshape(-1) for name in FIELDS]
        if any(len(array) != 86408 or not np.isfinite(array).all() for array in arrays):
            raise ValueError(f"invalid field in {path}")
        states.append(
            np.column_stack(
                [
                    np.clip(arrays[0], 0.0, 1.0),
                    np.maximum(arrays[1], 0.0),
                    np.clip(arrays[2], 0.0, 1.0),
                    np.log10(np.maximum(arrays[3], 1.0e-12)),
                ]
            ).astype(np.float32)
        )
    return cycles, np.stack(states)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-root", type=Path, required=True)
    parser.add_argument("--reference-graph", type=Path, required=True)
    parser.add_argument("--pidl-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"output must be fresh: {args.out}")
    (args.out / "trajectories").mkdir(parents=True)
    (args.out / "pidl_matches").mkdir()
    shutil.copy2(args.reference_graph, args.out / "graph.npz")
    graph = np.load(args.reference_graph, allow_pickle=False)
    reference_connectivity = np.asarray(graph["connectivity"])
    reference_centroids = np.asarray(graph["centroids"])

    rows = []
    for trajectory_id, specification in CASES.items():
        candidates = list((args.fem_root / specification["subdir"]).glob("SENS_*"))
        if len(candidates) != 1:
            raise ValueError(f"expected one FEM case for {trajectory_id}, found {candidates}")
        case_dir = candidates[0]
        mesh = meshio.read(case_dir / "peak_load_c1.vtk")
        connectivity = np.asarray(mesh.cells_dict["quad"])
        centroids = np.asarray(mesh.points)[connectivity, :2].mean(axis=1)
        if not np.array_equal(connectivity, reference_connectivity) or not np.array_equal(centroids, reference_centroids):
            raise ValueError(f"mesh/element order mismatch for {trajectory_id}")
        cycles, states = load_states(case_dir)
        if specification["confirmed"] > int(cycles[-1]):
            raise ValueError(f"confirmed cycle unavailable for {trajectory_id}")
        trajectory_path = args.out / "trajectories" / f"{trajectory_id}.npz"
        np.savez_compressed(
            trajectory_path,
            cycles=cycles,
            states=states,
            trajectory_id=np.asarray(trajectory_id),
            physics_family=np.asarray("hard_eta0_5step"),
            trajectory_count=np.asarray(1, dtype=np.int16),
            umax=np.asarray(specification["umax"], dtype=np.float64),
            first_hit_cycle=np.asarray(specification["first_hit"], dtype=np.int16),
            confirmed_cycle=np.asarray(specification["confirmed"], dtype=np.int16),
        )
        pidl_source = args.pidl_root / specification["pidl"]
        pidl_destination = args.out / "pidl_matches" / f"{trajectory_id}.npz"
        shutil.copy2(pidl_source, pidl_destination)
        rows.append(
            {
                "trajectory_id": trajectory_id,
                "umax": specification["umax"],
                "cycle_count": int(len(cycles)),
                "first_hit_cycle": specification["first_hit"],
                "confirmed_cycle": specification["confirmed"],
                "data_file": trajectory_path.name,
                "data_sha256": sha256(trajectory_path),
                "pidl_match_file": pidl_destination.name,
                "pidl_match_sha256": sha256(pidl_destination),
                "fem_case": str(case_dir.resolve()),
                "reference_vtk_sha256": sha256(case_dir / "peak_load_c1.vtk"),
            }
        )
    manifest = {
        "dataset_id": "hard5_loao_fem_states_v1",
        "claim_class": "processed_griphfith_archive_imitation_only",
        "teacher_qualified": False,
        "damage_fixed_point_gate": "fail",
        "physics_loss_weight": 0.0,
        "physical_validation": False,
        "trajectory_count": 3,
        "graph_file": "graph.npz",
        "state_channels": ["damage_clipped_0_1", "alpha_bar_nonnegative", "fatigue_degradation_clipped_0_1", "log10_peak_raw_tensile_driver"],
        "split": "leave_one_complete_umax_trajectory_out",
        "trajectories": rows,
        "pidl_use": "evaluation_only_never_loaded_before_training_finishes",
    }
    (args.out / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    files = [args.out / "RUN_MANIFEST.json", args.out / "graph.npz", *sorted((args.out / "trajectories").glob("*.npz")), *sorted((args.out / "pidl_matches").glob("*.npz"))]
    (args.out / "HASHES.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(args.out)}\n" for path in files),
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "manifest_sha256": sha256(args.out / "RUN_MANIFEST.json"), "hash_file_sha256": sha256(args.out / "HASHES.sha256"), "files": {str(path.relative_to(args.out)): sha256(path) for path in files}}, indent=2))


if __name__ == "__main__":
    main()
