#!/usr/bin/env python3
"""
plot_hero_fem_vs_pidl.py — Paper hero figure: FEM vs PIDL damage fields at N_f.

Generates fig_hero_FEM_vs_PIDL.png — 4×3 grid:
    rows: FEM, PIDL Baseline, PIDL Williams v4, PIDL Enriched v1
    cols: alpha_elem (fatigue accumulator), psi_elem (elastic energy), f_elem (degradation)
All at each method's N_f for U_max=0.12.

For PIDL rows: loads checkpoint at N_f, reconstructs FieldComputation with
appropriate williams_dict/ansatz_dict per archive, forward passes to compute
per-element psi+ and uses hist_fat (saved ᾱ field) directly.

Usage:
    cd "upload code/SENS_tensile"
    python plot_hero_fem_vs_pidl.py
"""
from __future__ import annotations
from pathlib import Path
import sys
import re

import numpy as np
import torch
import scipy.io as sio
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
import matplotlib.tri as mtri

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

FEM_DIR = Path.home() / "Downloads" / "post_process" / "psi_snapshots_for_agent"

# Load config with dummy argv
_saved_argv = sys.argv
sys.argv = ["plot_hero_fem_vs_pidl.py", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict, fatigue_dict)
sys.argv = _saved_argv

from field_computation import FieldComputation
from construct_model import construct_model
from compute_energy import get_psi_plus_per_elem
from input_data_from_mesh import prep_input_data

FINE_MESH = str(HERE / "meshed_geom2.msh")
ALPHA_T = float(fatigue_dict.get("alpha_T", 0.5))


# --- FEM mesh + snapshot ----------------------------------------------------

def fem_load_mesh():
    m = sio.loadmat(FEM_DIR / "mesh_geometry.mat")
    nodes = m["node_coords"]
    conn = m["connectivity"].astype(int) - 1    # 4-node quads, 1→0 indexed
    # Split each quad into 2 triangles
    tri = np.vstack([conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]])
    return nodes, tri


def fem_load_cycle(u_tag: str, cycle: int) -> dict:
    m = sio.loadmat(FEM_DIR / f"u{u_tag}_cycle_{cycle:04d}.mat")
    return {
        "alpha": m["alpha_elem"].flatten(),     # (77730,)
        "f":     m["f_alpha_elem"].flatten(),
        "psi":   m["psi_elem"].flatten(),
    }


# --- PIDL reconstruction ----------------------------------------------------

def carrara_f(alpha_bar: np.ndarray, alpha_T: float) -> np.ndarray:
    """Carrara asymptotic degradation function."""
    out = np.ones_like(alpha_bar)
    mask = alpha_bar > alpha_T
    out[mask] = (2.0 * alpha_T / (alpha_bar[mask] + alpha_T)) ** 2
    return out


