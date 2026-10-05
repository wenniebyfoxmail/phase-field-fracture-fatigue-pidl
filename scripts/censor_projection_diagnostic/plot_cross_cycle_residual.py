"""Render the frozen S04-E005 trend and spatial residual diagnostics."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument("audit", type=Path)
args = parser.parse_args()
rows = list(csv.DictReader((args.audit / "cycle_residuals.csv").open()))
trend = json.loads((args.audit / "trend_summary.json").read_text())
fields = np.load(args.audit / "spatial_fields.npz")
cycles = [int(row["cycle"]) for row in rows]
out = args.audit / "figures"
out.mkdir(exist_ok=True)


fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
for axis, key, title in (
    (axes[0], "rho_u", "Free-UV residual"),
    (axes[1], "box_rho_d_common_free", "Damage box residual / common-free"),
):
    values = [float(row[key]) for row in rows]
    line_style = "-" if trend["trend_status"] == "EVALUATED" else "none"
    axis.plot(cycles, values, marker="o", ls=line_style, label="PIDL histories on FEM field")
    native_key = "matlab_rho_u" if key == "rho_u" else "matlab_box_rho_d_common_free"
    native_label = (
        "archived FEM UV oracle"
        if key == "rho_u"
        else "archived FEM damage diagnostic (different operator semantics)"
    )
    native_style = "--" if trend["trend_status"] == "EVALUATED" else "none"
    axis.plot(
        cycles,
        [float(row[native_key]) for row in rows],
        marker="s",
        ls=native_style,
        label=native_label,
    )
    axis.axhline(1.0e-3, color="black", lw=0.8, ls=":", label="frozen 1e-3 screen")
    axis.set_yscale("log")
    axis.set_xlabel("Physical cycle (native peak s4)")
    axis.set_ylabel(key)
    axis.set_title(title)
    if trend["trend_status"] != "EVALUATED":
        axis.text(0.5, 0.95, "TREND BLOCKED: vector gate failure", transform=axis.transAxes, ha="center", va="top")
    axis.set_xticks(cycles)
    axis.legend(fontsize=7)
fig.savefig(out / "cross_cycle_trend.png", dpi=200)
fig.savefig(out / "cross_cycle_trend.pdf")
plt.close(fig)


uv_max = max(float(fields[f"c{cycle}_pidl_uv_density"].max()) for cycle in cycles)
dmax = max(float(np.abs(fields[f"c{cycle}_pidl_projected_damage"]).max()) for cycle in cycles)
fig, axes = plt.subplots(2, len(cycles), figsize=(4 * len(cycles), 7), layout="constrained")
for column, cycle in enumerate(cycles):
    xy = fields[f"c{cycle}_xy"]
    damage = fields[f"c{cycle}_damage"]
    uv = fields[f"c{cycle}_pidl_uv_density"]
    projected = np.abs(fields[f"c{cycle}_pidl_projected_damage"])
    panel = axes[0, column].scatter(xy[:, 0], xy[:, 1], c=uv, s=1, vmin=0, vmax=uv_max, rasterized=True)
    axes[0, column].tricontour(xy[:, 0], xy[:, 1], damage, levels=[0.25, 0.5, 0.75], colors="white", linewidths=0.35)
    axes[0, column].set_title(f"c{cycle}: assembled UV dual density")
    fig.colorbar(panel, ax=axes[0, column], shrink=0.75)
    panel = axes[1, column].scatter(xy[:, 0], xy[:, 1], c=projected, s=1, vmin=0, vmax=dmax, rasterized=True)
    axes[1, column].tricontour(xy[:, 0], xy[:, 1], damage, levels=[0.25, 0.5, 0.75], colors="white", linewidths=0.35)
    axes[1, column].set_title(f"c{cycle}: |box-projected damage correction|")
    fig.colorbar(panel, ax=axes[1, column], shrink=0.75)
    for row in range(2):
        axes[row, column].set_aspect("equal")
        axes[row, column].set_xlabel("x")
        axes[row, column].set_ylabel("y")
fig.savefig(out / "cross_cycle_spatial.png", dpi=180)
fig.savefig(out / "cross_cycle_spatial.pdf")
plt.close(fig)


pairs = [(76, 82), (82, 83)]
uv_diff_max = max(
    float(np.abs(fields[f"c{right}_pidl_uv_density"] - fields[f"c{left}_pidl_uv_density"]).max())
    for left, right in pairs
)
d_diff_max = max(
    float(
        np.abs(
            np.abs(fields[f"c{right}_pidl_projected_damage"])
            - np.abs(fields[f"c{left}_pidl_projected_damage"])
        ).max()
    )
    for left, right in pairs
)
fig, axes = plt.subplots(2, len(pairs), figsize=(8, 7), layout="constrained")
for column, (left, right) in enumerate(pairs):
    xy = fields[f"c{left}_xy"]
    uv_delta = fields[f"c{right}_pidl_uv_density"] - fields[f"c{left}_pidl_uv_density"]
    d_delta = np.abs(fields[f"c{right}_pidl_projected_damage"]) - np.abs(fields[f"c{left}_pidl_projected_damage"])
    panel = axes[0, column].scatter(xy[:, 0], xy[:, 1], c=uv_delta, s=1, cmap="coolwarm", vmin=-uv_diff_max, vmax=uv_diff_max, rasterized=True)
    axes[0, column].set_title(f"UV magnitude change c{left}->c{right}")
    fig.colorbar(panel, ax=axes[0, column], shrink=0.75)
    panel = axes[1, column].scatter(xy[:, 0], xy[:, 1], c=d_delta, s=1, cmap="coolwarm", vmin=-d_diff_max, vmax=d_diff_max, rasterized=True)
    axes[1, column].set_title(f"Damage correction change c{left}->c{right}")
    fig.colorbar(panel, ax=axes[1, column], shrink=0.75)
    for row in range(2):
        axes[row, column].set_aspect("equal")
        axes[row, column].set_xlabel("x")
        axes[row, column].set_ylabel("y")
fig.savefig(out / "cross_cycle_spatial_change.png", dpi=180)
fig.savefig(out / "cross_cycle_spatial_change.pdf")
plt.close(fig)


(out / "README_analysis.md").write_text(
    """# S04-E005 cross-cycle residual figures

Question: on the same native FEM peak fields and correctly paired native-Q4 PIDL predecessor histories, is the mismatch already visible at c76 and does it increase by the frozen local threefold rule at both c82 and c83?

Read in order: `cross_cycle_trend` keeps UV and damage channels separate and shows the unchanged 1e-3 screen; `cross_cycle_spatial` locates the assembled nodal UV dual-density and box-projected damage correction under common cross-cycle colour rules; `cross_cycle_spatial_change` shows fixed c76->c82 and c82->c83 changes without crack-tip realignment.

Sources: `cycle_residuals.csv`, `trend_summary.json`, and `spatial_fields.npz` from S04-E005-R001. White contours are native FEM damage 0.25/0.5/0.75. The UV map uses globally assembled nodal residuals, not unassembled element force magnitudes.

Allowed: a local c76-to-c82/c83 statement under the frozen branch and explicit stationarity/feasibility qualifications. Blocked: onset before c76, a complete c20-c83 temporal verdict, FEM teacher accuracy, field-error growth, causal attribution to the optimizer/network/fatigue mechanism, or replacement of S04-E006. Numerical vector agreement and stationarity are separate gates.

The archived FEM damage trace is a contextual diagnostic with different penalty/fixed-DOF semantics; it is not a damage-operator equivalence claim. If any same-field UV vector comparison fails, points remain visible but are not connected and the trend is explicitly marked blocked.
"""
)
