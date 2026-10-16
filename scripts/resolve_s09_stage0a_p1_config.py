#!/usr/bin/env python3
"""Resolve the S09-E008 producer config without entering the training loop."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from s09_stage0a_p1_trainer import resolve_execution_config

parser = argparse.ArgumentParser()
parser.add_argument("--packet-dir", type=Path, required=True)
parser.add_argument("--base-config", type=Path, required=True)
parser.add_argument("--output-config", type=Path, required=True)
parser.add_argument("--authorize-reviewed-run", action="store_true")
parser.add_argument("--resolve-reviewed-config", action="store_true")
args = parser.parse_args()
if not args.resolve_reviewed_config:
    parser.error("--resolve-reviewed-config is required")
resolved = resolve_execution_config(
    packet_dir=args.packet_dir, base_config_path=args.base_config,
    output_path=args.output_config, repo_root=ROOT,
    authorize_execution=args.authorize_reviewed_run,
)
print(json.dumps({
    "status": resolved["status"],
    "execution_authorized": resolved["execution_authorized"],
    "training_commit": resolved["source"]["training_commit"],
    "packet_manifest_sha256": resolved["source"]["input_packet_sha256"],
}, sort_keys=True))
