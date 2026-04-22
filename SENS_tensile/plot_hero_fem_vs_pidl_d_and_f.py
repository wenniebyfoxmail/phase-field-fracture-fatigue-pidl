#!/usr/bin/env python3
"""
plot_hero_fem_vs_pidl_d_and_f.py — Paper hero: FEM vs PIDL at N_f, Option C.

Produces TWO independent 2x2 hero figures:

  fig_hero_structural_d.png  (field = phase-field structural damage)
     FEM:  d_elem           (from ~/Downloads/_pidl_handoff_v2/...)
     PIDL: alpha_node averaged over triangle vertices (per element)

  fig_hero_fatigue_f.png    (field = fatigue weakening factor)
     FEM:  f_alpha_elem
     PIDL: carrara_f(hist_fat)

Panels in each 2x2 (left->right, top->bottom):
  FEM, PIDL Baseline, PIDL Williams v4, PIDL Enriched v1
All at each method's N_f for U_max=0.12.

Key paper narrative this figure drives:
  - d panel: FEM has a narrow ~2% crack band; PIDL methods show
    a broader, smoother damage region -> visual confirmation of
    the dispersed-vs-concentrated gap.
  - f panel: f_min differs by orders of magnitude (FEM ~1e-6,
    PIDL ~1e-2) and f_mean is systematically higher in PIDL.

Data source: ~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/
Usage:
    cd "upload code/SENS_tensile"
    python plot_hero_fem_vs_pidl_d_and_f.py
"""
from __future__ import annotations
from pathlib import Path
import sys
import re

import numpy as np
import torch
import scipy.io as sio
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import matplotlib.tri as mtri

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

FEM_DIR = Path.home() / "Downloads" / "_pidl_handoff_v2" / "psi_snapshots_for_agent"

# Config load (dummy argv)
_saved_argv = sys.argv
sys.argv = ["plot_hero_fem_vs_pidl_d_and_f.py", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict, fatigue_dict)
sys.argv = _saved_argv

from field_computation import FieldComputation
from construct_model import construct_model
from input_data_from_mesh import prep_input_data

FINE_MESH = str(HERE / "meshed_geom2.msh")
ALPHA_T = float(fatigue_dict.get("alpha_T", 0.5))
U_MAX = 0.12
FEM_U_TAG = "12"
FEM_NF = 82


# --- FEM ---------------------------------------------------------------------

def fem_load_mesh():
    m = sio.loadmat(FEM_DIR / "mesh_geometry.mat")
    nodes = m["node_coords"]
    conn = m["connectivity"].astype(int) - 1
    tri = np.vstack([conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]])
    return nodes, tri


def fem_load_nf() -> dict:
    m = sio.loadmat(FEM_DIR / f"u{FEM_U_TAG}_cycle_{FEM_NF:04d}.mat")
    return {
        "d":         m["d_elem"].flatten(),
        "f":         m["f_alpha_elem"].flatten(),
        "alpha_bar": m["alpha_bar_elem"].flatten(),
    }


# --- PIDL --------------------------------------------------------------------

def carrara_f(alpha_bar: np.ndarray, alpha_T) -> np.ndarray:
    """Carrara asymptotic f = [2α_T/(ᾱ+α_T)]² ; supports scalar or per-element α_T."""
    alpha_T_arr = np.broadcast_to(np.asarray(alpha_T, dtype=alpha_bar.dtype),
                                  alpha_bar.shape)
    out = np.ones_like(alpha_bar)
    mask = alpha_bar > alpha_T_arr
    out[mask] = (2.0 * alpha_T_arr[mask] / (alpha_bar[mask] + alpha_T_arr[mask])) ** 2
    return out


def _parse_spalphaT_params(dname: str) -> tuple[float, float, float, float] | None:
    """Parse (β, r_T, x_tip, y_tip) from `_spAlphaT_b{β}_r{r_T}` dir-name tag.
    tip fixed at (0,0) per config. Returns None if tag absent."""
    import re
    m = re.search(r"spAlphaT_b([\d.]+)_r([\d.]+)", dname)
    if m is None:
        return None
    return float(m.group(1)), float(m.group(2)), 0.0, 0.0


