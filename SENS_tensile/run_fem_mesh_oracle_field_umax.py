#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with FEM-projected oracle history inputs.

Modes:

raw_pidl_g
    Project FEM raw psi_plus onto PIDL elements, then multiply by PIDL's
    current g(alpha). Tests whether FEM strain-energy localization closes the
    history gap when PIDL damage is still used in the active driver.

active_fem
    Project FEM g(alpha_FEM) * psi_plus_raw directly. Tests whether the exact
    FEM active process-zone driver is sufficient.

delta_alpha_bar
    Project FEM cycle-wise Delta alpha_bar and inject it into the accumulator
    at the peak substep. Tests whether correct history placement is sufficient.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DEFAULT_STANDARD_FEM_DIR = (
    PROJECT_ROOT
    / "Alignment check 2"
    / "FEM cyclic 012"
    / "cases"
    / "standard"
    / "raw_data"
)


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


def _parse_factors(raw: str) -> list[float]:
    vals = [float(x) for x in raw.split(",") if x.strip()]
    if len(vals) < 2:
        raise argparse.ArgumentTypeError("need at least two substep factors")
    return vals


def _parse_cycles(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip()]


def _diag_steps(physical_cycles: list[int], n_substeps: int) -> list[int]:
    steps = {0}
    for cyc in physical_cycles:
        if cyc < 1:
            continue
        base = (cyc - 1) * n_substeps
        steps.add(base + n_substeps - 2)
        steps.add(base + n_substeps - 1)
    return sorted(steps)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument(
        "--oracle-kind",
        choices=("raw_pidl_g", "active_fem", "delta_alpha_bar"),
        required=True,
    )
    parser.add_argument("--n-cycles-physical", "--n-cycles", dest="n_cycles_physical",
                        type=int, default=80)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--coarse-mesh-file", default=None)
    parser.add_argument("--fem-data-dir", default=os.environ.get(
        "FEM_DATA_DIR", str(DEFAULT_STANDARD_FEM_DIR)))
    parser.add_argument("--tag", default="")
    parser.add_argument("--substeps", type=_parse_factors,
                        default=_parse_factors("0.25,0.5,0.75,1,0"))
    parser.add_argument("--diag-physical-cycles", default="1,2,3,20,40,60,69")
    parser.add_argument("--zone-radius", type=float, default=None,
                        help="If set, override only r <= zone-radius around the initial tip.")
    parser.add_argument("--fracture-confirm-cycles", type=int, default=3)
    parser.add_argument("--plot-every", type=int, default=20)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    os.chdir(HERE)
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "source"))

    import torch  # noqa: WPS433
    import config  # noqa: WPS433
    from construct_model import construct_model  # noqa: WPS433
    from fem_supervision import FEMSupervision  # noqa: WPS433
    from input_data_from_mesh import prep_input_data  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(HERE, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(HERE, args.coarse_mesh_file or config.coarse_mesh_file)
    fem_data_dir = Path(args.fem_data_dir).expanduser()

    # Strict benchmark controls: isolate only the oracle history input.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.fatigue_dict["void_notch_mask"]["enable"] = False
    config.fatigue_dict["history_driver_reduction"] = {"enable": False}
    config.fatigue_dict["fem_oracle"] = {"enable": False}
    config.fatigue_dict["history_increment_oracle"] = {"enable": False}
    if hasattr(config, "adaptive_sampling_dict"):
        config.adaptive_sampling_dict["enable"] = False
    if hasattr(config, "sidecar_S1_dict"):
        config.sidecar_S1_dict["enable"] = False
    if hasattr(config, "sidecar_S2_dict"):
        config.sidecar_S2_dict["enable"] = False
    if hasattr(config, "tip_local_net_dict"):
        config.tip_local_net_dict["enable"] = False
    config.symmetry_prior = False

    factors = np.asarray(args.substeps, dtype=float)
    disp_steps = np.tile(factors * float(args.umax), int(args.n_cycles_physical))
    total_steps = int(len(disp_steps))
    peak_substep_index = int(np.argmax(factors))
    diag_steps = _diag_steps(_parse_cycles(args.diag_physical_cycles), len(factors))

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    config.fatigue_dict["accum_type"] = "carrara"
    config.fatigue_dict["degrad_type"] = "asymptotic"
    config.fatigue_dict["alpha_T"] = 0.5
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles_physical)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["R_ratio"] = 0.0
    config.fatigue_dict["enable_E_fallback"] = False
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(factors))
    config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
    config.fatigue_dict["history_driver_mode"] = "current_active"
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": f"element_diagnostics_oracle_{args.oracle_kind}",
    }
    config.fatigue_dict["gradient_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": 1,
        "dense_sampling": True,
        "on_fracture": True,
    }
    config.disp_cyclic = disp_steps

    fem_sup = FEMSupervision(umax=float(args.umax), fem_dir=fem_data_dir)

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
        config.domain_extrema, config.device, williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict,
    )
    inp_cent, T_conn_cent, _, _ = prep_input_data(
        matprop, pffmodel, config.crack_dict, config.numr_dict,
        mesh_file=config.fine_mesh_file, device=config.device,
    )
    inp_np = inp_cent.detach().cpu().numpy()
    T_np = (
        T_conn_cent.detach().cpu().numpy()
        if torch.is_tensor(T_conn_cent)
        else T_conn_cent
    )
    cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
    cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
    pidl_centroids = np.stack([cx, cy], axis=1)
    if args.zone_radius is None:
        override_mask_np = np.ones(len(pidl_centroids), dtype=bool)
        mask_tag = "full"
    else:
        override_mask_np = np.sqrt(cx ** 2 + cy ** 2) <= float(args.zone_radius)
        mask_tag = f"zone{args.zone_radius:g}"
    override_mask = torch.from_numpy(override_mask_np).to(config.device)

    oracle_cycle_cfg = {
        "cycle_mode": "explicit_cycle_peak_scaled",
        "explicit_cycle_substeps": int(len(factors)),
        "explicit_cycle_factors": [float(x) for x in factors],
        "peak_substep_index": peak_substep_index,
        "cycle_start": 1,
        "load_factor_power": 2.0,
    }
    if args.oracle_kind == "raw_pidl_g":
        config.fatigue_dict["fem_oracle"] = {
            "enable": True,
            "fem_sup": fem_sup,
            "pidl_centroids": pidl_centroids,
            "override_mask": override_mask,
            "target_kind": "raw",
            "apply_g": True,
            **oracle_cycle_cfg,
        }
    elif args.oracle_kind == "active_fem":
        config.fatigue_dict["fem_oracle"] = {
            "enable": True,
            "fem_sup": fem_sup,
            "pidl_centroids": pidl_centroids,
            "override_mask": override_mask,
            "target_kind": "active",
            "apply_g": False,
            "fem_residual_stiffness": float(getattr(pffmodel, "residual_stiffness", 0.0)),
            **oracle_cycle_cfg,
        }
    elif args.oracle_kind == "delta_alpha_bar":
        config.fatigue_dict["history_increment_oracle"] = {
            "enable": True,
            "fem_sup": fem_sup,
            "pidl_centroids": pidl_centroids,
            "override_mask": override_mask,
            "mode": "cycle_delta_at_peak",
            "initial_zero": True,
            **oracle_cycle_cfg,
        }

    fat = config.fatigue_dict
    mesh_tag = _mesh_tag(fem_mesh, args.tag or f"oracle_{args.oracle_kind}")
    sub_tag = "-".join(f"{x:g}" for x in factors)
    dir_name = (
        f"oracle_{args.oracle_kind}_hl{config.network_dict['hidden_layers']}"
        f"_n{config.network_dict['neurons']}"
        f"_seed{config.network_dict['seed']}"
        f"_{config.PFF_model_dict['PFF_model']}"
        f"_{config.numr_dict['gradient_type']}"
        f"_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}"
        f"_Ncyc{fat['n_cycles']}_Nstep{total_steps}"
        f"_U{fat['disp_max']}"
        f"_{mesh_tag}_{mask_tag}"
        f"_s{sub_tag}"
        f"{'_compile' if args.compile else ''}"
    )
    config.model_path = config.resolve_archive_dir(HERE, dir_name)
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

    c_probe = 69 if 69 in fem_sup.cycles else fem_sup.cycles[-1]
    raw_probe = fem_sup.psi_target_at_cycle(c_probe, pidl_centroids)
    print("=" * 72)
    print("PIDL FEM-mesh FEM-oracle history-input discriminator")
    print(f"  oracle kind    = {args.oracle_kind}")
    print(f"  U_max          = {args.umax} | physical cycles = {args.n_cycles_physical}")
    print(f"  training steps = {total_steps} | seed = {args.seed}")
    print(f"  substeps       = {list(factors)} | peak substep = {peak_substep_index}")
    print(f"  FEM data       = {fem_data_dir}")
    print(f"  FEM cycles     = {fem_sup.cycles[:5]} ... {fem_sup.cycles[-5:]}")
    print(f"  FEM mesh       = {fem_mesh}")
    print(f"  override mask  = {mask_tag} ({int(override_mask_np.sum())}/{len(override_mask_np)} elems)")
    print(f"  FEM raw c{c_probe} max = {raw_probe.max().item():.3e}")
    if args.oracle_kind == "active_fem":
        active_probe = fem_sup.active_target_at_cycle(c_probe, pidl_centroids)
        print(f"  FEM active c{c_probe} max = {active_probe.max().item():.3e}")
    if args.oracle_kind == "delta_alpha_bar":
        delta_probe = fem_sup.alpha_bar_delta_target_at_cycle(c_probe, pidl_centroids)
        print(f"  FEM Delta alpha_bar c{c_probe} max = {delta_probe.max().item():.3e}")
    print(f"  elem diag      = {diag_steps}")
    print("  gradient diag  = pre-history-refresh every step")
    print(f"  device         = {config.device}")
    print(f"  archive        = {dir_name}")
    print(f"  full path      = {config.model_path}")
    print("=" * 72)

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as handle:
        handle.write("runner: run_fem_mesh_oracle_field_umax.py\n")
        handle.write(f"oracle_kind: {args.oracle_kind}\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"n_cycles_physical: {args.n_cycles_physical}\n")
        handle.write(f"n_training_steps: {total_steps}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"fem_data_dir: {fem_data_dir}\n")
        handle.write(f"fem_cycles_available: {fem_sup.cycles}\n")
        handle.write(f"mesh_tag: {mesh_tag}\n")
        handle.write(f"override_mask: {mask_tag}\n")
        handle.write(f"override_mask_count: {int(override_mask_np.sum())}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        handle.write("history_driver_mode: current_active\n")
        handle.write(f"fem_oracle_enable: {fat.get('fem_oracle', {}).get('enable', False)}\n")
        handle.write(
            f"fem_oracle_target_kind: "
            f"{fat.get('fem_oracle', {}).get('target_kind', 'none')}\n"
        )
        handle.write(
            f"fem_oracle_apply_g: "
            f"{fat.get('fem_oracle', {}).get('apply_g', 'none')}\n"
        )
        handle.write(
            f"history_increment_oracle_enable: "
            f"{fat.get('history_increment_oracle', {}).get('enable', False)}\n"
        )
        handle.write(
            f"history_increment_oracle_mode: "
            f"{fat.get('history_increment_oracle', {}).get('mode', 'none')}\n"
        )
        handle.write(f"explicit_cycle_substeps: {fat['explicit_cycle_substeps']}\n")
        handle.write(f"explicit_cycle_factors: {fat['explicit_cycle_factors']}\n")
        handle.write(f"peak_substep_index: {peak_substep_index}\n")
        handle.write(f"element_diagnostics_steps: {diag_steps}\n")
        handle.write("element_diagnostics_fields: mechanics+energy+driver+delta_alpha_bar_input\n")
        handle.write(
            "state_mapping: cN_peak -> PIDL step 5*(N-1)+3 for default substeps\n"
        )

    main_path = HERE / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
