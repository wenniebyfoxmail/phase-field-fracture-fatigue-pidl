#!/usr/bin/env python3
"""Run one fixed-parameter Manav-style monotonic SENT forward solve.

This runner deliberately keeps the neural solver and monotonic loading path
unchanged.  It varies only ``l0`` and sets ``w1 = Gc_bar / l0`` so that the
common-unit toughness proxy ``w1*l0`` remains fixed across profile trials.
Fatigue is forced off and no observation data enter the forward solve.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l0", type=float, required=True)
    parser.add_argument("--gc-bar", type=float, default=0.01)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--hidden-layers", type=int, default=8)
    parser.add_argument("--neurons", type=int, default=400)
    parser.add_argument("--activation", default="TrainableReLU")
    parser.add_argument("--init-coeff", type=float, default=1.0)
    parser.add_argument("--rprop-epochs", type=int, default=10000)
    parser.add_argument("--lbfgs-epochs", type=int, default=0)
    parser.add_argument(
        "--max-load-steps",
        type=int,
        default=None,
        help="Diagnostic-only prefix of the original loading path.",
    )
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.l0) or not math.isfinite(args.gc_bar):
        parser.error("--l0 and --gc-bar must be finite")
    if args.l0 <= 0 or args.gc_bar <= 0:
        parser.error("--l0 and --gc-bar must be positive")
    if args.rprop_epochs < 0 or args.lbfgs_epochs < 0:
        parser.error("optimizer epoch counts must be non-negative")
    if args.hidden_layers < 1 or args.neurons < 1:
        parser.error("network dimensions must be positive")
    if args.activation != "TrainableReLU":
        parser.error("this frozen reproduction requires --activation TrainableReLU")
    if not math.isfinite(args.init_coeff) or args.init_coeff <= 0:
        parser.error("--init-coeff must be finite and positive")
    if args.max_load_steps is not None and args.max_load_steps < 1:
        parser.error("--max-load-steps must be positive")
    return args


def main() -> int:
    args = parse_args()
    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    out = args.out.expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing non-empty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)

    here = Path(__file__).resolve().parent
    repo = here.parent
    executed_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(repo / "source"))
    sys.argv = [
        Path(__file__).name,
        str(args.hidden_layers),
        str(args.neurons),
        str(args.seed),
        args.activation,
        str(args.init_coeff),
    ]

    import torch
    from torch.utils.tensorboard import SummaryWriter

    import config
    from construct_model import construct_model
    from field_computation import FieldComputation
    from model_train import train

    # Fail closed if a future config change could route this runner into fatigue.
    config.fatigue_dict["fatigue_on"] = False
    config.fatigue_dict["loading_type"] = "monotonic"
    assert config.fatigue_dict["fatigue_on"] is False

    config.mat_prop_dict["mat_E"] = 1.0
    config.mat_prop_dict["mat_nu"] = 0.3
    config.mat_prop_dict["l0"] = float(args.l0)
    config.mat_prop_dict["w1"] = float(args.gc_bar / args.l0)
    invariant = config.mat_prop_dict["w1"] * config.mat_prop_dict["l0"]
    if abs(invariant - args.gc_bar) > 1.0e-12:
        raise RuntimeError("fixed-Gc invariant w1*l0 was not preserved")

    config.optimizer_dict["n_epochs_RPROP"] = int(args.rprop_epochs)
    config.optimizer_dict["n_epochs_LBFGS"] = int(args.lbfgs_epochs)
    active_disp = config.disp.copy()
    if args.max_load_steps is not None:
        active_disp = active_disp[: args.max_load_steps]
    if (
        len(active_disp) == 0
        or not all(
            math.isfinite(float(value)) and float(value) > 0 for value in active_disp
        )
        or not all(
            float(b) > float(a) for a, b in zip(active_disp[:-1], active_disp[1:])
        )
    ):
        raise RuntimeError(
            "active displacements must be finite, positive, and strictly increasing"
        )

    trained = out / "best_models"
    intermediate = out / "intermediate_models"
    trained.mkdir(parents=True, exist_ok=True)
    intermediate.mkdir(parents=True, exist_ok=True)
    try:
        config.writer.close()
    except Exception:
        pass
    writer = SummaryWriter(out / "TBruns")

    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    coarse_mesh = (here / config.coarse_mesh_file).resolve()
    fine_mesh = (here / config.fine_mesh_file).resolve()
    manifest = {
        "runner": str(Path(__file__).resolve()),
        "base_source_commit": "6429b2b6ec0372821c3cc6c1bc798ca42186604a",
        "executed_commit": executed_commit,
        "executed_worktree_dirty": dirty,
        "scope": "Manav-style monotonic SENT forward solve; fatigue disabled",
        "inverse_role": "fixed-parameter forward member of outer l0 profile",
        "l0": float(args.l0),
        "gc_bar": float(args.gc_bar),
        "w1": float(config.mat_prop_dict["w1"]),
        "w1_times_l0": float(invariant),
        "mat_E": 1.0,
        "mat_nu": 0.3,
        "PFF_model": config.PFF_model_dict["PFF_model"],
        "se_split": config.PFF_model_dict["se_split"],
        "tol_ir": config.PFF_model_dict["tol_ir"],
        "fatigue_on": False,
        "loading_type": "monotonic",
        "displacements": [float(value) for value in active_disp],
        "seed": int(args.seed),
        "hidden_layers": int(args.hidden_layers),
        "neurons": int(args.neurons),
        "activation": args.activation,
        "init_coeff": float(args.init_coeff),
        "rprop_epochs": int(args.rprop_epochs),
        "lbfgs_epochs": int(args.lbfgs_epochs),
        "coarse_mesh": str(coarse_mesh),
        "coarse_mesh_sha256": sha256(coarse_mesh),
        "fine_mesh": str(fine_mesh),
        "fine_mesh_sha256": sha256(fine_mesh),
        "device": str(config.device),
        "diagnostic_prefix_only": args.max_load_steps is not None,
    }
    manifest_path = out / "forward_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_sha256 = sha256(manifest_path)
    status_path = out / "run_status.json"
    status_path.write_text(
        json.dumps(
            {
                "status": "RUNNING",
                "manifest_sha256": manifest_sha256,
                "expected_steps": len(active_disp),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    # The frozen helper seeds after constructing the network. Seed here first
    # so the declared run seed actually controls the initial weights while the
    # architecture and subsequent Manav optimization path remain unchanged.
    torch.manual_seed(int(args.seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(args.seed))
    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict,
        config.mat_prop_dict,
        config.network_dict,
        config.domain_extrema,
        config.device,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema,
        lmbda=torch.tensor([0.0], device=config.device),
        theta=config.loading_angle,
        alpha_constraint=config.numr_dict["alpha_constraint"],
    )
    field_comp.net = field_comp.net.to(config.device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
    field_comp.theta = field_comp.theta.to(config.device)

    try:
        train(
            field_comp,
            active_disp,
            pffmodel,
            matprop,
            config.crack_dict,
            config.numr_dict,
            config.optimizer_dict,
            config.training_dict,
            str(coarse_mesh),
            str(fine_mesh),
            config.device,
            trained,
            intermediate,
            writer,
            fatigue_dict={"fatigue_on": False, "loading_type": "monotonic"},
        )
        checkpoints = sorted(trained.glob("trained_1NN_[0-9]*.pt"))
        expected_names = {
            f"trained_1NN_{index}.pt" for index in range(len(active_disp))
        }
        actual_names = {path.name for path in checkpoints}
        if actual_names != expected_names:
            raise RuntimeError(
                f"checkpoint completion mismatch: expected={sorted(expected_names)}, "
                f"actual={sorted(actual_names)}"
            )
        loss_summaries = []
        import numpy as np

        for index in range(len(active_disp)):
            loss_path = trained / f"trainLoss_1NN_{index}.npy"
            if not loss_path.is_file():
                raise FileNotFoundError(f"missing loss history: {loss_path}")
            loss = np.load(loss_path, allow_pickle=False)
            if loss.size == 0 or not np.all(np.isfinite(loss)):
                raise RuntimeError(f"non-finite or empty loss history: {loss_path}")
            loss_summaries.append(
                {
                    "step": index,
                    "count": int(loss.size),
                    "final": float(loss.reshape(-1)[-1]),
                }
            )
        checkpoint_hashes = {path.name: sha256(path) for path in checkpoints}
        status_path.write_text(
            json.dumps(
                {
                    "status": "COMPLETE",
                    "manifest_sha256": manifest_sha256,
                    "expected_steps": len(active_disp),
                    "checkpoint_count": len(checkpoints),
                    "checkpoint_sha256": checkpoint_hashes,
                    "loss_check": "all step loss histories present, non-empty and finite",
                    "loss_summaries": loss_summaries,
                    "convergence_claim": "not established by completion check",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        status_path.write_text(
            json.dumps(
                {
                    "status": "FAILED",
                    "manifest_sha256": manifest_sha256,
                    "expected_steps": len(active_disp),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        writer.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
