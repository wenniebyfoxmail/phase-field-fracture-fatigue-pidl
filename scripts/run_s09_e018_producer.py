#!/usr/bin/env python3
"""Single-use producer entrypoint for the E018 matched two-arm comparison."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_real_adapter import canonical_json  # noqa: E402
from s09_e018_real_adapter import ARM_ORDER, run_reviewed_producer  # noqa: E402


RUN_ID = "S09-E018-R002-amplitude-priority-ab"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), "JSON root must be an object")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    _require(path.read_bytes() == payload, "control receipt retrieval mismatch")


def _resolve_bindings(bindings: Mapping[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for name, reference in bindings.items():
        _require(isinstance(reference, str) and ":" in reference, f"bad binding {name}")
        module_name, attribute_name = reference.split(":", 1)
        target: Any = importlib.import_module(module_name)
        for component in attribute_name.split("."):
            target = getattr(target, component)
        _require(callable(target), f"binding not callable: {name}")
        resolved[name] = target
    return resolved


def validate(config: Mapping[str, Any], *, config_path: Path, output_dir: Path) -> None:
    required = {
        "schema_version", "run_id", "status", "execution_authorized", "arms",
        "data", "mapping", "physics", "optimizer", "budget", "producer", "bindings",
    }
    _require(set(config) == required, "E018 config keys drift")
    _require(config["schema_version"] == "s09-e018-final-run-v1", "schema drift")
    _require(config["run_id"] == RUN_ID, "run identity drift")
    _require(config["status"] == "AUTHORISED_FOR_ONE_COMPLETE_RUN", "run status drift")
    _require(config["execution_authorized"] is True, "execution is not authorised")
    _require(tuple(config["arms"]) == ARM_ORDER, "arm order drift")
    _require(config["budget"] == {"updates_per_arm": 64, "total_update_cap": 128, "retry": False, "resume": False}, "budget drift")
    _require(config["physics"]["beta"] == 0.25, "beta drift")
    _require(config["mapping"]["sample_semantics"] == "independent_cycle", "sample semantics drift")
    _require(config["mapping"]["autoregressive"] is False, "rollout must remain disabled")
    _require(config["data"]["new_fem"] is False and config["data"]["fresh_holdout"] is False, "data scope drift")
    _require(output_dir == Path(config["producer"]["output_root"]), "output path drift")
    _require(config_path.resolve().is_file(), "config missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--base-runtime-config", type=Path, required=True)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute-authorised-e018", action="store_true")
    args = parser.parse_args()
    if not args.execute_authorised_e018:
        raise PermissionError("--execute-authorised-e018 is required")
    config = _load(args.config)
    validate(config, config_path=args.config, output_dir=args.output_dir)
    _require(not args.output_dir.exists(), "output path already exists")
    _require(not args.control_dir.exists(), "control path already exists")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()
    _require(len(commit) == 40, "unresolved code identity")
    control = args.control_dir
    control.mkdir(parents=True)
    config_sha = _sha(args.config)
    _write_once(
        control / "authority_consumption.json",
        {"run_id": RUN_ID, "terminal_state": "AUTHORITY_CONSUMED_NO_RETRY", "config_sha256": config_sha, "commit": commit, "retry": False, "resume": False},
    )
    run_root = args.output_dir.parent
    temp_root = run_root / "tmp"
    cache_root = run_root / "cache"
    temp_root.mkdir()
    cache_root.mkdir()
    configured = dict(config)
    configured["_execution_control"] = {
        "authority_sha256": config_sha,
        "reviewed_commit": commit,
        "paths": {
            "code_root": str(ROOT),
            "output_root": str(args.output_dir),
            "control_root": str(control),
            "temp_root": str(temp_root),
            "cache_root": str(cache_root),
        },
        "resources": {
            "host_rss_cap_bytes": 16 * 1024**3,
            "minimum_free_disk_bytes": 20 * 1024**3,
            "output_tree_cap_bytes": 10 * 1024**3,
            "temp_tree_cap_bytes": 4 * 1024**3,
        },
    }
    bindings = _resolve_bindings(config["bindings"])
    try:
        result = run_reviewed_producer(
            config=configured,
            packet_dir=args.packet_dir,
            base_runtime_config=args.base_runtime_config,
            initial_checkpoint=args.initial_checkpoint,
            output_dir=args.output_dir,
            bindings=bindings,
        )
    except Exception as error:
        _write_once(
            control / "producer_failure.json",
            {"run_id": RUN_ID, "terminal_state": "FAILED", "reason": f"{type(error).__name__}: {error}", "retry": False, "resume": False},
        )
        raise
    _write_once(control / "producer_completion.json", result)


if __name__ == "__main__":
    main()
