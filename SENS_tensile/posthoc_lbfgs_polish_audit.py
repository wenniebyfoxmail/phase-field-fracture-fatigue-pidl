#!/usr/bin/env python3
"""Post-hoc LBFGS polish audit for a frozen PIDL checkpoint.

This script does not advance fatigue cycles. It loads one trained checkpoint
and its frozen history variables, then runs a bounded LBFGS polish on the same
cycle energy. The goal is to separate optimizer error from representation /
probe error: if energy and local diagnostics improve sharply after polish, the
original checkpoint was under-optimized; if not, the gap is more likely in the
trial space, probes, or loss landscape.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["posthoc_lbfgs_polish_audit", "8", "400", "1", "TrainableReLU", "1.0"]
import config
from compute_energy import compute_energy, get_psi_plus_per_elem
from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
sys.argv = _saved_argv


def parse_settings(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
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


def resolve_mesh_file(raw: str, archive: Path, override: Path | None = None) -> str:
    if override is not None:
        return str(override.expanduser().resolve())
    candidate = Path(raw).expanduser()
    if candidate.is_file():
        return str(candidate)
    local = HERE / candidate.name
    if local.is_file():
        return str(local)
    pulled = archive / candidate.name
    if pulled.is_file():
        return str(pulled)
    return str(candidate)


def mesh_from_settings(archive: Path, override: Path | None = None) -> str:
    settings = parse_settings(archive / "model_settings.txt")
    raw = settings.get("fine_mesh_file") or str(config.fine_mesh_file)
    return resolve_mesh_file(raw, archive, override)


def carrara_f(alpha_bar: torch.Tensor, alpha_t: float = 0.5) -> torch.Tensor:
    out = torch.ones_like(alpha_bar)
    mask = alpha_bar > alpha_t
    out[mask] = (2.0 * alpha_t / (alpha_bar[mask] + alpha_t)) ** 2
    return out


def weighted_mean(x: np.ndarray, w: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(x)
    if not np.any(m):
        return float("nan")
    return float(np.sum(x[m] * w[m]) / np.sum(w[m]))


def probe_metrics(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    vf = values[finite]
    r = np.sqrt(centroids[:, 0] ** 2 + centroids[:, 1] ** 2)
    if vf.size == 0:
        return {}
    return {
        "max": float(np.nanmax(values)),
        "p99": float(np.nanpercentile(values, 99.0)),
        "domain_mean": weighted_mean(values, areas, np.ones_like(finite, dtype=bool)),
        "tip_2l0_mean": weighted_mean(values, areas, r <= 0.02),
        "right_band_mean": weighted_mean(values, areas, centroids[:, 0] >= 0.45),
        "crack_strip_mean": weighted_mean(values, areas, np.abs(centroids[:, 1]) <= 0.02),
    }


def build_model(archive: Path, umax: float, device: torch.device,
                mesh_override: Path | None = None):
    settings = parse_settings(archive / "model_settings.txt")
    net_cfg = dict(config.network_dict)
    if "seed" in settings:
        net_cfg["seed"] = int(settings["seed"])
    if "coeff" in settings:
        net_cfg["init_coeff"] = float(settings["coeff"])

    mesh_file = mesh_from_settings(archive, mesh_override)
    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict, net_cfg,
        config.domain_extrema, device,
        williams_dict=None,
        fourier_dict=getattr(config, "fourier_dict", None),
    )
    inp, t_conn, area_t, _ = prep_input_data(
        matprop, pffmodel, config.crack_dict, config.numr_dict,
        mesh_file=mesh_file, device=device,
    )
    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema.to(device),
        lmbda=torch.tensor([umax], device=device),
        theta=config.loading_angle.to(device),
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=None,
        l0=config.mat_prop_dict["l0"],
        exact_bc_dict=exact_bc_from_settings(archive),
    )
    field_comp.net = field_comp.net.to(device)
    return field_comp, pffmodel, matprop, inp, t_conn, area_t, mesh_file


def safe_load(path: Path, device: torch.device):
    try:
        return torch.load(str(path), map_location=device, weights_only=True)
    except TypeError:
        return torch.load(str(path), map_location=device)


def evaluate(field_comp, inp, t_conn, area_t, hist_alpha, f_fatigue, matprop, pffmodel,
             weight_decay: float, do_backward: bool = False) -> tuple[torch.Tensor, dict[str, float]]:
    if do_backward:
        field_comp.net.zero_grad(set_to_none=True)
    with torch.enable_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        e_el, e_d, e_hist = compute_energy(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_t, t_conn,
            f_fatigue=f_fatigue,
        )
        loss_var = torch.log10(e_el + e_d + e_hist)
        loss_reg = torch.zeros((), device=inp.device)
        if weight_decay:
            for name, param in field_comp.net.named_parameters():
                if "weight" in name:
                    loss_reg = loss_reg + torch.sum(param ** 2)
        loss = loss_var + weight_decay * loss_reg
        if do_backward:
            loss.backward()

    grad_sq = 0.0
    if do_backward:
        for p in field_comp.net.parameters():
            if p.grad is not None:
                grad_sq += float(torch.sum(p.grad.detach() ** 2).cpu())

    with torch.no_grad():
        psi = get_psi_plus_per_elem(inp, u, v, alpha, matprop, pffmodel, area_t, t_conn)
        alpha_elem = (alpha[t_conn[:, 0]] + alpha[t_conn[:, 1]] + alpha[t_conn[:, 2]]) / 3.0
        inp_np = inp.detach().cpu().numpy()
        t_np = t_conn.detach().cpu().numpy()
        centroids = inp_np[t_np].mean(axis=1)
        areas = area_t.detach().cpu().numpy().reshape(-1)
        psi_m = probe_metrics(psi.detach().cpu().numpy().reshape(-1), areas, centroids)
        alpha_m = probe_metrics(alpha_elem.detach().cpu().numpy().reshape(-1), areas, centroids)

    metrics = {
        "loss_total": float(loss.detach().cpu()),
        "loss_var": float(loss_var.detach().cpu()),
        "E_el": float(e_el.detach().cpu()),
        "E_d": float(e_d.detach().cpu()),
        "E_hist": float(e_hist.detach().cpu()),
        "grad_norm": float(np.sqrt(grad_sq)) if do_backward else float("nan"),
    }
    metrics.update({f"psi_plus_{k}": v for k, v in psi_m.items()})
    metrics.update({f"alpha_{k}": v for k, v in alpha_m.items()})
    return loss, metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--cycle", type=int, required=True)
    ap.add_argument("--umax", type=float, default=0.12)
    ap.add_argument("--max-iter", type=int, default=400)
    ap.add_argument("--history-size", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--weight-decay", type=float, default=1e-5)
    ap.add_argument("--device", default=None, help="cuda, cuda:0, or cpu; default uses config.device")
    ap.add_argument("--mesh-file", type=Path, default=None,
                    help="Override mesh used to reconstruct the checkpoint fields")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    archive = args.archive.resolve()
    out_dir = args.out_dir or (archive / "optimizer_audit" / f"cycle_{args.cycle:04d}_lbfgs{args.max_iter}")
    out_dir.mkdir(parents=True, exist_ok=True)

    field_comp, pffmodel, matprop, inp, t_conn, area_t, mesh_file = build_model(
        archive, args.umax, device, args.mesh_file
    )
    field_comp.net.load_state_dict(safe_load(archive / "best_models" / f"trained_1NN_{args.cycle}.pt", device))
    step = safe_load(archive / "best_models" / f"checkpoint_step_{args.cycle}.pt", device)
    hist_alpha = step["hist_alpha"].to(device)
    hist_fat = step["hist_fat"].to(device)
    f_fatigue = carrara_f(hist_fat, alpha_t=float(config.fatigue_dict.get("alpha_T", 0.5))).detach()

    rows: list[dict[str, float | str | int]] = []
    _, before = evaluate(field_comp, inp, t_conn, area_t, hist_alpha, f_fatigue,
                         matprop, pffmodel, args.weight_decay, do_backward=True)
    before.update({"stage": "before", "cycle": args.cycle, "closure_calls": 0})
    rows.append(before)

    optimizer = torch.optim.LBFGS(
        field_comp.net.parameters(),
        lr=args.lr,
        max_iter=args.max_iter,
        max_eval=args.max_iter * 4,
        history_size=args.history_size,
        line_search_fn="strong_wolfe",
        tolerance_change=1e-9,
        tolerance_grad=1e-12,
    )
    calls = {"n": 0}

    def closure():
        calls["n"] += 1
        loss, _ = evaluate(field_comp, inp, t_conn, area_t, hist_alpha, f_fatigue,
                           matprop, pffmodel, args.weight_decay, do_backward=True)
        if calls["n"] % 25 == 0:
            print(f"[LBFGS] closure={calls['n']} loss={float(loss.detach().cpu()):.8e}", flush=True)
        return loss

    optimizer.step(closure)

    _, after = evaluate(field_comp, inp, t_conn, area_t, hist_alpha, f_fatigue,
                        matprop, pffmodel, args.weight_decay, do_backward=True)
    after.update({"stage": "after", "cycle": args.cycle, "closure_calls": calls["n"]})
    rows.append(after)

    torch.save(field_comp.net.state_dict(), out_dir / f"polished_trained_1NN_{args.cycle}.pt")
    with open(out_dir / "lbfgs_polish_metrics.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "lbfgs_polish_metadata.txt").write_text(
        "\n".join([
            f"archive={archive}",
            f"cycle={args.cycle}",
            f"umax={args.umax}",
            f"device={device}",
            f"mesh_file={mesh_file}",
            f"max_iter={args.max_iter}",
            f"lr={args.lr}",
            f"weight_decay={args.weight_decay}",
            "",
        ]),
        encoding="utf-8",
    )

    print(f"saved {out_dir / 'lbfgs_polish_metrics.csv'}")
    print(f"mesh={mesh_file}")
    for row in rows:
        print(
            f"{row['stage']}: loss={row['loss_total']:.8e} "
            f"grad={row['grad_norm']:.3e} E=({row['E_el']:.3e}, {row['E_d']:.3e}, {row['E_hist']:.3e}) "
            f"psi_tip2l0={row.get('psi_plus_tip_2l0_mean', float('nan')):.3e} "
            f"psi_right={row.get('psi_plus_right_band_mean', float('nan')):.3e} "
            f"alpha_right={row.get('alpha_right_band_mean', float('nan')):.3e}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
