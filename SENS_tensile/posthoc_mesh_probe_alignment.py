#!/usr/bin/env python3
"""Post-hoc FEM/PIDL mesh-probe alignment audit.

This script compares FEM snapshot fields and PIDL checkpoint fields on the
same PIDL element probes. FEM fields are area-averaged from the fine FEM mesh
into each PIDL triangle. PIDL fields are recomputed from the trained NN on the
same PIDL triangles.

Fields compared:
  - alpha/damage: FEM d_elem vs PIDL alpha_elem
  - psi_plus_raw: FEM raw peak psi_elem vs PIDL raw psi+_0
  - psi_plus_active: FEM g(d) * raw peak psi_elem vs PIDL g(alpha) * psi+_0
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
try:
    import h5py
except ImportError:  # pragma: no cover - optional, only needed for MATLAB v7.3 handoffs
    h5py = None

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
from compute_energy import gradients, strain_energy_with_split

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


def mesh_from_settings(archive: Path, override: Path | None) -> str:
    if override is not None:
        return str(override)
    settings = parse_settings(archive / "model_settings.txt")
    raw = settings.get("fine_mesh_file", "")
    if raw:
        path = Path(raw).expanduser()
        if path.is_file():
            return str(path)
        local = HERE / path.name
        if local.is_file():
            return str(local)
    return FINE_MESH


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


def orient_by_last_dim(arr: np.ndarray, n_cols: int) -> np.ndarray:
    """Return MATLAB/HDF arrays as N x n_cols when they arrive transposed."""
    a = np.asarray(arr)
    if a.ndim == 2 and a.shape[0] == n_cols and a.shape[1] != n_cols:
        return a.T
    return a


def fem_mesh_from_arrays(centroids: np.ndarray, nodes: np.ndarray, conn: np.ndarray):
    centroids = orient_by_last_dim(np.asarray(centroids, dtype=float), 2)
    nodes = orient_by_last_dim(np.asarray(nodes, dtype=float), 2)
    conn = np.asarray(conn, dtype=int)
    if conn.ndim == 2 and conn.shape[0] in (3, 4) and conn.shape[1] > conn.shape[0]:
        conn = conn.T
    if conn.min() == 1:
        conn = conn - 1
    pts = nodes[conn]
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    areas = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    return centroids, areas


def fem_mesh():
    mesh = sio.loadmat(str(FEM_DIR / "mesh_geometry.mat"))
    return fem_mesh_from_arrays(mesh["element_centroids"], mesh["node_coords"], mesh["connectivity"])


def load_combined_handoff(path: Path) -> dict:
    """Load reverseBC P0 HDF5/MATLAB v7.3 combined handoff.

    Windows-FEM exports arrays as n_cycle x n_elem under h5py because MATLAB
    stores them transposed relative to scipy.io.loadmat v7 output.
    """
    if h5py is None:
        raise RuntimeError("h5py is required to read MATLAB v7.3 combined handoff files")
    with h5py.File(path, "r") as f:
        cycles = np.asarray(f["cycles"], dtype=int).reshape(-1).tolist()
        out = {
            "cycles": cycles,
            "centroids": np.asarray(f["element_centroids"], dtype=float),
            "nodes": np.asarray(f["node_coords"], dtype=float),
            "conn": np.asarray(f["connectivity"], dtype=int),
            "fields": {},
        }
        aliases = {
            "d_elem": ("d_elem",),
            "psi_elem": ("psi_elem", "psi_plus_elem"),
            "alpha_bar_elem": ("alpha_bar_elem",),
            "f_alpha_elem": ("f_alpha_elem", "f_fatigue_elem"),
        }
        for key, candidates in aliases.items():
            found = next((name for name in candidates if name in f), None)
            if found is None:
                raise KeyError(f"Missing FEM field for {key}; tried {candidates}")
            arr = np.asarray(f[found])
            if arr.shape[0] == len(cycles):
                arr = arr.T
            out["fields"][key] = np.asarray(arr, dtype=float)
    out["centroids"], out["areas"] = fem_mesh_from_arrays(out["centroids"], out["nodes"], out["conn"])
    return out


def load_fem_snapshot(cycle: int, umax: float, combined: dict | None):
    if combined is not None:
        idx = combined["cycles"].index(cycle)
        return {
            "d_elem": combined["fields"]["d_elem"][:, idx],
            "psi_elem": combined["fields"]["psi_elem"][:, idx],
            "alpha_bar_elem": combined["fields"]["alpha_bar_elem"][:, idx],
            "f_alpha_elem": combined["fields"]["f_alpha_elem"][:, idx],
        }
    return sio.loadmat(str(FEM_DIR / f"u{int(round(umax * 100)):02d}_cycle_{cycle:04d}.mat"))


def pidl_model_and_mesh(archive: Path, umax: float, cycle: int, mesh_file: str):
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
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=mesh_file, device=DEVICE
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
        s11, s22, s12, _, _ = gradients(inp, u, v, alpha, area_t, t_conn)
        alpha_elem_t = (alpha[t_conn[:, 0]] + alpha[t_conn[:, 1]] + alpha[t_conn[:, 2]]) / 3.0
        _, psi_raw_t = strain_energy_with_split(s11, s22, s12, alpha_elem_t, matprop, pffmodel)
        g_alpha_t, _ = pffmodel.Edegrade(alpha_elem_t)
        psi_active_t = g_alpha_t * psi_raw_t
    step = torch.load(str(archive / "best_models" / f"checkpoint_step_{cycle}.pt"), map_location=DEVICE)
    hist_fat = step["hist_fat"].detach().cpu().numpy().reshape(-1)
    inp_np = inp.detach().cpu().numpy()
    t_np = t_conn.detach().cpu().numpy()
    centroids = inp_np[t_np].mean(axis=1)
    areas = area_t.detach().cpu().numpy().reshape(-1)
    return {
        "alpha": alpha_elem_t.detach().cpu().numpy().reshape(-1),
        "psi_plus_raw": psi_raw_t.detach().cpu().numpy().reshape(-1),
        "psi_plus_active": psi_active_t.detach().cpu().numpy().reshape(-1),
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
    tip_l0 = r <= 0.01
    tip_2l0 = r <= 0.02
    tip_4l0 = r <= 0.04
    return {
        "max": float(np.nanmax(x)),
        "p999": float(np.nanpercentile(x, 99.9)),
        "p99": float(np.nanpercentile(x, 99.0)),
        "top1_mean": float(np.mean(np.sort(xf)[-max(1, xf.size // 100):])),
        "domain_mean": weighted_mean(x, areas, np.ones_like(finite, dtype=bool)),
        "tip_l0_mean": weighted_mean(x, areas, tip_l0),
        "tip_2l0_mean": weighted_mean(x, areas, tip_2l0),
        "tip_4l0_mean": weighted_mean(x, areas, tip_4l0),
        "tip_l0_integral": float(np.nansum(x[tip_l0] * areas[tip_l0])),
        "tip_2l0_integral": float(np.nansum(x[tip_2l0] * areas[tip_2l0])),
        "tip_4l0_integral": float(np.nansum(x[tip_4l0] * areas[tip_4l0])),
        "crack_strip_mean": weighted_mean(x, areas, np.abs(centroids[:, 1]) <= 0.02),
        "right_band_mean": weighted_mean(x, areas, centroids[:, 0] >= 0.45),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, default=HERE / DEFAULT_ARCHIVE)
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--cycles", default=None)
    ap.add_argument("--fem-combined-mat", type=Path, default=None,
                    help="MATLAB v7.3 combined handoff with cycles and FEM fields")
    ap.add_argument("--center-fem", action="store_true",
                    help="Shift FEM coordinates by -0.5 in x/y for [0,1] diffuse-precrack handoffs")
    ap.add_argument("--pidl-mesh", type=Path, default=None,
                    help="PIDL .msh to use when reconstructing checkpoints. Defaults to archive model_settings fine_mesh_file, then meshed_geom2.msh.")
    ap.add_argument("--out", type=Path, default=HERE / "alignment_mesh_probe_u012_baseline.csv")
    args = ap.parse_args()

    combined = load_combined_handoff(args.fem_combined_mat) if args.fem_combined_mat else None
    if args.cycles:
        cycles = [int(x) for x in args.cycles.split(",") if x.strip()]
    elif combined is not None:
        cycles = list(combined["cycles"])
    else:
        cycles = [1, 40, 70, 82]
    fem_centroids, fem_areas = (combined["centroids"], combined["areas"]) if combined is not None else fem_mesh()
    if args.center_fem:
        fem_centroids = fem_centroids.copy()
        fem_centroids[:, :2] -= 0.5
    pidl_mesh = mesh_from_settings(args.archive, args.pidl_mesh)
    print(f"PIDL mesh: {pidl_mesh}")
    first = pidl_model_and_mesh(args.archive, args.umax, cycles[0], pidl_mesh)
    assignment = build_assignment(fem_centroids, first["centroids"], first["inp"], first["conn"])

    rows = []
    for cycle in cycles:
        print(f"cycle {cycle}")
        fem = load_fem_snapshot(cycle, args.umax, combined)
        pidl = first if cycle == cycles[0] else pidl_model_and_mesh(args.archive, args.umax, cycle, pidl_mesh)
        fem_d = np.asarray(fem["d_elem"], dtype=float).reshape(-1)
        fem_psi_raw = np.asarray(fem["psi_elem"], dtype=float).reshape(-1)
        fem_psi_active = ((1.0 - fem_d) ** 2 + 1e-6) * fem_psi_raw
        field_pairs = {
            "damage_alpha": (fem_d, pidl["alpha"]),
            "psi_plus_raw": (fem_psi_raw, pidl["psi_plus_raw"]),
            "psi_plus_active": (fem_psi_active, pidl["psi_plus_active"]),
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
