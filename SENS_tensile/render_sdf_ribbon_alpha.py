#!/usr/bin/env python3
"""render_sdf_ribbon_alpha.py — α(x,y) panels: baseline vs SDF ribbon

Renders side-by-side α field at multiple cycles for visual mechanism check.
Per user May 14: the critical question is whether the ribbon causes healthy
tip-localized α growth (GOOD) or a sgn(y) ribbon-shortcut artifact (BAD).

Outputs 2-row figure: top = baseline @ each cycle, bottom = SDF @ same cycles.
Overlays on SDF row:
  - notch + grown crack path: line from (-0.5, 0) to (x_tip(c), 0) in red
  - ribbon discontinuity boundary: x_tip vertical (where γ transitions)

Usage:
    python3 render_sdf_ribbon_alpha.py <baseline_archive> <sdf_archive> \
        --cycles 4 5 10 15 20 29
"""
from __future__ import annotations
import argparse
import sys
import re
from pathlib import Path
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent


def parse_settings(path: Path) -> dict:
    if not path.is_file():
        return {}
    out = {}
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
    if "epsilon" not in out or "apply_to" not in out:
        m = re.search(r"_sdfRibbon_eps([\d.eE+-]+)_(uv_only|all)", archive.name)
        if m:
            out.setdefault("epsilon", float(m.group(1)))
            out.setdefault("apply_to", m.group(2))
    return out


def load_x_tip(archive: Path) -> np.ndarray | None:
    bm = archive / "best_models"
    for fn in ("x_tip_psi_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy", "x_tip_vs_cycle.npy"):
        p = bm / fn
        if p.exists():
            return np.load(p)
    return None


def build_field_comp(archive: Path, sdf_ribbon_dict, device):
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "source"))
    # Pass dummy argv for config import
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
    field_comp = FieldComputation(**fc_kw)
    field_comp.net = field_comp.net.to(device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(device)
    field_comp.theta = field_comp.theta.to(device)
    return field_comp, inp, T_conn


def render_one(field_comp, inp, T_conn, ckpt_path: Path, x_tip: float | None,
               ax, title: str, *, draw_ribbon: bool):
    sd = torch.load(str(ckpt_path), map_location='cpu', weights_only=True)
    field_comp.net.load_state_dict(sd)
    field_comp.net.eval()
    if x_tip is not None and getattr(field_comp, "sdf_ribbon_enabled", False):
        field_comp.x_tip = float(x_tip)
    with torch.no_grad():
        _, _, alpha = field_comp.fieldCalculation(inp)
    a = alpha.detach().cpu().numpy().flatten()
    x = inp.detach().cpu().numpy()[:, 0]
    y = inp.detach().cpu().numpy()[:, 1]
    T = T_conn.detach().cpu().numpy() if torch.is_tensor(T_conn) else T_conn

    tpc = ax.tripcolor(x, y, T, a, shading="gouraud", vmin=0, vmax=1, cmap="plasma")
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 0.5); ax.set_ylim(-0.5, 0.5)
    ax.set_title(title, fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])

    # Crack path overlay: notch + grown crack from (-0.5, 0) to (x_tip, 0)
    tip_x = x_tip if x_tip is not None else 0.0
    ax.plot([-0.5, tip_x], [0, 0], color="cyan", lw=1.2, alpha=0.85)
    ax.plot(tip_x, 0, "o", color="cyan", ms=4, mew=0, alpha=0.95)

    # Ribbon γ discontinuity boundary on SDF panels: vertical line at x = x_tip
    # (sigmoid transition center); plus crack-mouth notch boundary at x = -0.5
    if draw_ribbon:
        ax.axvline(tip_x, color="lime", lw=0.8, ls="--", alpha=0.7)

    return float(a.max())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("baseline", type=Path)
    p.add_argument("sdf_archive", type=Path)
    p.add_argument("--cycles", type=int, nargs="+", default=[4, 5, 10, 15, 20, 29])
    p.add_argument("-o", "--out", type=Path, default=None)
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    base_ribbon = detect_sdf_ribbon(args.baseline)            # should be None
    sdf_ribbon  = detect_sdf_ribbon(args.sdf_archive)         # required
    print(f"[setup] baseline ribbon={base_ribbon}  sdf ribbon={sdf_ribbon}")
    if sdf_ribbon is None:
        print("  ERROR: sdf_archive does not look like an SDF ribbon dir.")
        return 1

    base_xtip = load_x_tip(args.baseline)
    sdf_xtip  = load_x_tip(args.sdf_archive)

    fc_base, inp_b, T_b = build_field_comp(args.baseline,     None,        device)
    fc_sdf,  inp_s, T_s = build_field_comp(args.sdf_archive,  sdf_ribbon,  device)

    n_cyc = len(args.cycles)
    fig, axes = plt.subplots(2, n_cyc, figsize=(2.2 * n_cyc + 0.8, 5.4))
    axes = np.atleast_2d(axes)

    for j, c in enumerate(args.cycles):
        # baseline row 0
        ckpt_b = args.baseline / "best_models" / f"trained_1NN_{c}.pt"
        if ckpt_b.is_file():
            xt = float(base_xtip[c]) if base_xtip is not None and c < len(base_xtip) else 0.0
            a_max = render_one(fc_base, inp_b, T_b, ckpt_b, xt,
                               axes[0, j], f"baseline c{c} (x_tip={xt:.3f})",
                               draw_ribbon=False)
            print(f"  baseline c{c}: α_max={a_max:.3f}")
        else:
            axes[0, j].set_title(f"baseline c{c}\n(no ckpt)", fontsize=9)
            axes[0, j].axis("off")

        # sdf row 1
        ckpt_s = args.sdf_archive / "best_models" / f"trained_1NN_{c}.pt"
        if ckpt_s.is_file():
            xt = float(sdf_xtip[c]) if sdf_xtip is not None and c < len(sdf_xtip) else 0.0
            a_max = render_one(fc_sdf, inp_s, T_s, ckpt_s, xt,
                               axes[1, j], f"SDF c{c} (x_tip={xt:.3f})",
                               draw_ribbon=True)
            print(f"  SDF      c{c}: α_max={a_max:.3f}")
        else:
            axes[1, j].set_title(f"SDF c{c}\n(no ckpt)", fontsize=9)
            axes[1, j].axis("off")

    axes[0, 0].set_ylabel("baseline", fontsize=11, rotation=0, labelpad=35,
                          va="center", ha="right")
    axes[1, 0].set_ylabel("SDF v1\n(uv_only ε=1e-3)", fontsize=11, rotation=0,
                          labelpad=40, va="center", ha="right")

    fig.suptitle("α(x,y) — baseline vs SDF ribbon (uv_only, ε=1e-3, seed=1)  "
                 "cyan = crack path,  green dashed = current tip position",
                 fontsize=11)
    fig.tight_layout()

    if args.out is None:
        out_dir = HERE.parent / "references_local" / "sdf_ribbon_smoke"
        out_dir.mkdir(parents=True, exist_ok=True)
        cstr = "_".join(f"c{c}" for c in args.cycles)
        args.out = out_dir / f"alpha_panels_baseline_vs_sdf_{cstr}.png"

    fig.savefig(args.out, dpi=150)
    print(f"\nsaved: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
