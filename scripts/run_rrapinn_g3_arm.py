#!/usr/bin/env python3
"""Authorized launcher that guarantees an external stdout log for one G3 arm."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--authorization-receipt", type=Path, required=True)
    ap.add_argument("--arm", choices=("A_absent", "B_off", "C_on"), required=True)
    ap.add_argument("--init-checkpoint", type=Path, required=True)
    ap.add_argument("--stdout-log", type=Path, required=True)
    args = ap.parse_args()
    if args.stdout_log.exists():
        raise FileExistsError(f"refusing to overwrite {args.stdout_log}")
    packet = json.loads(args.receipt.read_text(encoding="utf-8"))
    auth = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    head = subprocess.check_output(
        ["git", "-C", str(args.repo), "rev-parse", "HEAD"], text=True
    ).strip()
    required_auth = {
        "schema": "rrapinn-g3-user-authorization-v1",
        "authorized": True,
        "scope": "three-arm-producer-smoke",
        "producer_head": head,
    }
    if any(auth.get(key) != value for key, value in required_auth.items()):
        raise RuntimeError("missing or mismatched explicit G3 user authorization receipt")
    if packet.get("launch_receipt_frozen") is not True or packet.get("required_head_commit") != head:
        raise RuntimeError("launch receipt does not lock the current producer HEAD")
    if subprocess.check_output(
        ["git", "-C", str(args.repo), "status", "--porcelain"], text=True
    ).strip():
        raise RuntimeError("producer checkout must be clean")
    arm = next(item for item in packet["arms"] if item["name"] == args.arm)
    command = [
        str(args.init_checkpoint) if token == "${G3_INIT_CHECKPOINT}" else token
        for token in packet["command_common"] + arm["extra_args"]
    ]
    args.stdout_log.parent.mkdir(parents=True, exist_ok=True)
    with args.stdout_log.open("x", encoding="utf-8") as log:
        subprocess.run(command, cwd=args.repo, stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == "__main__":
    main()
