#!/usr/bin/env python3
"""Restart PIDL fatigue evolution from a mapped FEM state.

The runner seeds the post-pretraining PIDL histories from a selected FEM cycle:

* FEM d_elem -> nodal hist_alpha floor (element-to-node max projection)
* FEM alpha_bar_elem -> PIDL element hist_fat
* FEM g(d_elem) * psi_plus_elem -> PIDL psi_plus_prev

It then solves the following peak-only PIDL steps without any further FEM oracle.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import torch


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


def _element_centroids(inp_np: np.ndarray, conn_np: np.ndarray) -> np.ndarray:
    cx = (
        inp_np[conn_np[:, 0], 0]
        + inp_np[conn_np[:, 1], 0]
        + inp_np[conn_np[:, 2], 0]
    ) / 3.0
    cy = (
        inp_np[conn_np[:, 0], 1]
        + inp_np[conn_np[:, 1], 1]
        + inp_np[conn_np[:, 2], 1]
    ) / 3.0
    return np.stack([cx, cy], axis=1)


def _element_to_node_max(elem_values: torch.Tensor,
                         T_conn: torch.Tensor,
                         n_nodes: int) -> torch.Tensor:
    conn = T_conn.to(device=elem_values.device, dtype=torch.long)
    flat_nodes = conn.reshape(-1)
    flat_vals = elem_values.reshape(-1).repeat_interleave(conn.shape[1])
    out = torch.full(
        (n_nodes,), -torch.inf, dtype=elem_values.dtype, device=elem_values.device
    )
    out.scatter_reduce_(0, flat_nodes, flat_vals, reduce="amax", include_self=True)
    return torch.where(torch.isfinite(out), out, torch.zeros_like(out))


def _tip_x_from_elem(alpha_elem: torch.Tensor,
                     pidl_centroids: np.ndarray,
                     threshold: float) -> float:
    alpha_np = alpha_elem.detach().cpu().numpy().reshape(-1)
    mask = alpha_np >= float(threshold)
    if not np.any(mask):
        return float("nan")
    return float(np.max(pidl_centroids[mask, 0]) + 0.5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--restart-fem-cycle", type=int, required=True)
    parser.add_argument("--end-fem-cycle", type=int, default=72)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument(
        "--coarse-mesh-file",
        default=None,
        help="Pretraining mesh; defaults to the same FEM-aligned mesh.",
    )
    parser.add_argument("--fem-data-dir", required=True)
    parser.add_argument("--tag", default="")
    parser.add_argument("--fracture-confirm-cycles", type=int, default=3)
    parser.add_argument("--plot-every", type=int, default=1)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if args.end_fem_cycle <= args.restart_fem_cycle:
        raise ValueError("--end-fem-cycle must be greater than --restart-fem-cycle")

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433
    from construct_model import construct_model  # noqa: WPS433
    from fem_supervision import FEMSupervision  # noqa: WPS433
    from input_data_from_mesh import prep_input_data  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(
        here, args.coarse_mesh_file or fem_mesh
    )
    fem_data_dir = Path(args.fem_data_dir).expanduser().resolve()
    n_steps = int(args.end_fem_cycle - args.restart_fem_cycle)
    local_steps = list(range(n_steps))

    # Keep the aligned baseline physics; only the initial histories are replaced.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
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

    for key in (
        "fem_oracle",
        "history_increment_oracle",
        "alpha_feedback_oracle",
        "hist_alpha_oracle",
        "g_stiffness_oracle",
        "alpha_bar_state_oracle",
        "f_fatigue_oracle",
    ):
        config.fatigue_dict[key] = {"enable": False}

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    config.fatigue_dict["accum_type"] = "carrara"
    config.fatigue_dict["degrad_type"] = "asymptotic"
    config.fatigue_dict["alpha_T"] = 0.5
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = n_steps
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["R_ratio"] = 0.0
    config.fatigue_dict["enable_E_fallback"] = False
    config.fatigue_dict["history_driver_mode"] = "current_active"
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["log_every_n_cycles"] = 1
    config.fatigue_dict.pop("explicit_cycle_substeps", None)
    config.fatigue_dict.pop("explicit_cycle_factors", None)
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": local_steps,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics_fem_state_restart",
    }
    config.fatigue_dict["gradient_diagnostics"] = {
        "enable": True,
        "cycles": local_steps,
        "every_n_cycles": 1,
        "dense_sampling": True,
        "on_fracture": True,
    }
    config.disp_cyclic = np.ones(n_steps, dtype=float) * float(args.umax)

    fem_sup = FEMSupervision(umax=float(args.umax), fem_dir=fem_data_dir)
    if args.restart_fem_cycle not in fem_sup.cycles:
        raise ValueError(
            f"FEM restart cycle c{args.restart_fem_cycle} is unavailable; "
            f"available range is c{fem_sup.cycles[0]}-c{fem_sup.cycles[-1]}"
        )

    pffmodel, matprop, _ = construct_model(
        config.PFF_model_dict,
        config.mat_prop_dict,
        config.network_dict,
        config.domain_extrema,
        config.device,
        williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict,
    )
    inp_cent, T_conn_cent, _, _ = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        config.numr_dict,
        mesh_file=config.fine_mesh_file,
        device=config.device,
    )
    inp_np = inp_cent.detach().cpu().numpy()
    T_np = (
        T_conn_cent.detach().cpu().numpy()
        if torch.is_tensor(T_conn_cent)
        else T_conn_cent
    )
    pidl_centroids = _element_centroids(inp_np, T_np)

    alpha_elem0 = fem_sup.alpha_target_at_cycle(
        args.restart_fem_cycle, pidl_centroids,
        device=config.device, dtype=torch.float32,
    ).detach()
    hist_alpha_node0 = _element_to_node_max(
        alpha_elem0, T_conn_cent, int(inp_cent.shape[0])
    ).detach()
    hist_fat_elem0 = fem_sup.alpha_bar_target_at_cycle(
        args.restart_fem_cycle, pidl_centroids,
        device=config.device, dtype=torch.float32,
    ).detach()
    psi_prev_elem0 = fem_sup.active_target_at_cycle(
        args.restart_fem_cycle,
        pidl_centroids,
        residual_stiffness=float(getattr(pffmodel, "residual_stiffness", 0.0)),
        device=config.device,
        dtype=torch.float32,
    ).detach()
    f_fatigue_elem0 = fem_sup.f_fatigue_target_at_cycle(
        args.restart_fem_cycle, pidl_centroids,
        device=config.device, dtype=torch.float32,
    ).detach()

    config.fatigue_dict["initial_state_oracle"] = {
        "enable": True,
        "fem_cycle": int(args.restart_fem_cycle),
        "hist_alpha": hist_alpha_node0,
        "hist_fat": hist_fat_elem0,
        "hist_fat_policy": "replace",
        "psi_plus_prev": psi_prev_elem0,
        "f_fatigue": f_fatigue_elem0,
    }

    fat = config.fatigue_dict
    mesh_tag = _mesh_tag(fem_mesh, args.tag or "fem_state_restart")
    dir_name = (
        f"fem_state_restart_c{args.restart_fem_cycle}_to_c{args.end_fem_cycle}"
        f"_hl{config.network_dict['hidden_layers']}"
        f"_n{config.network_dict['neurons']}"
        f"_seed{config.network_dict['seed']}"
        f"_{config.PFF_model_dict['PFF_model']}"
        f"_{config.numr_dict['gradient_type']}"
        f"_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}"
        f"_Nstep{n_steps}"
        f"_U{fat['disp_max']}"
        f"_{mesh_tag}"
        f"{'_compile' if args.compile else ''}"
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

    np.savez(
        config.model_path / "fem_restart_seed_fields.npz",
        restart_fem_cycle=np.asarray([args.restart_fem_cycle], dtype=np.int32),
        end_fem_cycle=np.asarray([args.end_fem_cycle], dtype=np.int32),
        local_step=np.asarray(local_steps, dtype=np.int32),
        mapped_fem_cycle=np.asarray(
            [args.restart_fem_cycle + j + 1 for j in local_steps],
            dtype=np.int32,
        ),
        pidl_centroids=pidl_centroids.astype(np.float32),
        fem_alpha_elem=alpha_elem0.detach().cpu().numpy().astype(np.float32),
        hist_alpha_node=hist_alpha_node0.detach().cpu().numpy().astype(np.float32),
        hist_fat_elem=hist_fat_elem0.detach().cpu().numpy().astype(np.float32),
        psi_plus_prev_elem=psi_prev_elem0.detach().cpu().numpy().astype(np.float32),
        f_fatigue_elem=f_fatigue_elem0.detach().cpu().numpy().astype(np.float32),
    )

    seed_tip_d095 = _tip_x_from_elem(alpha_elem0, pidl_centroids, 0.95)
    c_probe = min(args.restart_fem_cycle + 1, fem_sup.cycles[-1])
    alpha_probe_next = fem_sup.alpha_target_at_cycle(c_probe, pidl_centroids)
    next_tip_d095 = _tip_x_from_elem(alpha_probe_next, pidl_centroids, 0.95)

    print("=" * 72)
    print("PIDL FEM-state restart runner")
    print(f"  U_max          = {args.umax} | seed = {args.seed}")
    print(f"  restart FEM    = c{args.restart_fem_cycle}")
    print(f"  solve through  = mapped FEM c{args.end_fem_cycle}")
    print(f"  training steps = {n_steps} | local step 0 maps to FEM c{args.restart_fem_cycle + 1}")
    print(f"  FEM data       = {fem_data_dir}")
    print(f"  FEM cycles     = {fem_sup.cycles[:5]} ... {fem_sup.cycles[-5:]}")
    print(f"  FEM mesh       = {fem_mesh}")
    print(f"  coarse mesh    = {coarse_mesh}")
    print(f"  seed d095 tip  = {seed_tip_d095:.6f}")
    print(f"  next FEM d095  = c{c_probe}: {next_tip_d095:.6f}")
    print(f"  seed alpha max = {alpha_elem0.max().item():.6e}")
    print(f"  seed hist max  = {hist_fat_elem0.max().item():.6e}")
    print(f"  seed f min     = {f_fatigue_elem0.min().item():.6e}")
    print(f"  seed active max= {psi_prev_elem0.max().item():.6e}")
    print(f"  elem diag      = {local_steps}")
    print(f"  device         = {config.device}")
    print(f"  archive        = {dir_name}")
    print(f"  full path      = {config.model_path}")
    print("=" * 72)

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as handle:
        handle.write("runner: run_fem_state_restart_umax.py\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"restart_fem_cycle: {args.restart_fem_cycle}\n")
        handle.write(f"end_fem_cycle: {args.end_fem_cycle}\n")
        handle.write(f"n_training_steps: {n_steps}\n")
        handle.write("local_step_to_fem_cycle: fem_cycle = restart_fem_cycle + local_step + 1\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"fem_data_dir: {fem_data_dir}\n")
        handle.write(f"fem_cycles_available: {fem_sup.cycles}\n")
        handle.write(f"mesh_tag: {mesh_tag}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        handle.write("history_driver_mode: current_active\n")
        handle.write("hist_alpha_update: max(previous,current)\n")
        handle.write("initial_state_oracle_enable: True\n")
        handle.write("initial_hist_alpha: FEM d_elem projected element-to-node max\n")
        handle.write("initial_hist_fat: FEM alpha_bar_elem replace\n")
        handle.write("initial_psi_plus_prev: FEM g(d_elem)*psi_plus_elem\n")
        handle.write("initial_f_fatigue: FEM f_fatigue_elem for first restarted solve\n")
        handle.write(f"initial_seed_tip_x_d095: {seed_tip_d095}\n")
        handle.write(f"tol_ir: {config.PFF_model_dict['tol_ir']}\n")
        handle.write(f"alpha_constraint: {config.numr_dict['alpha_constraint']}\n")
        handle.write(f"residual_stiffness_eta: {config.PFF_model_dict.get('residual_stiffness', 0.0)}\n")
        handle.write(f"exact_bc_enable: {config.exact_bc_dict.get('enable', False)}\n")
        handle.write(f"fracture_confirm_cycles: {fat['fracture_confirm_cycles']}\n")
        handle.write(f"element_diagnostics_steps: {local_steps}\n")
        handle.write("purpose: FEM-state restart discriminator for path-history vs one-step solver error\n")

    main_path = here / "main.py"
    exec(
        compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
        {"__name__": "__main__", "__file__": str(main_path)},
    )


if __name__ == "__main__":
    main()
