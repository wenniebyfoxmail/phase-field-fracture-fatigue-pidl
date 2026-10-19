"""Read-only producer preflight for HQ-ROAD-UQ-MATRIX-001-R001."""
import argparse
import json
import os
import platform
import socket
from pathlib import Path

import torch

import paired_matrix_evaluator as matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--old-checkpoint", required=True)
    parser.add_argument("--new-checkpoint", required=True)
    parser.add_argument("--valzip", required=True)
    parser.add_argument("--cfd", required=True)
    parser.add_argument("--gapszip", required=True)
    parser.add_argument("--old-cfd-csv", required=True)
    parser.add_argument("--new-gaps-csv", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    approval = json.loads(Path(args.approval).read_text())
    lock = json.loads(Path(args.lock).read_text())
    matrix.approval_gate(approval, args.lock)
    paths = {
        "old_checkpoint": Path(args.old_checkpoint),
        "new_checkpoint": Path(args.new_checkpoint),
        "valzip": Path(args.valzip),
        "gapszip": Path(args.gapszip),
        "old_cfd_csv": Path(args.old_cfd_csv),
        "new_gaps_csv": Path(args.new_gaps_csv),
    }
    observed = {}
    for key, path in paths.items():
        digest = matrix.sha256(path)
        if digest != lock[key]["sha256"]:
            raise RuntimeError(f"hash mismatch {key}")
        observed[key] = {"bytes": path.stat().st_size, "sha256": digest}
    cfd_lock = matrix.base.cfd_lock(Path(args.cfd))
    if cfd_lock != lock["cfd_lock"]:
        raise RuntimeError("CFD content drift")

    old_model = matrix.base.UNet()
    old_state = torch.load(args.old_checkpoint, map_location="cpu", weights_only=True)
    old_model.load_state_dict(old_state["model"], strict=True)
    new_model = matrix.ResNet18UNet()
    new_state = torch.load(args.new_checkpoint, map_location="cpu", weights_only=True)
    new_model.load_state_dict(new_state["model"], strict=True)

    result = {
        "status": "PASS_REMOTE_PREFLIGHT_NO_TRAINING",
        "run_id": approval["run_id"],
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "gpu": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "cuda_available": torch.cuda.is_available(),
        "environment": matrix.environment(),
        "code_snapshot": matrix.snapshot(),
        "data_lock_sha256": matrix.sha256(args.lock),
        "inputs": observed,
        "cfd_lock": cfd_lock,
        "strict_checkpoint_loads": ["old_scratch_unet", "repair_resnet18unet"],
        "training_or_optimizer_steps": 0,
        "road420_access": False,
    }
    Path(args.output).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
