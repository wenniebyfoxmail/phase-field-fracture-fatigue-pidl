#!/usr/bin/env python3
"""Compare c1 alt-min follow-up branches against FEM22 c1 peak gates."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_c1_altmin_vs_fem22 import load_fem22_c1_peak, project, reductions


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "_analysis_fem_mechanism_20260528" / "experiments" / "c1_altmin_branch_matrix_20260603"
SYNC = EXPERIMENT / "0_sync"
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"

BRANCHES = {
    "baseline_r3_a2000": ROOT
    / "_analysis_fem_mechanism_20260528"
    / "experiments"
    / "c1_altmin_20260603"
    / "0_sync",
    "shortAlpha_a200": SYNC / "shortAlpha_a200",
    "shortAlpha_a500": SYNC / "shortAlpha_a500",
    "smallStagger_r6": SYNC / "smallStagger_r6",
    "alphaLR1e6_r6": SYNC / "alphaLR1e6_r6",
}
FIELDS = ("alpha", "eps_eq", "psi_raw", "g_alpha", "psi_active")
METRICS = ("tip_2l0_mean", "p99", "p999", "max")


def load_branch(folder: Path) -> dict[str, np.ndarray]:
    raw = np.load(folder / "c1_altmin_fields.npz")
    return {
        "labels": np.asarray(raw["labels"]).astype(str),
        "centroids": np.column_stack([raw["elem_x"], raw["elem_y"]]).astype(float),
        "areas": raw["area_elem"].astype(float),
        "alpha": raw["alpha_elem"].astype(float),
        "eps_eq": raw["eps_eq_elem"].astype(float),
        "psi_raw": raw["psi_raw_elem"].astype(float),
        "g_alpha": raw["g_alpha_elem"].astype(float),
        "psi_active": raw["psi_active_elem"].astype(float),
    }


def last_uv_label(labels: np.ndarray) -> str:
    uv = [label for label in labels if label.endswith("_uv")]
    return uv[-1] if uv else str(labels[-1])


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    fem = load_fem22_c1_peak()
    ratio_rows: list[dict[str, object]] = []
    trace_rows: list[pd.DataFrame] = []
    for branch, folder in BRANCHES.items():
        alt = load_branch(folder)
        label = last_uv_label(alt["labels"])
        idx = int(np.where(alt["labels"] == label)[0][0])
        for field in FIELDS:
            fem_proj = project(fem[field], fem["centroids"], alt["centroids"])
            f_red = reductions(fem_proj, alt["areas"], alt["centroids"])
            p_red = reductions(alt[field][idx], alt["areas"], alt["centroids"])
            for metric in METRICS:
                denom = f_red[metric]
                ratio_rows.append(
                    {
                        "branch": branch,
                        "selected_state": label,
                        "field": field,
                        "metric": metric,
                        "PIDL": p_red[metric],
                        "FEM22_projected": denom,
                        "PIDL_over_FEM": p_red[metric] / denom
                        if np.isfinite(denom) and abs(denom) > 1e-30
                        else np.nan,
                    }
                )
        trace = pd.read_csv(folder / "c1_altmin_trace.csv")
        trace["branch"] = branch
        trace_rows.append(trace)
    return pd.DataFrame(ratio_rows), pd.concat(trace_rows, ignore_index=True)


def plot_branch_scalars(trace: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.2), constrained_layout=True)
    for branch, sub in trace.groupby("branch", sort=False):
        x = np.arange(len(sub))
        axes[0].plot(x, sub["psi_raw_max"], marker="o", linewidth=1.2, label=branch)
        axes[1].plot(x, sub["psi_active_max"], marker="o", linewidth=1.2, label=branch)
        alpha_grad = sub["grad_logEhist"].replace(0.0, np.nan)
        axes[2].plot(x, alpha_grad, marker="o", linewidth=1.2, label=branch)
    axes[0].set_ylabel("psi_raw max")
    axes[1].set_ylabel("psi_active max")
    axes[2].set_ylabel("grad logE_hist")
    for ax in axes:
        ax.set_yscale("log")
        ax.set_xlabel("exported substage index")
        ax.grid(True, alpha=0.25)
    axes[2].legend(frameon=False, fontsize=7, loc="best")
    fig.suptitle("C1 alt-min branch matrix: scalar trajectories")
    out = OUT_FIG / "c1_altmin_branch_scalar_matrix.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_final_ratios(ratios: pd.DataFrame) -> Path:
    key = ratios[
        ratios["field"].isin(["eps_eq", "psi_raw", "psi_active", "alpha"])
        & ratios["metric"].isin(["tip_2l0_mean", "max"])
    ].copy()
    key["series"] = key["field"] + " " + key["metric"]
    branches = list(BRANCHES)
    series = ["eps_eq tip_2l0_mean", "psi_raw max", "psi_active tip_2l0_mean", "alpha max"]
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.4), constrained_layout=True)
    for ax, name in zip(axes.ravel(), series):
        vals = key[key["series"] == name].set_index("branch").reindex(branches)["PIDL_over_FEM"]
        ax.bar(np.arange(len(branches)), vals.to_numpy(), color="#0072B2")
        ax.axhline(1.0, color="0.25", linestyle="--", linewidth=1.0)
        ax.set_yscale("log")
        ax.set_title(name)
        ax.grid(True, axis="y", alpha=0.25)
    for ax in axes[-1]:
        ax.set_xticks(np.arange(len(branches)))
        ax.set_xticklabels(branches, rotation=30, ha="right")
    for ax in axes[0]:
        ax.set_xticks(np.arange(len(branches)))
        ax.set_xticklabels([])
    fig.suptitle("Final uv state ratios against FEM22 c1 peak")
    out = OUT_FIG / "c1_altmin_branch_final_ratios.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def write_summary(ratios: pd.DataFrame, trace: pd.DataFrame, figs: list[Path]) -> Path:
    def ratio(branch: str, field: str, metric: str) -> float:
        row = ratios[(ratios["branch"] == branch) & (ratios["field"] == field) & (ratios["metric"] == metric)]
        return float(row["PIDL_over_FEM"].iloc[0])

    final_rows = []
    for branch, sub in trace.groupby("branch", sort=False):
        final_uv = sub[sub["label"].str.endswith("_uv")].iloc[-1]
        final_alpha = sub[sub["label"].str.endswith("_alpha")].iloc[-1]
        final_rows.append(
            {
                "branch": branch,
                "selected_uv": final_uv["label"],
                "psi_raw_max": final_uv["psi_raw_max"],
                "psi_active_max": final_uv["psi_active_max"],
                "alpha_max_after_alpha": final_alpha["alpha_max"],
                "grad_logEhist_after_alpha": final_alpha["grad_logEhist"],
                "eps_eq_tip2_ratio": ratio(branch, "eps_eq", "tip_2l0_mean"),
                "psi_raw_max_ratio": ratio(branch, "psi_raw", "max"),
                "psi_active_tip2_ratio": ratio(branch, "psi_active", "tip_2l0_mean"),
                "alpha_max_ratio": ratio(branch, "alpha", "max"),
            }
        )
    final = pd.DataFrame(final_rows)
    out_csv = OUT_FIG / "c1_altmin_branch_final_summary.csv"
    final.to_csv(out_csv, index=False)

    lines = [
        "# C1 Alt-Min Branch Matrix Result",
        "",
        "## Final UV-State Summary",
        "",
        final.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- Shortening alpha from 2000 to 200 or 500 epochs does not stop the final uv re-equilibration from rebuilding the raw hotspot.",
        "- Smaller repeated uv/alpha blocks also do not suppress the feedback; by the final uv stage, `psi_raw_max` returns to the same order as the original coupled c1 hotspot.",
        "- Lowering alpha RPROP lr to `1e-6` has little effect, consistent with RPROP sign-based updates and/or the alpha stage still being dominated by the irreversibility gradient channel.",
        "- The useful conclusion is negative but sharp: the feedback loop is robust to simple alpha softening and small stagger schedules. The next lever should target the alpha irreversibility/update formulation or the local stiffness/degradation response, not just epoch scheduling.",
        "",
        "## Figures",
        "",
    ]
    lines += [f"- `{fig}`" for fig in figs]
    lines.append(f"- `{out_csv}`")
    out = OUT_ANALYSIS / "c1_altmin_branch_matrix_result.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    ratios, trace = build_tables()
    ratios.to_csv(OUT_FIG / "c1_altmin_branch_fem22_ratios.csv", index=False)
    trace.to_csv(OUT_FIG / "c1_altmin_branch_trace_all.csv", index=False)
    figs = [plot_branch_scalars(trace), plot_final_ratios(ratios)]
    summary = write_summary(ratios, trace, figs)
    print(f"wrote {summary}")
    for fig in figs:
        print(f"wrote {fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
