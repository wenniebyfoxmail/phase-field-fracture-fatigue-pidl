#!/usr/bin/env python3
"""Extract generalized reaction and energy curves from a completed forward run."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--force-cpu", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    run = args.run.expanduser().resolve()
    manifest = json.loads((run / "forward_manifest.json").read_text(encoding="utf-8"))
    output = (args.out or (run / "reaction_curve.csv")).expanduser().resolve()

    here = Path(__file__).resolve().parent
    repo = here.parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(repo / "source"))
    sys.argv = [
        Path(__file__).name,
        str(manifest["hidden_layers"]),
        str(manifest["neurons"]),
        str(manifest["seed"]),
        str(manifest["activation"]),
        str(manifest["init_coeff"]),
    ]

    import torch

    import config
    from compute_energy import compute_energy
    from construct_model import construct_model
    from field_computation import FieldComputation
    from input_data_from_mesh import prep_input_data

    device = "cpu" if args.force_cpu else config.device
    config.mat_prop_dict.update(
        {
            "mat_E": float(manifest["mat_E"]),
            "mat_nu": float(manifest["mat_nu"]),
            "w1": float(manifest["w1"]),
            "l0": float(manifest["l0"]),
        }
    )
    config.fatigue_dict["fatigue_on"] = False
    try:
        config.writer.close()
    except Exception:
        pass

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict,
        config.mat_prop_dict,
        config.network_dict,
        config.domain_extrema,
        device,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema,
        lmbda=torch.tensor(0.0, device=device),
        theta=config.loading_angle,
        alpha_constraint=config.numr_dict["alpha_constraint"],
    )
    field_comp.net = field_comp.net.to(device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(device)
    field_comp.theta = field_comp.theta.to(device)
    inp, t_conn, area, hist_alpha = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        config.numr_dict,
        mesh_file=manifest["fine_mesh"],
        device=device,
    )

    rows: list[dict[str, float | int]] = []
    for index, displacement in enumerate(manifest["displacements"]):
        checkpoint = run / "best_models" / f"trained_1NN_{index}.pt"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"missing checkpoint: {checkpoint}")
        field_comp.net.load_state_dict(torch.load(checkpoint, map_location=device))
        load = torch.tensor(float(displacement), device=device, requires_grad=True)
        field_comp.lmbda = load
        u, v, alpha = field_comp.fieldCalculation(inp)
        e_el, e_d, e_hist = compute_energy(
            inp,
            u,
            v,
            alpha,
            hist_alpha,
            matprop,
            pffmodel,
            area,
            t_conn,
            f_fatigue=1.0,
        )
        total = e_el + e_d + e_hist
        reaction = torch.autograd.grad(total, load, retain_graph=False)[0]
        elastic_identity = 2.0 * e_el.detach() / load.detach()
        rows.append(
            {
                "step": index,
                "displacement": float(displacement),
                "reaction": float(reaction.detach().cpu()),
                "reaction_elastic_identity": float(elastic_identity.cpu()),
                "reaction_identity_abs_error": float(
                    torch.abs(reaction.detach() - elastic_identity).cpu()
                ),
                "E_el": float(e_el.detach().cpu()),
                "E_d": float(e_d.detach().cpu()),
                "E_hist": float(e_hist.detach().cpu()),
                "E_total": float(total.detach().cpu()),
                "alpha_max": float(alpha.detach().max().cpu()),
                "alpha_mean": float(alpha.detach().mean().cpu()),
            }
        )
        hist_alpha = alpha.detach()

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
