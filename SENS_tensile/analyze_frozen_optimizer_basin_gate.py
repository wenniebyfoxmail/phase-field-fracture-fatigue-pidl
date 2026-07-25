#!/usr/bin/env python3
"""Summarize and plot frozen optimizer-basin gate results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def numeric(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def final_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = [row for row in rows if row.get("stage") == "best_restored"]
    if not selected:
        raise ValueError("no best_restored rows found")
    return selected


def classify_branch(initial: dict[str, str], final: dict[str, str]) -> str:
    loss_drop = numeric(initial, "loss_total") - numeric(final, "loss_total")
    grad_ratio = numeric(final, "gradient_rms") / max(numeric(initial, "gradient_rms"), 1.0e-30)
    has_fem = np.isfinite(numeric(final, "active_absolute_p99_iou"))
    if not np.isfinite(loss_drop) or not np.isfinite(grad_ratio):
        return "invalid"
    if loss_drop <= 1.0e-4 and grad_ratio >= 0.1:
        return "no_material_stationarity_gain"
    if not has_fem:
        return "stationarity_only_no_fem_reference"
    iou_gain = numeric(final, "active_absolute_p99_iou") - numeric(
        initial, "active_absolute_p99_iou"
    )
    mae_gain = numeric(initial, "active_log_mae") - numeric(final, "active_log_mae")
    if loss_drop > 1.0e-4 and grad_ratio < 0.1 and iou_gain > 0.02 and mae_gain > 0.02:
        return "optimizer_confounder_supported"
    if loss_drop > 1.0e-4 and grad_ratio < 0.1 and iou_gain <= 0.02:
        return "objective_mechanism_misalignment_signal"
    return "mixed"


def branch_pairs(rows: list[dict[str, str]]):
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["branch"], []).append(row)
    pairs = []
    for branch, branch_rows in grouped.items():
        initial = next((row for row in branch_rows if row["stage"] == "initial"), None)
        final = next((row for row in reversed(branch_rows) if row["stage"] == "best_restored"), None)
        if initial is not None and final is not None:
            pairs.append((branch, initial, final))
    return pairs


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def plot_traces(rows: list[dict[str, str]], output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for branch, branch_rows in _group(rows).items():
        x = np.asarray([numeric(row, "record") for row in branch_rows])
        axes[0].plot(x, [numeric(row, "loss_total") for row in branch_rows], alpha=0.55, label=branch)
        axes[1].semilogy(
            x,
            np.maximum([numeric(row, "gradient_rms") for row in branch_rows], 1.0e-16),
            alpha=0.55,
            label=branch,
        )
    axes[0].set(xlabel="optimizer record", ylabel="total objective", title="Frozen-state objective")
    axes[1].set(xlabel="optimizer record", ylabel="gradient RMS", title="Direct total gradient")
    axes[0].grid(alpha=0.25)
    axes[1].grid(alpha=0.25)
    if len(_group(rows)) <= 12:
        axes[1].legend(fontsize=6, loc="best")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def _group(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["branch"], []).append(row)
    return grouped


def plot_objective_mechanism(final: list[dict[str, str]], output: Path) -> bool:
    valid = [row for row in final if np.isfinite(numeric(row, "active_absolute_p99_iou"))]
    if not valid:
        return False
    fig, ax = plt.subplots(figsize=(7, 5))
    for row in valid:
        ax.scatter(
            numeric(row, "loss_total"),
            numeric(row, "active_absolute_p99_iou"),
            s=35,
            label=row["branch"],
        )
    ax.set(
        xlabel="PIDL total objective",
        ylabel="FEM absolute-p99 active IoU",
        title="Does a lower PIDL objective imply a more FEM-like mechanism?",
    )
    ax.grid(alpha=0.25)
    if len(valid) <= 12:
        ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return True


def write_decision(path: Path, summaries: list[dict], has_fem: bool) -> None:
    counts: dict[str, int] = {}
    for row in summaries:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    lines = [
        "# Frozen optimizer-basin decision",
        "",
        "## Evidence boundary",
        "",
        "This is a frozen-state diagnostic. It does not advance fatigue cycles and does not replace the FEM reference.",
        "",
        f"FEM-centred reference metrics present: **{'yes' if has_fem else 'no'}**.",
        "",
        "## Branch classifications",
        "",
        "| classification | count |",
        "|---|---:|",
    ]
    lines.extend(f"| `{key}` | {value} |" for key, value in sorted(counts.items()))
    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "- Stationarity and FEM fields both improve: optimizer remains a material confounder.",
            "- Objective/gradient improve but FEM fields do not: evidence of objective-mechanism misalignment.",
            "- Several stationary field clusters: basin selection matters.",
            "- One stable non-FEM cluster: optimizer basin is unlikely to be the primary cause.",
            "",
            "Pure Graph is not assigned a retrospective convergence verdict unless exact frozen model/history provenance is available.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    output = (args.out_dir or (run_dir / "analysis")).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = read_rows(run_dir / "all_optimizer_traces.csv")
    pairs = branch_pairs(rows)
    summaries = []
    for branch, initial, final in pairs:
        summary = dict(final)
        summary["classification"] = classify_branch(initial, final)
        summary["loss_drop"] = numeric(initial, "loss_total") - numeric(final, "loss_total")
        summary["gradient_rms_ratio"] = numeric(final, "gradient_rms") / max(
            numeric(initial, "gradient_rms"), 1.0e-30
        )
        summaries.append(summary)
    write_csv(output / "best_branch_summary.csv", summaries)
    plot_traces(rows, output / "optimizer_objective_gradient_traces.png")
    has_fem = plot_objective_mechanism(
        final_rows(rows), output / "objective_vs_fem_active_support.png"
    )
    write_decision(output / "decision.md", summaries, has_fem)
    (output / "analysis_manifest.json").write_text(
        json.dumps(
            {
                "source": str(run_dir / "all_optimizer_traces.csv"),
                "branches": len(pairs),
                "has_fem_reference": has_fem,
                "classification_is_predeclared_diagnostic_not_model_promotion": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
