#!/usr/bin/env python3
"""CPU-only zero-step audit of the exact S09-E013 merged directions."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e013_producer import (  # noqa: E402
    EXPECTED_B25_CHECKPOINT_SHA256,
    EXPECTED_PACKET_MANIFEST_SHA256,
    _initialise_arms,
    zero_step_audit,
)
from s09_e013_local_ranking_objective import ARM_LOCAL  # noqa: E402
from s09_stage0a_p1_packet import canonical_json, sha256_file  # noqa: E402
from s09_stage0a_p1_trainer import build_runtime  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256_file(args.initial_checkpoint) != EXPECTED_B25_CHECKPOINT_SHA256:
        raise ValueError("B25 checkpoint identity mismatch")
    packet_identity = json.loads((args.packet_dir / "packet_identity.json").read_text())
    if packet_identity["manifest_sha256"] != EXPECTED_PACKET_MANIFEST_SHA256:
        raise ValueError("packet identity mismatch")
    config = json.loads(args.base_config.read_text())
    torch.manual_seed(int(config["model"]["seed"]))
    runtime = build_runtime(
        packet_dir=args.packet_dir,
        config_path=args.base_config,
        device=torch.device("cpu"),
        executable=False,
    )
    checkpoint = torch.load(args.initial_checkpoint, map_location="cpu", weights_only=False)
    runtime.model.load_state_dict(checkpoint["model"], strict=True)
    models, optimizers, identity = _initialise_arms(runtime, copy.deepcopy(checkpoint))
    runtime.model = models[ARM_LOCAL]
    audit = zero_step_audit(runtime, optimizers[ARM_LOCAL])
    receipt = {
        "schema_version": "s09-e013-zero-step-preflight-v1",
        "purpose": "actual pair-specific merged/projected direction and next-AdamW-state audit",
        "packet_manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256,
        "source_checkpoint_sha256": EXPECTED_B25_CHECKPOINT_SHA256,
        "common_initial_identity": identity,
        "optimizer_constructed": True,
        "optimizer_steps_performed": 0,
        "fresh_holdout_accessed": False,
        "audit": audit,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(receipt))
    print(json.dumps({
        "status": audit["status"],
        "wrong_local_helpful": audit["predicted_adamw_increases_wrong_local_margin_count"],
        "correct_global_flips": audit["local_arm_predicted_adamw_flips_correct_global_margin_count"],
        "directional_tier": audit["directional_tier"],
        "optimizer_steps_performed": 0,
        "output": str(args.output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
