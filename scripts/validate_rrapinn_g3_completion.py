#!/usr/bin/env python3
"""Cross-arm G3 producer validator; this alone may write the final verdict."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import torch


MODES = {"A_absent": "absent", "B_off": "off", "C_on": "on"}
STEPS = tuple(range(6))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_losses(run: Path) -> tuple[bool, dict[int, np.ndarray]]:
    rows = {}
    for step in STEPS:
        path = run / "best_models" / f"trainLoss_1NN_{step}.npy"
        rows[step] = np.load(path, allow_pickle=False)
    return all(np.all(np.isfinite(row)) and row.size > 0 for row in rows.values()), rows


def load_outputs(run: Path) -> tuple[dict, dict[int, dict], dict[int, np.ndarray]]:
    models, checkpoints = {}, {}
    finite, losses = finite_losses(run)
    if not finite:
        raise ValueError(f"non-finite or empty loss in {run}")
    for step in STEPS:
        models[step] = torch.load(
            run / "best_models" / f"trained_1NN_{step}.pt",
            map_location="cpu", weights_only=True,
        )
        checkpoints[step] = torch.load(
            run / "best_models" / f"checkpoint_step_{step}.pt",
            map_location="cpu", weights_only=False,
        )
    return models, checkpoints, losses


def tensors_exact(left: dict, right: dict) -> bool:
    return left.keys() == right.keys() and all(
        torch.equal(left[key], right[key]) for key in left
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--arm", action="append", required=True,
                    help="NAME=/absolute/run/path; exactly A_absent, B_off, C_on")
    ap.add_argument("--log", action="append", required=True,
                    help="NAME=/absolute/external_stdout.log")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    arms = dict(item.split("=", 1) for item in args.arm)
    logs = dict(item.split("=", 1) for item in args.log)
    if set(arms) != set(MODES) or set(logs) != set(MODES):
        raise ValueError("exactly three named arm paths and logs are required")
    receipt = load_json(args.receipt)
    repo = args.repo.resolve()
    expected_head = receipt["required_head_commit"]
    actual_runner_sha = sha256(repo / "SENS_tensile" / "run_fem_mesh_probe_driver_umax.py")
    checks = {
        "receipt_frozen": receipt.get("launch_receipt_frozen") is True,
        "repo_head": subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip() == expected_head,
    }
    loaded = {}
    for name, mode in MODES.items():
        run = Path(arms[name]).resolve()
        provenance = load_json(run / "RUN_PROVENANCE.json")
        metrics = load_json(run / "g3_smoke_metrics.json")
        log_text = Path(logs[name]).read_text(encoding="utf-8", errors="replace")
        checks[f"{name}:head"] = provenance.get("runner_git_commit") == expected_head
        checks[f"{name}:runner_sha"] = provenance.get("runner_sha256") == actual_runner_sha
        checks[f"{name}:mode"] = provenance.get("mechanical_risk_mode") == mode
        checks[f"{name}:init"] = provenance.get("init_checkpoint", {}).get("sha256") == receipt["init_checkpoint_sha256"]
        checks[f"{name}:init_file_sha"] = sha256(
            run / "best_models" / "trained_1NN_initTraining.pt"
        ) == receipt["init_checkpoint_sha256"]
        checks[f"{name}:returned"] = metrics.get("execution_returned") is True
        checks[f"{name}:six_checkpoints"] = metrics.get("checkpoint_count") == 6
        checks[f"{name}:log_finite"] = re.search(r"(?<![A-Za-z])[+-]?(?:nan|inf)(?![A-Za-z])", log_text, re.I) is None
        try:
            loaded[name] = load_outputs(run)
            checks[f"{name}:reload_and_finite"] = True
        except Exception as exc:
            loaded[name] = None
            checks[f"{name}:reload_and_finite"] = False
            checks[f"{name}:reload_error"] = str(exc)

    if loaded["A_absent"] is not None and loaded["B_off"] is not None:
        a_models, a_states, a_losses = loaded["A_absent"]
        b_models, b_states, b_losses = loaded["B_off"]
        checks["A_B:loss_exact"] = all(np.array_equal(a_losses[s], b_losses[s]) for s in STEPS)
        checks["A_B:model_exact"] = all(tensors_exact(a_models[s], b_models[s]) for s in STEPS)
        state_keys = ("hist_alpha", "hist_fat", "psi_plus_prev", "psi_history_elem")
        checks["A_B:state_exact"] = all(
            all(torch.equal(a_states[s][key], b_states[s][key]) for key in state_keys)
            for s in STEPS
        )
    else:
        checks["A_B:loss_exact"] = checks["A_B:model_exact"] = checks["A_B:state_exact"] = False

    passed = all(value is True for key, value in checks.items() if not key.endswith("reload_error"))
    verdict = {
        "schema": "rrapinn-g3-final-verdict-v1",
        "status": "pass_producer_smoke_only" if passed else "fail_block_training",
        "checks": checks,
        "claim_boundary": "No fracture timing, field accuracy, or efficacy claim.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