def pidl_reconstruct(archive_dir: Path, cycle: int) -> dict:
    """Rebuild FieldComputation + reload NN at given cycle, return per-element
    alpha, psi+, f values PLUS mesh info (node coords, tri conn).

    For Williams / Enriched runs, infers config from archive dir name and
    injects corresponding dicts into FieldComputation."""
    dname = archive_dir.name
    is_williams = "williams" in dname
    is_enriched = "enriched_ansatz" in dname
    is_fourier = "fourier_nf" in dname

    williams_dict = None
    if is_williams:
        williams_dict = {"enable": True, "theta_mode": "atan2", "r_min": 1e-6}

    ansatz_dict = None
    if is_enriched:
        ansatz_dict = {
            "enable": True, "x_tip": 0.0, "y_tip": 0.0,
            "r_cutoff": 0.1, "nu": 0.3, "c_init": 0.01, "modes": ["I"],
        }

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, "cpu",
        williams_dict=williams_dict)

    inp, T_conn, area_T, hist_alpha_init = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=FINE_MESH, device="cpu")

    fc_kwargs = dict(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0]),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=williams_dict,
        l0=mat_prop_dict["l0"])
    if ansatz_dict is not None:
        fc_kwargs["ansatz_dict"] = ansatz_dict
    field_comp = FieldComputation(**fc_kwargs)

    # Load Williams x_tip per-cycle if applicable
    best = archive_dir / "best_models"
    if is_williams:
        xt = best / "x_tip_psi_vs_cycle.npy"
        if xt.exists():
            x_tip_arr = np.load(xt)
            if cycle < len(x_tip_arr):
                field_comp.x_tip = float(x_tip_arr[cycle])

    # Load Enriched c_singular per-cycle if applicable
    if is_enriched:
        cs_file = best / "c_singular_vs_cycle.npy"
        if cs_file.exists():
            cs = np.load(cs_file)
            row = cs[cs[:, 0].astype(int) == cycle]
            if len(row) > 0 and field_comp.c_singular is not None:
                field_comp.c_singular.data = torch.tensor(
                    [float(row[0, 1])], dtype=torch.float32)

    # Load NN weights at this cycle
    model_file = best / f"trained_1NN_{cycle}.pt"
    field_comp.net.load_state_dict(
        torch.load(str(model_file), map_location='cpu', weights_only=True))
    field_comp.net.eval()

    # Loading amplitude
    field_comp.lmbda = torch.tensor(fatigue_dict.get("disp_max", 0.12))

    # Forward pass → psi+ per element
    with torch.no_grad():
        u, v, alpha_node = field_comp.fieldCalculation(inp)
        psi = get_psi_plus_per_elem(inp, u, v, alpha_node,
                                    matprop, pffmodel, area_T, T_conn)
    psi_np = psi.cpu().numpy().flatten()
    alpha_node_np = alpha_node.detach().cpu().numpy().flatten()

    # Load saved hist_fat (ᾱ per element) from checkpoint
    ckpt_file = best / f"checkpoint_step_{cycle}.pt"
    ckpt = torch.load(str(ckpt_file), map_location='cpu', weights_only=False)
    hist_fat = ckpt["hist_fat"].cpu().numpy().flatten()     # (n_elem,)
    f_vals = carrara_f(hist_fat, ALPHA_T)

    # Mesh info for plotting (node coords, element conn)
    inp_np = inp.detach().cpu().numpy()
    T_np = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn

    return {
        "nodes": inp_np,
        "tri_conn": T_np,           # (n_elem, 3) triangles
        "alpha": hist_fat,          # per-element ᾱ
        "psi": psi_np,              # per-element ψ⁺
        "f": f_vals,                # per-element f(ᾱ)
        "cycle": cycle,
    }


# --- Archive dir discovery --------------------------------------------------

def find_archive(tag: str) -> Path | None:
    for d in HERE.iterdir():
        if d.is_dir() and "Umax0.12" in d.name and tag in d.name:
            if (d / "best_models").exists():
                return d
    return None


def baseline_dir() -> Path | None:
    for d in HERE.iterdir():
        if d.is_dir() and d.name.endswith("Umax0.12") and "hl_8_Neurons_400" in d.name:
            if (d / "best_models" / "checkpoint_step_0.pt").exists():
                return d
    return None


def parse_nf(dirname: str, default: int) -> int:
    m = re.search(r"_Nf(\d+)_", dirname)
    return int(m.group(1)) if m else default


# --- Plotting ---------------------------------------------------------------

def plot_one_panel(ax, nodes, tri_conn, values, vmin, vmax, cmap, use_log,
                   title, clip_low=None):
    triang = mtri.Triangulation(nodes[:, 0], nodes[:, 1], tri_conn)
    if clip_low is not None:
        values = np.maximum(values, clip_low)
    norm = (LogNorm(vmin=max(vmin, 1e-12), vmax=vmax) if use_log
            else Normalize(vmin=vmin, vmax=vmax))
    tpc = ax.tripcolor(triang, facecolors=values, cmap=cmap, norm=norm,
                       shading='flat', edgecolors='none')
    ax.set_aspect('equal')
    ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=9)
    ax.plot([-0.5, 0], [0, 0], 'k-', lw=0.6, alpha=0.6)
    return tpc


