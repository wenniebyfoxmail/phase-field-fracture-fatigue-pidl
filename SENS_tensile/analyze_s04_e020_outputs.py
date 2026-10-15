"""Offline paired E020/E019 saved-array analysis; never trains or changes scoring."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

from run_s04_e019_frozen_residual_screen import validate_reference, US, sha256
from aggregate_s04_e020_delayed_decay import validate_schedule_and_pair
from s04_e020_delayed_decay import CONTROL_LOCKS, check_pair_identity

STATES = ("c20s4", "c60s4", "c83s4")
REGIONS = ("full", "damage", "background")
TRACE_KEYS = ("displacement_mass_rms_over_abs_Us", "damage_conditional_rms_over_abs_Us",
              "background_conditional_rms_over_abs_Us")
COLORS = {"backbone": "#777777", "E019": "#2878b5", "E020": "#df651b"}


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(raw, old, out):
    summary = json.loads((raw / "aggregate/summary.json").read_text())
    assert summary["valid_completed_runs"] == 3 and not summary["integrity_errors"]
    assert not summary["missing"]
    # Require all three final files before computing or displaying any comparison.
    candidates = {}
    for state in STATES:
        paths = list((raw / "runs").glob(f"*-{state}-localized-s7"))
        assert len(paths) == 1, (state, paths)
        candidates[state] = paths[0]
        for name in ("metrics.json", "prediction.npz", "monitoring.json", "RUN_RECEIPT.json", "learning_rates.npy", "final_step_10000.pt"):
            assert (paths[0] / name).is_file(), (state, name)
    rows, comparisons, support_rows, traces, fields, trajectory_rows = [], [], [], {}, {}, []
    for state in STATES:
        data = validate_reference(state, old / "inputs" / f"{state}.npz")
        w = data["mass"] / data["mass"].sum()
        active = data["damage"] > .1
        target = data["equilibrated_uv"]
        base = np.load(old / "backbones" / state / "prediction.npz")["uv"]
        candidate = candidates[state]
        validate_schedule_and_pair(candidate / "metrics.json")
        record = json.loads((candidate / "metrics.json").read_text())
        receipt = json.loads((candidate / "RUN_RECEIPT.json").read_text())
        assert receipt["code_commit"] == summary["code_commit"] and receipt["dirty"] is False
        assert record["steps"] == record["new_optimizer_steps"] == 10000
        check_pair_identity(state, record["geometry"], record["backbone_digest"], record["initial_residual_digest"], record["sampler_index_sha256"])
        geometry = record["geometry"]
        xy, conn = data["xy"], data["conn"]
        support = np.all((xy > np.asarray(geometry["lower"]) - .02) & (xy < np.asarray(geometry["upper"]) + .02), axis=1)
        core = np.all((xy >= geometry["lower"]) & (xy <= geometry["upper"]), axis=1)
        fields[state] = (xy, conn, {})
        local_rows = {}
        for label, path in (("backbone", None), ("E019", old / "runs" / CONTROL_LOCKS[state]["run_id"]), ("E020", candidate)):
            if path is None:
                uv, trace = base, None
            else:
                if label == "E019":
                    for name, digest in CONTROL_LOCKS[state]["files"].items():
                        assert sha256(path / name) == digest, (state, name)
                else:
                    for name, key in (("prediction.npz", "prediction_sha256"), ("monitoring.json", "monitoring_sha256")):
                        assert sha256(path / name) == record[key]
                uv = np.load(path / "prediction.npz")["uv"]
                trace = json.loads((path / "monitoring.json").read_text())
                assert [t["step"] for t in trace] == list(range(0, 10001, 1000))
                traces[state, label] = trace
            assert uv.shape == target.shape and np.isfinite(uv).all()
            sq = np.sum((uv - target)**2, axis=1) / abs(US)**2
            row = dict(state=state, arm=label)
            for region, mask in zip(REGIONS, (np.ones(len(w), bool), active, ~active)):
                row[region] = float(np.sqrt(np.sum(w[mask] * sq[mask]) / w[mask].sum()))
            row["damage_squared_error_fraction"] = float(np.sum(w[active] * sq[active]) / np.sum(w * sq))
            if trace is not None:
                for region, key in zip(REGIONS, TRACE_KEYS):
                    np.testing.assert_allclose(row[region], trace[-1][key], rtol=0, atol=1e-14)
                for t in trace:
                    trajectory_rows.append(dict(state=state, arm=label, step=t["step"], **{k: t[v] for k, v in zip(REGIONS, TRACE_KEYS)}))
            rows.append(row); local_rows[label] = row
            fields[state][2][label] = np.sqrt(sq[conn].mean(axis=1))
            sr = dict(state=state, arm=label, outside_support_max_abs_delta=float(np.max(np.abs((uv-base)[~support]))))
            for name, mask in (("background_inside", ~active & support), ("background_outside", ~active & ~support)):
                sr[name + "_rms"] = float(np.sqrt(np.sum(w[mask]*sq[mask]) / w[mask].sum()))
            if label == "E020":
                delta, desired = uv-base, target-base
                scale = float(np.sum(w[:, None]*delta*desired) / np.sum(w[:, None]*delta**2))
                sr["oracle_scale"] = scale
                sr["oracle_full"] = float(np.sqrt(np.sum(w[:, None]*(base+scale*delta-target)**2))/abs(US))
                sr["damage_core_fraction"] = float(np.sum(w[active & core]*sq[active & core])/np.sum(w[active]*sq[active]))
                assert sr["outside_support_max_abs_delta"] <= 1e-12
            support_rows.append(sr)
        for region in REGIONS:
            b, c, n = (local_rows[a][region] for a in COLORS)
            comparisons.append(dict(state=state, region=region, backbone=b, E019=c, E020=n,
                E020_reduction_percent_vs_E019=100*(1-n/c), E020_reduction_percent_vs_backbone=100*(1-n/b)))
    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / "regional_metrics.csv", rows)
    write_csv(out / "paired_comparison.csv", comparisons)
    write_csv(out / "trajectories.csv", trajectory_rows)
    (out / "support_and_oracle.json").write_text(json.dumps(support_rows, indent=2))
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout="constrained")
    for ax, region in zip(axes, REGIONS):
        for arm, color in COLORS.items():
            ax.plot(range(3), [next(r[region] for r in rows if r["state"] == s and r["arm"] == arm) for s in STATES], "o-", color=color, label=arm)
        if region == "full": ax.axhline(.001, color="black", ls="--", label="primary .001")
        ax.set(xticks=range(3), xticklabels=["c20", "c60", "c83"], yscale="log", title=region, ylabel="Mass UV RMS / |Us|")
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("E020 delayed decay vs E019 | final update10000 | seed7")
    for ext in ("png", "pdf"): fig.savefig(out / f"regional_comparison.{ext}", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(12, 9), layout="constrained")
    for i, state in enumerate(STATES):
        for j, (region, key) in enumerate(zip(REGIONS, TRACE_KEYS)):
            ax = axes[i, j]
            ax.axhline(next(r[region] for r in rows if r["state"] == state and r["arm"] == "backbone"), color=COLORS["backbone"], ls=":")
            for label in ("E019", "E020"):
                tr = traces[state, label]; ax.plot([t["step"] for t in tr], [t[key] for t in tr], color=COLORS[label], label=label)
            if j == 0: ax.axhline(.001, color="black", ls="--")
            ax.axvline(8000, color="black", alpha=.2)
            ax.set(title=f"{state}: {region}", yscale="log", xlabel="New residual updates", ylabel="RMS / |Us|"); ax.grid(alpha=.2)
    axes[0, 0].legend()
    fig.savefig(out / "regional_trajectories.png", dpi=160); plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(12, 8), layout="constrained")
    for i, state in enumerate(STATES):
        xy, conn, arrays = fields[state]; vmax = max(float(a.max()) for a in arrays.values())
        for j, label in enumerate(COLORS):
            ax = axes[i,j]; pc = PolyCollection(xy[conn], array=arrays[label], cmap="magma", clim=(0,vmax), rasterized=True, edgecolors="none", linewidths=0, antialiased=False)
            ax.add_collection(pc); ax.set(xlim=(-.5,.5), ylim=(-.06,.06), title=f"{state}: {label}", xlabel="x", ylabel="y")
            fig.colorbar(pc, ax=ax, label="Cell RMS UV error / |Us|")
    fig.savefig(out / "near_crack_errors.png", dpi=180); plt.close(fig)
    takeaway = "; ".join(
        f"{state}: E019 full={next(r['full'] for r in rows if r['state'] == state and r['arm'] == 'E019'):.12g}, "
        f"E020 full={next(r['full'] for r in rows if r['state'] == state and r['arm'] == 'E020'):.12g}"
        for state in STATES
    )
    for stem in ("regional_comparison", "regional_trajectories", "near_crack_errors"):
        (out / f"{stem}.md").write_text(f"# {stem}\n\nExact source671fba2; paired historical E019 localized controls ae238713, seed7, alpha.7, frozen history/fatigue. Saved final UV arrays, original references and backbones; see regional_metrics.csv, paired_comparison.csv, trajectories.csv. Full and conditional regional mass UV RMS / |Us|; damage>.1, background complement. Lower is better. .001 applies to full only. No checkpoint selection. Near-crack panels show Q4 cell mean nodal squared error, y±.06, shared scale within each state. Support diagnostics include inside-window background, independent of outside-support invariance. Oracle is post-hoc diagnostic only, never scored prediction. One exposed trajectory/seed; no physical/transfer qualification. Frozen producer scoring and separate strict local replay remain authoritative with any portability exceptions preserved.\n")
        with (out / f"{stem}.md").open("a") as stream:
            stream.write(f"\nMain numerical takeaway (final step only): {takeaway}. All states selected in advance; see exact paired_comparison.csv and README_analysis.md.\n")
    print(json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.raw, args.old, args.out)
