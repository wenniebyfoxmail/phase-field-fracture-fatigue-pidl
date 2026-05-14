#!/usr/bin/env python3
"""
recompute_psi_peak.py — Reload checkpoints, recompute per-element psi+,
and compare different "tip" reductions (max, top-3 mean, top-10 mean).

Purpose: answer the question "does Williams have a higher PEAK psi+, or
just a higher top-10-mean psi+?" (i.e. is the observed Kt improvement real
concentration or averaging artifact?)

Usage:
    cd "upload code/SENS_tensile"
    python recompute_psi_peak.py [--model-dir <dir>] [--output <output.npy>]

If --model-dir is not provided, runs for both baseline and Williams v3
archive and writes a combined CSV.

Outputs:
    <model_dir>/best_models/psi_peak_vs_cycle.npy   shape (N, 4)
        columns: [cycle, max_psi, top3_mean, top10_mean, psi_nominal]
    figures/compare_kt/fig_psi_peak_comparison.png
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import os

import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# NOTE: these imports will load config.py which reads sys.argv for network size.
# We need to pass dummy argv so config.py doesn't fail.
_saved_argv = sys.argv
sys.argv = ["recompute_psi_peak.py", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict, optimizer_dict,
                    device, fatigue_dict, training_dict)
sys.argv = _saved_argv

from field_computation import FieldComputation
from construct_model import construct_model
from compute_energy import get_psi_plus_per_elem
from input_data_from_mesh import prep_input_data

fine_mesh_file = str(HERE / 'meshed_geom2.msh')


def list_default_dirs():
    """Return list of (label, path) for baseline + Williams v3 archive."""
    tensile = HERE
    tag_base = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1"
                "_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5"
                "_N300_R0.0_Umax0.12")
    baseline = tensile / tag_base
    williams = tensile / f"{tag_base}_williams_std_v3_cycle69_Kt15p6_fallback_false_stop"
    williams_v4 = tensile / f"{tag_base}_williams_std"
    dirs = []
    for label, p in [("baseline", baseline),
                     ("williams_v3", williams),
                     ("williams_v4", williams_v4)]:
        if p.is_dir() and (p / "best_models").is_dir():
            dirs.append((label, p))
    return dirs


def _parse_sdf_ribbon_settings(model_dir: Path) -> dict | None:
    """★ 2026-05-14 C8: parse SDF ribbon settings from model_settings.txt.

    Returns None if not a ribbon archive, else dict with 'enable', 'epsilon',
    'apply_to'.
    """
    if "sdfRibbon" not in model_dir.name:
        return None
    settings = model_dir / "model_settings.txt"
    if not settings.exists():
        # Fallback: parse from dir name pattern _sdfRibbon_eps<ε>_<apply_to>
        import re
        m = re.search(r"_sdfRibbon_eps([\d.eE+-]+)_(uv_only|all)", model_dir.name)
        if not m:
            raise ValueError(f"cannot parse SDF ribbon settings from {model_dir.name}")
        return {"enable": True, "epsilon": float(m.group(1)),
                "apply_to": m.group(2)}
    out = {"enable": True}
    for line in settings.read_text().splitlines():
        if line.startswith("sdf_ribbon_epsilon:"):
            out["epsilon"] = float(line.split(":", 1)[1].strip())
        elif line.startswith("sdf_ribbon_apply_to:"):
            out["apply_to"] = line.split(":", 1)[1].strip()
    out.setdefault("epsilon", 1e-3)
    out.setdefault("apply_to", "uv_only")
    return out


def recompute_psi_stats(model_dir: Path, williams_enabled: bool,
                        x_tip_per_cycle: np.ndarray | None,
                        ansatz_enabled: bool = False,
                        c_per_cycle: np.ndarray | None = None) -> np.ndarray:
    """Run through all checkpoints in model_dir and compute psi+ statistics.

    Returns array shape (N_cycles, 5):
        columns: [cycle_idx, psi_max, psi_top3_mean, psi_top10_mean, psi_nominal]

    ★ Direction 5: when ansatz_enabled=True, reconstructs enriched FieldComputation
    with c_singular loaded per-cycle from c_per_cycle (from c_singular_vs_cycle.npy).
    ★ 2026-05-14 C8: when dir name contains "sdfRibbon", reconstructs SplitUVAlphaNet
    (uv_only) or single NN (all-head) with γ injection in fieldCalculation; x_tip
    restored per cycle from x_tip_psi_vs_cycle.npy (same plumbing as Williams).
    """
    best = model_dir / "best_models"

    # Build the FieldComputation fresh for this run
    # Check if Williams enabled in its config
    williams_dict = None
    if williams_enabled:
        williams_dict = {"enable": True, "theta_mode": "atan2", "r_min": 1e-6}

    # ★ Direction 5: ansatz_dict for enriched archives (matches training config)
    ansatz_dict = None
    if ansatz_enabled:
        ansatz_dict = {
            "enable": True,
            "x_tip": 0.0, "y_tip": 0.0,
            "r_cutoff": 0.1, "nu": 0.3,
            "c_init": 0.01, "modes": ["I"],
        }

    # ★ 2026-05-14 C8: SDF ribbon
    sdf_ribbon_dict = _parse_sdf_ribbon_settings(model_dir)
    if sdf_ribbon_dict is not None:
        print(f"  [SDF-rib] detected: ε={sdf_ribbon_dict['epsilon']}, "
              f"apply_to={sdf_ribbon_dict['apply_to']}")

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        williams_dict=williams_dict,
        sdf_ribbon_dict=sdf_ribbon_dict)

    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=fine_mesh_file, device=device)

    # Build FieldComputation with or without ansatz/ribbon
    _fc_kwargs = dict(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=williams_dict,
        l0=mat_prop_dict["l0"])
    if ansatz_dict is not None:
        _fc_kwargs["ansatz_dict"] = ansatz_dict
    if sdf_ribbon_dict is not None:
        _fc_kwargs["sdf_ribbon_dict"] = sdf_ribbon_dict
    field_comp = FieldComputation(**_fc_kwargs)
    field_comp.net = field_comp.net.to(device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(device)
    field_comp.theta = field_comp.theta.to(device)
    # ★ Direction 5: move c_singular to device
    if field_comp.c_singular is not None:
        import torch.nn as _nn
        field_comp.c_singular = _nn.Parameter(field_comp.c_singular.data.to(device))

    # Element centroids
    T_np = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn
    inp_np = inp.detach().cpu().numpy()
    cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
    cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
    nominal_mask = (np.abs(cy) > 0.3) & (cx > -0.3)
    n_nominal = int(nominal_mask.sum())
    print(f"  Nominal elements: {n_nominal}  (|y|>0.3, x>-0.3)")

    # Loading amplitude from config
    lmbda_val = fatigue_dict.get('disp_max', 0.12)

    results = []
    j = 0
    while True:
        model_file = best / f"trained_1NN_{j}.pt"
        if not model_file.is_file():
            break

        # ★ Direction 4 / C8 v0a: restore per-cycle x_tip for any tip-tracking branch
        _tip_tracking_now = williams_enabled or getattr(field_comp, "sdf_ribbon_enabled", False)
        if _tip_tracking_now and x_tip_per_cycle is not None and j < len(x_tip_per_cycle):
            field_comp.x_tip = float(x_tip_per_cycle[j])

        # ★ Direction 5: restore c_singular for this cycle (from c_singular_vs_cycle.npy)
        if ansatz_enabled and c_per_cycle is not None and field_comp.c_singular is not None:
            # c_per_cycle shape: (N, 2) = [cycle_idx, c_val]; look up row where col 0 == j
            row = c_per_cycle[c_per_cycle[:, 0].astype(int) == j]
            if len(row) > 0:
                field_comp.c_singular.data = torch.tensor(
                    [float(row[0, 1])], dtype=torch.float32, device=device)

        field_comp.lmbda = torch.tensor(lmbda_val, device=device)
        field_comp.net.load_state_dict(
            torch.load(str(model_file), map_location='cpu', weights_only=True))
        field_comp.net.eval()

        with torch.no_grad():
            u, v, alpha = field_comp.fieldCalculation(inp)
            psi_plus_0 = get_psi_plus_per_elem(
                inp, u, v, alpha, matprop, pffmodel, area_T, T_conn)

        psi0 = psi_plus_0.cpu().numpy()  # shape (N_elem,)

        # Different reductions
        sorted_psi = np.sort(psi0)
        psi_max = float(sorted_psi[-1])
        psi_top3 = float(sorted_psi[-3:].mean())
        psi_top10 = float(sorted_psi[-10:].mean())
        psi_nom = float(psi0[nominal_mask].mean()) if n_nominal > 0 else float(psi0.mean())

        results.append([j, psi_max, psi_top3, psi_top10, psi_nom])

        if j % 10 == 0 or j < 5:
            print(f"  cycle {j:>3}: max={psi_max:.3e}  top3={psi_top3:.3e}  "
                  f"top10={psi_top10:.3e}  nom={psi_nom:.3e}")

        j += 1

    arr = np.array(results)
    out_file = best / "psi_peak_vs_cycle.npy"
    np.save(str(out_file), arr)
    print(f"  → saved {out_file.name}  ({len(arr)} cycles)")
    return arr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=None,
                        help="Single model directory (optional)")
    parser.add_argument("--max-cycles", type=int, default=None,
                        help="Limit number of cycles to process (for speed)")
    args = parser.parse_args()

    if args.model_dir:
        targets = [(Path(args.model_dir).name, Path(args.model_dir))]
    else:
        targets = list_default_dirs()

    if not targets:
        print("No target directories found.")
        return 1

    for label, d in targets:
        print(f"\n=== Processing {label}: {d.name} ===")
        williams_enabled = "williams" in d.name
        # ★ Direction 5: detect enriched_ansatz flavor
        ansatz_enabled = "enriched_ansatz" in d.name
        # ★ 2026-05-14 C8 v0a: detect SDF ribbon flavor (tip-tracking same as Williams)
        sdf_ribbon_enabled = "sdfRibbon" in d.name

        x_tip_per_cycle = None
        if williams_enabled or sdf_ribbon_enabled:
            for fname in ('x_tip_psi_vs_cycle.npy',
                          'x_tip_alpha_vs_cycle.npy',
                          'x_tip_vs_cycle.npy'):
                p = d / "best_models" / fname
                if p.exists():
                    x_tip_per_cycle = np.load(str(p))
                    print(f"  Loaded x_tip: {fname}  ({len(x_tip_per_cycle)} cycles)")
                    break

        c_per_cycle = None
        if ansatz_enabled:
            p = d / "best_models" / "c_singular_vs_cycle.npy"
            if p.exists():
                c_per_cycle = np.load(str(p))
                print(f"  Loaded c_singular: {len(c_per_cycle)} cycles "
                      f"(init {c_per_cycle[0,1]:+.4f} → final {c_per_cycle[-1,1]:+.4f})")
            else:
                print(f"  WARN: ansatz enabled but c_singular_vs_cycle.npy missing → using c_init=0.01")

        arr = recompute_psi_stats(d, williams_enabled, x_tip_per_cycle,
                                  ansatz_enabled=ansatz_enabled,
                                  c_per_cycle=c_per_cycle)
        if args.max_cycles and len(arr) > args.max_cycles:
            print(f"  (stopped after {args.max_cycles} cycles per --max-cycles)")

    print("\nDone. Now run compare_psi_peak_plot.py or inspect the .npy files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
