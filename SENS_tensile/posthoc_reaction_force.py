#!/usr/bin/env python3
"""Estimate PIDL reaction force by central-differencing energy at Umax +/- eps."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["posthoc_reaction_force", "8", "400", "1", "TrainableReLU", "1.0"]
from config import domain_extrema, loading_angle, network_dict, mat_prop_dict, numr_dict, PFF_model_dict, crack_dict
sys.argv = _saved_argv

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import compute_energy

DEVICE = torch.device("cpu")
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


def load_case(archive: Path, cycle: int):
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
        lmbda=torch.tensor([0.0], device=DEVICE),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None,
        l0=mat_prop_dict["l0"],
        exact_bc_dict=exact_bc_from_settings(archive),
    )
    ckpt = archive / "best_models" / f"trained_1NN_{cycle}.pt"
    field_comp.net.load_state_dict(torch.load(str(ckpt), map_location=DEVICE, weights_only=True))
    field_comp.net.eval()
    step = torch.load(str(archive / "best_models" / f"checkpoint_step_{cycle}.pt"), map_location=DEVICE)
    hist_alpha = step.get("hist_alpha", hist_alpha0).to(DEVICE)
    hist_fat = step.get("hist_fat")
    f_fatigue = 1.0
    if hist_fat is not None:
        alpha_bar = hist_fat.to(DEVICE)
        alpha_t = 0.5
        f_fatigue = torch.ones_like(alpha_bar)
        mask = alpha_bar > alpha_t
        f_fatigue[mask] = (2.0 * alpha_t / (alpha_bar[mask] + alpha_t)) ** 2
    return field_comp, inp, t_conn, area_t, hist_alpha, matprop, pffmodel, f_fatigue


def energies_at(field_comp, inp, t_conn, area_t, hist_alpha, matprop, pffmodel, f_fatigue, u: float):
    field_comp.lmbda = torch.tensor([u], device=DEVICE)
    with torch.no_grad():
        disp_u, disp_v, alpha = field_comp.fieldCalculation(inp)
        e_el, e_d, e_hist = compute_energy(
            inp, disp_u, disp_v, alpha, hist_alpha, matprop, pffmodel, area_t, t_conn,
            f_fatigue=f_fatigue,
        )
    return float(e_el), float(e_d), float(e_hist), float(e_el + e_d + e_hist)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, default=HERE / DEFAULT_ARCHIVE)
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--eps", type=float, default=1e-4)
    ap.add_argument("--cycles", default="1,5,40,70,80,82")
    ap.add_argument("--out", type=Path, default=HERE / "alignment_reaction_force_u012_baseline.csv")
    args = ap.parse_args()

    fem_csv = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_12_timeseries.csv")
    fem = pd.read_csv(fem_csv) if fem_csv.is_file() else pd.DataFrame()
    rows = []
    for cycle in [int(x) for x in args.cycles.split(",") if x.strip()]:
        print(f"cycle {cycle}")
        case = load_case(args.archive, cycle)
        em = energies_at(*case, args.umax - args.eps)
        e0 = energies_at(*case, args.umax)
        ep = energies_at(*case, args.umax + args.eps)
        reaction_elastic = (ep[0] - em[0]) / (2.0 * args.eps)
        reaction_total = (ep[3] - em[3]) / (2.0 * args.eps)
        row = {
            "cycle": cycle,
            "umax": args.umax,
            "eps": args.eps,
            "PIDL_E_el_minus": em[0],
            "PIDL_E_el": e0[0],
            "PIDL_E_el_plus": ep[0],
            "PIDL_reaction_dEel_dU": reaction_elastic,
            "PIDL_reaction_dEtot_dU": reaction_total,
        }
        fr = fem[fem["N"] == cycle] if not fem.empty else pd.DataFrame()
        if len(fr):
            fr = fr.iloc[0]
            row["FEM_E_el"] = float(fr["E_el"])
            row["FEM_effective_reaction_2Eel_over_U"] = 2.0 * float(fr["E_el"]) / args.umax
            row["PIDL_over_FEM_effective_reaction"] = reaction_elastic / row["FEM_effective_reaction_2Eel_over_U"]
            if "W_ext" in fr:
                row["FEM_W_ext"] = float(fr["W_ext"])
        rows.append(row)
    df = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(df.to_string(index=False))
    print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
