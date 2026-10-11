#!/usr/bin/env python3
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
rows = list(csv.DictReader((HERE / "r002_metrics.csv").open()))
monitor = {
    state: json.loads((HERE / f"r002_{state[:3]}_monitoring.json").read_text())
    for state in ("c20s4", "c83s4")
}
colors = {"c20s4": "#2878B5", "c83s4": "#D95319"}

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
ax = axes[0]
for state in ("c20s4", "c83s4"):
    ax.plot(
        [r["step"] for r in monitor[state]],
        [r["displacement_mass_rms_over_abs_Us"] for r in monitor[state]],
        marker="o", ms=3.5, lw=1.8, color=colors[state], label=state,
    )
ax.axhline(1e-3, color="black", ls="--", lw=1.2, label="absolute gate")
ax.set_yscale("log")
ax.set_xlabel("Training step")
ax.set_ylabel(r"Displacement RMS / $|U_s|$")
ax.set_title("Fixed full-field monitoring")
ax.grid(alpha=0.25)
ax.legend(frameon=False)

ax = axes[1]
x = np.arange(2)
baseline = np.array([float(row["baseline_displacement"]) for row in rows])
repaired = np.array([float(row["displacement_mass_rms_over_abs_Us"]) for row in rows])
width = 0.34
ax.bar(x - width / 2, baseline, width, color="#A9A9A9", label="S04-E013 baseline")
ax.bar(x + width / 2, repaired, width, color=[colors[row["state"]] for row in rows],
       label="stratified repair")
ax.axhline(1e-3, color="black", ls="--", lw=1.2, label="absolute gate")
for i, row in enumerate(rows):
    improvement = 100 * float(row["relative_improvement"])
    ax.text(i + width / 2, repaired[i] + 0.00012, f"{improvement:.1f}% better",
            ha="center", va="bottom", fontsize=9)
ax.set_xticks(x, [row["state"] for row in rows])
ax.set_ylabel(r"Final displacement RMS / $|U_s|$")
ax.set_title("Final result versus frozen comparator")
ax.set_ylim(0, 0.0062)
ax.grid(axis="y", alpha=0.25)
ax.legend(frameon=False, fontsize=8)

fig.suptitle("S04-E014: sampling helps, but does not meet the repair gate", fontweight="bold")
fig.tight_layout()
for suffix in ("png", "pdf"):
    fig.savefig(HERE / "figures" / f"r002_sampling_repair_decision.{suffix}", dpi=220,
                bbox_inches="tight")
