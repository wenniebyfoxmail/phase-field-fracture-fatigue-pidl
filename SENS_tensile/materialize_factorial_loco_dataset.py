#!/usr/bin/env python3
"""Materialise the four signed Agent2 FEM bundles for producer training."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_multitrajectory_contract_adapter import (  # noqa: E402
    AGENT2_COMMIT,
    EXPECTED_GROUPS,
    EXPECTED_LOCO_LOCK_SHA256,
    load_agent2_factorial_loco_contract,
)
from prepare_fem_mechanism_operator_dataset import load_cycle_state  # noqa: E402


LOG_FLOOR = 1.0e-12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_agent2_factorial_loco_contract(args.contract)
    package = args.contract.parent
    args.out.mkdir(parents=True, exist_ok=True)
    trajectories_dir = args.out / "trajectories"
    trajectories_dir.mkdir(exist_ok=True)

    graph_source: Path | None = None
    rows = []
    for record in records:
        bundle = json.loads(Path(record.bundle_path).read_text(encoding="utf-8"))
        candidate_graph = Path(bundle["mesh"]["source"])
        if graph_source is None:
            graph_source = candidate_graph
        elif candidate_graph != graph_source:
            raise ValueError("factorial bundles do not use one graph asset")
        states = []
        for state in bundle["states"]:
            source = Path(state["source_file"])
            if sha256_file(source) != state["source_sha256"]:
                raise ValueError(f"source shard hash mismatch: {source}")
            states.append(
                load_cycle_state(source, int(bundle["mesh"]["cell_count"]), LOG_FLOOR)
            )
        values = np.stack(states)
        n_substeps = int(bundle["physics"]["n_substeps"])
        loading_metadata = np.tile(
            np.asarray([float(n_substeps == 5), float(n_substeps == 8)], dtype=np.float32),
            (len(values), 1),
        )
        path = trajectories_dir / f"{record.trajectory_id}.npz"
        np.savez_compressed(
            path,
            trajectory_id=np.asarray(record.trajectory_id),
            independence_group_id=np.asarray(record.independence_group_id),
            states=values,
            cycles=np.arange(1, len(values) + 1, dtype=np.int16),
            loading_metadata=loading_metadata,
            first_hit_cycle=np.asarray(bundle["event"]["first_hit"]["cycle"], dtype=np.int16),
            confirmed_cycle=np.asarray(bundle["event"]["confirmed"]["cycle"], dtype=np.int16),
            event_phase=np.asarray(bundle["event"]["first_hit"]["phase"]),
            source_bundle_sha256=np.asarray(record.bundle_sha256),
            fem_eta=np.asarray(0.0, dtype=np.float64),
            synthetic_reference=np.asarray(True),
        )
        rows.append(
            {
                "trajectory_id": record.trajectory_id,
                "independence_group_id": record.independence_group_id,
                "state_count": len(values),
                "first_hit_cycle": int(bundle["event"]["first_hit"]["cycle"]),
                "confirmed_cycle": int(bundle["event"]["confirmed"]["cycle"]),
                "data_file": str(path.name),
                "data_sha256": sha256_file(path),
                "source_bundle_sha256": record.bundle_sha256,
            }
        )
        print(json.dumps(rows[-1]), flush=True)

    assert graph_source is not None
    graph_out = args.out / "graph.npz"
    shutil.copyfile(graph_source, graph_out)
    split_out = args.out / "within_hard5_factorial_loco_split_lock_v1.json"
    shutil.copyfile(args.split, split_out)
    manifest = {
        "dataset_id": "factorial_loco_fem_states_v1",
        "agent2_commit": AGENT2_COMMIT,
        "agent2_contract_file_sha256": sha256_file(args.contract),
        "agent2_loco_internal_lock_sha256": EXPECTED_LOCO_LOCK_SHA256,
        "agent2_loco_file_sha256": sha256_file(args.split),
        "trajectory_count": len(rows),
        "state_count": sum(row["state_count"] for row in rows),
        "element_count": 86408,
        "state_channels": [
            "damage_clipped_0_1",
            "alpha_bar_nonnegative",
            "fatigue_degradation_clipped_0_1",
            "log10_peak_raw_tensile_driver",
        ],
        "loading_metadata": ["is_5step", "is_8step"],
        "graph_file": graph_out.name,
        "graph_sha256": sha256_file(graph_out),
        "trajectories": rows,
        "claim_scope": "within-Hard5 shared-geometry numerical factorial only",
        "synthetic_not_real_road": True,
    }
    manifest_path = args.out / "RUN_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes = [
        f"{sha256_file(manifest_path)}  RUN_MANIFEST.json",
        f"{sha256_file(graph_out)}  graph.npz",
        f"{sha256_file(split_out)}  {split_out.name}",
    ]
    hashes.extend(
        f"{row['data_sha256']}  trajectories/{row['data_file']}" for row in rows
    )
    (args.out / "HASHES.sha256").write_text("\n".join(hashes) + "\n")
    print(json.dumps({"status": "PASS", "states": manifest["state_count"]}))


if __name__ == "__main__":
    main()

