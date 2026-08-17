#!/usr/bin/env python3
"""Tooling-only Umax micro-run: KAN displacement plus RBF phase field.

This runner changes only the field representation.  The variational energy,
fatigue law, five-substep schedule, mesh, boundary-condition wrapper, history
commit, and fracture detector remain on the strict soft-hist0 baseline path.
It is intended for one-cycle numerical viability tests, not lifetime claims.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float, nargs="?", default=0.12)
    parser.add_argument("--n-cycles", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--tag", default="kanUV_rbfAlpha_fiveStep_micro_v1")
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if args.n_cycles < 1:
        raise ValueError("n_cycles must be >= 1")

    sys.argv = ["main.py", "1", "32", str(args.seed), "TrainableTanh", "1.0"]
    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    config.network_dict.update({
        "model_type": "kan_rbf",
        "hidden_layers": 1,
        "neurons": 32,
        "activation": "TrainableTanh",
        "init_coeff": 1.0,
        "compile": False,
        "kan_rbf": {
            "kan_width": 32,
            "kan_basis": 9,
            "rbf_x_centres": 41,
            "rbf_y_centres": 17,
            "rbf_y_extent": 0.20,
            "rbf_sigma_x": 0.08,
            "rbf_sigma_y": 0.035,
        },
    })
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    if hasattr(config, "graph_dict"):
        config.graph_dict["enable"] = False
    config.local_patch_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.symmetry_prior = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.coarse_mesh_file = args.mesh_file
    config.fine_mesh_file = args.mesh_file
    config.optimizer_dict["n_epochs_RPROP"] = int(args.epochs)
    config.optimizer_dict["n_epochs_LBFGS"] = 0
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    factors = np.asarray([0.25, 0.50, 0.75, 1.00, 0.00], dtype=float)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(factors))
    config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
    config.fatigue_dict["fracture_confirm_cycles"] = 3
    config.fatigue_dict["plot_every_n_cycles"] = 1
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": list(range(0, 5 * int(args.n_cycles))),
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics",
    }
    config.disp_cyclic = np.tile(factors * float(args.umax), int(args.n_cycles))

    tag = (
        f"kanUV_rbfAlpha_Umax{args.umax}_N{args.n_cycles}_seed{args.seed}"
        f"_ep{args.epochs}_{args.tag}"
    )
    config.model_path = config.resolve_archive_dir(here, tag)
    config.trainedModel_path = config.model_path / "best_models"
    config.intermediateModel_path = config.model_path / "intermediate_models"
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / "TBruns")

    settings = config.model_path / "model_settings.txt"
    settings.write_text(
        "\n".join([
            "runner: run_kan_rbf_umax.py",
            "claim_class: tooling-only",
            "representation: Gaussian-edge KAN for u,v; anisotropic spatial Gaussian RBF for alpha",
            f"umax: {args.umax}",
            f"n_cycles: {args.n_cycles}",
            "loading: five-substep 0.25,0.50,0.75,1.00,unload",
            f"epochs_per_solve_cap: {args.epochs}",
            f"mesh: {args.mesh_file}",
            "first_detect_is_separate_from_confirmation: true",
            "purpose: finite forward/spatial-gradient/backprop/archive micro-test only",
        ]) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("KAN displacement + RBF phase-field tooling micro-test")
    print(f"Umax={args.umax} cycles={args.n_cycles} epochs={args.epochs}")
    print(f"archive={config.model_path}")
    print(f"device={config.device}")
    print("=" * 72)
    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
