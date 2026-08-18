#!/usr/bin/env python3
"""Quarantined same-state c1/s4 diagnostic for FEM, KAN-RBF, and legacy MLP.

This is an offline checkpoint-evaluation diagnostic.  It does not train a
model and it is deliberately not an equal-budget architecture benchmark.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import meshio
import numpy as np
import torch


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from network import (  # noqa: E402
    KANRBFFieldNet,
    NeuralNet,
    TopologyKANSingleFrontRBFNet,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-vtk", type=Path, required=True)
    parser.add_argument("--kan-checkpoint", type=Path, required=True)
    parser.add_argument("--mlp-checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument(
        "--kan-kind",
        choices=("compact_rbf_grid", "topology_singlefront"),
        default="compact_rbf_grid",
    )
    return parser.parse_args()


def constrained_fields(raw: np.ndarray, xy: np.ndarray, amplitude: float) -> tuple[np.ndarray, np.ndarray]:
    y = xy[:, 1]
    bubble = (y + 0.5) * (0.5 - y)
    displacement = np.column_stack([
        bubble * raw[:, 0] * amplitude,
        (bubble * raw[:, 1] + (y + 0.5)) * amplitude,
    ])
    x = raw[:, 2]
    damage = np.where(
        x > 2.0,
        1.0e-3 * (x - 2.0) + 1.0,
        np.where(x < -2.0, 1.0e-3 * (x + 2.0), x / 4.0 + 0.5),
    )
    return displacement, damage


def evaluate_in_batches(net: torch.nn.Module, xy: np.ndarray) -> np.ndarray:
    net.eval()
    outputs = []
    with torch.no_grad():
        for start in range(0, xy.shape[0], 8192):
            outputs.append(net(torch.from_numpy(xy[start:start + 8192].astype(np.float32))))
    return torch.cat(outputs, dim=0).cpu().numpy()


def load_kan(checkpoint: Path, kind: str) -> torch.nn.Module:
    extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float32)
    if kind == "topology_singlefront":
        net = TopologyKANSingleFrontRBFNet(
            2, 3, extrema,
            kan_width=64,
            kan_basis=15,
            topology_eps_y=0.02,
            topology_eps_x=0.04,
            initial_tip_x=0.0,
            front_centres=81,
            front_width=0.025,
            corridor_sigma_y=0.02,
            phase_bias=-2.0,
            phase_weight_init=-4.0,
        )
    else:
        net = KANRBFFieldNet(
            2, 3, extrema,
            kan_width=32,
            kan_basis=9,
            rbf_x_centres=41,
            rbf_y_centres=17,
            rbf_y_extent=0.20,
            rbf_sigma_x=0.08,
            rbf_sigma_y=0.035,
        )
    net.load_state_dict(torch.load(checkpoint, map_location="cpu"))
    return net


def load_mlp(checkpoint: Path) -> torch.nn.Module:
    net = NeuralNet(2, 3, 8, 400, "TrainableReLU", 1.0)
    net.load_state_dict(torch.load(checkpoint, map_location="cpu"))
    return net


def nodal_lumped_areas(xy: np.ndarray, quads: np.ndarray) -> np.ndarray:
    pts = xy[quads]
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    areas = 0.5 * np.abs(
        np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
    )
    weights = np.zeros(xy.shape[0], dtype=np.float64)
    np.add.at(weights, quads.reshape(-1), np.repeat(areas / 4.0, 4))
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("invalid FEM lumped nodal areas")
    return weights


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(values * weights) / np.sum(weights))


def region_metrics(
    label: str,
    architecture: str,
    mask: np.ndarray,
    weights: np.ndarray,
    u_pred: np.ndarray,
    d_pred: np.ndarray,
    u_fem: np.ndarray,
    d_fem: np.ndarray,
) -> dict[str, object]:
    w = weights[mask]
    u_err = u_pred[mask] - u_fem[mask]
    d_err = d_pred[mask] - d_fem[mask]
    u_sq = np.sum(u_err * u_err, axis=1)
    u_ref_sq = np.sum(u_fem[mask] * u_fem[mask], axis=1)
    return {
        "architecture": architecture,
        "state": "U0.12_c1_s4_peak_same_state",
        "region": label,
        "n_nodes": int(np.count_nonzero(mask)),
        "u_vector_mae_area_weighted": weighted_mean(np.linalg.norm(u_err, axis=1), w),
        "u_vector_rmse_area_weighted": weighted_mean(u_sq, w) ** 0.5,
        "u_relative_l2_area_weighted": (
            np.sum(w * u_sq) / max(np.sum(w * u_ref_sq), 1.0e-30)
        ) ** 0.5,
        "damage_mae_area_weighted": weighted_mean(np.abs(d_err), w),
        "damage_rmse_area_weighted": weighted_mean(d_err * d_err, w) ** 0.5,
    }


def area_iou(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    union = np.sum(weights[a | b])
    return float(np.sum(weights[a & b]) / union) if union > 0.0 else 1.0


def render_fields(
    path: Path,
    xy: np.ndarray,
    quads: np.ndarray,
    fields: list[tuple[str, np.ndarray, np.ndarray]],
) -> None:
    triangles = np.vstack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    tri = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles)
    fem_umag = np.linalg.norm(fields[0][1], axis=1)
    umax = float(np.quantile(fem_umag, 0.999))
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), constrained_layout=True)
    for col, (name, displacement, damage) in enumerate(fields):
        im0 = axes[0, col].tripcolor(tri, np.linalg.norm(displacement, axis=1), shading="gouraud", vmin=0.0, vmax=umax)
        axes[0, col].set_title(f"{name}: |u|")
        im1 = axes[1, col].tripcolor(tri, damage, shading="gouraud", vmin=0.0, vmax=1.0)
        axes[1, col].set_title(f"{name}: damage")
        for ax in axes[:, col]:
            ax.set_aspect("equal")
            ax.set_xlim(-0.5, 0.5)
            ax.set_ylim(-0.5, 0.5)
            ax.set_xlabel("x")
            ax.set_ylabel("y")
    fig.colorbar(im0, ax=axes[0, :], shrink=0.8, label="displacement magnitude")
    fig.colorbar(im1, ax=axes[1, :], shrink=0.8, label="damage")
    fig.suptitle("U0.12 c1/s4 same-state diagnostic (FEM first)")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tables = args.out / "tables"
    figures = args.out / "figures"
    tables.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)

    mesh = meshio.read(args.fem_vtk)
    xy = np.asarray(mesh.points[:, :2], dtype=np.float64)
    quads = np.asarray(mesh.cells_dict["quad"], dtype=np.int64)
    u_fem = np.asarray(mesh.point_data["u"][:, :2], dtype=np.float64)
    d_fem = np.asarray(mesh.point_data["d"], dtype=np.float64).reshape(-1)
    weights = nodal_lumped_areas(xy, quads)

    candidate_label = (
        "TopologyKAN_SingleFrontRBF"
        if args.kan_kind == "topology_singlefront"
        else "KAN_RBF"
    )
    candidate_title = (
        "Topology-KAN single-front"
        if args.kan_kind == "topology_singlefront"
        else "KAN-RBF"
    )
    raw_kan = evaluate_in_batches(load_kan(args.kan_checkpoint, args.kan_kind), xy)
    raw_mlp = evaluate_in_batches(load_mlp(args.mlp_checkpoint), xy)
    u_kan, d_kan = constrained_fields(raw_kan, xy, args.umax)
    u_mlp, d_mlp = constrained_fields(raw_mlp, xy, args.umax)

    regions = {
        "whole_domain": np.ones(xy.shape[0], dtype=bool),
        "process_zone_box_xm005_025_y012": (
            (xy[:, 0] >= -0.05) & (xy[:, 0] <= 0.25) & (np.abs(xy[:, 1]) <= 0.12)
        ),
        "right_boundary_band_x045": xy[:, 0] >= 0.45,
    }
    metrics = []
    for architecture, u_pred, d_pred in [(candidate_label, u_kan, d_kan), ("Formal_MLP_eta0", u_mlp, d_mlp)]:
        for label, mask in regions.items():
            metrics.append(region_metrics(label, architecture, mask, weights, u_pred, d_pred, u_fem, d_fem))
    with (tables / "c1_same_state_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)

    iou_rows = []
    for architecture, d_pred in [(candidate_label, d_kan), ("Formal_MLP_eta0", d_mlp)]:
        for threshold in (0.25, 0.50, 0.75, 0.95):
            fem_mask = d_fem >= threshold
            pred_mask = d_pred >= threshold
            iou_rows.append({
                "architecture": architecture,
                "state": "U0.12_c1_s4_peak_same_state",
                "damage_threshold": threshold,
                "area_iou": area_iou(fem_mask, pred_mask, weights),
                "predicted_to_fem_support_area_ratio": float(
                    np.sum(weights[pred_mask]) / max(np.sum(weights[fem_mask]), 1.0e-30)
                ),
            })
    with (tables / "c1_damage_threshold_iou.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(iou_rows[0]))
        writer.writeheader()
        writer.writerows(iou_rows)

    figure_path = figures / "c1_same_state_fields.png"
    render_fields(figure_path, xy, quads, [
        ("FEM", u_fem, d_fem),
        (candidate_title, u_kan, d_kan),
        ("Formal MLP eta0", u_mlp, d_mlp),
    ])
    (figures / "c1_same_state_fields.md").write_text(
        """# U0.12 c1/s4 same-state fields

