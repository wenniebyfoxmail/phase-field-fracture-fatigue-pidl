#!/usr/bin/env python3
"""Launch one exact G4 arm only after lock and explicit-authorization checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_launch_contract import (  # noqa: E402
    CANONICAL_RESTART_MANIFEST_SHA256,
    load_and_verify_prelaunch_lock,
    verify_user_authorization,
)


def frozen_command(
    *, repo: Path, arm: str, restart_bundle: Path,
    producer_head: str,
) -> list[str]:
    common = [
        "python3", "SENS_tensile/run_fem_mesh_probe_driver_umax.py", "0.12",
        "--n-cycles-physical", "92", "--seed", "1",
        "--hidden-layers", "8", "--neurons", "400", "--init-coeff", "1.0",
        "--epochs-rprop", "10000", "--epochs-lbfgs", "0",
        "--optim-rel-tol", "5e-7",
        "--displacement-steps", "0.03,0.06,0.09,0.12,0",
        "--history-driver-reduction-mode", "fem_gp_tri3_g_mean",
        "--res-stiffness", "0", "--fem-irr-penalty",
        "--hard-alpha-recovery-step", "--hard-alpha-target", "1",
        "--fracture-confirm-cycles", "3",
        "--diag-physical-cycles", "76,82",
        "--diag-full-physical-cycles", "76,82",
        "--plot-every", "999", "--tag", f"g4_u012_{arm.lower()}",
        "--resume-bundle", str(restart_bundle.resolve()),
        "--resume-bundle-manifest-sha256", CANONICAL_RESTART_MANIFEST_SHA256,
        "--mechanical-residual-export-steps", "379,409",
        "--boundary-first-detect-receipt", "--hard-stop-physical-cycle", "92",
        "--require-clean-git", "--fresh-output-required",
        "--required-head-commit", producer_head,
    ]
    if arm == "A_absent":
        return common + ["--mechanical-risk-mode", "absent"]
    return common + [
        "--mechanical-risk-mode", "on", "--mechanical-risk-alpha", "0.85",
        "--mechanical-risk-lambda", "0.000549728557462236",
        "--mechanical-risk-e-ref", "1", "--mechanical-risk-l-ref", "1",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--prelaunch-lock", type=Path, required=True)
    parser.add_argument("--prelaunch-lock-sha256", required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    parser.add_argument("--arm", choices=("A_absent", "B_on"), required=True)
    parser.add_argument("--restart-bundle", type=Path, required=True)
    parser.add_argument("--stdout-log", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip()
    if subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"], text=True,
    ).strip():
        raise RuntimeError("producer checkout must be clean before G4 launch")
    load_and_verify_prelaunch_lock(
        args.prelaunch_lock.resolve(), args.prelaunch_lock_sha256, repo, head,
    )
    verify_user_authorization(args.authorization_receipt.resolve(), args.prelaunch_lock_sha256, head)
    command = frozen_command(
        repo=repo, arm=args.arm, restart_bundle=args.restart_bundle,
        producer_head=head,
    )
    if args.preflight_only:
        print(" ".join(command))
        return
    if args.stdout_log.exists():
        raise FileExistsError(f"refusing to overwrite {args.stdout_log}")
    args.stdout_log.parent.mkdir(parents=True, exist_ok=True)
    with args.stdout_log.open("x", encoding="utf-8") as log:
        subprocess.run(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == "__main__":
    main()
