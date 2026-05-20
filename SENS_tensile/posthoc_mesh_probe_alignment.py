#!/usr/bin/env python3
"""Post-hoc FEM/PIDL mesh-probe alignment audit.

This script compares FEM snapshot fields and PIDL checkpoint fields on the
same PIDL element probes. FEM fields are area-averaged from the fine FEM mesh
into each PIDL triangle. PIDL fields are recomputed from the trained NN on the
same PIDL triangles.

Fields compared:
  - alpha/damage: FEM d_elem vs PIDL alpha_elem
  - psi_plus: FEM psi_elem vs PIDL degraded psi_plus_elem
  - alpha_bar: FEM alpha_bar_elem vs PIDL hist_fat
  - fatigue factor: FEM f_alpha_elem vs Carrara f(PIDL hist_fat)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio
import torch
from scipy.spatial import cKDTree

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["posthoc_mesh_probe_alignment", "8", "400", "1", "TrainableReLU", "1.0"]
from config import domain_extrema, loading_angle, network_dict, mat_prop_dict, numr_dict, PFF_model_dict, crack_dict
sys.argv = _saved_argv

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import gradients, get_psi_plus_per_elem

DEVICE = torch.device("cpu")
FEM_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")
FINE_MESH = str(HERE / "meshed_geom2.msh")
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


def exact_bc_from_settings(archive: Path) -> dict | None:
    settings = parse_settings(archive / "model_settings.txt")
    if settings.get("exact_bc_enable", "False").lower() == "true":
        return {"enable": True, "mode": settings.get("exact_bc_mode", "sent_plane_strain")}
    if "_femAnchorBC" in archive.name:
        return {"enable": True, "mode": "fem_anchor"}
    return None


def carrara_f(alpha_bar: np.ndarray, alpha_t: float = 0.5) -> np.ndarray:
    out = np.ones_like(alpha_bar, dtype=float)
    mask = alpha_bar > alpha_t
    out[mask] = (2.0 * alpha_t / (alpha_bar[mask] + alpha_t)) ** 2
    return out


def point_in_triangle(p, v1, v2, v3, tol=1e-12) -> bool:
    denom = (v2[1] - v3[1]) * (v1[0] - v3[0]) + (v3[0] - v2[0]) * (v1[1] - v3[1])
    if abs(denom) < tol:
        return False
    a = ((v2[1] - v3[1]) * (p[0] - v3[0]) + (v3[0] - v2[0]) * (p[1] - v3[1])) / denom
    b = ((v3[1] - v1[1]) * (p[0] - v3[0]) + (v1[0] - v3[0]) * (p[1] - v3[1])) / denom
    c = 1.0 - a - b
    return (a >= -tol) and (b >= -tol) and (c >= -tol)


def fem_mesh():
    mesh = sio.loadmat(str(FEM_DIR / "mesh_geometry.mat"))
    centroids = np.asarray(mesh["element_centroids"], dtype=float)
    nodes = np.asarray(mesh["node_coords"], dtype=float)
    conn = np.asarray(mesh["connectivity"], dtype=int) - 1
    pts = nodes[conn]
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    areas = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    return centroids, areas


def pidl_model_and_mesh(archive: Path, umax: float, cycle: int):
    settings = parse_settings(archive / "model_settings.txt")
    net_cfg = dict(network_dict)
    if "seed" in settings:
        net_cfg["seed"] = int(settings["seed"])
    if "coeff" in settings:
        net_cfg["init_coeff"] = float(settings["coeff"])
    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, net_cfg, domain_extrema, DEVICE, williams_dict=None
    )
    inp, t_conn, area_t, hist_alpha0 = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=FINE_MESH, device=DEVICE
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor([umax], device=DEVICE),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None,
        l0=mat_prop_dict["l0"],
        exact_bc_dict=exact_bc_from_settings(archive),
    )
    ckpt = archive / "best_models" / f"trained_1NN_{cycle}.pt"
    field_comp.net.load_state_dict(torch.load(str(ckpt), map_location=DEVICE, weights_only=True))
    field_comp.net.eval()
    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        alpha_elem_t = (alpha[t_conn[:, 0]] + alpha[t_conn[:, 1]] + alpha[t_conn[:, 2]]) / 3.0
        psi_t = get_psi_plus_per_elem(inp, u, v, alpha, matprop, pffmodel, area_t, t_conn)
    step = torch.load(str(archive / "best_models" / f"checkpoint_step_{cycle}.pt"), map_location=DEVICE)
    hist_fat = step["hist_fat"].detach().cpu().numpy().reshape(-1)
    inp_np = inp.detach().cpu().numpy()
    t_np = t_conn.detach().cpu().numpy()
    centroids = inp_np[t_np].mean(axis=1)
    areas = area_t.detach().cpu().numpy().reshape(-1)
    return {
        "alpha": alpha_elem_t.detach().cpu().numpy().reshape(-1),
        "psi_plus": psi_t.detach().cpu().numpy().reshape(-1),
        "alpha_bar": hist_fat,
        "f": carrara_f(hist_fat),
        "centroids": centroids,
        "areas": areas,
        "inp": inp_np,
        "conn": t_np,
    }


def build_assignment(fem_centroids: np.ndarray, pidl_centroids: np.ndarray, pidl_inp: np.ndarray, pidl_conn: np.ndarray) -> np.ndarray:
    tree = cKDTree(pidl_centroids)
    assignment = np.empty(len(fem_centroids), dtype=int)
    fallback = 0
    for i, xy in enumerate(fem_centroids):
        if i and i % 20000 == 0:
            print(f"  assignment {i}/{len(fem_centroids)}")
        _, ids = tree.query(xy, k=20)
        ids = np.atleast_1d(ids)
        found = -1
        for j in ids:
            tri = pidl_inp[pidl_conn[int(j)]]
            if point_in_triangle(xy, tri[0], tri[1], tri[2]):
                found = int(j)
                break
        if found < 0:
            found = int(ids[0])
            fallback += 1
        assignment[i] = found
    print(f"  fallback nearest assignments: {fallback}/{len(fem_centroids)}")
    return assignment


def project_to_pidl(values: np.ndarray, fem_areas: np.ndarray, assignment: np.ndarray, n_pidl: int) -> np.ndarray:
    sums = np.zeros(n_pidl, dtype=float)
    areas = np.zeros(n_pidl, dtype=float)
    np.add.at(sums, assignment, values * fem_areas)
    np.add.at(areas, assignment, fem_areas)
    out = np.full(n_pidl, np.nan, dtype=float)
    mask = areas > 0
    out[mask] = sums[mask] / areas[mask]
    return out


def weighted_mean(x: np.ndarray, w: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(x)
    if not np.any(m):
        return float("nan")
    return float(np.sum(x[m] * w[m]) / np.sum(w[m]))


def metrics(x: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(x)
    xf = x[finite]
    if xf.size == 0:
        return {}
    r = np.sqrt(centroids[:, 0] ** 2 + centroids[:, 1] ** 2)
    return {
        "max": float(np.nanmax(x)),
        "p99": float(np.nanpercentile(x, 99.0)),
        "top1_mean": float(np.mean(np.sort(xf)[-max(1, xf.size // 100):])),
        "domain_mean": weighted_mean(x, areas, np.ones_like(finite, dtype=bool)),
        "tip_l0_mean": weighted_mean(x, areas, r <= 0.01),
        "tip_2l0_mean": weighted_mean(x, areas, r <= 0.02),
        "crack_strip_mean": weighted_mean(x, areas, np.abs(centroids[:, 1]) <= 0.02),
        "right_band_mean": weighted_mean(x, areas, centroids[:, 0] >= 0.45),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, default=HERE / DEFAULT_ARCHIVE)
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--cycles", default="1,40,70,82")
    ap.add_argument("--out", type=Path, default=HERE / "alignment_mesh_probe_u012_baseline.csv")
    args = ap.parse_args()

    cycles = [int(x) for x in args.cycles.split(",") if x.strip()]
    fem_centroids, fem_areas = fem_mesh()
    first = pidl_model_and_mesh(args.archive, args.umax, cycles[0])
    assignment = build_assignment(fem_centroids, first["centroids"], first["inp"], first["conn"])

    rows = []
    for cycle in cycles:
        print(f"cycle {cycle}")
        fem = sio.loadmat(str(FEM_DIR / f"u{int(round(args.umax * 100)):02d}_cycle_{cycle:04d}.mat"))
        pidl = first if cycle == cycles[0] else pidl_model_and_mesh(args.archive, args.umax, cycle)
        field_pairs = {
            "damage_alpha": (np.asarray(fem["d_elem"], dtype=float).reshape(-1), pidl["alpha"]),
            "psi_plus": (np.asarray(fem["psi_elem"], dtype=float).reshape(-1), pidl["psi_plus"]),
            "alpha_bar": (np.asarray(fem["alpha_bar_elem"], dtype=float).reshape(-1), pidl["alpha_bar"]),
            "fatigue_f": (np.asarray(fem["f_alpha_elem"], dtype=float).reshape(-1), pidl["f"]),
        }
        for field, (fem_native, pidl_native) in field_pairs.items():
            fem_proj = project_to_pidl(fem_native, fem_areas, assignment, len(pidl_native))
            m_fem = metrics(fem_proj, pidl["areas"], pidl["centroids"])
            m_pidl = metrics(pidl_native, pidl["areas"], pidl["centroids"])
            for metric_name in sorted(m_fem):
                fv = m_fem[metric_name]
                pv = m_pidl[metric_name]
                rows.append({
                    "cycle": cycle,
                    "field": field,
                    "metric": metric_name,
                    "FEM_projected_to_PIDL": fv,
                    "PIDL_native": pv,
                    "PIDL_over_FEM_projected": pv / fv if np.isfinite(fv) and abs(fv) > 1e-30 else np.nan,
                    "FEM_projected_over_PIDL": fv / pv if np.isfinite(pv) and abs(pv) > 1e-30 else np.nan,
                })
    df = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"saved {args.out}")
    summary = df[df["metric"].isin(["max", "p99", "tip_2l0_mean", "right_band_mean"])]
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
