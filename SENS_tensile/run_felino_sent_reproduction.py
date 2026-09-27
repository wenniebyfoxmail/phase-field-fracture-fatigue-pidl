#!/usr/bin/env python3
"""Prepare or execute the locked PINN reproduction of Felino's SENT tutorial.

Default operation is a fail-closed dry run.  ``--execute`` enters the existing
PIDL training loop and is intended for the authorised Taobo producer only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SOURCE = REPO / "source"
CONTRACT_PATH = HERE / "felino_sent" / "contract.json"


def _default_assets(project_root: Path) -> dict[str, Path]:
    q1 = project_root / (
        "local_archive/after_strict_setting_alignment/fem/"
        "moose_felino_sent_q1_final_qualification_20260810"
    )
    aligned = project_root / (
        "local_archive/after_strict_setting_alignment/fem/"
        "moose_felino_aligned_sent_instrumented_final_20260812/raw"
    )
    return {
        "disp_input": q1 / "inputs/AD_disp.i",
        "damage_input": q1 / "inputs/AD_f.i",
        "reference_csv": q1 / "mean_loadR05_ICLA.csv",
        "mesh": aligned / "mesh_files/single_notch_square.msh",
    }


def _disable_unrelated_variants(config) -> None:
    for name in ("williams_dict", "ansatz_dict", "fourier_dict", "graph_dict",
                 "adaptive_sampling_dict", "sidecar_S1_dict", "sidecar_S2_dict",
                 "tip_local_net_dict", "local_patch_dict"):
        value = getattr(config, name, None)
        if isinstance(value, dict):
            value["enable"] = False
    config.symmetry_prior = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False


def _configure(config, contract: dict, assets: dict[str, Path], args) -> None:
    material = contract["material"]
    fatigue = contract["fatigue"]
    _disable_unrelated_variants(config)

    config.numr_dict["gradient_type"] = "numerical"
    config.numr_dict["orient_triangles_ccw"] = True
    config.PFF_model_dict.update({
        "PFF_model": material["phase_field"],
        "se_split": material["energy_split"],
        "tol_ir": 1e-3,
        "residual_stiffness": material["residual_stiffness"],
        "degradation_mode": "multiplicative_residual",
    })
    config.mat_prop_dict.update({
        "mat_E": material["E_MPa"],
        "mat_nu": material["nu"],
        "w1": material["Gc_MPa_mm"] / material["ell_mm"],
        "l0": material["ell_mm"],
    })
    config.crack_dict = {
        "x_init": [-0.5], "y_init": [0.0], "L_crack": [0.0],
        "angle_crack": [0.0],
    }
    config.exact_bc_dict.update({
        "enable": True, "mode": "felino_sent", "nu": material["nu"],
    })
    config.fatigue_dict.update({
        "fatigue_on": True,
        "loading_type": "cyclic",
        "n_cycles": fatigue["accepted_steps"],
        "disp_max": fatigue["umax_mm"],
        "R_ratio": fatigue["R"],
        "accum_type": "felino_icla",
        "material_constant_n": fatigue["material_constant_n"],
        "cycle_jump": fatigue["cycle_jump"],
        "degrad_type": "asymptotic",
        "alpha_T": fatigue["alpha_critical_MPa"],
        "history_driver_mode": "current_active",
        "enable_E_fallback": False,
        "alpha_bdy_warn": 1.1,
        "alpha_bdy_threshold": 1.1,
        "plot_every_n_cycles": 10,
        "fracture_confirm_cycles": 0,
        "felino_observables": {"enable": True},
        "element_diagnostics": {
            "enable": True,
            "cycles": [0, 99, 149, 249, 369, 379],
            "every_n_cycles": None,
            "dense_sampling": False,
            "on_fracture": False,
            "dir": "felino_checkpoints",
        },
    })
    config.coarse_mesh_file = str(assets["mesh"])
    config.fine_mesh_file = str(assets["mesh"])
    config.network_dict.update({
        "hidden_layers": args.hidden_layers,
        "neurons": args.neurons,
        "seed": args.seed,
        "activation": args.activation,
        "init_coeff": args.init_coeff,
        "compile": bool(args.compile),
    })
    config.rebuild_disp_cyclic()

    run_name = (
        f"felino_sent_icla_at2_spectral_h{args.hidden_layers}_n{args.neurons}"
        f"_seed{args.seed}"
    )
    config.model_path = config.resolve_archive_dir(HERE, run_name)
    config.trainedModel_path = config.model_path / "best_models"
    config.intermediateModel_path = config.model_path / "intermediate_models"
    for path in (config.model_path, config.trainedModel_path,
                 config.intermediateModel_path):
        path.mkdir(parents=True, exist_ok=True)
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / "TBruns")
    receipt = {
        "runner": Path(__file__).name,
        "contract": contract,
        "assets": {key: str(value) for key, value in assets.items()},
        "claim_boundary": (
            "small-strain PINN reproduction of a locked numerical reference; "
            "not physical truth, teacher qualification, or strict solver equivalence"
        ),
    }
    (config.model_path / "felino_reproduction_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="enter the training loop; Taobo only")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--mesh", type=Path)
    parser.add_argument("--reference-csv", type=Path)
    parser.add_argument("--disp-input", type=Path)
    parser.add_argument("--damage-input", type=Path)
    parser.add_argument("--hidden-layers", type=int, default=8)
    parser.add_argument("--neurons", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--activation", default="TrainableReLU")
    parser.add_argument("--init-coeff", type=float, default=1.0)
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(SOURCE))
    from felino_sent_contract import (discover_project_root, load_contract,
                                      validate_reference)

    project_root = args.project_root or discover_project_root(HERE)
    assets = _default_assets(project_root)
    for key, override in {
        "mesh": args.mesh,
        "reference_csv": args.reference_csv,
        "disp_input": args.disp_input,
        "damage_input": args.damage_input,
    }.items():
        if override is not None:
            assets[key] = override.expanduser().resolve()
    contract = load_contract(CONTRACT_PATH)
    summary = validate_reference(contract, **assets)
    print(json.dumps({"status": "REFERENCE_PREFLIGHT_PASS", **summary}, indent=2))

    if not args.execute:
        print("DRY_RUN_ONLY: no training entered; use --execute on authorised Taobo")
        return
    if sys.platform == "darwin":
        raise RuntimeError("Mac-PIDL is development-only; execute this runner on Taobo")
    if not os.environ.get("CUDA_VISIBLE_DEVICES"):
        raise RuntimeError("CUDA_VISIBLE_DEVICES must be explicit on Taobo")

    os.chdir(HERE)
    sys.path.insert(0, str(HERE))
    sys.argv = ["main.py", str(args.hidden_layers), str(args.neurons),
                str(args.seed), args.activation, str(args.init_coeff)]
    import config
    _configure(config, contract, assets, args)
    main_path = HERE / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