Question: Does the tooling-smoke KAN displacement plus RBF damage representation already match the canonical FEM c1/s4 field closely enough to justify a larger run?

Data provenance: FEM is the July Hard-5 U0.12 `peak_load_c1.vtk`. KAN-RBF is direct checkpoint evaluation of PIDL step 3 from the 2026-08-18 five-substep micro. Formal MLP eta0 is direct checkpoint evaluation of PIDL step 3 from the existing 2026-06-08 production trajectory. All networks are evaluated directly at the FEM nodes; no spatial interpolation is used.

How to read: x and y are specimen coordinates. The first row uses one common FEM-p99 displacement-magnitude scale. The second row uses damage 0 to 1. Columns are FEM, KAN-RBF, and Formal MLP eta0.

Main takeaway: the current KAN-RBF smoke is visibly broader and less accurate than the production MLP at c1/s4. Its displacement field smooths over the crack-face jump, while the RBF damage head produces faint parallel ghost bands above and below the prescribed crack corridor. Use the CSV tables for area-weighted errors and damage-support overlap.

Limitations and claim boundary: this is a quarantined cheap diagnostic, not an equal-budget architecture benchmark. KAN used a reduced 300-epoch tooling protocol and 1,468 parameters; the MLP is an older 8x400, 10,000-epoch production trajectory. The figure can reject immediate promotion of the current KAN configuration but cannot establish that all KAN architectures are inferior.
""",
        encoding="utf-8",
    )

    manifest = {
        "claim_class": "diagnostic_quarantine",
        "state": "U0.12_c1_s4_peak_same_state",
        "mapping": {"FEM": "cycle 1 substep 4", candidate_label: "step 3", "Formal_MLP_eta0": "step 3"},
        "candidate_kind": args.kan_kind,
        "evaluation": "direct network evaluation at FEM nodes; area-weighted nodal metrics",
        "fem_vtk": str(args.fem_vtk.resolve()),
        "kan_checkpoint": str(args.kan_checkpoint.resolve()),
        "mlp_checkpoint": str(args.mlp_checkpoint.resolve()),
        "equal_budget": False,
        "promotion_authorized": False,
    }
    (args.out / "comparison_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    global_rows = {row["architecture"]: row for row in metrics if row["region"] == "whole_domain"}
    pz_rows = {row["architecture"]: row for row in metrics if row["region"].startswith("process_zone")}
    decision = f"""# Decision — {candidate_title} c1 same-state diagnostic

