#!/usr/bin/env python3
"""Recompute PIDL/FEM crack-tip x with one element-threshold rule.

This is a post-hoc analysis tool only. It does not train. The default inputs are
the current soft-hist0 diffuse-precrack reverseBC FEM reference and the aligned
FEM-mesh PIDL archive.

Rule:
  x_tip(threshold) = max element-centroid x among elements with damage >= threshold

PIDL damage is the element mean of nodal alpha over the triangular PIDL mesh.
FEM damage/tip columns are read from the cyclewise mechanism metrics CSV, whose
metadata defines x_tip_dXXX with the same element-centroid rule.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SOURCE = REPO_ROOT / "source"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SOURCE))

from construct_model import construct_model  # noqa: E402
from field_computation import FieldComputation  # noqa: E402
from input_data_from_mesh import prep_input_data  # noqa: E402
from validate_pidl_archive import _parse_archive_arch, _parse_settings  # noqa: E402


DEFAULT_PIDL = (
    HERE
    / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0"
)
DEFAULT_PIDL_MESH = HERE / "meshed_geom_fem_soft_hist0.msh"
DEFAULT_FEM_METRICS = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28/"
    "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv"
)
DEFAULT_OUT = (
    REPO_ROOT
    / "_analysis_fem_mechanism_20260528"
    / "experiments"
    / "strict_femmesh_soft_hist0_alignment_20260529"
    / "2_figures"
    / "element_tip_criterion_softHist0.csv"
)
DEFAULT_SUMMARY = DEFAULT_OUT.with_name("element_tip_criterion_softHist0_summary.csv")


def _trained_models(archive: Path) -> dict[int, Path]:
    models: dict[int, Path] = {}
    for path in sorted((archive / "best_models").glob("trained_1NN_*.pt")):
        match = re.search(r"trained_1NN_(\d+)\.pt$", path.name)
        if match:
            models[int(match.group(1))] = path
    if not models:
        raise FileNotFoundError(f"No trained_1NN_*.pt files under {archive / 'best_models'}")
    return models


def _parse_thresholds(raw: str) -> list[float]:
    vals = [float(x) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("At least one threshold is required")
    return vals


def _thr_label(threshold: float) -> str:
    return f"d{int(round(threshold * 100)):03d}"


def _parse_cycles(raw: str, fem_cycles: list[int]) -> list[int]:
    if raw.lower() == "all":
        return fem_cycles
    wanted = [int(x) for x in raw.split(",") if x.strip()]
    return [c for c in wanted if c in set(fem_cycles)]


def _build_pidl_case(archive: Path, mesh_file: Path):
    cfg = _parse_settings(archive)
    arch = _parse_archive_arch(archive)
    if arch is None:
        raise ValueError(f"Could not parse architecture from archive name: {archive.name}")

    network_dict = {
        "model_type": "MLP",
        "hidden_layers": int(cfg.get("hidden_layers", arch["hl"])),
        "neurons": int(cfg.get("neurons", arch["neurons"])),
        "seed": int(cfg.get("seed", arch["seed"])),
        "activation": cfg.get("activation", arch["activation"]),
        "init_coeff": float(cfg.get("coeff", arch["init_coeff"])),
        "compile": False,
    }
    pff_model_dict = {
        "PFF_model": cfg.get("PFF_model", "AT1"),
        "se_split": cfg.get("se_split", "volumetric"),
        "tol_ir": float(cfg.get("tol_ir", 5e-3)),
        "residual_stiffness": float(cfg.get("residual_stiffness", 0.0)),
    }
    mat_prop_dict = {
        "mat_E": float(cfg.get("mat_E", 1.0)),
        "mat_nu": float(cfg.get("mat_nu", 0.3)),
        "w1": float(cfg.get("w1", 1.0)),
        "l0": float(cfg.get("l0", 0.01)),
    }
    numr_dict = {
        "alpha_constraint": cfg.get("alpha_constraint", "nonsmooth"),
        "gradient_type": cfg.get("gradient_type", "numerical"),
    }
    crack_dict = {
        "x_init": [-0.5],
        "y_init": [0.0],
        "L_crack": [0.5],
        "angle_crack": [0.0],
    }
    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle = torch.tensor([np.pi / 2])

    pffmodel, matprop, network = construct_model(
        pff_model_dict,
        mat_prop_dict,
        network_dict,
        domain_extrema,
        "cpu",
    )
    inp, t_conn, _, _ = prep_input_data(
        matprop,
        pffmodel,
        crack_dict,
        numr_dict,
        mesh_file=str(mesh_file),
        device="cpu",
    )
    if t_conn is None:
        raise ValueError("Element-tip criterion requires numerical-gradient mesh connectivity")

    field_comp = FieldComputation(
        net=network,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor([float(cfg.get("disp_max", 0.12))]),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None,
        ansatz_dict=None,
        l0=mat_prop_dict["l0"],
        symmetry_prior=False,
        exact_bc_dict=None,
    )

    xy = inp.detach().cpu().numpy()
    conn = t_conn.detach().cpu().numpy()
    elem_xy = xy[conn].mean(axis=1)
    return field_comp, inp, conn, elem_xy


def _pidl_tip_for_cycle(
    field_comp: FieldComputation,
    inp: torch.Tensor,
    conn: np.ndarray,
    elem_xy: np.ndarray,
    model_path: Path,
    thresholds: list[float],
    x_shift: float,
    y_shift: float,
) -> list[dict]:
    state = torch.load(str(model_path), map_location="cpu", weights_only=False)
    field_comp.net.load_state_dict(state)
    field_comp.net.eval()
    with torch.no_grad():
        _, _, alpha = field_comp.fieldCalculation(inp)
    alpha_node = alpha.detach().cpu().numpy().reshape(-1)
    alpha_elem = alpha_node[conn].mean(axis=1)

    rows: list[dict] = []
    for threshold in thresholds:
        damaged = alpha_elem >= threshold
        if damaged.any():
            idxs = np.flatnonzero(damaged)
            idx = idxs[np.argmax(elem_xy[idxs, 0])]
            tip_x_centered = float(elem_xy[idx, 0])
            tip_y_centered = float(elem_xy[idx, 1])
        else:
            tip_x_centered = np.nan
            tip_y_centered = np.nan
        rows.append({
            "threshold": threshold,
            "threshold_label": _thr_label(threshold),
            "pidl_tip_x_centered": tip_x_centered,
            "pidl_tip_y_centered": tip_y_centered,
            "pidl_tip_x_fem_frame": tip_x_centered + x_shift if np.isfinite(tip_x_centered) else np.nan,
            "pidl_tip_y_fem_frame": tip_y_centered + y_shift if np.isfinite(tip_y_centered) else np.nan,
            "pidl_n_elem_ge_threshold": int(damaged.sum()),
            "pidl_alpha_elem_min": float(np.nanmin(alpha_elem)),
            "pidl_alpha_elem_max": float(np.nanmax(alpha_elem)),
        })
    return rows


def build_table(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    archive = args.pidl_archive.resolve()
    models = _trained_models(archive)
    fem = pd.read_csv(args.fem_metrics)
    fem_cycles = [int(c) for c in fem["cycle"].tolist()]
    cycles = _parse_cycles(args.cycles, fem_cycles)
    thresholds = _parse_thresholds(args.thresholds)

    field_comp, inp, conn, elem_xy = _build_pidl_case(archive, args.pidl_mesh)
    rows: list[dict] = []
    for fem_cycle in cycles:
        pidl_cycle = fem_cycle + int(args.pidl_cycle_shift)
        model_path = models.get(pidl_cycle)
        if model_path is None:
            continue
        fem_row = fem.loc[fem["cycle"] == fem_cycle].iloc[0]
        pidl_rows = _pidl_tip_for_cycle(
            field_comp, inp, conn, elem_xy, model_path, thresholds,
            float(args.pidl_to_fem_x_shift), float(args.pidl_to_fem_y_shift),
        )
        for prow in pidl_rows:
            label = prow["threshold_label"]
            fem_tip_col = f"x_tip_{label}"
            fem_y_col = f"y_tip_{label}"
            fem_tip_x = float(fem_row[fem_tip_col]) if fem_tip_col in fem_row else np.nan
            fem_tip_y = float(fem_row[fem_y_col]) if fem_y_col in fem_row else np.nan
            rows.append({
                "fem_cycle": fem_cycle,
                "pidl_cycle": pidl_cycle,
                "threshold": prow["threshold"],
                "threshold_label": label,
                "fem_tip_x": fem_tip_x,
                "fem_tip_y": fem_tip_y,
                "pidl_tip_x_fem_frame": prow["pidl_tip_x_fem_frame"],
                "pidl_tip_y_fem_frame": prow["pidl_tip_y_fem_frame"],
                "tip_x_error_pidl_minus_fem": prow["pidl_tip_x_fem_frame"] - fem_tip_x,
                "pidl_tip_x_centered": prow["pidl_tip_x_centered"],
                "pidl_tip_y_centered": prow["pidl_tip_y_centered"],
                "pidl_n_elem_ge_threshold": prow["pidl_n_elem_ge_threshold"],
                "pidl_alpha_elem_min": prow["pidl_alpha_elem_min"],
                "pidl_alpha_elem_max": prow["pidl_alpha_elem_max"],
                "fem_right_boundary_d095_count": (
                    int(fem_row["right_boundary_d095_count"])
                    if "right_boundary_d095_count" in fem_row else ""
                ),
                "pidl_model": model_path.name,
                "pidl_archive": str(archive),
                "pidl_mesh": str(args.pidl_mesh),
                "fem_metrics": str(args.fem_metrics),
                "coord_note": "PIDL centered coordinates shifted by (+0.5,+0.5) into FEM [0,1] frame",
            })

    summary: list[dict] = []
    for threshold in thresholds:
        label = _thr_label(threshold)
        subset = [r for r in rows if r["threshold_label"] == label]
        if not subset:
            continue
        finite = [r for r in subset if np.isfinite(r["tip_x_error_pidl_minus_fem"])]
        first_fem_right = next(
            (r["fem_cycle"] for r in subset if r["fem_tip_x"] >= args.right_tip_x),
            None,
        )
        first_pidl_right = next(
            (r["fem_cycle"] for r in subset if r["pidl_tip_x_fem_frame"] >= args.right_tip_x),
            None,
        )
        summary.append({
            "threshold_label": label,
            "threshold": threshold,
            "n_compared": len(finite),
            "mean_abs_tip_x_error": (
                float(np.mean([abs(r["tip_x_error_pidl_minus_fem"]) for r in finite]))
                if finite else np.nan
            ),
            "max_abs_tip_x_error": (
                float(np.max([abs(r["tip_x_error_pidl_minus_fem"]) for r in finite]))
                if finite else np.nan
            ),
            "first_fem_tip_ge_right_tip_x": first_fem_right,
            "first_pidl_tip_ge_right_tip_x_in_fem_cycle": first_pidl_right,
            "right_tip_x": args.right_tip_x,
        })
    return rows, summary


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pidl-archive", type=Path, default=DEFAULT_PIDL)
    parser.add_argument("--pidl-mesh", type=Path, default=DEFAULT_PIDL_MESH)
    parser.add_argument("--fem-metrics", type=Path, default=DEFAULT_FEM_METRICS)
    parser.add_argument("--thresholds", default="0.95,0.90,0.50")
    parser.add_argument("--cycles", default="all",
                        help="'all' FEM cycles from the metrics CSV, or comma-separated FEM cycles")
    parser.add_argument("--pidl-cycle-shift", type=int, default=-1,
                        help="PIDL cycle = FEM cycle + shift; default maps FEM c1 to PIDL j0.")
    parser.add_argument("--pidl-to-fem-x-shift", type=float, default=0.5)
    parser.add_argument("--pidl-to-fem-y-shift", type=float, default=0.5)
    parser.add_argument("--right-tip-x", type=float, default=0.995)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    rows, summary = build_table(args)
    _write_csv(args.out, rows)
    _write_csv(args.summary_out, summary)

    print(f"Wrote {args.out}")
    print(f"Wrote {args.summary_out}")
    for item in summary:
        print(
            f"{item['threshold_label']}: n={item['n_compared']} "
            f"mean_abs_err={item['mean_abs_tip_x_error']:.6g} "
            f"max_abs_err={item['max_abs_tip_x_error']:.6g} "
            f"FEM_right={item['first_fem_tip_ge_right_tip_x']} "
            f"PIDL_right={item['first_pidl_tip_ge_right_tip_x_in_fem_cycle']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
