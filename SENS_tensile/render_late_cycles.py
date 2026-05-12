#!/usr/bin/env python3
"""render_late_cycles.py — render alpha-field PNG for specific cycle indices
from a PIDL archive, including non-standard cycles missed by the runner's
every-20 snapshot cadence (e.g. the final cycle of an N=99 run).

Auto-detects:
  - C4 exact-BC archives (`_exactBCsent_nu<value>` in archive name) →
    rebuild FieldComputation with exact_bc_dict
  - C10 Fourier-feature archives (`_fourier_sig<value>_nf<n>` in archive name) →
    rebuild network with FourierFeatureNet wrapper so the inner.* state_dict
    prefix matches

Usage:
  python render_late_cycles.py <archive_dir> --cycles 90 95 99
  python render_late_cycles.py <archive_dir>                 # default: last 3 cycles available

Output: alpha_cycle_<NNNN>.png in <archive_dir>/alpha_snapshots/

This script is used as part of the "visual-judgment plot habit on sync"
workflow — see memory/feedback_visual_plot_habit_on_sync.md.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_settings(settings_path):
    """Parse model_settings.txt key:value lines."""
    if not settings_path.is_file():
        return {}
    out = {}
    for line in settings_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def detect_exact_bc(archive):
    """Return exact_bc_dict or None."""
    if "_exactBCsent" not in archive.name:
        return None
    settings = parse_settings(archive / "model_settings.txt")
    nu = float(settings.get("exact_bc_nu", 0.3))
    return {"enable": True, "mode": "sent_plane_strain", "nu": nu}


def detect_fourier(archive):
    """Return fourier_dict or None."""
    if "_fourier_sig" not in archive.name:
        return None
    m_sig = re.search(r"_fourier_sig([\d.]+)", archive.name)
    m_nf = re.search(r"_nf(\d+)", archive.name)
    return {
        "enable": True,
        "sigma": float(m_sig.group(1)) if m_sig else 30.0,
        "n_features": int(m_nf.group(1)) if m_nf else 128,
        "seed": 0,
    }


def default_cycles(archive, n=3):
    """If --cycles not given, pick the last n available trained_1NN files.

    Filters out non-integer suffixes (e.g. `trained_1NN_initTraining.pt` from
    the pretraining stage).
    """
    best = archive / "best_models"
    if not best.is_dir():
        return []
    cyc_files = []
    for p in best.glob("trained_1NN_*.pt"):
        suffix = p.stem.rsplit("_", 1)[-1]
        try:
            cyc_files.append((int(suffix), p))
        except ValueError:
            continue   # skip non-numeric like 'initTraining'
    cyc_files.sort()
    return [c for c, _ in cyc_files[-n:]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    ap.add_argument("--cycles", type=int, nargs="*", default=None,
                    help="Cycle indices to render. Default: last 3 trained_1NN_*.pt")
    ap.add_argument("--repo-root", type=Path, default=None,
                    help="Repo root (auto-detected as <archive>/../..)")
    args = ap.parse_args()

    if args.repo_root is None:
        args.repo_root = args.archive.resolve().parents[1]

    sys.path.insert(0, str(args.repo_root / "SENS_tensile"))
    sys.path.insert(0, str(args.repo_root / "source"))

    from construct_model import construct_model
    from input_data_from_mesh import prep_input_data
    from field_computation import FieldComputation

    cycles = args.cycles if args.cycles else default_cycles(args.archive, n=3)
    if not cycles:
        print(f"[error] no cycles to render in {args.archive}")
        return 1

    settings = parse_settings(args.archive / "model_settings.txt")
    exact_bc_dict = detect_exact_bc(args.archive)
    fourier_dict = detect_fourier(args.archive)
    disp_max = float(settings.get("disp_max", 0.12))
    print(f"[setup] archive={args.archive.name}")
    print(f"[setup] disp_max={disp_max} exact_bc={'on' if exact_bc_dict else 'off'} "
          f"fourier={'on' if fourier_dict else 'off'}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    PFF_model_dict = {"PFF_model": "AT1", "se_split": "volumetric", "tol_ir": 5e-3}
    mat_prop_dict = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
    network_dict = {"hidden_layers": 8, "neurons": 400, "activation": "TrainableReLU",
                    "init_coeff": 1.0, "seed": int(settings.get("seed", 1)),
                    "compile": False}
    numr_dict = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical"}

    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle = torch.tensor([np.pi / 2])
    crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    mesh_file = str(args.repo_root / "SENS_tensile" / "meshed_geom2.msh")

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
    field_comp.net = field_comp.net.to(device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(device)
    field_comp.theta = field_comp.theta.to(device)

    best = args.archive / "best_models"
    snap = args.archive / "alpha_snapshots"
    snap.mkdir(parents=True, exist_ok=True)

    for cyc in cycles:
        ckpt = best / f"trained_1NN_{cyc}.pt"
        if not ckpt.is_file():
            print(f"[skip] missing {ckpt.name}")
            continue
        sd = torch.load(str(ckpt), map_location=device, weights_only=True)
        field_comp.net.load_state_dict(sd)
        field_comp.net.eval()
        with torch.no_grad():
            _, _, alpha = field_comp.fieldCalculation(inp)
        a = alpha.detach().cpu().numpy().flatten()
        x = inp.detach().cpu().numpy()[:, 0]
        y = inp.detach().cpu().numpy()[:, 1]
        T = T_conn.detach().cpu().numpy() if torch.is_tensor(T_conn) else T_conn

        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_aspect("equal")
        tpc = ax.tripcolor(x, y, T, a, shading="gouraud", vmin=0, vmax=1, cmap="plasma")
        plt.colorbar(tpc, ax=ax, label="α (damage)")
        ax.set_title(f"α field — cycle {cyc:04d}  (α_max={a.max():.3f})")
        plt.tight_layout()
        out = snap / f"alpha_cycle_{cyc:04d}.png"
        plt.savefig(out, dpi=200)
        plt.close(fig)
        print(f"[saved] {out.name}  α_max={a.max():.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
