#!/usr/bin/env python3
"""Producer-scale Umax run with KAN displacement and RBF phase field.

This is the equal-formulation follow-up to ``run_kan_rbf_umax.py``.  It keeps
the exact compact representation used by the c1 micro diagnostic, but restores
the production optimizer cap and runs the full Hard-5 five-substep schedule.
The result remains quarantined until the predeclared FEM/MLP gates are applied.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


def _capture_steps(n_cycles: int) -> list[int]:
    """Return selected zero-based peak/unload training steps."""
    physical_cycles = (1, 3, 5, 10, 20, 40, 60, 80, 100, 120)
    steps: list[int] = []
    for cycle in physical_cycles:
        if cycle <= n_cycles:
            base = 5 * (cycle - 1)
            steps.extend((base + 3, base + 4))
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float, nargs="?", default=0.12)
    parser.add_argument("--n-cycles", type=int, default=120)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=10000)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--tag", default="kanUV_rbfAlpha_fiveStep_production_v1")
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if args.n_cycles < 1:
        raise ValueError("n_cycles must be >= 1")
    if args.epochs < 1:
        raise ValueError("epochs must be >= 1")

    sys.argv = ["main.py", "1", "32", str(args.seed), "TrainableTanh", "1.0"]
    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    # Freeze the representation from the c1 micro diagnostic.  The production
    # discriminator changes only optimizer budget, trajectory length and output
    # retention, so a pass/fail has one clear interpretation.
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

    factors = np.asarray([0.25, 0.50, 0.75, 1.00, 0.00], dtype=float)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(factors))
    config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
    config.fatigue_dict["fracture_confirm_cycles"] = 3
    config.fatigue_dict["plot_every_n_cycles"] = 100
    capture_steps = _capture_steps(int(args.n_cycles))
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": capture_steps,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics",
    }
    config.disp_cyclic = np.tile(factors * float(args.umax), int(args.n_cycles))

    tag = (
        f"kanUV_rbfAlpha_Umax{args.umax}_Nphys{args.n_cycles}_Nstep{5 * args.n_cycles}"
        f"_seed{args.seed}_ep{args.epochs}_{args.tag}"
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
            "runner: run_kan_rbf_production_umax.py",
            "claim_class: producer-discriminator-quarantine",
            "representation: frozen micro KAN(u,v) plus anisotropic Gaussian RBF(alpha)",
            "representation_parameter_count: 1468",
            f"umax: {args.umax}",
            f"n_cycles_physical: {args.n_cycles}",
            f"n_training_steps_max: {5 * args.n_cycles}",
            "loading: five-substep 0.25,0.50,0.75,1.00,unload",
            f"epochs_per_solve_cap: {args.epochs}",
            "early_stopping_rel_tol: 5e-7",
            f"mesh: {args.mesh_file}",
            f"diagnostic_steps: {capture_steps}",
            "first_detect_is_separate_from_confirmation: true",
            "promotion_gate: c1 same-state fields then first_detect and trajectory",
            "external_architecture_review: unavailable; quarantine remains active",
        ]) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("KAN displacement + RBF phase-field producer discriminator")
    print(f"Umax={args.umax} physical_cycles={args.n_cycles} epochs={args.epochs}")
    print(f"archive={config.model_path}")
    print(f"device={config.device}")
    print("claim_class=producer-discriminator-quarantine")
    print("=" * 72)
    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
