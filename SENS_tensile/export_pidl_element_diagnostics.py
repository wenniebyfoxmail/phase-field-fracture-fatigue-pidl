#!/usr/bin/env python3
"""Export cycle-end PIDL element fields from an existing archive.

This is the post-hoc counterpart of model_train.py's optional
``element_diagnostics`` hook. It lets us test the FEM/PIDL comparison pipeline
on already-finished baseline archives before waiting for new reruns.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["export_pidl_element_diagnostics", "8", "400", "1", "TrainableReLU", "1.0"]
import config
from compute_energy import (compute_energy_per_elem, get_psi_plus_per_elem)
from construct_model import construct_model
from fatigue_history import compute_fatigue_degrad
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
sys.argv = _saved_argv


def safe_torch_load(path: Path, device: torch.device):
    try:
        return torch.load(str(path), map_location=device, weights_only=True)
    except TypeError:
        return torch.load(str(path), map_location=device)


def parse_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    if not path.exists():
        return settings
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            settings[key.strip()] = value.strip()
    return settings


def bool_setting(settings: dict[str, str], key: str) -> bool:
    return settings.get(key, "False").strip().lower() in {"1", "true", "yes"}


def build_field_computation(archive: Path, device: torch.device, umax: float):
    settings = parse_settings(archive / "model_settings.txt")
    net_cfg = dict(config.network_dict)
    for key, target in [("hidden_layers", "hidden_layers"),
                        ("neurons", "neurons"),
                        ("seed", "seed")]:
        if key in settings:
            net_cfg[target] = int(float(settings[key]))
    if "activation" in settings:
        net_cfg["activation"] = settings["activation"]
    if "coeff" in settings:
        net_cfg["init_coeff"] = float(settings["coeff"])

    williams_dict = None
    if "williams" in archive.name or bool_setting(settings, "williams_enable"):
        williams_dict = {"enable": True, "theta_mode": "atan2", "r_min": 1e-6}

    fourier_dict = None
    if "fourier_sig" in archive.name or bool_setting(settings, "fourier_enable"):
        fourier_dict = dict(getattr(config, "fourier_dict", {}))
        fourier_dict["enable"] = True

    exact_bc_dict = None
    if bool_setting(settings, "exact_bc_enable"):
        exact_bc_dict = {
            "enable": True,
            "mode": settings.get("exact_bc_mode", "sent_plane_strain"),
        }
    elif "_femAnchorBC" in archive.name:
        exact_bc_dict = {"enable": True, "mode": "fem_anchor"}

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict, net_cfg,
        config.domain_extrema, device,
        williams_dict=williams_dict, fourier_dict=fourier_dict,
    )
    inp, t_conn, area_t, _ = prep_input_data(
        matprop, pffmodel, config.crack_dict, config.numr_dict,
        mesh_file=str(HERE / "meshed_geom2.msh"), device=device,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema.to(device),
        lmbda=torch.tensor([umax], device=device),
        theta=config.loading_angle.to(device),
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=williams_dict,
        l0=config.mat_prop_dict["l0"],
        exact_bc_dict=exact_bc_dict,
    )
    field_comp.net = field_comp.net.to(device)
    return field_comp, pffmodel, matprop, inp, t_conn, area_t


def tensor_np(value: torch.Tensor | float, like_tensor: torch.Tensor | None = None) -> np.ndarray:
    if torch.is_tensor(value):
        return value.detach().cpu().numpy()
    if like_tensor is not None:
        return np.full(int(like_tensor.numel()), float(value), dtype=np.float32)
    return np.asarray(value)


def masked_stats(values: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    selected = values[mask]
    if selected.size == 0:
        return {"max": np.nan, "mean": np.nan, "min": np.nan, "sum": 0.0}
    return {
        "max": float(np.nanmax(selected)),
        "mean": float(np.nanmean(selected)),
        "min": float(np.nanmin(selected)),
        "sum": float(np.nansum(selected)),
    }


def export_cycle(archive: Path, cycle: int, out_dir: Path, device: torch.device,
                 umax: float, write_fields: bool = True,
                 precrack_half_width: float = 0.02,
                 precrack_x_max: float = 0.0) -> dict[str, float | int | str]:
    best = archive / "best_models"
    model_path = best / f"trained_1NN_{cycle}.pt"
    ckpt_path = best / f"checkpoint_step_{cycle}.pt"
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(ckpt_path)

    field_comp, pffmodel, matprop, inp, t_conn, area_t = build_field_computation(
        archive, device, umax,
    )
    field_comp.net.load_state_dict(safe_torch_load(model_path, device))
    field_comp.net.eval()
    ckpt = safe_torch_load(ckpt_path, device)
    hist_alpha = ckpt["hist_alpha"].to(device)
    hist_fat = ckpt.get("hist_fat")
    if hist_fat is None:
        hist_fat = torch.zeros(t_conn.shape[0], device=device)
    else:
        hist_fat = hist_fat.to(device)
    psi_prev = ckpt.get("psi_plus_prev")
    if psi_prev is None:
        psi_prev = torch.zeros_like(hist_fat)
    else:
        psi_prev = psi_prev.to(device)
    f_fatigue = compute_fatigue_degrad(hist_fat, config.fatigue_dict)

    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        alpha_elem = (alpha[t_conn[:, 0]] + alpha[t_conn[:, 1]] + alpha[t_conn[:, 2]]) / 3.0
        psi_plus = get_psi_plus_per_elem(
            inp, u, v, alpha, matprop, pffmodel, area_t, t_conn,
        )
        e_el, e_d, e_hist = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_t, t_conn,
            f_fatigue=f_fatigue,
        )
        elem_x = (inp[t_conn[:, 0], 0] + inp[t_conn[:, 1], 0] + inp[t_conn[:, 2], 0]) / 3.0
        elem_y = (inp[t_conn[:, 0], 1] + inp[t_conn[:, 1], 1] + inp[t_conn[:, 2], 1]) / 3.0

    out_path = out_dir / f"element_fields_cycle_{cycle:04d}.npz"
    hist_np = tensor_np(hist_fat).reshape(-1)
    f_np = tensor_np(f_fatigue).reshape(-1)
    psi_np = tensor_np(psi_plus).reshape(-1)
    e_el_np = tensor_np(e_el).reshape(-1)
    e_d_np = tensor_np(e_d).reshape(-1)
    e_hist_np = tensor_np(e_hist).reshape(-1)
    elem_x_np = tensor_np(elem_x).reshape(-1)
    elem_y_np = tensor_np(elem_y).reshape(-1)
    precrack_mask = (elem_x_np <= precrack_x_max) & (np.abs(elem_y_np) <= precrack_half_width)
    outside_precrack = ~precrack_mask
    hist_out = masked_stats(hist_np, outside_precrack)
    f_out = masked_stats(f_np, outside_precrack)
    psi_out = masked_stats(psi_np, outside_precrack)
    e_el_out = masked_stats(e_el_np, outside_precrack)
    e_d_out = masked_stats(e_d_np, outside_precrack)
    e_hist_out = masked_stats(e_hist_np, outside_precrack)
    if write_fields:
        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            out_path,
            cycle=np.array([cycle], dtype=np.int32),
            elem_x=elem_x_np.astype(np.float32),
            elem_y=elem_y_np.astype(np.float32),
            area_elem=tensor_np(area_t).reshape(-1).astype(np.float32),
            alpha_elem=tensor_np(alpha_elem).reshape(-1).astype(np.float32),
            hist_fat_elem=hist_np.astype(np.float32),
            f_fatigue_elem=f_np.astype(np.float32),
            psi_plus_elem=psi_np.astype(np.float32),
            psi_plus_prev_elem=tensor_np(psi_prev).reshape(-1).astype(np.float32),
            E_el_elem=e_el_np.astype(np.float32),
            E_d_elem=e_d_np.astype(np.float32),
            E_hist_elem=e_hist_np.astype(np.float32),
            residual_abs_Eel_Ed=(np.abs(e_el_np) + np.abs(e_d_np)).astype(np.float32),
        )
    return {
        "cycle": cycle,
        "path": str(out_path) if write_fields else "",
        "n_elem": int(alpha_elem.numel()),
        "alpha_max": float(alpha_elem.max().detach().cpu()),
        "hist_max": float(hist_fat.max().detach().cpu()),
        "hist_mean": float(hist_fat.mean().detach().cpu()),
        "f_min": float(f_fatigue.min().detach().cpu()),
        "psi_max": float(psi_plus.max().detach().cpu()),
        "E_el": float(e_el.sum().detach().cpu()),
        "E_d": float(e_d.sum().detach().cpu()),
        "E_hist": float(e_hist.sum().detach().cpu()),
        "precrack_half_width": float(precrack_half_width),
        "precrack_x_max": float(precrack_x_max),
        "n_elem_precrack_mask": int(precrack_mask.sum()),
        "n_elem_outside_precrack": int(outside_precrack.sum()),
        "hist_max_outside_precrack": hist_out["max"],
        "hist_mean_outside_precrack": hist_out["mean"],
        "f_min_outside_precrack": f_out["min"],
        "f_mean_outside_precrack": f_out["mean"],
        "psi_max_outside_precrack": psi_out["max"],
        "psi_mean_outside_precrack": psi_out["mean"],
        "E_el_outside_precrack": e_el_out["sum"],
        "E_d_outside_precrack": e_d_out["sum"],
        "E_hist_outside_precrack": e_hist_out["sum"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--cycles", default="40,70,75,80")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--summary-only", action="store_true",
                        help="Write only the scalar CSV summary, not per-cycle NPZ field files.")
    parser.add_argument("--precrack-half-width", type=float, default=0.02,
                        help="Half-width of the initial pre-crack corridor to exclude in masked summaries.")
    parser.add_argument("--precrack-x-max", type=float, default=0.0,
                        help="Maximum x-coordinate of the initial pre-crack corridor.")
    args = parser.parse_args()

    archive = args.archive.resolve()
    out_dir = args.out_dir or (archive / "element_diagnostics_posthoc")
    cycles = [int(c.strip()) for c in args.cycles.split(",") if c.strip()]
    device = torch.device(args.device)

    rows = []
    for cycle in cycles:
        rows.append(export_cycle(
            archive, cycle, out_dir, device, args.umax,
            write_fields=not args.summary_only,
            precrack_half_width=args.precrack_half_width,
            precrack_x_max=args.precrack_x_max,
        ))
        print(rows[-1])

    import csv
    csv_path = out_dir / "element_diagnostics_summary.csv"
    out_dir.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
