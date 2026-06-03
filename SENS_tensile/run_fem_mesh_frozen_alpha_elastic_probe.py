#!/usr/bin/env python3
"""Frozen-alpha elastic c1 discriminator on the strict FEM mesh.

This is a deliberately narrow diagnostic.  It starts from a post-pretraining
PIDL network, fixes the phase-field damage to the analytic soft-hist0
precrack, optimises only the displacement field through the elastic energy,
and exports the resulting strain/psi fields.

Question: does the early PIDL/FEM psi_raw mismatch already appear when alpha is
not allowed to evolve?
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import torch


def _resolve_file(here: Path, filename: str | Path, launch_cwd: Path | None = None) -> Path:
    path = Path(filename).expanduser()
    if path.is_absolute():
        return path
    if launch_cwd is not None:
        from_launch = launch_cwd / path
        if from_launch.exists():
            return from_launch
    local = here / path
    if local.exists():
        return local
    for parent in here.parents:
        candidate = parent / "SENS_tensile" / path
        if candidate.exists():
            return candidate
    return local


def _safe_torch_load(path: Path, device: torch.device):
    try:
        return torch.load(str(path), map_location=device, weights_only=True)
    except TypeError:
        return torch.load(str(path), map_location=device)


def _tensor_np(value: torch.Tensor) -> np.ndarray:
    return value.detach().cpu().numpy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=10000)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--tag", default="softHist0_resStiff1e6_frozenAlphaElastic")
    parser.add_argument("--res-stiffness", type=float, default=1e-6)
    parser.add_argument("--init-ckpt", type=Path, default=None,
                        help="Post-pretraining state dict. If omitted, use random init.")
    parser.add_argument("--force-cpu", action="store_true")
    parser.add_argument("--log-every", type=int, default=250)
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = [
        "run_fem_mesh_frozen_alpha_elastic_probe.py",
        "8",
        "400",
        str(args.seed),
        "TrainableReLU",
        "1.0",
    ]
    launch_cwd = Path.cwd()
    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433
    from compute_energy import gradients, strain_energy_with_split
    from construct_model import construct_model
    from field_computation import FieldComputation
    from input_data_from_mesh import prep_input_data

    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.symmetry_prior = False
    config.PFF_model_dict["residual_stiffness"] = float(args.res_stiffness)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = 1
    config.rebuild_disp_cyclic()

    device = torch.device(config.device)
    mesh_file = _resolve_file(here, args.mesh_file, launch_cwd)
    init_ckpt = _resolve_file(here, args.init_ckpt, launch_cwd) if args.init_ckpt else None

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict,
        config.mat_prop_dict,
        config.network_dict,
        config.domain_extrema,
        device,
        williams_dict=None,
        fourier_dict=None,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema.to(device),
        lmbda=torch.tensor([float(args.umax)], device=device),
        theta=config.loading_angle.to(device),
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=None,
        l0=config.mat_prop_dict["l0"],
        exact_bc_dict={"enable": False},
        local_patch_dict=None,
    )
    field_comp.net = field_comp.net.to(device)

    if init_ckpt is not None and init_ckpt.exists():
        print(f"[FrozenAlphaElastic] loading init checkpoint: {init_ckpt}")
        field_comp.net.load_state_dict(_safe_torch_load(init_ckpt, device))
    elif init_ckpt is not None:
        raise FileNotFoundError(init_ckpt)
    else:
        print("[FrozenAlphaElastic] no init checkpoint supplied; using random init")

    inp, t_conn, area_t, hist_alpha = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        config.numr_dict,
        mesh_file=str(mesh_file),
        device=device,
    )
    alpha_fixed = hist_alpha.detach()
    alpha_elem_fixed = (
        alpha_fixed[t_conn[:, 0]] + alpha_fixed[t_conn[:, 1]] + alpha_fixed[t_conn[:, 2]]
    ) / 3.0

    fatigue_tag = (
        f"_fatigue_off_N1_R0.0_Umax{args.umax}"
        f"_femmesh_{args.tag}_ep{args.epochs}"
    )
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
    )
    model_path = config.resolve_archive_dir(here, dir_name)
    best = model_path / "best_models"
    diag = model_path / "element_diagnostics"
    best.mkdir(parents=True, exist_ok=True)
    diag.mkdir(parents=True, exist_ok=True)

    params = list(field_comp.parameters())
    optimizer = torch.optim.Rprop(params, lr=1e-5, step_sizes=(1e-10, 50))
    weight_decay = float(config.optimizer_dict["weight_decay"])
    loss_rows: list[tuple[int, float, float, float]] = []

    def forward_metrics():
        u, v, _alpha_ignored = field_comp.fieldCalculation(inp)
        eps_xx, eps_yy, eps_xy, _, _ = gradients(inp, u, v, alpha_fixed, area_t, t_conn)
        e_el_density, psi_raw = strain_energy_with_split(
            eps_xx, eps_yy, eps_xy, alpha_elem_fixed, matprop, pffmodel
        )
        e_el = torch.sum(area_t * e_el_density)
        return u, v, eps_xx, eps_yy, eps_xy, psi_raw, e_el

    print("=" * 72)
    print("Frozen-alpha elastic probe")
    print(f"  device       = {device}")
    print(f"  Umax         = {args.umax}")
    print(f"  mesh         = {mesh_file}")
    print(f"  init_ckpt    = {init_ckpt}")
    print(f"  epochs       = {args.epochs}")
    print(f"  archive      = {model_path}")
    print("=" * 72)

    for epoch in range(int(args.epochs)):
        optimizer.zero_grad()
        *_unused, e_el = forward_metrics()
        reg = torch.zeros((), device=device)
        if weight_decay:
            for name, param in field_comp.net.named_parameters():
                if "weight" in name:
                    reg = reg + torch.sum(param**2)
        loss = torch.log10(e_el) + weight_decay * reg
        loss.backward()
        optimizer.step()
        if epoch == 0 or (epoch + 1) % int(args.log_every) == 0 or epoch + 1 == int(args.epochs):
            loss_rows.append((epoch + 1, float(loss.detach().cpu()), float(e_el.detach().cpu()), float(reg.detach().cpu())))
            print(f"epoch={epoch+1:06d} loss={loss_rows[-1][1]:.8e} E_el={loss_rows[-1][2]:.8e}")

    with torch.no_grad():
        u, v, eps_xx, eps_yy, eps_xy, psi_raw, e_el = forward_metrics()
        g_alpha, _ = pffmodel.Edegrade(alpha_elem_fixed)
        psi_active = g_alpha * psi_raw
        elem_x = (inp[t_conn[:, 0], 0] + inp[t_conn[:, 1], 0] + inp[t_conn[:, 2], 0]) / 3.0
        elem_y = (inp[t_conn[:, 0], 1] + inp[t_conn[:, 1], 1] + inp[t_conn[:, 2], 1]) / 3.0

    np.savez_compressed(
        diag / "frozen_alpha_elastic_fields.npz",
        cycle=np.array([0], dtype=np.int32),
        elem_x=_tensor_np(elem_x).astype(np.float32),
        elem_y=_tensor_np(elem_y).astype(np.float32),
        area_elem=_tensor_np(area_t).astype(np.float32),
        alpha_fixed_elem=_tensor_np(alpha_elem_fixed).astype(np.float32),
        eps_xx_elem=_tensor_np(eps_xx).astype(np.float32),
        eps_yy_elem=_tensor_np(eps_yy).astype(np.float32),
        eps_xy_elem=_tensor_np(eps_xy).astype(np.float32),
        eps_trace_elem=_tensor_np(eps_xx + eps_yy).astype(np.float32),
        eps_eq_elem=_tensor_np(torch.sqrt(eps_xx**2 + eps_yy**2 + 2.0 * eps_xy**2)).astype(np.float32),
        psi_raw_elem=_tensor_np(psi_raw).astype(np.float32),
        g_alpha_elem=_tensor_np(g_alpha).astype(np.float32),
        psi_active_elem=_tensor_np(psi_active).astype(np.float32),
        E_el_elem=_tensor_np(area_t * strain_energy_with_split(eps_xx, eps_yy, eps_xy, alpha_elem_fixed, matprop, pffmodel)[0]).astype(np.float32),
    )
    np.savetxt(
        best / "frozen_alpha_elastic_loss.csv",
        np.asarray(loss_rows, dtype=float),
        delimiter=",",
        header="epoch,loss,E_el,weight_reg",
        comments="",
    )
    torch.save(field_comp.net.state_dict(), best / "trained_frozen_alpha_elastic.pt")
    with open(model_path / "model_settings.txt", "w", encoding="utf-8") as fh:
        fh.write("runner: run_fem_mesh_frozen_alpha_elastic_probe.py\n")
        fh.write(f"umax: {args.umax}\n")
        fh.write(f"seed: {args.seed}\n")
        fh.write(f"epochs: {args.epochs}\n")
        fh.write(f"mesh_file: {mesh_file}\n")
        fh.write(f"init_ckpt: {init_ckpt}\n")
        fh.write(f"residual_stiffness: {args.res_stiffness}\n")
        fh.write("alpha_mode: fixed analytic hist_alpha_init on FEM-derived triangular mesh\n")
        fh.write("loss: log10(sum area * elastic_energy_density(u,v,alpha_fixed)) + weight_decay\n")
        fh.write("purpose: c1 frozen-alpha elastic discriminator for FEM/PIDL epsilon mismatch\n")

    print(f"[FrozenAlphaElastic] wrote {diag / 'frozen_alpha_elastic_fields.npz'}")
    print(f"[FrozenAlphaElastic] final E_el={float(e_el.detach().cpu()):.8e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
