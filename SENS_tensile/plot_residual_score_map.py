#!/usr/bin/env python3
"""Plot PIDL residual-score maps for diagnostics and adaptive refinement.

This script uses the same detached score that score-driven S2/v4 refinement
uses:

    score_e = |E_el,e|/A_e + |E_d,e|/A_e

It is not a supervised "prediction - target" residual.  It is a Deep Ritz
variational residual proxy: where does the physical energy density still
concentrate?  The output is suitable both as a diagnostic map and as the
sampling/refinement signal for score-driven adaptive refinement.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import torch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "source"))

# config.py expects training-style argv in some legacy paths.
_saved_argv = sys.argv
sys.argv = ["plot_residual_score_map", "8", "400", "1", "TrainableReLU", "1.0"]
import config
from config import (
    PFF_model_dict,
    crack_dict,
    domain_extrema,
    loading_angle,
    mat_prop_dict,
    network_dict,
    numr_dict,
)
sys.argv = _saved_argv

from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from fatigue_history import compute_fatigue_degrad
from residual_score import compute_residual_score


DEVICE = torch.device("cpu")
OUT_DIR = ROOT / "docs" / "figures" / "residual_score_maps"


def parse_settings(archive: Path) -> dict[str, str]:
    path = archive / "model_settings.txt"
    settings: dict[str, str] = {}
    if not path.exists():
        return settings
    for line in path.read_text(errors="ignore").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        settings[key.strip()] = value.strip()
    return settings


def parse_umax(archive: Path, settings: dict[str, str]) -> float:
    for key in ("disp_max", "Umax"):
        if key in settings:
            try:
                return float(settings[key])
            except ValueError:
                pass
    m = re.search(r"Umax([0-9.]+)", archive.name)
    if m:
        return float(m.group(1).rstrip("."))
    return float(config.fatigue_dict.get("disp_max", 0.12))


def find_cycle(archive: Path, requested: int | None) -> int:
    bm = archive / "best_models"
    cycles = []
    for path in bm.glob("trained_1NN_*.pt"):
        try:
            c = int(path.stem.rsplit("_", 1)[-1])
        except ValueError:
            continue
        if (bm / f"checkpoint_step_{c}.pt").exists():
            cycles.append(c)
    if not cycles:
        raise FileNotFoundError(f"No paired trained_1NN_*.pt/checkpoint_step_*.pt in {bm}")
    if requested is None:
        return max(cycles)
    if requested in cycles:
        return requested
    return min(cycles, key=lambda c: abs(c - requested))


def sidecar_s1_cfg_from_name(name: str) -> dict | None:
    if "sidecarS1" not in name:
        return None
    m_r = re.search(r"_rt([0-9.]+)", name)
    m_np = re.search(r"_np([0-9]+)", name)
    cfg = dict(config.sidecar_S1_dict)
    cfg["enable"] = True
    cfg["r_tip_sample"] = float(m_r.group(1).rstrip(".")) if m_r else 0.05
    cfg["n_refine_passes"] = int(m_np.group(1)) if m_np else 1
    cfg["tip_xy"] = (0.0, 0.0)
    return cfg


def build_field_comp(settings: dict[str, str], umax: float):
    pffmodel, matprop, network = construct_model(
        PFF_model_dict,
        mat_prop_dict,
        network_dict,
        domain_extrema,
        DEVICE,
        williams_dict=None,
        fourier_dict=None,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor(umax, device=DEVICE),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None,
        ansatz_dict=None,
        l0=mat_prop_dict["l0"],
        symmetry_prior=False,
        exact_bc_dict=None,
    )
    return pffmodel, matprop, field_comp


def mesh_from_checkpoint_or_config(archive: Path, ckpt: dict, pffmodel, matprop):
    s2 = ckpt.get("_S2_state")
    if s2 is not None:
        x = np.asarray(s2["X_curr"], dtype=np.float64)
        y = np.asarray(s2["Y_curr"], dtype=np.float64)
        T = np.asarray(s2["T_curr"], dtype=np.int64)
        area = np.asarray(s2["area_curr"], dtype=np.float64)
        inp = torch.from_numpy(np.column_stack((x, y))).float().to(DEVICE)
        T_conn = torch.from_numpy(T).long().to(DEVICE)
        area_T = torch.from_numpy(area).float().to(DEVICE)
        return inp, T_conn, area_T

    s1_cfg = sidecar_s1_cfg_from_name(archive.name)
    inp, T_conn, area_T, _ = prep_input_data(
        matprop,
        pffmodel,
        crack_dict,
        numr_dict,
        mesh_file=str(HERE / config.fine_mesh_file),
        device=DEVICE,
        sidecar_S1_dict=s1_cfg,
        sidecar_label="residual-map",
    )
    return inp, T_conn, area_T


def elem_centroids(inp: torch.Tensor, T_conn: torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    xy = inp.detach().cpu().numpy()
    T = T_conn.detach().cpu().numpy()
    cx = (xy[T[:, 0], 0] + xy[T[:, 1], 0] + xy[T[:, 2], 0]) / 3.0
    cy = (xy[T[:, 0], 1] + xy[T[:, 1], 1] + xy[T[:, 2], 1]) / 3.0
    return cx, cy


def write_csv(path: Path, cx, cy, score, elastic, damage, hist, psi):
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "x_centroid", "y_centroid", "score_density",
            "elastic_density", "damage_density", "hist_density",
            "psi_plus_density",
        ])
        for row in zip(cx, cy, score, elastic, damage, hist, psi):
            writer.writerow([float(v) for v in row])


def plot_maps(path: Path, inp, T_conn, score, elastic, damage, title: str):
    xy = inp.detach().cpu().numpy()
    T = T_conn.detach().cpu().numpy()
    tri = mtri.Triangulation(xy[:, 0], xy[:, 1], T)
    fields = [
        ("log10 score", np.log10(np.maximum(score, 1e-30))),
        ("log10 elastic", np.log10(np.maximum(elastic, 1e-30))),
        ("log10 damage", np.log10(np.maximum(damage, 1e-30))),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.0), constrained_layout=True)
    for ax, (label, values) in zip(axes, fields):
        im = ax.tripcolor(tri, facecolors=values, shading="flat", cmap="magma")
        ax.set_aspect("equal")
        ax.set_title(label)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, shrink=0.85)
    fig.suptitle(title)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path, help="PIDL archive directory")
    parser.add_argument("--cycle", type=int, default=None, help="Cycle to plot; default latest")
    parser.add_argument("--include-hist", action="store_true", help="Include E_hist density in score")
    parser.add_argument("--hist-weight", type=float, default=1.0)
    args = parser.parse_args()

    archive = args.archive.expanduser().resolve()
    if not archive.exists():
        raise FileNotFoundError(archive)

    settings = parse_settings(archive)
    umax = parse_umax(archive, settings)
    cycle = find_cycle(archive, args.cycle)
    bm = archive / "best_models"
    model_path = bm / f"trained_1NN_{cycle}.pt"
    ckpt_path = bm / f"checkpoint_step_{cycle}.pt"

    pffmodel, matprop, field_comp = build_field_comp(settings, umax)
    ckpt = torch.load(ckpt_path, map_location=DEVICE, weights_only=False)
    inp, T_conn, area_T = mesh_from_checkpoint_or_config(archive, ckpt, pffmodel, matprop)
    field_comp.net.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=False))
    field_comp.net.eval()

    hist_alpha = ckpt["hist_alpha"].reshape(-1).to(DEVICE)
    hist_fat = ckpt.get("hist_fat")
    if hist_fat is not None:
        hist_fat = hist_fat.reshape(-1).to(DEVICE)
        f_fatigue = compute_fatigue_degrad(hist_fat, config.fatigue_dict)
    else:
        f_fatigue = torch.ones(area_T.shape[0], device=DEVICE)

    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
    residual = compute_residual_score(
        inp, u, v, alpha, hist_alpha,
        matprop, pffmodel, area_T, T_conn=T_conn,
        f_fatigue=f_fatigue,
        include_hist=args.include_hist,
        hist_weight=args.hist_weight,
    )

    cx, cy = elem_centroids(inp, T_conn)
    stem = f"{archive.name}_cycle{cycle:04d}_residual_score"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"{stem}.csv"
    png_path = OUT_DIR / f"{stem}.png"

    score = residual.score_density.cpu().numpy()
    elastic = residual.elastic_density.cpu().numpy()
    damage = residual.damage_density.cpu().numpy()
    hist = residual.hist_density.cpu().numpy()
    psi = residual.psi_plus_density.cpu().numpy()
    write_csv(csv_path, cx, cy, score, elastic, damage, hist, psi)
    plot_maps(
        png_path, inp, T_conn, score, elastic, damage,
        title=f"{archive.name} | cycle {cycle} | Umax={umax}",
    )

    top = int(np.argmax(score))
    print(f"Wrote {csv_path}")
    print(f"Wrote {png_path}")
    print(
        "Top score element: "
        f"x={cx[top]:+.5f}, y={cy[top]:+.5f}, "
        f"score={score[top]:.6e}, elastic={elastic[top]:.6e}, damage={damage[top]:.6e}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