def main() -> int:
    outdir = HERE / "figures" / "fem_fields"
    outdir.mkdir(parents=True, exist_ok=True)

    # === Load FEM ===
    print("Loading FEM ...")
    fem_nodes, fem_tri = fem_load_mesh()
    fem_data = fem_load_cycle("12", 82)    # N_f=82

    # === Collect PIDL archives ===
    pidl_specs = [
        ("Baseline",    baseline_dir(),                          80),
        ("Williams v4", find_archive("williams_std_v4_"),        None),
        ("Enriched v1", find_archive("enriched_ansatz_modeI_v1"),None),
    ]
    # Parse N_f from archive names where possible
    for i, (lbl, d, nf) in enumerate(pidl_specs):
        if d is None:
            print(f"⚠️  {lbl}: archive not found")
            continue
        if nf is None:
            nf = parse_nf(d.name, 0)
        pidl_specs[i] = (lbl, d, nf)
        print(f"  {lbl}: {d.name} @ N_f={nf}")

    # === Reconstruct PIDL fields ===
    pidl_fields = []
    for lbl, d, nf in pidl_specs:
        if d is None:
            pidl_fields.append((lbl, None))
            continue
        print(f"Reconstructing {lbl} at cycle {nf} ...")
        try:
            data = pidl_reconstruct(d, nf)
            pidl_fields.append((lbl, data))
        except Exception as e:
            print(f"  ERROR reconstructing {lbl}: {e}")
            pidl_fields.append((lbl, None))

    # === Determine global color scales (per-column) ===
    print("\nComputing color scales ...")
    # Collect all data
    all_alpha = [fem_data["alpha"]] + [d["alpha"] for _, d in pidl_fields if d is not None]
    all_psi   = [fem_data["psi"]]   + [d["psi"]   for _, d in pidl_fields if d is not None]

    # For alpha (log): use percentile to avoid outlier skew
    alpha_clip = 1e-3
    av = np.concatenate([np.maximum(x, alpha_clip) for x in all_alpha])
    alpha_vmin, alpha_vmax = np.percentile(av, 1), av.max()

    # For psi (log)
    psi_clip = 1e-6
    pv = np.concatenate([np.maximum(x, psi_clip) for x in all_psi])
    psi_vmin, psi_vmax = np.percentile(pv, 1), pv.max()

    # f is linear [0, 1]
    f_vmin, f_vmax = 0.0, 1.0

    print(f"  α: log [{alpha_vmin:.2e}, {alpha_vmax:.2e}]")
    print(f"  ψ: log [{psi_vmin:.2e}, {psi_vmax:.2e}]")

    # === Plot 4x3 grid ===
    n_rows = 1 + len(pidl_fields)       # FEM + PIDL variants
    fig, axes = plt.subplots(n_rows, 3, figsize=(10, 2.9 * n_rows))
    if n_rows == 1:
        axes = np.array([axes])

    # FEM: alpha/psi/f are per-QUAD (77730); tri_conn has 2×77730 triangles.
    # Duplicate each value to match (quad splits into 2 triangles sharing value).
    fem_data_dup = {
        "alpha": np.concatenate([fem_data["alpha"], fem_data["alpha"]]),
        "psi":   np.concatenate([fem_data["psi"],   fem_data["psi"]]),
        "f":     np.concatenate([fem_data["f"],     fem_data["f"]]),
    }
    rows_data = [("FEM @ N_f=82", fem_nodes, fem_tri, fem_data_dup)]
    for lbl, data in pidl_fields:
        if data is None:
            rows_data.append((f"{lbl}: N/A", None, None, None))
        else:
            rows_data.append((f"{lbl} @ cycle {data['cycle']}",
                              data["nodes"], data["tri_conn"], data))

    tpc_a = tpc_p = tpc_f = None
    for r, (row_title, nodes, tri, data) in enumerate(rows_data):
        for c in range(3):
            ax = axes[r, c]
            if data is None:
                ax.set_visible(False)
                continue
            if c == 0:
                tpc_a = plot_one_panel(ax, nodes, tri, data["alpha"],
                                       alpha_vmin, alpha_vmax, "plasma",
                                       True, f"{row_title}\nα̅ field",
                                       clip_low=alpha_clip)
            elif c == 1:
                tpc_p = plot_one_panel(ax, nodes, tri, data["psi"],
                                       psi_vmin, psi_vmax, "viridis",
                                       True, f"{row_title}\nψ⁺ field",
                                       clip_low=psi_clip)
            else:
                tpc_f = plot_one_panel(ax, nodes, tri, data["f"],
                                       f_vmin, f_vmax, "RdYlGn",
                                       False, f"{row_title}\nf(α̅) field")

    fig.subplots_adjust(right=0.88, top=0.94, hspace=0.35, wspace=0.08)
    if tpc_a: fig.colorbar(tpc_a, ax=axes[:, 0], fraction=0.03, pad=0.02,
                           label=r"$\bar{\alpha}$ (log)")
    if tpc_p: fig.colorbar(tpc_p, ax=axes[:, 1], fraction=0.03, pad=0.02,
                           label=r"$\psi^+$ (log)")
    if tpc_f: fig.colorbar(tpc_f, ax=axes[:, 2], fraction=0.03, pad=0.02,
                           label=r"$f(\bar{\alpha})$")

    fig.suptitle("FEM vs PIDL damage fields at fracture (U_max=0.12)",
                 y=0.99, fontsize=13, fontweight="bold")
    out = outdir / "fig_hero_FEM_vs_PIDL.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"\n✅ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