def pidl_reconstruct(archive_dir: Path, cycle: int) -> dict:
    """Reload NN at given cycle, return per-element PIDL fields:
       d_elem  = mean of alpha_node over triangle vertices (phase-field damage)
       f_elem  = carrara_f(hist_fat)"""
    dname = archive_dir.name
    is_williams = "williams" in dname
    is_enriched = "enriched_ansatz" in dname

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

    inp, T_conn, area_T, _ = prep_input_data(
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

    best = archive_dir / "best_models"
    if is_williams:
        xt = best / "x_tip_psi_vs_cycle.npy"
        if xt.exists():
            x_tip_arr = np.load(xt)
            if cycle < len(x_tip_arr):
                field_comp.x_tip = float(x_tip_arr[cycle])

    if is_enriched:
        cs_file = best / "c_singular_vs_cycle.npy"
        if cs_file.exists():
            cs = np.load(cs_file)
            row = cs[cs[:, 0].astype(int) == cycle]
            if len(row) > 0 and field_comp.c_singular is not None:
                field_comp.c_singular.data = torch.tensor(
                    [float(row[0, 1])], dtype=torch.float32)

    field_comp.net.load_state_dict(
        torch.load(str(best / f"trained_1NN_{cycle}.pt"),
                   map_location="cpu", weights_only=True))
    field_comp.net.eval()
    field_comp.lmbda = torch.tensor(U_MAX)

    with torch.no_grad():
        _, _, alpha_node = field_comp.fieldCalculation(inp)
    alpha_node_np = alpha_node.detach().cpu().numpy().flatten()

    ckpt = torch.load(str(best / f"checkpoint_step_{cycle}.pt"),
                      map_location="cpu", weights_only=False)
    hist_fat = ckpt["hist_fat"].cpu().numpy().flatten()

    T_np = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn

    # ★ Direction 6.1: spatial α_T modulation —— per-element α_T from dir-name params
    sp_params = _parse_spalphaT_params(dname)
    if sp_params is not None:
        beta, r_T, x_tip, y_tip = sp_params
        nodes_np = inp.detach().cpu().numpy()
        cx = nodes_np[T_np[:, 0], 0] + nodes_np[T_np[:, 1], 0] + nodes_np[T_np[:, 2], 0]
        cy = nodes_np[T_np[:, 0], 1] + nodes_np[T_np[:, 1], 1] + nodes_np[T_np[:, 2], 1]
        cx = cx / 3.0; cy = cy / 3.0
        r_elem = np.sqrt((cx - x_tip) ** 2 + (cy - y_tip) ** 2 + 1e-12)
        alpha_T_arr = ALPHA_T * (1.0 - beta * np.exp(-r_elem / r_T))
        f_vals = carrara_f(hist_fat, alpha_T_arr)
    else:
        f_vals = carrara_f(hist_fat, ALPHA_T)

    d_pidl_elem = alpha_node_np[T_np].mean(axis=1)      # (n_elem,)

    return {
        "nodes":    inp.detach().cpu().numpy(),
        "tri_conn": T_np,
        "d":        d_pidl_elem,
        "f":        f_vals,
        "cycle":    cycle,
    }


# --- Archive discovery -------------------------------------------------------

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


# --- Plot helper -------------------------------------------------------------

def panel(ax, nodes, tri, values_per_elem, cmap, vmin, vmax,
          title, threshold_line=None):
    """Plot one field on a triangulated mesh. values_per_elem length must
    match number of triangles. For FEM (quads) caller must duplicate."""
    values = np.clip(values_per_elem, vmin, vmax)
    triang = mtri.Triangulation(nodes[:, 0], nodes[:, 1], tri)
    tpc = ax.tripcolor(triang, facecolors=values, cmap=cmap,
                       norm=Normalize(vmin=vmin, vmax=vmax),
                       shading="flat", edgecolors="none")
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=10)
    ax.plot([-0.5, 0.0], [0.0, 0.0], "k-", lw=0.6, alpha=0.5)
    return tpc


def stats_d(d: np.ndarray) -> str:
    return f"$d_{{max}}$={d.max():.2f}   $d\\!\\geq\\!0.95$: {(d>=0.95).mean()*100:.2f}%"


def stats_f(f: np.ndarray) -> str:
    return f"$f_{{min}}$={f.min():.2e}   $f\\!<\\!0.5$: {(f<0.5).mean()*100:.1f}%"


# --- Figure generators -------------------------------------------------------

