#!/usr/bin/env python3
"""extract_psi_field.py — extract ψ⁺ per-element field at specific cycles.

Reuses render_late_cycles.py setup; instead of rendering α only, it also
calls compute_energy.get_psi_plus_per_elem to get g(α)·ψ⁺_0 per element,
and renders both α and ψ⁺ side-by-side.

Usage:
    python extract_psi_field.py <archive_dir> --cycles 60 80 90

Output (in <archive>/psi_snapshots/):
    psi_alpha_cycle_<NNNN>.png    side-by-side α + ψ⁺ heatmap
    psi_cycle_<NNNN>.npy          per-element ψ⁺ values (n_elem,)
    psi_centroids.npy             once: per-element centroids (n_elem, 2)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Reuse helpers
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent / "source"))

from render_late_cycles import (parse_settings, detect_exact_bc, detect_fourier,
                                default_cycles)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    ap.add_argument("--cycles", type=int, nargs="*", default=None)
    args = ap.parse_args()

    archive = args.archive.resolve()
    repo_root = archive.parents[1]

    from construct_model import construct_model
    from input_data_from_mesh import prep_input_data
    from field_computation import FieldComputation
    from compute_energy import get_psi_plus_per_elem

    cycles = args.cycles if args.cycles else default_cycles(archive, n=5)
    if not cycles:
        print(f"[error] no cycles to extract in {archive}")
        return 1

    settings = parse_settings(archive / "model_settings.txt")
    exact_bc_dict = detect_exact_bc(archive)
    fourier_dict = detect_fourier(archive)
    disp_max = float(settings.get("disp_max", 0.12))

    print(f"[setup] archive={archive.name}")
    print(f"[setup] cycles={cycles}  disp_max={disp_max}")
    print(f"[setup] exact_bc={'on' if exact_bc_dict else 'off'} "
          f"fourier={'on' if fourier_dict else 'off'}")

    device = torch.device("cpu")

    PFF_model_dict = {"PFF_model": "AT1", "se_split": "volumetric", "tol_ir": 5e-3}
    mat_prop_dict = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
    network_dict = {"hidden_layers": 8, "neurons": 400, "activation": "TrainableReLU",
                    "init_coeff": float(settings.get("coeff", 1.0)),
                    "seed": int(settings.get("seed", 1)), "compile": False}
    numr_dict = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical"}

    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle = torch.tensor([np.pi / 2])
    crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    mesh_file = str(repo_root / "SENS_tensile" / "meshed_geom2.msh")

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        williams_dict=None, fourier_dict=fourier_dict)

    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=mesh_file, device=device)

    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([disp_max], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        l0=mat_prop_dict["l0"],
        exact_bc_dict=exact_bc_dict)
    for attr in ("net", "domain_extrema", "theta"):
        setattr(field_comp, attr, getattr(field_comp, attr).to(device))

    best = archive / "best_models"
    out_dir = archive / "psi_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    # centroids: per-element (x, y)
    Tnp = T_conn.detach().cpu().numpy() if torch.is_tensor(T_conn) else T_conn
    pts = inp.detach().cpu().numpy()
    cx = pts[Tnp].mean(axis=1)[:, 0]
    cy = pts[Tnp].mean(axis=1)[:, 1]
    np.save(out_dir / "psi_centroids.npy", np.stack([cx, cy], axis=1))

    for cyc in cycles:
        ckpt = best / f"trained_1NN_{cyc}.pt"
        if not ckpt.is_file():
            print(f"[skip] missing {ckpt.name}")
            continue

        sd = torch.load(str(ckpt), map_location=device, weights_only=True)
        field_comp.net.load_state_dict(sd)
        field_comp.net.eval()

        with torch.no_grad():
            u, v, alpha = field_comp.fieldCalculation(inp)
            psi_plus = get_psi_plus_per_elem(
                inp, u, v, alpha, matprop, pffmodel, area_T, T_conn)

        a = alpha.detach().cpu().numpy().flatten()
        psi = psi_plus.detach().cpu().numpy().flatten()
        np.save(out_dir / f"psi_cycle_{cyc:04d}.npy", psi)

        # log-scaled tripcolor for ψ⁺ (spans many decades typically)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        ax_a, ax_p = axes
        ax_a.set_aspect("equal")
        tp1 = ax_a.tripcolor(pts[:, 0], pts[:, 1], Tnp, a,
                             shading="gouraud", vmin=0, vmax=1, cmap="plasma")
        plt.colorbar(tp1, ax=ax_a, label="α")
        ax_a.set_title(f"α  c={cyc}  α_max={a.max():.3f}")

        ax_p.set_aspect("equal")
        psi_safe = np.clip(psi, 1e-12, None)
        tp2 = ax_p.tripcolor(pts[:, 0], pts[:, 1], Tnp,
                             np.log10(psi_safe), shading="flat", cmap="viridis")
        plt.colorbar(tp2, ax=ax_p, label=r"$\log_{10}\psi^+$")
        ax_p.set_title(f"ψ⁺  c={cyc}  max={psi.max():.3e}")
        for ax in axes:
            ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)

        plt.tight_layout()
        out = out_dir / f"psi_alpha_cycle_{cyc:04d}.png"
        plt.savefig(out, dpi=200)
        plt.close(fig)
        print(f"[saved] {out.name}  α_max={a.max():.3f}  ψ⁺_max={psi.max():.3e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
