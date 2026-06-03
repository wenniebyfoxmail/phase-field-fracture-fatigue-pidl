#!/usr/bin/env python3
"""C1 alternate-minimisation micro-solve on the strict FEM mesh.

This diagnostic is narrower than a normal fatigue run.  It starts from the
same post-pretraining PIDL checkpoint used by the strict FEM-mesh branches, then
performs a FEM-like first loaded solve:

    freeze alpha -> optimise u/v
    freeze u/v   -> optimise alpha

The frozen field in each substage is a detached snapshot, and only the matching
final output-head rows are trainable.  The variational energy is unchanged; only
the optimiser path is changed.  Every substage exports alpha, strain, psi_raw,
psi_active, and energy/gradient diagnostics.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import sys
from pathlib import Path

import numpy as np
import torch


def _resolve_file(here: Path, filename: str | Path | None, launch_cwd: Path | None = None) -> Path | None:
    if filename is None:
        return None
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


def _resolve_output_layer(net):
    raw_net = getattr(net, "_orig_mod", net)
    if hasattr(raw_net, "output_layer"):
        return raw_net.output_layer
    if hasattr(raw_net, "inner") and hasattr(raw_net.inner, "output_layer"):
        return raw_net.inner.output_layer
    raise AttributeError("Could not locate output_layer for c1 alt-min probe")


@contextlib.contextmanager
def _head_rows_only(field_comp, rows: tuple[int, ...], label: str):
    """Enable only selected rows of the final output layer."""
    output_layer = _resolve_output_layer(field_comp.net)
    row_mask = torch.zeros_like(output_layer.weight)
    row_mask[list(rows), :] = 1.0
    bias_mask = torch.zeros_like(output_layer.bias)
    bias_mask[list(rows)] = 1.0
    old_requires_grad = {p: p.requires_grad for p in field_comp.parameters()}
    hooks = []
    try:
        for p in old_requires_grad:
            p.requires_grad_(False)
        output_layer.weight.requires_grad_(True)
        output_layer.bias.requires_grad_(True)
        hooks.append(output_layer.weight.register_hook(lambda grad: grad * row_mask))
        hooks.append(output_layer.bias.register_hook(lambda grad: grad * bias_mask))
        print(f"[AltMin] {label}: active final-head rows {list(rows)}")
        yield [output_layer.weight, output_layer.bias]
    finally:
        for hook in hooks:
            hook.remove()
        for p, requires_grad in old_requires_grad.items():
            p.requires_grad_(requires_grad)


def _grad_norm(term: torch.Tensor, params: list[torch.nn.Parameter]) -> float:
    if not getattr(term, "requires_grad", False):
        return 0.0
    grads = torch.autograd.grad(
        torch.log10(torch.clamp(term, min=1e-30)),
        params,
        retain_graph=True,
        allow_unused=True,
    )
    total = torch.zeros((), device=term.device)
    for grad in grads:
        if grad is not None:
            total = total + torch.sum(grad.detach() ** 2)
    return float(torch.sqrt(total).detach().cpu())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--tag", default="softHist0_resStiff1e6_c1AltMin")
    parser.add_argument("--res-stiffness", type=float, default=1e-6)
    parser.add_argument("--init-ckpt", type=Path, default=None,
                        help="Post-pretraining state dict. If omitted, use random init.")
    parser.add_argument("--initial-alpha", choices=("analytic", "network"), default="analytic",
                        help="Alpha snapshot before first uv solve.")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--uv-epochs", type=int, default=2000)
    parser.add_argument("--alpha-epochs", type=int, default=2000)
    parser.add_argument("--joint-epochs", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--log-every", type=int, default=250)
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = [
        "run_fem_mesh_c1_altmin_probe.py",
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
    from compute_energy import compute_energy, compute_energy_per_elem, gradients, strain_energy_with_split
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
    if mesh_file is None:
        raise FileNotFoundError(args.mesh_file)

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
        print(f"[AltMin] loading init checkpoint: {init_ckpt}")
        field_comp.net.load_state_dict(_safe_torch_load(init_ckpt, device))
    elif init_ckpt is not None:
        raise FileNotFoundError(init_ckpt)
    else:
        print("[AltMin] no init checkpoint supplied; using random init")

    inp, t_conn, area_t, hist_alpha = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        config.numr_dict,
        mesh_file=str(mesh_file),
        device=device,
    )

    fatigue_tag = (
        f"_fatigue_off_N1_R0.0_Umax{args.umax}"
        f"_femmesh_{args.tag}_r{args.rounds}_uv{args.uv_epochs}"
        f"_a{args.alpha_epochs}_j{args.joint_epochs}"
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

    weight_decay = float(config.optimizer_dict["weight_decay"])
    eps_floor = torch.tensor(1e-30, device=device)
    trace_rows: list[list[float | int | str]] = []
    states: list[dict[str, np.ndarray | str | int | float]] = []

    def element_alpha(alpha_node: torch.Tensor) -> torch.Tensor:
        return (alpha_node[t_conn[:, 0]] + alpha_node[t_conn[:, 1]] + alpha_node[t_conn[:, 2]]) / 3.0

    def forward_fields():
        return field_comp.fieldCalculation(inp)

    def energy_terms(u: torch.Tensor, v: torch.Tensor, alpha: torch.Tensor):
        e_el_e, e_d_e, e_hist_e = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_t, t_conn, f_fatigue=1.0
        )
        return torch.sum(e_el_e), torch.sum(e_d_e), torch.sum(e_hist_e), e_el_e, e_d_e, e_hist_e

    def strain_driver_fields(u: torch.Tensor, v: torch.Tensor, alpha: torch.Tensor):
        eps_xx, eps_yy, eps_xy, _, _ = gradients(inp, u, v, alpha, area_t, t_conn)
        alpha_elem = element_alpha(alpha)
        e_el_density, psi_raw = strain_energy_with_split(
            eps_xx, eps_yy, eps_xy, alpha_elem, matprop, pffmodel
        )
        g_alpha, _ = pffmodel.Edegrade(alpha_elem)
        return eps_xx, eps_yy, eps_xy, alpha_elem, e_el_density, psi_raw, g_alpha, g_alpha * psi_raw

    with torch.no_grad():
        u0, v0, alpha0_net = forward_fields()
    if args.initial_alpha == "analytic":
        alpha_snapshot = hist_alpha.detach().clone()
    else:
        alpha_snapshot = alpha0_net.detach().clone()
    u_snapshot = u0.detach().clone()
    v_snapshot = v0.detach().clone()

    elem_x = (inp[t_conn[:, 0], 0] + inp[t_conn[:, 1], 0] + inp[t_conn[:, 2], 0]) / 3.0
    elem_y = (inp[t_conn[:, 0], 1] + inp[t_conn[:, 1], 1] + inp[t_conn[:, 2], 1]) / 3.0

    def record_state(label: str, stage_index: int, active_params: list[torch.nn.Parameter] | None = None):
        u_cur, v_cur, alpha_cur = forward_fields()
        if label.endswith("_uv"):
            alpha_eval = alpha_snapshot
            u_eval, v_eval = u_cur, v_cur
        elif label.endswith("_alpha"):
            alpha_eval = alpha_cur
            u_eval, v_eval = u_snapshot, v_snapshot
        else:
            alpha_eval = alpha_cur
            u_eval, v_eval = u_cur, v_cur
        E_el, E_d, E_hist, E_el_e, E_d_e, E_hist_e = energy_terms(u_eval, v_eval, alpha_eval)
        eps_xx, eps_yy, eps_xy, alpha_elem, e_el_density, psi_raw, g_alpha, psi_active = strain_driver_fields(
            u_eval, v_eval, alpha_eval
        )
        if active_params is None:
            g_el = g_d = g_hist = 0.0
        else:
            g_el = _grad_norm(E_el, active_params)
            g_d = _grad_norm(E_d, active_params)
            g_hist = _grad_norm(E_hist, active_params)
        trace_rows.append([
            stage_index,
            label,
            float(E_el.detach().cpu()),
            float(E_d.detach().cpu()),
            float(E_hist.detach().cpu()),
            float(torch.log10(torch.clamp(E_el + E_d + E_hist, min=eps_floor)).detach().cpu()),
            g_el,
            g_d,
            g_hist,
            float(torch.max(alpha_elem).detach().cpu()),
            float(torch.max(psi_raw).detach().cpu()),
            float(torch.max(psi_active).detach().cpu()),
        ])
        states.append({
            "label": label,
            "stage_index": stage_index,
            "alpha_elem": _tensor_np(alpha_elem).astype(np.float32),
            "eps_xx_elem": _tensor_np(eps_xx).astype(np.float32),
            "eps_yy_elem": _tensor_np(eps_yy).astype(np.float32),
            "eps_xy_elem": _tensor_np(eps_xy).astype(np.float32),
            "eps_eq_elem": _tensor_np(torch.sqrt(eps_xx**2 + eps_yy**2 + 2.0 * eps_xy**2)).astype(np.float32),
            "psi_raw_elem": _tensor_np(psi_raw).astype(np.float32),
            "g_alpha_elem": _tensor_np(g_alpha).astype(np.float32),
            "psi_active_elem": _tensor_np(psi_active).astype(np.float32),
            "E_el_elem": _tensor_np(E_el_e).astype(np.float32),
            "E_d_elem": _tensor_np(E_d_e).astype(np.float32),
            "E_hist_elem": _tensor_np(E_hist_e).astype(np.float32),
        })
        print(
            f"[AltMin] {label:>16s} E_el={trace_rows[-1][2]:.8e} "
            f"E_d={trace_rows[-1][3]:.8e} E_hist={trace_rows[-1][4]:.8e} "
            f"grad(logE)={g_el:.3e}/{g_d:.3e}/{g_hist:.3e} "
            f"alpha_max={trace_rows[-1][9]:.4e} psi_raw_max={trace_rows[-1][10]:.4e}"
        )

    def run_stage(label: str, rows: tuple[int, ...], epochs: int, loss_kind: str, stage_index: int):
        if int(epochs) <= 0:
            return
        with _head_rows_only(field_comp, rows, label) as active_params:
            optimizer = torch.optim.Rprop(active_params, lr=float(args.lr), step_sizes=(1e-10, 50))
            for epoch in range(int(epochs)):
                optimizer.zero_grad()
                u_cur, v_cur, alpha_cur = forward_fields()
                if loss_kind == "uv":
                    E_el, _E_d, _E_hist, *_ = energy_terms(u_cur, v_cur, alpha_snapshot)
                    loss_var = torch.log10(torch.clamp(E_el, min=eps_floor))
                elif loss_kind == "alpha":
                    E_el, E_d, E_hist, *_ = energy_terms(u_snapshot, v_snapshot, alpha_cur)
                    loss_var = torch.log10(torch.clamp(E_el + E_d + E_hist, min=eps_floor))
                else:
                    E_el, E_d, E_hist, *_ = energy_terms(u_cur, v_cur, alpha_cur)
                    loss_var = torch.log10(torch.clamp(E_el + E_d + E_hist, min=eps_floor))
                reg = torch.zeros((), device=device)
                if weight_decay:
                    for name, param in field_comp.net.named_parameters():
                        if "weight" in name and param.requires_grad:
                            reg = reg + torch.sum(param**2)
                loss = loss_var + weight_decay * reg
                loss.backward()
                optimizer.step()
                if epoch == 0 or (epoch + 1) % int(args.log_every) == 0 or epoch + 1 == int(epochs):
                    print(f"[AltMin] {label} epoch={epoch+1:06d}/{epochs} loss={float(loss.detach().cpu()):.8e}")
            record_state(label, stage_index, active_params)

    print("=" * 72)
    print("C1 alternate-minimisation probe")
    print(f"  device        = {device}")
    print(f"  Umax          = {args.umax}")
    print(f"  mesh          = {mesh_file}")
    print(f"  init_ckpt     = {init_ckpt}")
    print(f"  initial_alpha = {args.initial_alpha}")
    print(f"  rounds        = {args.rounds}")
    print(f"  uv/alpha/j    = {args.uv_epochs}/{args.alpha_epochs}/{args.joint_epochs}")
    print(f"  archive       = {model_path}")
    print("=" * 72)

    record_state("initial_joint", 0, None)
    record_state("initial_uv", 0, None)
    stage_index = 1
    for round_idx in range(1, int(args.rounds) + 1):
        run_stage(f"r{round_idx}_uv", (0, 1), int(args.uv_epochs), "uv", stage_index)
        with torch.no_grad():
            u_snapshot, v_snapshot, _ = forward_fields()
            u_snapshot = u_snapshot.detach().clone()
            v_snapshot = v_snapshot.detach().clone()
        stage_index += 1
        run_stage(f"r{round_idx}_alpha", (2,), int(args.alpha_epochs), "alpha", stage_index)
        with torch.no_grad():
            _, _, alpha_snapshot = forward_fields()
            alpha_snapshot = alpha_snapshot.detach().clone()
        stage_index += 1
    run_stage("joint", (0, 1, 2), int(args.joint_epochs), "joint", stage_index)

    labels = np.asarray([str(s["label"]) for s in states])
    np.savez_compressed(
        diag / "c1_altmin_fields.npz",
        labels=labels,
        stage_index=np.asarray([int(s["stage_index"]) for s in states], dtype=np.int32),
        elem_x=_tensor_np(elem_x).astype(np.float32),
        elem_y=_tensor_np(elem_y).astype(np.float32),
        area_elem=_tensor_np(area_t).astype(np.float32),
        alpha_elem=np.stack([s["alpha_elem"] for s in states], axis=0),
        eps_xx_elem=np.stack([s["eps_xx_elem"] for s in states], axis=0),
        eps_yy_elem=np.stack([s["eps_yy_elem"] for s in states], axis=0),
        eps_xy_elem=np.stack([s["eps_xy_elem"] for s in states], axis=0),
        eps_eq_elem=np.stack([s["eps_eq_elem"] for s in states], axis=0),
        psi_raw_elem=np.stack([s["psi_raw_elem"] for s in states], axis=0),
        g_alpha_elem=np.stack([s["g_alpha_elem"] for s in states], axis=0),
        psi_active_elem=np.stack([s["psi_active_elem"] for s in states], axis=0),
        E_el_elem=np.stack([s["E_el_elem"] for s in states], axis=0),
        E_d_elem=np.stack([s["E_d_elem"] for s in states], axis=0),
        E_hist_elem=np.stack([s["E_hist_elem"] for s in states], axis=0),
    )
    np.savetxt(
        best / "c1_altmin_trace.csv",
        np.asarray(trace_rows, dtype=object),
        delimiter=",",
        fmt="%s",
        header=(
            "stage_index,label,E_el,E_d,E_hist,log10_E_total,"
            "grad_logEel,grad_logEd,grad_logEhist,alpha_max,psi_raw_max,psi_active_max"
        ),
        comments="",
    )
    torch.save(field_comp.net.state_dict(), best / "trained_c1_altmin.pt")
    with open(model_path / "model_settings.txt", "w", encoding="utf-8") as fh:
        fh.write("runner: run_fem_mesh_c1_altmin_probe.py\n")
        fh.write(f"umax: {args.umax}\n")
        fh.write(f"seed: {args.seed}\n")
        fh.write(f"mesh_file: {mesh_file}\n")
        fh.write(f"init_ckpt: {init_ckpt}\n")
        fh.write(f"residual_stiffness: {args.res_stiffness}\n")
        fh.write(f"initial_alpha: {args.initial_alpha}\n")
        fh.write(f"rounds: {args.rounds}\n")
        fh.write(f"uv_epochs: {args.uv_epochs}\n")
        fh.write(f"alpha_epochs: {args.alpha_epochs}\n")
        fh.write(f"joint_epochs: {args.joint_epochs}\n")
        fh.write("objective: fixed-field c1 alternate minimisation with unchanged E_el+E_d+E_hist physics\n")
        fh.write("outputs: element_diagnostics/c1_altmin_fields.npz and best_models/c1_altmin_trace.csv\n")

    print(f"[AltMin] wrote {diag / 'c1_altmin_fields.npz'}")
    print(f"[AltMin] wrote {best / 'c1_altmin_trace.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