def figure_structural_d(fem_nodes, fem_tri, fem, pidl_entries, outpath):
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 9.2))   # 6 panels: FEM + 5 PIDL
    ax_list = axes.flatten()
    tpc = None

    # FEM (duplicate quad values for 2-triangle split)
    d_fem_dup = np.concatenate([fem["d"], fem["d"]])
    tpc = panel(ax_list[0], fem_nodes, fem_tri, d_fem_dup, "hot_r", 0.0, 1.0,
                f"FEM @ $N_f$={FEM_NF}\n{stats_d(fem['d'])}")
    # PIDL
    for i, (label, data, nf) in enumerate(pidl_entries, start=1):
        if data is None:
            ax_list[i].set_visible(False); continue
        tpc = panel(ax_list[i], data["nodes"], data["tri_conn"], data["d"],
                    "hot_r", 0.0, 1.0,
                    f"PIDL {label} @ cycle {nf}\n{stats_d(data['d'])}")

    fig.subplots_adjust(right=0.89, top=0.91, bottom=0.04,
                        left=0.04, hspace=0.28, wspace=0.06)
    cax = fig.add_axes([0.91, 0.08, 0.018, 0.78])
    cb = fig.colorbar(tpc, cax=cax)
    cb.set_label(r"Structural damage $d$ (phase-field)", fontsize=11)
    cb.ax.axhline(0.95, color="black", lw=1.0, ls="--")
    cb.ax.text(1.8, 0.95, "0.95\n(fracture)", va="center", fontsize=8,
               transform=cb.ax.get_yaxis_transform())

    fig.suptitle(f"Structural damage at $N_f$: FEM vs PIDL   "
                 f"($U_{{max}}$={U_MAX})",
                 fontsize=13, fontweight="bold", y=0.97)
    fig.savefig(outpath, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {outpath}")


def figure_fatigue_f(fem_nodes, fem_tri, fem, pidl_entries, outpath):
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 9.2))   # 6 panels: FEM + 5 PIDL
    ax_list = axes.flatten()
    tpc = None

    f_fem_dup = np.concatenate([fem["f"], fem["f"]])
    tpc = panel(ax_list[0], fem_nodes, fem_tri, f_fem_dup, "YlOrRd_r", 0.0, 1.0,
                f"FEM @ $N_f$={FEM_NF}\n{stats_f(fem['f'])}")
    for i, (label, data, nf) in enumerate(pidl_entries, start=1):
        if data is None:
            ax_list[i].set_visible(False); continue
        tpc = panel(ax_list[i], data["nodes"], data["tri_conn"], data["f"],
                    "YlOrRd_r", 0.0, 1.0,
                    f"PIDL {label} @ cycle {nf}\n{stats_f(data['f'])}")

    fig.subplots_adjust(right=0.89, top=0.91, bottom=0.04,
                        left=0.04, hspace=0.28, wspace=0.06)
    cax = fig.add_axes([0.91, 0.08, 0.018, 0.78])
    cb = fig.colorbar(tpc, cax=cax)
    cb.set_label(r"$f(\bar\alpha)$  (1 = pristine, 0 = fully weakened)",
                 fontsize=11)
    cb.ax.axhline(0.5, color="black", lw=1.0, ls="--")
    cb.ax.text(1.8, 0.5, "0.5\n(weakened)", va="center", fontsize=8,
               transform=cb.ax.get_yaxis_transform())

    fig.suptitle(f"Fatigue weakening at $N_f$: FEM vs PIDL   "
                 f"($U_{{max}}$={U_MAX})",
                 fontsize=13, fontweight="bold", y=0.97)
    fig.savefig(outpath, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {outpath}")


def main() -> int:
    outdir = HERE / "figures" / "fem_fields"
    outdir.mkdir(parents=True, exist_ok=True)

    print("Loading FEM ...")
    fem_nodes, fem_tri = fem_load_mesh()
    fem = fem_load_nf()

    print("Finding PIDL archives ...")
    specs = [
        ("Baseline",        baseline_dir(),                                          80),
        ("Williams v4",     find_archive("williams_std_v4_"),                        None),
        ("Enriched v1",     find_archive("enriched_ansatz_modeI_v1"),                None),
        # ★ Dir 6.1: 加 "_cycle" suffix 过滤掉 config-import 产生的空 stub dir
        ("Dir 6.1 broad",   find_archive("spAlphaT_b0.5_r0.1_cycle"),                None),
        ("Dir 6.1 narrow",  find_archive("spAlphaT_b0.8_r0.03_cycle"),               None),
    ]
    pidl_entries = []
    for label, d, nf in specs:
        if d is None:
            print(f"  [SKIP] {label}: archive not found")
            pidl_entries.append((label, None, None))
            continue
        if nf is None:
            nf = parse_nf(d.name, 0)
        print(f"  {label}: {d.name} @ N_f={nf}")
        try:
            data = pidl_reconstruct(d, nf)
            pidl_entries.append((label, data, nf))
        except Exception as e:
            print(f"  [ERR] {label}: {e}")
            pidl_entries.append((label, None, nf))

    figure_structural_d(fem_nodes, fem_tri, fem, pidl_entries,
                        outdir / "fig_hero_structural_d.png")
    figure_fatigue_f(fem_nodes, fem_tri, fem, pidl_entries,
                     outdir / "fig_hero_fatigue_f.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
