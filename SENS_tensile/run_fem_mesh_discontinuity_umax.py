#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with one discontinuity representation enabled."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _resolve_mesh_file(here: Path, filename: str) -> str:
    path = Path(filename).expanduser()
    if path.is_absolute():
        return str(path)
    local = here / path
    if local.exists():
        return str(local)
    for parent in here.parents:
        candidate = parent / "SENS_tensile" / path
        if candidate.exists():
            return str(candidate)
    return filename


def _mesh_tag(mesh_file: str, explicit: str) -> str:
    if explicit:
        return explicit.strip().replace(" ", "_")
    stem = Path(mesh_file).stem
    return stem.removeprefix("meshed_geom_").replace(" ", "_")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--variant", required=True,
                   choices=("sdf_ribbon_uv_only", "xfem_jump_uv_only"))
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--tag", default="")
    p.add_argument("--epsilon", type=float, default=1e-3)
    p.add_argument("--x-tip", type=float, default=0.0)
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--jump-hidden-layers", type=int, default=4)
    p.add_argument("--jump-neurons", type=int, default=100)
    p.add_argument("--jump-activation", default="TrainableReLU")
    p.add_argument("--heaviside-kind", default="soft", choices=("soft", "hard"))
    p.add_argument("--diagnostic-cycles", default="0,1,2,3,20,40,69,80,99",
                   help="Cycles for state/gradient export.")
    p.add_argument("--no-field-files", action="store_true",
                   help="Write state-timing summary only, not per-cycle npz fields.")
    p.add_argument("--no-gradient-balance", action="store_true",
                   help="Disable routine E_el/E_d/E_hist head-wise gradient reporting.")
    p.add_argument("--compile", action="store_true")
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, config.coarse_mesh_file)

    # Strict benchmark controls: only the discontinuity representation changes.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.local_patch_dict["enable"] = False
    config.fatigue_dict.setdefault("local_patch_training", {})["enable"] = False
    config.fatigue_dict.setdefault("staged_head_training", {})["enable"] = False
    config.fatigue_dict.setdefault("staged_alpha", {})["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    if hasattr(config, "adaptive_sampling_dict"):
        config.adaptive_sampling_dict["enable"] = False
    if hasattr(config, "sidecar_S1_dict"):
        config.sidecar_S1_dict["enable"] = False
    if hasattr(config, "sidecar_S2_dict"):
        config.sidecar_S2_dict["enable"] = False
    if hasattr(config, "tip_local_net_dict"):
        config.tip_local_net_dict["enable"] = False
    config.symmetry_prior = False

    config.discontinuity_dict.update({
        "enable": True,
        "kind": args.variant,
        "x_tip": float(args.x_tip),
        "y_tip": 0.0,
        "epsilon": float(args.epsilon),
        "heaviside_kind": args.heaviside_kind,
        "jump_hidden_layers": int(args.jump_hidden_layers),
        "jump_neurons": int(args.jump_neurons),
        "jump_activation": args.jump_activation,
        "jump_relative_input": True,
    })

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["state_timing_export"] = {
        "enable": True,
        "cycles": args.diagnostic_cycles,
        "write_fields": not bool(args.no_field_files),
        "dir": "pidl_state_timing",
    }
    config.fatigue_dict["gradient_balance_probe"] = {
        "enable": not bool(args.no_gradient_balance),
        "cycles": args.diagnostic_cycles,
        "dir": "gradient_balance",
    }
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    mesh_tag = _mesh_tag(fem_mesh, args.tag)
    eps_tag = f"{args.epsilon:.0e}".replace("+", "")
    suffix = (
        f"_femmesh_{mesh_tag}_{args.variant}_eps{eps_tag}"
        f"{'_compile' if args.compile else ''}"
    )
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + suffix
    )
    config.model_path = config.resolve_archive_dir(here, dir_name)
    config.trainedModel_path = config.model_path / Path("best_models/")
    config.intermediateModel_path = config.model_path / Path("intermediate_models/")
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as f:
        f.write("runner: run_fem_mesh_discontinuity_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {mesh_tag}\n")
        f.write(f"torch_compile: {bool(args.compile)}\n")
        f.write(f"discontinuity_enable: {config.discontinuity_dict['enable']}\n")
        f.write(f"discontinuity_kind: {config.discontinuity_dict['kind']}\n")
        f.write(f"discontinuity_x_tip: {config.discontinuity_dict['x_tip']}\n")
        f.write(f"discontinuity_y_tip: {config.discontinuity_dict['y_tip']}\n")
        f.write(f"discontinuity_epsilon: {config.discontinuity_dict['epsilon']}\n")
        f.write(f"discontinuity_heaviside_kind: {config.discontinuity_dict['heaviside_kind']}\n")
        f.write(f"discontinuity_jump_hidden_layers: {config.discontinuity_dict['jump_hidden_layers']}\n")
        f.write(f"discontinuity_jump_neurons: {config.discontinuity_dict['jump_neurons']}\n")
        f.write(f"discontinuity_jump_activation: {config.discontinuity_dict['jump_activation']}\n")
        f.write(f"discontinuity_jump_relative_input: {config.discontinuity_dict['jump_relative_input']}\n")
        f.write(f"diagnostic_cycles: {args.diagnostic_cycles}\n")
        f.write(f"gradient_balance: {not bool(args.no_gradient_balance)}\n")
        f.write("purpose: strict FEM-mesh discontinuity-representation discriminator\n")

    print("=" * 72)
    print("PIDL FEM-mesh discontinuity runner")
    print(f"  variant     = {args.variant}")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  epsilon     = {args.epsilon} | x_tip = {args.x_tip}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  diagnostics= {args.diagnostic_cycles} | gradient={not bool(args.no_gradient_balance)}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
