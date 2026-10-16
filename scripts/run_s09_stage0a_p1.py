#!/usr/bin/env python3
"""Explicit producer-only entry point for S09-E008 P1."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from s09_stage0a_p1_trainer import run_training

parser = argparse.ArgumentParser()
parser.add_argument("--packet-dir", type=Path, required=True)
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--execute-reviewed-run", action="store_true")
args = parser.parse_args()
if not args.execute_reviewed_run:
    parser.error("--execute-reviewed-run is required")
receipt = run_training(packet_dir=args.packet_dir, config_path=args.config,
                       output_dir=args.output_dir, repo_root=ROOT)
print(json.dumps(receipt, sort_keys=True))
