#!/usr/bin/env python3
"""Resolve the exact clean producer HEAD into an external launch receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


PLACEHOLDER = "${G3_PRODUCER_COMMIT}"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def replace(value, head: str):
    if isinstance(value, str):
        return value.replace(PLACEHOLDER, head)
    if isinstance(value, list):
        return [replace(item, head) for item in value]
    if isinstance(value, dict):
        return {key: replace(item, head) for key, item in value.items()}
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    repo = args.repo.resolve()
    if git(repo, "status", "--porcelain"):
        raise RuntimeError("launch receipt requires an exactly clean producer checkout")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    head = git(repo, "rev-parse", "HEAD")
    raw = args.template.read_bytes()
    payload = json.loads(raw)
    if payload.get("required_head_commit") != PLACEHOLDER:
        raise RuntimeError("template is already resolved or malformed")
    frozen = replace(payload, head)
    frozen["template_sha256"] = hashlib.sha256(raw).hexdigest()
    frozen["launch_receipt_frozen"] = True
    frozen["training_authorized"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "frozen_not_authorized", "head": head, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
