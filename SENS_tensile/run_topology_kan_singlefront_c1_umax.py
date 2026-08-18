#!/usr/bin/env python3
"""U0.12 c1 gate for topology-aware KAN plus single-front phase corridor."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float, nargs="?", default=0.12)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=10000)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--tag", default="topologyKAN_singleFrontRBF_c1_gate_v1")
    parser.add_argument(
        "--pretrain-mode",
        choices=("default", "off"),
        default="default",
        help="Use the legacy coarse-mesh pretraining or start from seeded initialization.",
    )
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if args.epochs < 1:
        raise ValueError("epochs must be >= 1")

    sys.argv = ["main.py", "1", "64", str(args.seed), "TrainableTanh", "1.0"]
    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    model_cfg = {
        "kan_width": 64,
        "kan_basis": 15,
        "topology_eps_y": 0.02,
        "topology_eps_x": 0.04,
        "initial_tip_x": 0.0,
        "front_centres": 81,
        "front_width": 0.025,
        "corridor_sigma_y": 0.02,
        "phase_bias": -2.0,
        "phase_weight_init": -4.0,
    }
    config.network_dict.update({
        "model_type": "topology_kan_singlefront_rbf",
        "hidden_layers": 1,
        "neurons": 64,
        "activation": "TrainableTanh",
        "init_coeff": 1.0,
        "compile": False,
        "topology_kan_singlefront_rbf": model_cfg,
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
    config.training_dict["pretrain"] = {"mode": args.pretrain_mode}

    factors = np.asarray([0.25, 0.50, 0.75, 1.00, 0.00], dtype=float)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = 1
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = 5
    config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
    config.fatigue_dict["fracture_confirm_cycles"] = 3
    config.fatigue_dict["plot_every_n_cycles"] = 1
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": [0, 1, 2, 3, 4],
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics",
    }
    config.disp_cyclic = factors * float(args.umax)

    tag = (
        f"topologyKAN_singleFrontRBF_Umax{args.umax}_c1_seed{args.seed}"
        f"_ep{args.epochs}_pretrain-{args.pretrain_mode}_{args.tag}"
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
            "runner: run_topology_kan_singlefront_c1_umax.py",
            "claim_class: field-mechanism-discriminator-quarantine",
            "one_factor_change: topology coordinates plus monotone single-front phase corridor",
            f"umax: {args.umax}",
            "n_cycles_physical: 1",
            "n_training_steps: 5",
            "loading: five-substep 0.25,0.50,0.75,1.00,unload",
            f"epochs_per_solve_cap: {args.epochs}",
            f"pretrain_mode: {args.pretrain_mode}",
            "early_stopping_rel_tol: 5e-7",
            f"mesh: {args.mesh_file}",
            f"architecture: {model_cfg}",
            "gate: improve c1/s4 displacement, damage RMSE, and high-damage support versus compact KAN-RBF",
            "external_gpt_pro_review: approved exactly one pretrain-off c1 discriminator; no rescue sweep or lifetime escalation",
        ]) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("Topology-KAN + single-front RBF c1 field gate")
    print(f"Umax={args.umax} epochs={args.epochs} pretrain_mode={args.pretrain_mode}")
    print(f"archive={config.model_path}")
    print(f"device={config.device}")
    print("claim_class=field-mechanism-discriminator-quarantine")
    print("=" * 72)
    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
