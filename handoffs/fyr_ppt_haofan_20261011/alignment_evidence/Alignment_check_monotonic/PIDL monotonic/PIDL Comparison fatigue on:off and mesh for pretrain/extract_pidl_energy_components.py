#!/usr/bin/env python3
"""Extract E_el, E_d, and E_irrev histories from PIDL monotonic archives."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
import torch


DISP = np.concatenate((np.linspace(0.0, 0.075, 4), np.linspace(0.1, 0.2, 21)), axis=0)[1:]


def parse_settings(path: Path) -> dict[str, str]:
    settings = {}
    if not path.exists():
        return settings
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        settings[key.strip()] = value.strip()
    return settings


def cycle_number(path: Path) -> int:
    match = re.search(r"trained_1NN_(\d+)$", path.stem)
    if not match:
        raise ValueError(f"Cannot parse cycle number from {path}")
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sens-dir", type=Path, default=None)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    archive = args.archive.resolve()
    sens_dir = args.sens_dir.resolve() if args.sens_dir else archive.parent
    source_dir = sens_dir.parent / "source"
    sys.path.insert(0, str(sens_dir))
    sys.path.insert(0, str(source_dir))

    from construct_model import construct_model
    from input_data_from_mesh import prep_input_data
    from compute_energy import compute_energy
    from field_computation import FieldComputation
    from fatigue_history import compute_fatigue_degrad

    device = args.device
    best = archive / "best_models"
    settings = parse_settings(archive / "model_settings.txt")
    fatigue_on = settings.get("fatigue_on", "False").lower() == "true"
    mesh_file = settings.get("fine_mesh_file") or str(sens_dir / "meshed_geom_fem_soft_hist0.msh")

    network_dict = {
        "model_type": "MLP",
        "hidden_layers": int(settings.get("hidden_layers", 8)),
        "neurons": int(settings.get("neurons", 400)),
        "seed": int(settings.get("seed", 1)),
        "activation": settings.get("activation", "TrainableReLU"),
        "init_coeff": float(settings.get("coeff", 1.0)),
    }
    pff_dict = {
        "PFF_model": settings.get("PFF_model", "AT1"),
        "se_split": settings.get("se_split", "volumetric"),
        "tol_ir": float(settings.get("tol_ir", 5e-3)),
        "residual_stiffness": float(settings.get("residual_stiffness", 0.0)),
    }
    mat_dict = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
    numr_dict = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical"}
    crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], device=device)
    loading_angle = torch.tensor([np.pi / 2], device=device)

    pffmodel, matprop, network = construct_model(
        pff_dict, mat_dict, network_dict, domain_extrema, device
    )
    inp, t_conn, area_t, hist_alpha_initial = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=mesh_file, device=device
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        l0=mat_dict["l0"],
    )
    field_comp.net = field_comp.net.to(device)

    if t_conn is not None:
        centroids = (
            inp[t_conn[:, 0], :] + inp[t_conn[:, 1], :] + inp[t_conn[:, 2], :]
        ) / 3.0
    else:
        centroids = None

    fatigue_dict = {
        "fatigue_on": fatigue_on,
        "loading_type": "monotonic",
        "R_ratio": 0.0,
        "accum_type": "carrara",
        "degrad_type": "asymptotic",
        "alpha_T": 0.5,
        "kappa": 1.0,
        "spatial_alpha_T": {"enable": False},
    }

    rows = []
    model_files = [
        p for p in best.glob("trained_1NN_*.pt")
        if re.search(r"trained_1NN_\d+$", p.stem)
    ]
    model_files = sorted(model_files, key=cycle_number)
    for model_file in model_files:
        j = cycle_number(model_file)
        if j >= len(DISP):
            continue
        field_comp.lmbda = torch.tensor(float(DISP[j]), device=device)
        state = torch.load(model_file, map_location=device, weights_only=True)
        field_comp.net.load_state_dict(state)
        field_comp.net.eval()

        if j == 0:
            hist_alpha_for_loss = hist_alpha_initial
            f_fatigue = torch.tensor(1.0, device=device)
        else:
            prev = torch.load(best / f"checkpoint_step_{j - 1}.pt", map_location=device)
            hist_alpha_for_loss = prev["hist_alpha"].to(device)
            if fatigue_on and "hist_fat" in prev:
                hist_fat = prev["hist_fat"].to(device)
                f_fatigue = compute_fatigue_degrad(hist_fat, fatigue_dict, elem_centroids=centroids)
            else:
                f_fatigue = torch.tensor(1.0, device=device)

        with torch.no_grad():
            u, v, alpha = field_comp.fieldCalculation(inp)
            e_el, e_d, e_irrev = compute_energy(
                inp, u, v, alpha, hist_alpha_for_loss,
                matprop, pffmodel, area_t, t_conn,
                f_fatigue=f_fatigue,
            )

        e_el_v = float(e_el.detach().cpu())
        e_d_v = float(e_d.detach().cpu())
        e_irrev_v = float(e_irrev.detach().cpu())
        rows.append(
            {
                "cycle": j,
                "U": float(DISP[j]),
                "E_el": e_el_v,
                "E_d": e_d_v,
                "E_irrev": e_irrev_v,
                "E_total": e_el_v + e_d_v + e_irrev_v,
                "archive": str(archive),
                "model_file": str(model_file),
                "hist_alpha_reference": "initial" if j == 0 else f"checkpoint_step_{j - 1}.pt",
                "f_fatigue_reference": "1.0" if (not fatigue_on or j == 0) else f"checkpoint_step_{j - 1}.pt hist_fat",
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"archive: {archive.name}")
    print(f"rows: {len(rows)}")
    print(f"out: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
