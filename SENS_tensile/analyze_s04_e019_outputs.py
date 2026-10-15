"""Offline E019 saved-array diagnostics. Never trains or changes frozen scoring."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

from run_s04_e019_frozen_residual_screen import validate_reference, anchor_component_geometry, US


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    states = ("c20s4", "c60s4", "c83s4")
    keys = ("full", "damage", "background")
    fields, traces, rows, diagnostics = {}, {}, [], []
    for state in states:
        d = validate_reference(state, args.raw / "inputs" / f"{state}.npz")
        xy, conn = d["xy"], d["conn"]
        mass = d["mass"] / d["mass"].sum()
        active = d["damage"] > .1
        target = d["equilibrated_uv"]
        base = np.load(args.raw / "backbones" / state / "prediction.npz")["uv"]
        g = anchor_component_geometry(xy, d["damage"], conn, d["mass"])
        core = np.all((xy >= g["lower"]) & (xy <= g["upper"]), axis=1)
        support = np.all((xy > np.asarray(g["lower"]) - .02) & (xy < np.asarray(g["upper"]) + .02), axis=1)
        fields[state] = (d, {})
        for arm in ("backbone", "unrestricted", "localized"):
            if arm == "backbone":
                uv, trace = base, None
                run_id = "inherited E017 alpha.7 seed7"
            else:
                paths = list((args.raw / "runs").glob(f"*-{state}-{arm}-s7"))
                assert len(paths) == 1
                path = paths[0]
                uv = np.load(path / "prediction.npz")["uv"]
                trace = json.loads((path / "monitoring.json").read_text())
                run_id = path.name
                assert [t["step"] for t in trace] == list(range(0, 10001, 1000))
                traces[state, arm] = trace
            sq = np.sum((uv - target) ** 2, axis=1) / abs(US) ** 2
            r = dict(state=state, arm=arm, run_id=run_id)
            for key, mask in zip(keys, (np.ones(len(mass), bool), active, ~active)):
                r[key] = float(np.sqrt(np.sum(mass[mask] * sq[mask]) / mass[mask].sum()))
            r["damage_fraction_of_squared_full_error"] = float(np.sum(mass[active] * sq[active]) / np.sum(mass * sq))
            rows.append(r)
            fields[state][1][arm] = sq
            if arm == "localized":
                delta, residual = uv-base, target-base
                denom = np.sum(mass[:, None] * delta**2)
                scale = float(np.sum(mass[:, None] * delta * residual) / denom)
                best = base + scale * delta
                best_full = float(np.sqrt(np.sum(mass[:, None] * (best-target)**2)) / abs(US))
                diagnostics.append(dict(state=state, amplitude_oracle_scale=scale,
                    amplitude_oracle_full=best_full,
                    outside_max_abs_delta=float(np.max(np.abs(delta[~support]))),
                    damage_core_error_fraction=float(np.sum(mass[active & core]*sq[active & core])/np.sum(mass[active]*sq[active])),
                    damage_taper_error_fraction=float(np.sum(mass[active & support & ~core]*sq[active & support & ~core])/np.sum(mass[active]*sq[active])),
                    damage_outside_error_fraction=float(np.sum(mass[active & ~support]*sq[active & ~support])/np.sum(mass[active]*sq[active])),
                    trace=[dict(step=t["step"], full=t["displacement_mass_rms_over_abs_Us"], damage=t["damage_conditional_rms_over_abs_Us"], background=t["background_conditional_rms_over_abs_Us"]) for t in trace]))
    with (args.out / "regional_metrics.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (args.out / "offline_diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
    colors = dict(backbone="#777777", unrestricted="#2878b5", localized="#df651b")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout="constrained")
    for ax, key in zip(axes, keys):
        for arm in colors:
            vals = [next(r[key] for r in rows if r["state"] == s and r["arm"] == arm) for s in states]
            ax.plot(range(3), vals, "o-", label=arm, color=colors[arm])
        if key == "full": ax.axhline(.001, color="black", ls="--", label="primary threshold .001")
        ax.set(xticks=range(3), xticklabels=["c20", "c60", "c83"], yscale="log", title=key, ylabel="Conditional mass RMS / |Us|")
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Full mass RMS / |Us|"); axes[0].legend(fontsize=8)
    fig.suptitle("S04-E019 R001–R006 | synthetic same-state fit | seed7 | final step10000")
    fig.savefig(args.out / "regional_comparison.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(12, 9), layout="constrained")
    trace_keys = ("displacement_mass_rms_over_abs_Us", "damage_conditional_rms_over_abs_Us", "background_conditional_rms_over_abs_Us")
    for i, state in enumerate(states):
        for j, (key, tk) in enumerate(zip(keys, trace_keys)):
            ax=axes[i,j]
            base=next(r[key] for r in rows if r["state"]==state and r["arm"]=="backbone")
            ax.axhline(base, color=colors["backbone"], ls=":", label="inherited backbone")
            for arm in ("unrestricted", "localized"):
                tr=traces[state,arm]; ax.plot([t["step"] for t in tr], [t[tk] for t in tr], label=arm,color=colors[arm])
            if j==0: ax.axhline(.001,color="black",ls="--")
            ax.set(title=f"{state}: {key}", yscale="log",xlabel="New residual steps",ylabel="RMS / |Us|"); ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=7)
    fig.suptitle("S04-E019 fixed passive trajectories | no checkpoint selection")
    fig.savefig(args.out / "regional_trajectories.png",dpi=150); plt.close(fig)
    fig, axes = plt.subplots(3,3,figsize=(12,8),layout="constrained")
    for i,state in enumerate(states):
        d, arrays=fields[state]; xy,conn=d["xy"],d["conn"]
        # All states and all arms; Q4 cell mean of normalized nodal squared errors.
        cell={a:np.sqrt(sq[conn].mean(axis=1)) for a,sq in arrays.items()}
        vmax=max(float(v.max()) for v in cell.values())
        for j,arm in enumerate(colors):
            ax=axes[i,j]; pc=PolyCollection(xy[conn],array=cell[arm],cmap="magma",clim=(0,vmax),rasterized=True,edgecolors="none",linewidths=0,antialiased=False)
            ax.add_collection(pc); ax.set(xlim=(-.5,.5),ylim=(-.06,.06),aspect="auto",title=f"{state}: {arm}",xlabel="x",ylabel="y")
            fig.colorbar(pc,ax=ax,label="Cell RMS UV error / |Us|")
    fig.suptitle("Native Q4 near-crack view | fixed y ±.06 | common scale within each state")
    fig.savefig(args.out / "near_crack_errors.png",dpi=180); plt.close(fig)
    for name in ("regional_comparison", "regional_trajectories", "near_crack_errors"):
        (args.out/f"{name}.md").write_text(f"# {name}\n\nData provenance: E019 exact ae238713, R001–R006, all c20/c60/c83 s4 states; saved final UV arrays and fixed passive traces, inherited exact E017 backbones. Generated by analyze_s04_e019_outputs.py. Limitations: synthetic same-state development fitting only, no holdout/physical qualification. How to read: UV errors normalized by |Us|; regional conditional RMS differs from contribution to whole-domain squared RMS. Comparison includes fixed .001 primary threshold; traces do not select checkpoints. Near-crack panels use native Q4 cell mean nodal squared error, fixed y ±.06 and one shared zero-to-maximum scale per state. See regional_metrics.csv and offline_diagnostics.json for exact values; the frozen aggregate remains authoritative.\n")


if __name__ == "__main__":
    main()
