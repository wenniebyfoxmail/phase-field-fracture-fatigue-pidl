#!/usr/bin/env python3
"""Export PIDL baseline initial fields before cycle-1 loading.

This is the PIDL-side counterpart to the FEM state-timing request.  It records
two different "initial alpha" objects that are easy to conflate:

* hist_alpha_init_elem: analytic AT1 diffuse precrack memory from the mesh.
* alpha_pretrain_elem: actual NN alpha after initTraining, before cyclic solve.

The fatigue history is zero at this state, so f_fatigue is one everywhere.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import TwoSlopeNorm

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["export_pidl_initial_state", "8", "400", "1", "TrainableReLU", "1.0"]
from config import domain_extrema, loading_angle, network_dict, mat_prop_dict, numr_dict, PFF_model_dict, crack_dict
sys.argv = _saved_argv

from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data

DEVICE = torch.device("cpu")
FINE_MESH = HERE / "meshed_geom2.msh"
DEFAULT_ARCHIVE = (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N300_R0.0_Umax0.12"
)


def parse_settings(settings_path: Path) -> dict[str, str]:
    if not settings_path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in settings_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def element_mean(node_values: torch.Tensor, conn: torch.Tensor) -> np.ndarray:
    vals = node_values.reshape(-1)
    elem = (vals[conn[:, 0]] + vals[conn[:, 1]] + vals[conn[:, 2]]) / 3.0
    return elem.detach().cpu().numpy().reshape(-1)


def weighted_mean(values: np.ndarray, areas: np.ndarray) -> float:
    return float(np.sum(values * areas) / np.sum(areas))


def field_metrics(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    r = np.sqrt(centroids[:, 0] ** 2 + centroids[:, 1] ** 2)
    out = {
        "min": float(np.nanmin(values)),
        "max": float(np.nanmax(values)),
        "p99": float(np.nanpercentile(values, 99.0)),
        "p999": float(np.nanpercentile(values, 99.9)),
        "domain_mean": weighted_mean(values, areas),
    }
    for radius, name in [(0.01, "tip_l0"), (0.02, "tip_2l0"), (0.04, "tip_4l0")]:
        mask = r <= radius
        out[f"{name}_mean"] = weighted_mean(values[mask], areas[mask]) if np.any(mask) else np.nan
        out[f"{name}_integral"] = float(np.sum(values[mask] * areas[mask])) if np.any(mask) else np.nan
    return out


def plot_initial_fields(nodes: np.ndarray, conn: np.ndarray, fields: dict[str, np.ndarray], out_path: Path) -> None:
    tri = mtri.Triangulation(nodes[:, 0], nodes[:, 1], conn)
    diff = fields["alpha_pretrain_elem"] - fields["hist_alpha_init_elem"]
    vmax = float(np.nanmax(np.abs(diff)))
    if not np.isfinite(vmax) or vmax == 0.0:
        vmax = 1e-6

    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.3), constrained_layout=True)
    panels = [
        ("hist_alpha_init", fields["hist_alpha_init_elem"], "viridis", None, 0.0, 1.0),
        ("pretraining alpha", fields["alpha_pretrain_elem"], "viridis", None, 0.0, 1.0),
        ("pretrain - hist", diff, "RdBu_r", TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax), None, None),
    ]
    for ax, (title, values, cmap, norm, vmin, vmax_panel) in zip(axes, panels):
        im = ax.tripcolor(tri, values, shading="flat", cmap=cmap, norm=norm, vmin=vmin, vmax=vmax_panel)
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(-0.52, 0.52)
        ax.set_ylim(-0.52, 0.52)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, default=HERE / DEFAULT_ARCHIVE)
    ap.add_argument("--mesh", type=Path, default=FINE_MESH)
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--out-dir", type=Path, default=HERE.parent / "_analysis_fem_mechanism_20260528")
    args = ap.parse_args()

    settings = parse_settings(args.archive / "model_settings.txt")
    net_cfg = dict(network_dict)
    if "seed" in settings:
        net_cfg["seed"] = int(settings["seed"])
    if "coeff" in settings:
        net_cfg["init_coeff"] = float(settings["coeff"])

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, net_cfg, domain_extrema, DEVICE, williams_dict=None
    )
    inp, conn, area_t, hist_alpha_init = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=str(args.mesh), device=DEVICE
    )
    nodes = inp.detach().cpu().numpy()
    conn_np = conn.detach().cpu().numpy()
    areas = np.abs(area_t.detach().cpu().numpy().reshape(-1))
    centroids = nodes[conn_np].mean(axis=1)

    fields = {
        "hist_alpha_init_elem": element_mean(hist_alpha_init, conn),
        "hist_fat0_elem": np.zeros(len(conn_np), dtype=float),
        "f_fatigue0_elem": np.ones(len(conn_np), dtype=float),
    }

    init_ckpt = args.archive / "best_models" / "trained_1NN_initTraining.pt"
    field_comp = FieldComputation(
        net=network,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor([args.umax], device=DEVICE),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None,
        l0=mat_prop_dict["l0"],
    )
    if init_ckpt.is_file():
        field_comp.net.load_state_dict(torch.load(str(init_ckpt), map_location=DEVICE, weights_only=True))
        field_comp.net.eval()
        with torch.no_grad():
            _, _, alpha_pretrain = field_comp.fieldCalculation(inp)
        fields["alpha_pretrain_elem"] = element_mean(alpha_pretrain, conn)
    else:
        fields["alpha_pretrain_elem"] = np.full(len(conn_np), np.nan, dtype=float)

    fields["alpha_pretrain_minus_hist_elem"] = fields["alpha_pretrain_elem"] - fields["hist_alpha_init_elem"]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    npz_path = args.out_dir / "pidl_baseline_initial_state_fields.npz"
    summary_path = args.out_dir / "pidl_baseline_initial_state_summary.csv"
    fig_path = args.out_dir / "figures" / "pidl_baseline_initial_state_alpha.png"

    np.savez_compressed(
        npz_path,
        nodes=nodes,
        connectivity=conn_np,
        element_centroids=centroids,
        element_area=areas,
        archive=str(args.archive),
        mesh=str(args.mesh),
        **fields,
    )

    rows = []
    for field_name, values in fields.items():
        for metric, value in field_metrics(values, areas, centroids).items():
            rows.append({"state": "cycle0_initial_preload_prehistory", "field": field_name, "metric": metric, "value": value})
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    plot_initial_fields(nodes, conn_np, fields, fig_path)

    print(f"saved {npz_path}")
    print(f"saved {summary_path}")
    print(f"saved {fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
