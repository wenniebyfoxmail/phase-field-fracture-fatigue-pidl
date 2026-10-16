#!/usr/bin/env python3
"""Explicit reviewed entry point for the S09-E008 packet export."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from s09_stage0a_p1_packet import export_s09_e008_p1_packet

parser = argparse.ArgumentParser()
parser.add_argument("--run-root", type=Path, required=True)
parser.add_argument("--capability-receipt", type=Path, required=True)
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--export-reviewed-packet", action="store_true")
args = parser.parse_args()
if not args.export_reviewed_packet:
    parser.error("--export-reviewed-packet is required")
identity = export_s09_e008_p1_packet(
    run_root=args.run_root, capability_receipt_path=args.capability_receipt,
    config_path=args.config, output_dir=args.output_dir)
print(json.dumps(identity, sort_keys=True))
