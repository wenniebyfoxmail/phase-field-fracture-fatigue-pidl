#!/usr/bin/env python3
"""render_fem_vs_pidl_alpha.py — 3-row × 4-cycle α/d field comparison

Per user May 16: critical visual question — is C8 SDF more FEM-like in its
α localization (proper tip-localized band) or just sharper/faster than baseline?

Layout: 3 rows × 4 cols
  rows: baseline PIDL α  /  SDF v1 PIDL α  /  FEM d_elem
  cols: c1, c40, c70, c82 (FEM snapshot cycles)

PIDL uses tri mesh (~2000 elements) → tripcolor.
FEM uses quad mesh (77730 elements) → pcolormesh / scatter on centroids.

Both definitions = damage variable on [0, 1].
  PIDL α (network output, constrained nonsmooth)
  FEM d_elem (.mat per-element damage)

For SDF at c82: SDF archive ends at c89 due to fracture-confirmation early stop
at c79. c82 IS available as a checkpoint. Use it directly.

Caveat (already in memo Audit Caveat 1): post-fracture PIDL field is degenerate;
visual at c82 is for completeness but should be interpreted with that caveat.
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import scipy.io as sio
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
FEM_DIR = Path.home() / "Downloads" / "_pidl_handoff_v2" / "psi_snapshots_for_agent"

BASE_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
            "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
            "N300_R0.0_Umax0.12")
SDF_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
           "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
           "N100_R0.0_Umax0.12_sdfRibbon_eps0.001_uv_only")

CYCLES = [1, 40, 70, 82]            # FEM snapshot cycles


def find_baseline() -> Path:
    for n in range(0, 7):
        cand = HERE.parents[n] / "SENS_tensile" / BASE_REL if n > 0 else HERE / BASE_REL
        if (cand / "best_models").is_dir() and (cand / "best_models" / "alpha_bar_vs_cycle.npy").exists():
            return cand
    raise FileNotFoundError(f"baseline {BASE_REL} not found")


def parse_settings(path: Path) -> dict:
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def detect_sdf_ribbon(archive: Path) -> dict | None:
    if "sdfRibbon" not in archive.name:
        return None
    settings = parse_settings(archive / "model_settings.txt")
    out = {"enable": True}
    if "sdf_ribbon_epsilon" in settings:
        out["epsilon"] = float(settings["sdf_ribbon_epsilon"])
    if "sdf_ribbon_apply_to" in settings:
        out["apply_to"] = settings["sdf_ribbon_apply_to"]
    out.setdefault("epsilon", 1e-3)
    out.setdefault("apply_to", "uv_only")
    return out


def build_field_comp(archive: Path, sdf_ribbon_dict, device):
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "source"))
    _saved = sys.argv
    sys.argv = ["render", "8", "400", "1", "TrainableReLU", "1.0"]
    from config import (PFF_model_dict, mat_prop_dict, network_dict, numr_dict,
                        crack_dict, domain_extrema, loading_angle)
    sys.argv = _saved

    from construct_model import construct_model
    from input_data_from_mesh import prep_input_data
    from field_computation import FieldComputation

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        sdf_ribbon_dict=sdf_ribbon_dict)
    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=str(HERE / "meshed_geom2.msh"), device=device)
    fc_kw = dict(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.12], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        l0=mat_prop_dict["l0"])
    if sdf_ribbon_dict is not None:
        fc_kw["sdf_ribbon_dict"] = sdf_ribbon_dict
    fc = FieldComputation(**fc_kw)
    fc.net = fc.net.to(device)
    fc.domain_extrema = fc.domain_extrema.to(device)
    fc.theta = fc.theta.to(device)
    return fc, inp, T_conn


def render_pidl(ax, fc, inp, T_conn, ckpt: Path, title: str, *, x_tip=None,
                draw_ribbon=False):
    sd = torch.load(str(ckpt), map_location='cpu', weights_only=True)
    fc.net.load_state_dict(sd)
    fc.net.eval()
    if x_tip is not None and getattr(fc, "sdf_ribbon_enabled", False):
        fc.x_tip = float(x_tip)
    with torch.no_grad():
        _, _, alpha = fc.fieldCalculation(inp)
    a = alpha.detach().cpu().numpy().flatten()
    x = inp.detach().cpu().numpy()[:, 0]
    y = inp.detach().cpu().numpy()[:, 1]
    T = T_conn.detach().cpu().numpy() if torch.is_tensor(T_conn) else T_conn
    ax.tripcolor(x, y, T, a, shading="gouraud", vmin=0, vmax=1, cmap="plasma")
    ax.set_aspect("equal"); ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    tip_x = x_tip if x_tip is not None else 0.0
    ax.plot([-0.5, tip_x], [0, 0], color="cyan", lw=0.8, alpha=0.75)
    ax.plot(tip_x, 0, "o", color="cyan", ms=3, mew=0)
    if draw_ribbon:
        ax.axvline(tip_x, color="lime", lw=0.6, ls="--", alpha=0.6)
    ax.set_title(f"{title}\nα_max={a.max():.3f}", fontsize=8)


def render_fem(ax, cyc: int, title: str, mesh_geom: dict):
    fpath = FEM_DIR / f"u12_cycle_{cyc:04d}.mat"
    if not fpath.is_file():
        ax.text(0.5, 0.5, f"FEM c{cyc}\nmissing", ha="center", va="center",
                transform=ax.transAxes); ax.axis("off"); return
    m = sio.loadmat(fpath)
    d = m['d_elem'].squeeze()
    cx = mesh_geom['element_centroids'][:, 0]
    cy = mesh_geom['element_centroids'][:, 1]
    # Use scatter (small markers) for FEM since quad mesh needs more work for tripcolor
    sc = ax.scatter(cx, cy, c=d, s=0.2, vmin=0, vmax=1, cmap="plasma",
                    marker="s", edgecolors="none")
    ax.set_aspect("equal"); ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.plot([-0.5, 0], [0, 0], color="cyan", lw=0.4, alpha=0.5)   # notch only; FEM crack is in d field
    ax.set_title(f"{title}\nd_max={float(d.max()):.3f}", fontsize=8)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    base_path = find_baseline()
    sdf_path  = HERE / SDF_REL
    print(f"baseline: {base_path.name}")
    print(f"SDF:      {sdf_path.name}")

    sdf_ribbon = detect_sdf_ribbon(sdf_path)
    print(f"SDF ribbon config: {sdf_ribbon}")

    # Build FieldComputation for each
    fc_base, inp_b, T_b = build_field_comp(base_path, None, device)
    fc_sdf,  inp_s, T_s = build_field_comp(sdf_path,  sdf_ribbon, device)

    # x_tip per cycle (for SDF)
    sdf_xtip = None
    for fn in ("x_tip_psi_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy", "x_tip_vs_cycle.npy"):
        p = sdf_path / "best_models" / fn
        if p.exists():
            sdf_xtip = np.load(p); break

    # Load FEM mesh once
    mesh_geom = sio.loadmat(FEM_DIR / "mesh_geometry.mat")

    fig, axes = plt.subplots(3, len(CYCLES), figsize=(2.4 * len(CYCLES) + 1.2, 7.2))

    for j, c in enumerate(CYCLES):
        # Row 0: baseline PIDL
        ckpt_b = base_path / "best_models" / f"trained_1NN_{c}.pt"
        if ckpt_b.is_file():
            render_pidl(axes[0, j], fc_base, inp_b, T_b, ckpt_b,
                        f"baseline c{c}", x_tip=None, draw_ribbon=False)
        else:
            axes[0, j].set_title(f"baseline c{c}\n(no ckpt)", fontsize=9)
            axes[0, j].axis("off")

        # Row 1: SDF v1
        ckpt_s = sdf_path / "best_models" / f"trained_1NN_{c}.pt"
        if ckpt_s.is_file():
            xt = float(sdf_xtip[c]) if sdf_xtip is not None and c < len(sdf_xtip) else 0.0
            render_pidl(axes[1, j], fc_sdf, inp_s, T_s, ckpt_s,
                        f"SDF c{c} (x_tip={xt:.3f})", x_tip=xt, draw_ribbon=True)
        else:
            axes[1, j].set_title(f"SDF c{c}\n(no ckpt)", fontsize=9)
            axes[1, j].axis("off")

        # Row 2: FEM
        render_fem(axes[2, j], c, f"FEM c{c}", mesh_geom)

    # Row labels
    for row, lbl in enumerate(["baseline PIDL\n(α, damage)",
                               "SDF v1 PIDL\n(α, damage)",
                               "FEM\n(d_elem)"]):
        axes[row, 0].set_ylabel(lbl, fontsize=10, rotation=0, labelpad=42,
                                va="center", ha="right")

    fig.suptitle("α / d field — baseline PIDL vs SDF v1 vs FEM ref  (Umax=0.12)\n"
                 "cyan = crack path, green dashed = SDF x_tip transition",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))

    out_dir = HERE.parent / "references_local" / "sdf_ribbon_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "fem_vs_pidl_alpha_panels.png"
    fig.savefig(out_png, dpi=140)
    print(f"\nsaved: {out_png}")


if __name__ == "__main__":
    sys.exit(main())
