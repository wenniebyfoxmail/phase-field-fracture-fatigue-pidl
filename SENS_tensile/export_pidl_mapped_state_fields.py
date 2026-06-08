#!/usr/bin/env python3
"""Export PIDL fields at FEM-aligned cyclic states.

This post-processes an existing PIDL archive without entering the training
loop.  For a FEM cycle ``c`` under the five-state loading schedule
``[0.25, 0.50, 0.75, 1.00, 0.00]`` it exports

* peak state:      PIDL substep ``5*c - 2``
* unloaded state:  PIDL substep ``5*c - 1``

It also writes an explicit PIDL ``state0``: zero displacement, analytic initial
pre-crack phase field, zero fatigue history, and zero stress/strain.  This is
kept separate because ``checkpoint_step_0.pt`` is already after the first
0.25-load optimisation/history update.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["export_pidl_mapped_state_fields", "8", "400", "1", "TrainableReLU", "1.0"]
import config  # noqa: E402
from compute_energy import (  # noqa: E402
    compute_energy_per_elem,
    get_psi_plus_per_elem,
    gradients,
    stress as effective_stress,
    strain_energy_with_split,
)
from export_pidl_element_diagnostics import (  # noqa: E402
    build_field_computation,
    mesh_from_settings,
    safe_torch_load,
)
from fatigue_history import compute_fatigue_degrad  # noqa: E402
from input_data_from_mesh import prep_input_data  # noqa: E402

sys.argv = _saved_argv


DEFAULT_CYCLES = "1,2,3,20,40,60,69"
DEFAULT_SCHEDULE = (0.25, 0.50, 0.75, 1.00, 0.00)


def tensor_np(value: torch.Tensor | float, like_tensor: torch.Tensor | None = None) -> np.ndarray:
    if torch.is_tensor(value):
        return value.detach().cpu().numpy()
    if like_tensor is not None:
        return np.full(int(like_tensor.numel()), float(value), dtype=np.float32)
    return np.asarray(value)


def elem_average(values: torch.Tensor, conn: torch.Tensor) -> torch.Tensor:
    return (values[conn[:, 0]] + values[conn[:, 1]] + values[conn[:, 2]]) / 3.0


def principal_2d(xx: torch.Tensor, yy: torch.Tensor, xy: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    mean = 0.5 * (xx + yy)
    radius = torch.sqrt((0.5 * (xx - yy)) ** 2 + xy**2)
    return mean + radius, mean - radius


def full_linear_stress(
    eps_xx: torch.Tensor,
    eps_yy: torch.Tensor,
    eps_xy: torch.Tensor,
    matprop,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    trace = eps_xx + eps_yy
    sig_xx = matprop.mat_lmbda * trace + 2.0 * matprop.mat_mu * eps_xx
    sig_yy = matprop.mat_lmbda * trace + 2.0 * matprop.mat_mu * eps_yy
    sig_xy = 2.0 * matprop.mat_mu * eps_xy
    return sig_xx, sig_yy, sig_xy


def reductions(values: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    if not np.any(finite):
        return {"min": np.nan, "max": np.nan, "mean": np.nan, "p99": np.nan, "p999": np.nan}
    selected = values[finite]
    return {
        "min": float(np.nanmin(selected)),
        "max": float(np.nanmax(selected)),
        "mean": float(np.nanmean(selected)),
        "p99": float(np.nanpercentile(selected, 99.0)),
        "p999": float(np.nanpercentile(selected, 99.9)),
    }


def parse_cycles(text: str) -> list[int]:
    cycles = []
    for part in text.split(","):
        part = part.strip()
        if part:
            cycles.append(int(part))
    return cycles


def mapped_step(cycle: int, state_kind: str) -> int:
    if state_kind == "peak":
        return 5 * cycle - 2
    if state_kind == "unloaded":
        return 5 * cycle - 1
    raise ValueError(f"unknown state_kind={state_kind!r}")


def build_initial_state_tensors(archive: Path, device: torch.device, mesh_file: Path | None):
    field_comp, pffmodel, matprop, inp, t_conn, area_t = build_field_computation(
        archive, device, umax=0.0, mesh_file=mesh_file
    )
    mesh_path = Path(mesh_from_settings(archive, mesh_file))
    _, _, _, hist_alpha = prep_input_data(
        matprop,
        pffmodel,
        config.crack_dict,
        config.numr_dict,
        mesh_file=str(mesh_path),
        device=device,
    )
    return field_comp, pffmodel, matprop, inp, t_conn, area_t, hist_alpha


def save_state(
    out_path: Path,
    *,
    archive: Path,
    device: torch.device,
    umax: float,
    state_label: str,
    fem_cycle: int,
    pidl_step: int,
    load_factor: float,
    state_kind: str,
    mesh_file: Path | None,
    initial_state: bool = False,
) -> dict[str, object]:
    if initial_state:
        field_comp, pffmodel, matprop, inp, t_conn, area_t, hist_alpha = build_initial_state_tensors(
            archive, device, mesh_file
        )
        alpha = hist_alpha
        hist_fat = torch.zeros(t_conn.shape[0], device=device)
        psi_prev = torch.zeros(t_conn.shape[0], device=device)
        u = torch.zeros(inp.shape[0], device=device)
        v = torch.zeros(inp.shape[0], device=device)
    else:
        best = archive / "best_models"
        model_path = best / f"trained_1NN_{pidl_step}.pt"
        ckpt_path = best / f"checkpoint_step_{pidl_step}.pt"
        if not model_path.exists():
            raise FileNotFoundError(model_path)
        if not ckpt_path.exists():
            raise FileNotFoundError(ckpt_path)
        field_comp, pffmodel, matprop, inp, t_conn, area_t = build_field_computation(
            archive, device, umax=umax * load_factor, mesh_file=mesh_file
        )
        field_comp.lmbda = torch.tensor([umax * load_factor], device=device)
        field_comp.net.load_state_dict(safe_torch_load(model_path, device))
        field_comp.net.eval()
        ckpt = safe_torch_load(ckpt_path, device)
        hist_alpha = ckpt["hist_alpha"].to(device)
        hist_fat = ckpt.get("hist_fat")
        hist_fat = torch.zeros(t_conn.shape[0], device=device) if hist_fat is None else hist_fat.to(device)
        psi_prev = ckpt.get("psi_plus_prev")
        psi_prev = torch.zeros_like(hist_fat) if psi_prev is None else psi_prev.to(device)
        with torch.no_grad():
            u, v, alpha = field_comp.fieldCalculation(inp)

    with torch.no_grad():
        alpha_elem = elem_average(alpha, t_conn)
        hist_alpha_elem = elem_average(hist_alpha, t_conn)
        elem_x = elem_average(inp[:, 0], t_conn)
        elem_y = elem_average(inp[:, 1], t_conn)
        f_fatigue = compute_fatigue_degrad(hist_fat, config.fatigue_dict)

        eps_xx, eps_yy, eps_xy, grad_alpha_x, grad_alpha_y = gradients(
            inp, u, v, alpha, area_t, t_conn
        )
        eps_1, eps_2 = principal_2d(eps_xx, eps_yy, eps_xy)
        eps_trace = eps_xx + eps_yy
        eps_eq = torch.sqrt(eps_xx**2 + eps_yy**2 + 2.0 * eps_xy**2)

        sig_raw_xx, sig_raw_yy, sig_raw_xy = full_linear_stress(eps_xx, eps_yy, eps_xy, matprop)
        sig_raw_1, sig_raw_2 = principal_2d(sig_raw_xx, sig_raw_yy, sig_raw_xy)

        sig_eff_xx, sig_eff_yy, sig_eff_xy = effective_stress(
            eps_xx, eps_yy, eps_xy, alpha_elem, matprop, pffmodel
        )
        sig_eff_1, sig_eff_2 = principal_2d(sig_eff_xx, sig_eff_yy, sig_eff_xy)

        g_alpha, _ = pffmodel.Edegrade(alpha_elem)
        sig_g_xx = g_alpha * sig_raw_xx
        sig_g_yy = g_alpha * sig_raw_yy
        sig_g_xy = g_alpha * sig_raw_xy

        e_el_density, psi_raw = strain_energy_with_split(
            eps_xx, eps_yy, eps_xy, alpha_elem, matprop, pffmodel
        )
        psi_active = g_alpha * psi_raw
        psi_plus = get_psi_plus_per_elem(
            inp, u, v, alpha, matprop, pffmodel, area_t, t_conn
        )
        e_el, e_d, e_hist = compute_energy_per_elem(
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

    arrays = {
        "elem_x": elem_x,
        "elem_y": elem_y,
        "area_elem": area_t,
        "alpha_elem": alpha_elem,
        "hist_alpha_elem": hist_alpha_elem,
        "alpha_bar_elem": hist_fat,
        "hist_fat_elem": hist_fat,
        "f_fatigue_elem": f_fatigue,
        "g_alpha_elem": g_alpha,
        "psi_raw_elem": psi_raw,
        "psi_active_elem": psi_active,
        "psi_plus_elem": psi_plus,
        "psi_plus_prev_elem": psi_prev,
        "E_el_density_elem": e_el_density,
        "E_el_elem": e_el,
        "E_d_elem": e_d,
        "E_hist_elem": e_hist,
        "eps_xx_elem": eps_xx,
        "eps_yy_elem": eps_yy,
        "eps_xy_elem": eps_xy,
        "eps_trace_elem": eps_trace,
        "eps_eq_elem": eps_eq,
        "eps_principal_1_elem": eps_1,
        "eps_principal_2_elem": eps_2,
        "sigma_raw_xx_elem": sig_raw_xx,
        "sigma_raw_yy_elem": sig_raw_yy,
        "sigma_raw_xy_elem": sig_raw_xy,
        "sigma_raw_principal_1_elem": sig_raw_1,
        "sigma_raw_principal_2_elem": sig_raw_2,
        "sigma_effective_xx_elem": sig_eff_xx,
        "sigma_effective_yy_elem": sig_eff_yy,
        "sigma_effective_xy_elem": sig_eff_xy,
        "sigma_effective_principal_1_elem": sig_eff_1,
        "sigma_effective_principal_2_elem": sig_eff_2,
        "sigma_g_raw_xx_elem": sig_g_xx,
        "sigma_g_raw_yy_elem": sig_g_yy,
        "sigma_g_raw_xy_elem": sig_g_xy,
        "grad_alpha_x_elem": grad_alpha_x,
        "grad_alpha_y_elem": grad_alpha_y,
    }
    payload = {
        "state_label": np.array([state_label]),
        "state_kind": np.array([state_kind]),
        "fem_cycle": np.array([fem_cycle], dtype=np.int32),
        "pidl_step": np.array([pidl_step], dtype=np.int32),
        "load_factor": np.array([load_factor], dtype=np.float32),
        "disp": np.array([umax * load_factor], dtype=np.float32),
        "mapping_note": np.array([
            "FEM cycle c peak -> PIDL 5*c-2; FEM cycle c unloaded -> PIDL 5*c-1"
        ]),
    }
    for name, tensor in arrays.items():
        payload[name] = tensor_np(tensor).reshape(-1).astype(np.float32)
    np.savez_compressed(out_path, **payload)

    row: dict[str, object] = {
        "state_label": state_label,
        "state_kind": state_kind,
        "fem_cycle": fem_cycle,
        "pidl_step": pidl_step,
        "load_factor": load_factor,
        "disp": umax * load_factor,
        "path": str(out_path),
        "n_elem": int(t_conn.shape[0]),
        "E_el": float(torch.sum(e_el).detach().cpu()),
        "E_d": float(torch.sum(e_d).detach().cpu()),
        "E_hist": float(torch.sum(e_hist).detach().cpu()),
    }
    for field_name in [
        "alpha_elem",
        "alpha_bar_elem",
        "f_fatigue_elem",
        "psi_raw_elem",
        "psi_active_elem",
        "eps_eq_elem",
        "sigma_raw_principal_1_elem",
        "sigma_effective_principal_1_elem",
    ]:
        stats = reductions(payload[field_name])
        for stat_name, value in stats.items():
            row[f"{field_name}_{stat_name}"] = value
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--cycles", default=DEFAULT_CYCLES)
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--pidl-mesh", type=Path, default=None)
    parser.add_argument("--include-state0", action="store_true", default=True)
    parser.add_argument("--no-state0", dest="include_state0", action="store_false")
    args = parser.parse_args()

    archive = args.archive.expanduser().resolve()
    out_dir = args.out_dir or (archive / "mapped_state_fields_posthoc")
    out_dir.mkdir(parents=True, exist_ok=True)
    fields_dir = out_dir / "fields"
    fields_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    rows: list[dict[str, object]] = []
    if args.include_state0:
        rows.append(save_state(
            fields_dir / "pidl_state0_initial_unloaded_prehistory.npz",
            archive=archive,
            device=device,
            umax=args.umax,
            state_label="state0_initial_unloaded_prehistory",
            fem_cycle=0,
            pidl_step=-1,
            load_factor=0.0,
            state_kind="state0",
            mesh_file=args.pidl_mesh,
            initial_state=True,
        ))
        print(rows[-1]["state_label"], rows[-1]["path"])

    for cycle in parse_cycles(args.cycles):
        for state_kind in ("peak", "unloaded"):
            step = mapped_step(cycle, state_kind)
            load_factor = 1.0 if state_kind == "peak" else 0.0
            label = f"fem_c{cycle:04d}_{state_kind}_pidl_step_{step:04d}"
            path = fields_dir / f"{label}.npz"
            rows.append(save_state(
                path,
                archive=archive,
                device=device,
                umax=args.umax,
                state_label=label,
                fem_cycle=cycle,
                pidl_step=step,
                load_factor=load_factor,
                state_kind=state_kind,
                mesh_file=args.pidl_mesh,
                initial_state=False,
            ))
            print(rows[-1]["state_label"], rows[-1]["path"])

    summary_path = out_dir / "pidl_mapped_state_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "archive": str(archive),
        "out_dir": str(out_dir),
        "cycles": parse_cycles(args.cycles),
        "umax": args.umax,
        "schedule": list(DEFAULT_SCHEDULE),
        "mapping": {
            "state0": "explicit reconstructed PIDL initial unloaded prehistory",
            "peak": "PIDL step 5*c - 2",
            "unloaded": "PIDL step 5*c - 1",
        },
        "stress_conventions": {
            "sigma_raw_*": "full linear elastic stress from exported PIDL strain, no degradation",
            "sigma_effective_*": "PIDL compute_energy.stress output, including phase-field degradation/split",
            "sigma_g_raw_*": "g(alpha) multiplied by full raw linear stress",
        },
    }
    (out_dir / "pidl_mapped_state_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Wrote {summary_path}")
    print(f"Wrote {out_dir / 'pidl_mapped_state_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
