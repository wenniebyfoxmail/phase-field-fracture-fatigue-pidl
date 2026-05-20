#!/usr/bin/env python3
"""Global/dynamic V7 audit for PIDL side traction residuals.

Classic V7 reports pointwise max side residuals. This audit adds global views:
  - side-band RMS traction residual,
  - signed side traction mean and cancellation ratio,
  - approximate side-boundary work proxy ∫ |t · u| dΓ / E_el,
  - trajectory context: E_el, psi_peak, alpha_bar.

The boundary integral is approximated from element centroids in strips near
x=+-0.5. It is a diagnostic proxy, not a replacement for exact boundary
quadrature.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

from render_late_cycles import parse_settings, detect_fourier
from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import compute_energy, gradients, stress

DEVICE = torch.device("cpu")
DEFAULT_ARCHIVE = (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N300_R0.0_Umax0.12"
)


def default_cycles(archive: Path, n: int = 12) -> list[int]:
    cycles = []
    for p in (archive / "best_models").glob("trained_1NN_*.pt"):
        try:
            cycles.append(int(p.stem.rsplit("_", 1)[-1]))
        except ValueError:
            pass
    cycles = sorted(cycles)
    if len(cycles) <= n:
        return cycles
    picks = np.linspace(0, len(cycles) - 1, n).round().astype(int)
    return [cycles[i] for i in picks]


def detect_exact_bc_extended(archive: Path) -> dict | None:
    settings = parse_settings(archive / "model_settings.txt")
    if settings.get("exact_bc_enable", "False").lower() == "true":
        mode = settings.get("exact_bc_mode", "sent_plane_strain")
        out = {"enable": True, "mode": mode}
        if "exact_bc_nu" in settings:
            out["nu"] = float(settings["exact_bc_nu"])
        return out
    if "_exactBCsent" in archive.name:
        nu = float(settings.get("exact_bc_nu", 0.3))
        return {"enable": True, "mode": "sent_plane_strain", "nu": nu}
    if "_femAnchorBC" in archive.name:
        return {"enable": True, "mode": "fem_anchor"}
    return None


def scalar_series(archive: Path, name: str):
    p = archive / "best_models" / name
    if not p.is_file():
        return None
    return np.load(p, allow_pickle=True)


def build_case(archive: Path):
    settings = parse_settings(archive / "model_settings.txt")
    disp_max = float(settings.get("disp_max", 0.12))
    coeff = float(settings.get("coeff", 1.0))
    seed = int(settings.get("seed", 1))
    exact_bc_dict = detect_exact_bc_extended(archive)
    fourier_dict = detect_fourier(archive)

    pff_dict = {"PFF_model": "AT1", "se_split": "volumetric", "tol_ir": 5e-3}
    mat_dict = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
    net_dict = {
        "hidden_layers": 8,
        "neurons": 400,
        "activation": "TrainableReLU",
        "init_coeff": coeff,
        "seed": seed,
        "compile": False,
    }
    numr_dict = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical"}
    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle = torch.tensor([np.pi / 2])
    crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    mesh_file = str(HERE / "meshed_geom2.msh")

    pffmodel, matprop, network = construct_model(
        pff_dict, mat_dict, net_dict, domain_extrema, DEVICE,
        williams_dict=None, fourier_dict=fourier_dict
    )
    inp, t_conn, area_t, hist_alpha = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=mesh_file, device=DEVICE
    )
    fc = FieldComputation(
        net=network,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor([disp_max], device=DEVICE),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        l0=mat_dict["l0"],
        exact_bc_dict=exact_bc_dict,
    )
    return settings, disp_max, pffmodel, matprop, fc, inp, t_conn, area_t, hist_alpha


def weighted_rms(x: np.ndarray, w: np.ndarray) -> float:
    return float(np.sqrt(np.sum(w * x * x) / np.sum(w))) if np.sum(w) > 0 else float("nan")


def weighted_mean(x: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * x) / np.sum(w)) if np.sum(w) > 0 else float("nan")


def audit_cycle(archive: Path, cycle: int, case, x_thresh: float, e_series, psi_series, ab_series) -> dict:
    settings, disp_max, pffmodel, matprop, fc, inp, t_conn, area_t, hist_alpha0 = case
    ckpt = archive / "best_models" / f"trained_1NN_{cycle}.pt"
    fc.net.load_state_dict(torch.load(str(ckpt), map_location=DEVICE, weights_only=True))
    fc.net.eval()

    step_path = archive / "best_models" / f"checkpoint_step_{cycle}.pt"
    hist_alpha = hist_alpha0
    f_fatigue = 1.0
    if step_path.is_file():
        step = torch.load(str(step_path), map_location=DEVICE)
        hist_alpha = step.get("hist_alpha", hist_alpha0).to(DEVICE)
        if "hist_fat" in step:
            alpha_bar = step["hist_fat"].to(DEVICE)
            f_fatigue = torch.ones_like(alpha_bar)
            mask = alpha_bar > 0.5
            f_fatigue[mask] = (1.0 / (alpha_bar[mask] + 0.5)) ** 2

    with torch.no_grad():
        u, v, alpha = fc.fieldCalculation(inp)
        e11, e22, e12, _, _ = gradients(inp, u, v, alpha, area_t, t_conn)
        alpha_e = (alpha[t_conn[:, 0]] + alpha[t_conn[:, 1]] + alpha[t_conn[:, 2]]) / 3.0
        sxx_t, syy_t, sxy_t = stress(e11, e22, e12, alpha_e, matprop, pffmodel)
        e_el, e_d, e_hist = compute_energy(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_t, t_conn,
            f_fatigue=f_fatigue,
        )

    pts = inp.detach().cpu().numpy()
    t_np = t_conn.detach().cpu().numpy()
    area = area_t.detach().cpu().numpy().reshape(-1)
    cent = pts[t_np].mean(axis=1)
    u_e = u.detach().cpu().numpy()[t_np].mean(axis=1)
    v_e = v.detach().cpu().numpy()[t_np].mean(axis=1)
    sxx = sxx_t.detach().cpu().numpy().reshape(-1)
    syy = syy_t.detach().cpu().numpy().reshape(-1)
    sxy = sxy_t.detach().cpu().numpy().reshape(-1)

    bulk = (np.abs(cent[:, 0]) <= x_thresh) & (np.abs(cent[:, 1]) <= 0.45)
    s_ref_max = float(np.max(np.abs(syy[bulk]))) if np.any(bulk) else float("nan")
    s_ref_rms = weighted_rms(syy[bulk], area[bulk]) if np.any(bulk) else float("nan")
    s_ref = s_ref_max if np.isfinite(s_ref_max) and s_ref_max > 1e-30 else 1.0

    rows = {
        "cycle": cycle,
        "E_el_recomputed": float(e_el),
        "E_total_recomputed": float(e_el + e_d + e_hist),
        "bulk_syy_max_abs": s_ref_max,
        "bulk_syy_rms": s_ref_rms,
    }
    if e_series is not None and cycle < len(e_series):
        rows["E_el_saved"] = float(np.asarray(e_series[cycle]).reshape(-1)[-1])
    if psi_series is not None and cycle < len(psi_series):
        p = np.asarray(psi_series[cycle]).reshape(-1)
        rows["psi_peak_saved"] = float(p[1] if p.size > 1 else p[-1])
    if ab_series is not None and cycle < len(ab_series):
        rows["alpha_bar_max_saved"] = float(ab_series[cycle, 0])
        rows["alpha_bar_mean_saved"] = float(ab_series[cycle, 1])
        rows["f_min_saved"] = float(ab_series[cycle, 2])

    band_width = 0.5 - x_thresh
    for side, mask, nx in [
        ("L", cent[:, 0] <= -x_thresh, -1.0),
        ("R", cent[:, 0] >= x_thresh, 1.0),
    ]:
        if not np.any(mask):
            continue
        w_line = area[mask] / band_width
        tx = nx * sxx[mask]
        ty = nx * sxy[mask]
        traction_norm = np.sqrt(tx * tx + ty * ty)
        work_density = tx * u_e[mask] + ty * v_e[mask]
        rows[f"{side}_max_tn_over_ref"] = float(np.max(np.abs(tx)) / s_ref)
        rows[f"{side}_max_ts_over_ref"] = float(np.max(np.abs(ty)) / s_ref)
        rows[f"{side}_rms_t_over_ref"] = weighted_rms(traction_norm, w_line) / s_ref
        rows[f"{side}_rms_tn_over_ref"] = weighted_rms(tx, w_line) / s_ref
        rows[f"{side}_rms_ts_over_ref"] = weighted_rms(ty, w_line) / s_ref
        rows[f"{side}_signed_mean_tn_over_ref"] = weighted_mean(tx, w_line) / s_ref
        rows[f"{side}_signed_mean_ts_over_ref"] = weighted_mean(ty, w_line) / s_ref
        rows[f"{side}_cancellation_tn"] = abs(weighted_mean(tx, w_line)) / weighted_mean(np.abs(tx), w_line)
        rows[f"{side}_cancellation_ts"] = abs(weighted_mean(ty, w_line)) / weighted_mean(np.abs(ty), w_line)
        rows[f"{side}_abs_boundary_work_over_Eel"] = float(np.sum(w_line * np.abs(work_density)) / max(abs(float(e_el)), 1e-30))
        rows[f"{side}_signed_boundary_work_over_Eel"] = float(np.sum(w_line * work_density) / max(abs(float(e_el)), 1e-30))

    both = (cent[:, 0] <= -x_thresh) | (cent[:, 0] >= x_thresh)
    nx = np.where(cent[both, 0] < 0, -1.0, 1.0)
    w = area[both] / band_width
    tx = nx * sxx[both]
    ty = nx * sxy[both]
    tnorm = np.sqrt(tx * tx + ty * ty)
    work = tx * u_e[both] + ty * v_e[both]
    rows["both_rms_t_over_ref"] = weighted_rms(tnorm, w) / s_ref
    rows["both_signed_mean_tn_over_ref"] = weighted_mean(tx, w) / s_ref
    rows["both_signed_mean_ts_over_ref"] = weighted_mean(ty, w) / s_ref
    rows["both_cancellation_tn"] = abs(weighted_mean(tx, w)) / weighted_mean(np.abs(tx), w)
    rows["both_cancellation_ts"] = abs(weighted_mean(ty, w)) / weighted_mean(np.abs(ty), w)
    rows["both_abs_boundary_work_over_Eel"] = float(np.sum(w * np.abs(work)) / max(abs(float(e_el)), 1e-30))
    rows["both_signed_boundary_work_over_Eel"] = float(np.sum(w * work) / max(abs(float(e_el)), 1e-30))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path, nargs="?", default=HERE / DEFAULT_ARCHIVE)
    ap.add_argument("--cycles", default=None, help="comma-separated cycles; default: 12 spread over archive")
    ap.add_argument("--x-thresh", type=float, default=0.45)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    archive = args.archive.resolve()
    cycles = [int(x) for x in args.cycles.split(",") if x.strip()] if args.cycles else default_cycles(archive)
    if args.out is None:
        args.out = archive / "best_models" / "v7_global_audit.csv"

    case = build_case(archive)
    e_series = scalar_series(archive, "E_el_vs_cycle.npy")
    psi_series = scalar_series(archive, "psi_peak_vs_cycle.npy")
    ab_series = scalar_series(archive, "alpha_bar_vs_cycle.npy")

    rows = []
    for c in cycles:
        print(f"cycle {c}")
        rows.append(audit_cycle(archive, c, case, args.x_thresh, e_series, psi_series, ab_series))
    df = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    cols = [
        "cycle", "E_el_recomputed", "psi_peak_saved", "alpha_bar_max_saved",
        "both_rms_t_over_ref", "both_cancellation_tn", "both_cancellation_ts",
        "both_abs_boundary_work_over_Eel", "both_signed_boundary_work_over_Eel",
        "L_rms_t_over_ref", "R_rms_t_over_ref",
    ]
    shown = [c for c in cols if c in df.columns]
    print(df[shown].to_string(index=False))
    print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
