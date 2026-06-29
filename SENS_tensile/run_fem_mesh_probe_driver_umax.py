#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with opt-in fatigue-driver reduction.

By default this discriminator keeps the variational energy/objective unchanged:
only the post-fit fatigue-history driver changes from

    g(mean(alpha_nodes)) * psi_raw_elem

to either the archived probe rule or the FEM-like tri3 quadrature rule,

    mean_q[g(alpha_q)] * psi_raw_elem

where alpha_q is evaluated at three triangle points.  With
``--fem-irr-penalty`` the irreversibility penalty also moves from
``ReLU(-mean(delta_alpha_nodes))^2`` to local quadrature
``mean_q(ReLU(-delta_alpha_q)^2)``.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


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


def _parse_float_csv(raw: str) -> list[float]:
    vals = [float(x) for x in raw.split(",") if x.strip()]
    if len(vals) < 2:
        raise argparse.ArgumentTypeError("need at least two comma-separated values")
    return vals


def _parse_cycles(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip()]


def _peak_substep_index(values: np.ndarray) -> int:
    return int(np.argmax(np.asarray(values, dtype=float)))


def _diag_steps(
    physical_cycles: list[int],
    n_substeps: int,
    *,
    peak_substep: int,
    unload_substep: int,
    step_offset: int = 0,
    full_physical_cycles: list[int] | None = None,
) -> list[int]:
    steps = {0}
    full_cycles = {int(c) for c in (full_physical_cycles or []) if int(c) >= 1}
    for cyc in physical_cycles:
        if cyc < 1:
            continue
        base = int(step_offset) + (cyc - 1) * n_substeps
        if cyc in full_cycles:
            steps.update(base + i for i in range(n_substeps))
        else:
            steps.add(base + int(peak_substep))
            steps.add(base + int(unload_substep))
    return sorted(steps)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--n-cycles-physical", "--n-cycles", dest="n_cycles_physical",
                        type=int, default=120)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--coarse-mesh-file", default=None)
    parser.add_argument("--tag", default="probeDriver_softHist0_stateTiming")
    parser.add_argument("--hidden-layers", type=int, default=8)
    parser.add_argument("--neurons", type=int, default=400)
    parser.add_argument("--init-coeff", default="1.0")
    parser.add_argument("--epochs-rprop", type=int, default=None,
                        help="Override config.optimizer_dict['n_epochs_RPROP'] for smoke runs.")
    parser.add_argument("--epochs-lbfgs", type=int, default=None,
                        help="Override config.optimizer_dict['n_epochs_LBFGS'] for smoke runs.")
    parser.add_argument("--optim-rel-tol", type=float, default=None,
                        help="Override main/pretrain early-stopping relative tolerance.")
    parser.add_argument("--substeps", type=_parse_float_csv,
                        default=_parse_float_csv("0.25,0.5,0.75,1,0"),
                        help=("Legacy per-cycle displacement factors multiplied "
                              "by positional umax. Prefer --displacement-steps "
                              "for FEM/PIDL alignment protocols."))
    parser.add_argument("--displacement-steps", type=_parse_float_csv, default=None,
                        help=("Absolute per-cycle displacement values. When set, "
                              "these values are used directly and --substeps is "
                              "ignored except for backwards compatibility."))
    parser.add_argument("--history-driver-reduction-mode",
                        choices=("probe_g_mean", "fem_gp_tri3_g_mean"),
                        default="probe_g_mean")
    parser.add_argument("--fem-irr-penalty", action="store_true",
                        help="Use FEM-like tri3 quadrature for the irreversibility penalty.")
    parser.add_argument("--hard-alpha-recovery-step", action="store_true",
                        help=("Preset the current NN alpha field to a uniform hard "
                              "value, run step 0 at U=0 for recovery, then continue "
                              "the explicit cyclic schedule with histories preserved."))
    parser.add_argument("--hard-alpha-target", type=float, default=1.0,
                        help="Uniform current alpha target for --hard-alpha-recovery-step.")
    parser.add_argument("--diag-physical-cycles", default="1,2,3,20,40,60,69")
    parser.add_argument("--diag-full-physical-cycles", default="",
                        help=("Physical cycles for which all substeps should be "
                              "saved in element diagnostics. Other listed cycles "
                              "save only peak and final unloaded states."))
    parser.add_argument("--fracture-confirm-cycles", type=int, default=3)
    parser.add_argument("--plot-every", type=int, default=20)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = [
        "main.py",
        str(args.hidden_layers),
        str(args.neurons),
        str(args.seed),
        "TrainableReLU",
        str(args.init_coeff),
    ]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, args.coarse_mesh_file or config.coarse_mesh_file)

    # Strict benchmark controls: isolate only the history-driver reduction.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.fatigue_dict["void_notch_mask"]["enable"] = False
    if hasattr(config, "adaptive_sampling_dict"):
        config.adaptive_sampling_dict["enable"] = False
    if hasattr(config, "sidecar_S1_dict"):
        config.sidecar_S1_dict["enable"] = False
    if hasattr(config, "sidecar_S2_dict"):
        config.sidecar_S2_dict["enable"] = False
    if hasattr(config, "tip_local_net_dict"):
        config.tip_local_net_dict["enable"] = False
    config.symmetry_prior = False

    if args.displacement_steps is not None:
        cycle_disp_values = np.asarray(args.displacement_steps, dtype=float)
        if np.any(cycle_disp_values < -1.0e-12):
            raise ValueError("--displacement-steps must be non-negative")
        if not np.isclose(
            float(np.max(cycle_disp_values)),
            float(args.umax),
            rtol=1.0e-6,
            atol=1.0e-12,
        ):
            raise ValueError(
                "positional umax must equal max(--displacement-steps) for "
                "unambiguous displacement-history provenance"
            )
        step_source = "absolute_displacement"
    else:
        factors = np.asarray(args.substeps, dtype=float)
        cycle_disp_values = factors * float(args.umax)
        step_source = "umax_scaled_factors_legacy"
    if len(cycle_disp_values) < 2:
        raise ValueError("need at least two displacement values per cycle")
    if float(args.umax) <= 0.0:
        raise ValueError("umax must be positive")
    derived_factors = cycle_disp_values / float(args.umax)
    cyclic_disp_steps = np.tile(cycle_disp_values, int(args.n_cycles_physical))
    if args.hard_alpha_recovery_step:
        disp_steps = np.concatenate(([0.0], cyclic_disp_steps))
    else:
        disp_steps = cyclic_disp_steps
    total_steps = int(len(disp_steps))
    recovery_step_offset = 1 if args.hard_alpha_recovery_step else 0
    peak_substep = _peak_substep_index(cycle_disp_values)
    unload_substep = int(len(cycle_disp_values) - 1)
    diag_physical_cycles = _parse_cycles(args.diag_physical_cycles)
    diag_full_physical_cycles = _parse_cycles(args.diag_full_physical_cycles)
    diag_steps = _diag_steps(
        diag_physical_cycles,
        len(cycle_disp_values),
        peak_substep=peak_substep,
        unload_substep=unload_substep,
        step_offset=recovery_step_offset,
        full_physical_cycles=diag_full_physical_cycles,
    )

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    if args.epochs_rprop is not None:
        config.optimizer_dict["n_epochs_RPROP"] = int(args.epochs_rprop)
    if args.epochs_lbfgs is not None:
        config.optimizer_dict["n_epochs_LBFGS"] = int(args.epochs_lbfgs)
    if args.optim_rel_tol is not None:
        config.optimizer_dict["optim_rel_tol"] = float(args.optim_rel_tol)
        config.optimizer_dict["optim_rel_tol_pretrain"] = float(args.optim_rel_tol)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles_physical)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(cycle_disp_values))
    config.fatigue_dict["explicit_cycle_step_mode"] = step_source
    config.fatigue_dict["explicit_cycle_displacements"] = [
        float(x) for x in cycle_disp_values
    ]
    # Some legacy oracle helpers accept factors.  Keep them as a derived
    # internal quantity while preserving displacement values as the source.
    config.fatigue_dict["explicit_cycle_factors"] = [
        float(x) for x in derived_factors
    ]
    config.fatigue_dict["history_driver_mode"] = "current_active"
    config.fatigue_dict["history_driver_reduction"] = {
        "enable": True,
        "mode": args.history_driver_reduction_mode,
    }
    config.fatigue_dict["initial_alpha_protocol"] = {
        "enable": bool(args.hard_alpha_recovery_step),
        "mode": "uniform_current_alpha",
        "target_alpha": float(args.hard_alpha_target),
        "preserve_histories": True,
        "requires_first_displacement_zero": True,
    }
    config.numr_dict["irreversibility_penalty"] = {
        "enable": bool(args.fem_irr_penalty),
        "mode": "fem_gp_tri3",
    }
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics_probe_driver",
    }
    config.fatigue_dict["gradient_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": 1,
        "dense_sampling": True,
        "on_fracture": True,
    }
    config.disp_cyclic = disp_steps

    fat = config.fatigue_dict
    mesh_tag = _mesh_tag(fem_mesh, args.tag)
    if step_source == "absolute_displacement":
        step_tag = "u" + "-".join(f"{x:g}" for x in cycle_disp_values)
    else:
        step_tag = "s" + "-".join(f"{x:g}" for x in derived_factors)
    dir_name = (
        f"probeDriver_hl{config.network_dict['hidden_layers']}"
        f"_n{config.network_dict['neurons']}"
        f"_seed{config.network_dict['seed']}"
        f"_{config.PFF_model_dict['PFF_model']}"
        f"_{config.numr_dict['gradient_type']}"
        f"_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}"
        f"_Ncyc{fat['n_cycles']}_Nstep{total_steps}"
        f"_U{fat['disp_max']}"
        f"_{mesh_tag}"
        f"_current_active_{args.history_driver_reduction_mode}"
        f"{'_femIrrGP3' if args.fem_irr_penalty else ''}"
        f"{'_hardAlphaRecoverU0' if args.hard_alpha_recovery_step else ''}"
        f"_{step_tag}"
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

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as handle:
        handle.write("runner: run_fem_mesh_probe_driver_umax.py\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"n_cycles_physical: {args.n_cycles_physical}\n")
        handle.write(f"n_training_steps: {total_steps}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"hidden_layers: {config.network_dict['hidden_layers']}\n")
        handle.write(f"neurons: {config.network_dict['neurons']}\n")
        handle.write(f"init_coeff: {args.init_coeff}\n")
        handle.write(f"n_epochs_RPROP: {config.optimizer_dict['n_epochs_RPROP']}\n")
        handle.write(f"n_epochs_LBFGS: {config.optimizer_dict['n_epochs_LBFGS']}\n")
        handle.write(f"optim_rel_tol: {config.optimizer_dict['optim_rel_tol']}\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"mesh_tag: {mesh_tag}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        handle.write("history_driver_mode: current_active\n")
        handle.write(f"history_driver_reduction: {fat['history_driver_reduction']}\n")
        handle.write(
            f"irreversibility_penalty: {config.numr_dict['irreversibility_penalty']}\n"
        )
        handle.write(f"initial_alpha_protocol: {fat['initial_alpha_protocol']}\n")
        handle.write(f"recovery_step_offset: {recovery_step_offset}\n")
        handle.write(f"peak_substep_index: {peak_substep}\n")
        handle.write(f"unload_substep_index: {unload_substep}\n")
        handle.write(f"explicit_cycle_step_mode: {step_source}\n")
        handle.write(f"explicit_cycle_substeps: {fat['explicit_cycle_substeps']}\n")
        handle.write(
            f"explicit_cycle_displacements: {fat['explicit_cycle_displacements']}\n"
        )
        handle.write(
            "derived_explicit_cycle_factors_for_internal_oracles: "
            f"{fat['explicit_cycle_factors']}\n"
        )
        handle.write(f"diag_physical_cycles: {diag_physical_cycles}\n")
        handle.write(f"diag_full_physical_cycles: {diag_full_physical_cycles}\n")
        handle.write(f"void_notch_mask_enable: {fat['void_notch_mask']['enable']}\n")
        handle.write(f"element_diagnostics_steps: {diag_steps}\n")
        handle.write("element_diagnostics_fields: mechanics+energy+driver\n")
        handle.write("gradient_diagnostics: pre_history_refresh_every_step\n")
        handle.write(
            "gradient_diagnostics_columns: step,E_el,E_d,E_hist,"
            "grad_E_el,grad_E_d,grad_E_hist\n"
        )
        if args.hard_alpha_recovery_step:
            handle.write(
                "state_mapping: step0=U0_hard_alpha_recovery; "
                f"cN_peak={recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{peak_substep}; "
                f"cN_unloaded={recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{unload_substep}\n"
            )
            handle.write(
                "recovery_semantics: current NN alpha is set to hard target before "
                "step0; hist_alpha, hist_fat, f_fatigue, and psi_plus_prev remain "
                "state0 baseline until step0 post-commit\n"
            )
        handle.write(
            "purpose: strict FEM-mesh fatigue-driver reduction with optional "
            "FEM-like irreversibility penalty quadrature\n"
        )

    print("=" * 72)
    print("PIDL FEM-mesh probe-averaged fatigue-driver reduction")
    print(f"  U_max          = {args.umax} | physical cycles = {args.n_cycles_physical}")
    print(f"  training steps = {total_steps} | seed = {args.seed}")
    print(
        f"  network        = {config.network_dict['hidden_layers']}x"
        f"{config.network_dict['neurons']}"
    )
    print(
        f"  epochs         = RPROP {config.optimizer_dict['n_epochs_RPROP']} | "
        f"LBFGS {config.optimizer_dict['n_epochs_LBFGS']}"
    )
    print(f"  step mode      = {step_source}")
    print(f"  disp steps     = {list(cycle_disp_values)}")
    print(
        f"  peak/unload    = substep {peak_substep} U={cycle_disp_values[peak_substep]:g} | "
        f"substep {unload_substep} U={cycle_disp_values[unload_substep]:g}"
    )
    print(f"  FEM mesh       = {fem_mesh}")
    print(f"  coarse mesh    = {coarse_mesh}")
    print("  history driver = current_active")
    print(f"  reduction      = {args.history_driver_reduction_mode}")
    print(f"  irr penalty    = {'fem_gp_tri3' if args.fem_irr_penalty else 'legacy'}")
    if args.hard_alpha_recovery_step:
        print(f"  recovery step  = step0 U=0 after hard alpha target {args.hard_alpha_target:g}")
        print(
            "  mapping        = "
            f"cN_peak -> {recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{peak_substep}, "
            f"cN_unloaded -> {recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{unload_substep}"
        )
    print("  void mask      = disabled")
    print(f"  elem diag      = {diag_steps}")
    print("  gradient diag  = pre-history-refresh every step")
    print(f"  compile        = {bool(args.compile)}")
    print(f"  device         = {config.device}")
    print(f"  archive        = {dir_name}")
    print(f"  full path      = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
