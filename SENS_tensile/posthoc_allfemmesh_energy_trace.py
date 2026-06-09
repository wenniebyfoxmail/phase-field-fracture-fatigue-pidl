#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "source"))

USER_ARGS = sys.argv[1:]

# Match the strict all-FEM-mesh Taobo runs: 8x400, seed 1, TrainableReLU, coeff 1.0.
sys.argv = ["main.py", "8", "400", "1", "TrainableReLU", "1.0"]

import config  # noqa: E402
from compute_energy import compute_energy  # noqa: E402
from construct_model import construct_model  # noqa: E402
from fatigue_history import compute_fatigue_degrad  # noqa: E402
from field_computation import FieldComputation  # noqa: E402
from input_data_from_mesh import prep_input_data  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def parse_settings(archive: Path) -> dict[str, str]:
    out = {}
    settings_file = archive / "model_settings.txt"
    if not settings_file.is_file():
        return out
    for line in settings_file.read_text().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def cycle_num(path: Path) -> int:
    match = re.search(r"_(\d+)\.pt$", path.name)
    if not match:
        raise ValueError(path)
    return int(match.group(1))


def numbered_model_files(best_models_dir: Path) -> list[Path]:
    files = []
    for path in best_models_dir.glob("trained_1NN_*.pt"):
        if re.search(r"_(\d+)\.pt$", path.name):
            files.append(path)
    return sorted(files, key=cycle_num)


def build_case(mesh_file: str):
    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict,
        config.mat_prop_dict,
        config.network_dict,
        config.domain_extrema,
        DEVICE,
        williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema,
        lmbda=torch.tensor([0.0], device=DEVICE),
        theta=config.loading_angle,
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=config.williams_dict,
        ansatz_dict=config.ansatz_dict,
        l0=config.mat_prop_dict["l0"],
        symmetry_prior=config.symmetry_prior,
        exact_bc_dict=config.exact_bc_dict,
        local_patch_dict=config.local_patch_dict,
    )
    field_comp.net = field_comp.net.to(DEVICE)
    field_comp.domain_extrema = field_comp.domain_extrema.to(DEVICE)
    field_comp.theta = field_comp.theta.to(DEVICE)
    inp, t_conn, area_t, hist_alpha0 = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        config.numr_dict,
        mesh_file=mesh_file,
        device=DEVICE,
    )
    if t_conn is None:
        elem_centroids = None
    else:
        cx = (inp[t_conn[:, 0], 0] + inp[t_conn[:, 1], 0] + inp[t_conn[:, 2], 0]) / 3.0
        cy = (inp[t_conn[:, 0], 1] + inp[t_conn[:, 1], 1] + inp[t_conn[:, 2], 1]) / 3.0
        elem_centroids = torch.stack([cx, cy], dim=1).detach()
    return pffmodel, matprop, field_comp, inp, t_conn, area_t, hist_alpha0, elem_centroids


def extract_one(archive: Path, out_csv: Path) -> None:
    settings = parse_settings(archive)
    mesh_file = settings.get("fine_mesh_file") or str(HERE / "meshed_geom_fem_soft_hist0.msh")
    pffmodel, matprop, field_comp, inp, t_conn, area_t, hist_alpha0, elem_centroids = build_case(mesh_file)

    best_models = archive / "best_models"
    umax = float(settings.get("umax", 0.12))
    rows = []
    for model_path in numbered_model_files(best_models):
        cycle = cycle_num(model_path)
        ckpt_path = best_models / f"checkpoint_step_{cycle}.pt"
        if not ckpt_path.is_file():
            continue

        field_comp.lmbda = torch.tensor(umax, device=DEVICE)
        field_comp.net.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=True))
        field_comp.net.eval()

        ckpt = torch.load(ckpt_path, map_location=DEVICE)
        hist_alpha = ckpt.get("hist_alpha", hist_alpha0).to(DEVICE)
        hist_fat = ckpt.get("hist_fat")
        if hist_fat is None:
            f_fatigue = 1.0
        else:
            f_fatigue = compute_fatigue_degrad(
                hist_fat.to(DEVICE),
                config.fatigue_dict,
                elem_centroids=elem_centroids,
            )

        with torch.no_grad():
            u, v, alpha = field_comp.fieldCalculation(inp)
            e_el, e_d_degraded, e_irres = compute_energy(
                inp,
                u,
                v,
                alpha,
                hist_alpha,
                matprop,
                pffmodel,
                area_t,
                t_conn,
                f_fatigue=f_fatigue,
            )
            _, e_d_raw, _ = compute_energy(
                inp,
                u,
                v,
                alpha,
                hist_alpha,
                matprop,
                pffmodel,
                area_t,
                t_conn,
                f_fatigue=1.0,
            )

        total_degraded = e_el + e_d_degraded + e_irres
        total_raw = e_el + e_d_raw + e_irres
        rows.append(
            {
                "cycle": cycle,
                "E_el": float(e_el.detach().cpu()),
                "E_d": float(e_d_degraded.detach().cpu()),
                "E_d_degraded": float(e_d_degraded.detach().cpu()),
                "E_d_raw": float(e_d_raw.detach().cpu()),
                "E_irres": float(e_irres.detach().cpu()),
                "E_total": float(total_degraded.detach().cpu()),
                "E_total_degraded": float(total_degraded.detach().cpu()),
                "E_total_raw": float(total_raw.detach().cpu()),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "cycle",
                "E_el",
                "E_d",
                "E_d_degraded",
                "E_d_raw",
                "E_irres",
                "E_total",
                "E_total_degraded",
                "E_total_raw",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"{out_csv} rows={len(rows)} last={rows[-1] if rows else None}")


def main() -> None:
    if len(USER_ARGS) < 3:
        raise SystemExit(
            "usage: posthoc_allfemmesh_energy_trace.py "
            "<baseline_archive> <adapthist_archive> <out_dir>"
        )
    baseline = Path(USER_ARGS[0])
    adapthist = Path(USER_ARGS[1])
    out_dir = Path(USER_ARGS[2])
    extract_one(baseline, out_dir / "baseline_energy_components.csv")
    extract_one(adapthist, out_dir / "adapthist_energy_components.csv")


if __name__ == "__main__":
    main()
