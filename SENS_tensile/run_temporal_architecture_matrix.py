#!/usr/bin/env python3
"""Run a sealed, parameter-matched temporal architecture matrix on one GPU.

The launcher is intentionally sequential and requires an explicit single
``CUDA_VISIBLE_DEVICES`` value.  Parallelism is achieved by starting separate
attributable launchers on separate producer GPUs, never by exposing all cards
to one process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "source"))

from temporal_mesh_operator import TemporalMeshOperator, count_parameters  # noqa: E402


PROTOCOL_PATH = HERE / "temporal_architecture_protocol_v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_protocol(dataset: Path) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    actual_hash = sha256(dataset)
    expected_hash = protocol["dataset"]["sha256"]
    if actual_hash != expected_hash:
        raise ValueError(f"dataset hash mismatch: {actual_hash} != {expected_hash}")

    architecture = protocol["shared_architecture"]
    capacity = protocol["capacity_gate"]
    for family, entry in capacity["matched_widths"].items():
        model = TemporalMeshOperator(
            temporal_family=family,
            local_dim=architecture["local_dim"],
            token_dim=architecture["token_dim"],
            temporal_width=entry["temporal_width"],
            local_layers=architecture["local_layers"],
            coarse_layers=architecture["coarse_layers"],
            graph_enabled=True,
            max_context=max(architecture["context_candidates"]),
            transformer_heads=architecture["transformer_heads"],
        )
        actual = count_parameters(model)
        if actual != entry["parameters"]:
            raise ValueError(
                f"sealed parameter count drift for {family}: {actual} != {entry['parameters']}"
            )
    return protocol


def command_for(
    protocol: dict,
    dataset: Path,
    output: Path,
    family: str,
    seed: int,
    steps: int,
) -> list[str]:
    architecture = protocol["shared_architecture"]
    capacity = protocol["capacity_gate"]
    optimization = protocol["optimization"]
    width = capacity["matched_widths"][family]["temporal_width"]
    return [
        sys.executable,
        "-u",
        str(HERE / "train_temporal_mesh_operator.py"),
        "--dataset", str(dataset),
        "--out", str(output),
        "--temporal-model", family,
        "--context-lengths", ",".join(map(str, architecture["context_candidates"])),
        "--local-dim", str(architecture["local_dim"]),
        "--token-dim", str(architecture["token_dim"]),
        "--temporal-width", str(width),
        "--local-layers", str(architecture["local_layers"]),
        "--coarse-layers", str(architecture["coarse_layers"]),
        "--transformer-heads", str(architecture["transformer_heads"]),
        "--parameter-target", str(capacity["target_parameters"]),
        "--parameter-tolerance", str(capacity["relative_tolerance"]),
        "--rollout-steps", str(optimization["rollout_steps"]),
        "--teacher-forcing-ratio", str(optimization["teacher_forcing_ratio"]),
        "--steps", str(steps),
        "--eval-every", str(min(optimization["eval_every"], steps)),
        "--patience", str(optimization["patience"]),
        "--lr", str(optimization["lr"]),
        "--weight-decay", str(optimization["weight_decay"]),
        "--active-weight", str(optimization["active_weight"]),
        "--support-weight", str(optimization["support_weight"]),
        "--gradient-weight", str(optimization["gradient_weight"]),
        "--morphology-weight", str(optimization["morphology_weight"]),
        "--active-roughness-weight", str(optimization["active_roughness_weight"]),
        "--seed", str(seed),
        "--device", "cuda",
        "--allow-single-trajectory-diagnostic",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("smoke", "core_1", "core_2"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-complete",
        action="store_true",
        help="Skip a job only when its RUN_MANIFEST.json already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocol = load_and_validate_protocol(args.dataset.resolve())
    stage = protocol["stages"][args.stage]
    steps = int(stage.get("steps", protocol["optimization"]["steps"]))
    jobs = [
        (family, int(seed))
        for family in stage["families"]
        for seed in stage["seeds"]
    ]
    commands = []
    for family, seed in jobs:
        output = args.out_root / args.stage / f"{family}_seed{seed}"
        commands.append(
            {
                "family": family,
                "seed": seed,
                "output": str(output),
                "command": command_for(protocol, args.dataset.resolve(), output, family, seed, steps),
            }
        )

    if args.dry_run:
        print(json.dumps({"protocol_id": protocol["protocol_id"], "jobs": commands}, indent=2))
        return
    if sys.platform == "darwin":
        raise RuntimeError("matrix execution is disabled on Mac")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible or "," in visible:
        raise RuntimeError("set CUDA_VISIBLE_DEVICES to exactly one producer GPU")

    args.out_root.mkdir(parents=True, exist_ok=True)
    matrix_manifest = {
        "protocol_id": protocol["protocol_id"],
        "stage": args.stage,
        "dataset_sha256": protocol["dataset"]["sha256"],
        "cuda_visible_devices": visible,
        "started_unix": time.time(),
        "jobs": commands,
    }
    manifest_path = args.out_root / f"{args.stage}_matrix_manifest.json"
    manifest_path.write_text(json.dumps(matrix_manifest, indent=2) + "\n", encoding="utf-8")

    for job in commands:
        output = Path(job["output"])
        if args.skip_complete and (output / "RUN_MANIFEST.json").exists():
            print(f"SKIP complete {job['family']} seed {job['seed']}", flush=True)
            continue
        output.mkdir(parents=True, exist_ok=True)
        print(f"START {job['family']} seed {job['seed']}", flush=True)
        subprocess.run(job["command"], cwd=ROOT, check=True)
        print(f"DONE {job['family']} seed {job['seed']}", flush=True)

    matrix_manifest["completed_unix"] = time.time()
    manifest_path.write_text(json.dumps(matrix_manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