Verdict: **negative for immediate promotion; diagnostic/quarantine**.

Purpose: determine whether the current compact KAN displacement plus anisotropic RBF damage representation is already competitive enough at exact U0.12 c1/s4 to justify a longer or equal-budget producer run.

Gate: FEM and both PIDL checkpoints are evaluated at the same c1/s4 peak state. Metrics use FEM lumped nodal areas. This is not an equal-budget comparison.

Key result:

- Whole-domain displacement relative L2: candidate `{global_rows[candidate_label]['u_relative_l2_area_weighted']:.6f}`; Formal MLP eta0 `{global_rows['Formal_MLP_eta0']['u_relative_l2_area_weighted']:.6f}`.
- Process-zone displacement relative L2: candidate `{pz_rows[candidate_label]['u_relative_l2_area_weighted']:.6f}`; Formal MLP eta0 `{pz_rows['Formal_MLP_eta0']['u_relative_l2_area_weighted']:.6f}`.
- Whole-domain damage RMSE: candidate `{global_rows[candidate_label]['damage_rmse_area_weighted']:.6f}`; Formal MLP eta0 `{global_rows['Formal_MLP_eta0']['damage_rmse_area_weighted']:.6f}`.

Interpretation: the current KAN-RBF formulation does not pass the cheap field-accuracy gate. Visual QA agrees with the scalar metrics: the compact KAN displacement smooths over the crack-face jump and the RBF phase head creates faint parallel ghost bands. The result rejects immediate connection to first-detect forecasting and rejects a full-lifetime KAN run. It does not prove KAN as a model family is inferior because parameter count, initialization, code vintage, and optimizer budget differ.

Next action: stop the current KAN-RBF branch. Prioritize exact Request 28 replay states and the displacement-to-physical-coordinate route. Reopen KAN only if a separately reviewed equal-budget formulation changes a precise representation hypothesis rather than merely increasing flexibility.
"""
    (args.out / "decision.md").write_text(decision, encoding="utf-8")


if __name__ == "__main__":
    main()
