#!/usr/bin/env python3
"""Piecewise-linear audit of the recorded E013 G25/L25 displacements."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ARM_G = "G25_global_ranking_replay"
ARM_L = "L25_local_support_ranking_beta0p25"
TOL = 1e-14


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def interpolate(left: np.ndarray, right: np.ndarray, lam: float) -> np.ndarray:
    return (1.0 - lam) * left + lam * right


def roots(initial: np.ndarray, left: np.ndarray, right: np.ndarray) -> list[float]:
    result = []
    slope = right - left
    for value, base, delta in zip(initial, left, slope):
        if abs(delta) <= np.finfo(float).eps:
            continue
        root = -(value + base) / delta
        if TOL < root < 1.0 - TOL:
            result.append(float(root))
    return result


def change_roots(left: np.ndarray, right: np.ndarray) -> list[float]:
    return roots(np.zeros_like(left), left, right)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(args.receipt.read_text())
    audit = payload["audit"]
    rows = audit["records"]
    identity = payload["common_initial_identity"]
    if identity["model_state_sha256"] != audit["initial_model_state_sha256"]:
        raise ValueError("model identity mismatch")
    if identity["optimizer_state_sha256"] != audit["initial_optimizer_state_sha256"]:
        raise ValueError("optimizer identity mismatch")
    for row in rows:
        for key in ("global", "local"):
            expected = float(row[f"initial_{key}_margin"])
            for arm in (ARM_G, ARM_L):
                observed = float(row["arms"][arm][f"initial_{key}_margin"])
                if observed != expected:
                    raise ValueError(f"{key} initial margin differs across arms")

    growth = np.asarray([row["growth_cycle"] for row in rows], dtype=int)
    stagnant = np.asarray([row["stagnant_cycle"] for row in rows], dtype=int)
    global_initial = np.asarray([row["initial_global_margin"] for row in rows])
    local_initial = np.asarray([row["initial_local_margin"] for row in rows])

    def arm_values(arm: str, key: str) -> np.ndarray:
        return np.asarray([row["arms"][arm][key] for row in rows], dtype=float)

    global_g = arm_values(ARM_G, "predicted_adamw_global_margin_change")
    global_l = arm_values(ARM_L, "predicted_adamw_global_margin_change")
    local_g = arm_values(ARM_G, "predicted_adamw_local_margin_change")
    local_l = arm_values(ARM_L, "predicted_adamw_local_margin_change")
    ld_g = arm_values(ARM_G, "predicted_adamw_L_D_change")
    ld_l = arm_values(ARM_L, "predicted_adamw_L_D_change")
    lp_g = arm_values(ARM_G, "predicted_adamw_L_P_change")
    lp_l = arm_values(ARM_L, "predicted_adamw_L_P_change")

    global_wrong = global_initial < 0
    global_protected = global_initial > 0
    local_wrong = local_initial < 0
    local_protected = local_initial > 0
    if (int(global_wrong.sum()), int(global_protected.sum())) != (8, 17):
        raise ValueError("global cohort drift")
    if (int(local_wrong.sum()), int(local_protected.sum())) != (17, 8):
        raise ValueError("local cohort drift")

    event_specs = (
        ("global_post_margin", global_initial, global_g, global_l),
        ("local_post_margin", local_initial, local_g, local_l),
        ("global_direction_change", np.zeros_like(global_initial), global_g, global_l),
        ("local_direction_change", np.zeros_like(local_initial), local_g, local_l),
        ("L_D_linear_change", np.zeros_like(global_initial), ld_g, ld_l),
        ("L_P_linear_change", np.zeros_like(global_initial), lp_g, lp_l),
    )
    breakpoint_rows: list[dict[str, Any]] = []
    all_breakpoints = {0.0, 1.0}
    for event, initial, left, right in event_specs:
        slope = right - left
        for index, (value, base, delta) in enumerate(zip(initial, left, slope)):
            if abs(delta) <= np.finfo(float).eps:
                continue
            lam = -(value + base) / delta
            if TOL < lam < 1.0 - TOL:
                all_breakpoints.add(float(lam))
                epsilon = min(1e-10, lam / 4.0, (1.0 - lam) / 4.0)
                before = value + interpolate(left, right, lam - epsilon)[index]
                after = value + interpolate(left, right, lam + epsilon)[index]
                breakpoint_rows.append({
                    "lambda": float(lam),
                    "event": event,
                    "growth_cycle": int(growth[index]),
                    "stagnant_cycle": int(stagnant[index]),
                    "value_before": float(before),
                    "value_after": float(after),
                    "transition": "negative_to_positive" if before < after else "positive_to_negative",
                })
    breakpoint_rows.sort(key=lambda row: (row["lambda"], row["event"], row["growth_cycle"], row["stagnant_cycle"]))
    breakpoint_path = args.output_dir / "displacement_mixture_breakpoints.csv"
    write_csv(breakpoint_path, breakpoint_rows)

    margin_breakpoints = sorted({0.0, 1.0} | {
        float(row["lambda"]) for row in breakpoint_rows
        if row["event"] in {
            "global_post_margin", "local_post_margin",
            "global_direction_change", "local_direction_change",
        }
    })
    interval_rows: list[dict[str, Any]] = []
    for left, right in zip(margin_breakpoints[:-1], margin_breakpoints[1:]):
        lam = (left + right) / 2.0
        delta_global = interpolate(global_g, global_l, lam)
        delta_local = interpolate(local_g, local_l, lam)
        post_global = global_initial + delta_global
        post_local = local_initial + delta_local
        delta_ld = interpolate(ld_g, ld_l, lam)
        delta_lp = interpolate(lp_g, lp_l, lam)
        interval_rows.append({
            "lambda_left_open": left,
            "lambda_right_open": right,
            "lambda_representative": lam,
            "global_wrong_direction_improved": int((delta_global[global_wrong] > 0).sum()),
            "global_wrong_predicted_crossed": int((post_global[global_wrong] > 0).sum()),
            "global_protected_direction_regressed": int((delta_global[global_protected] < 0).sum()),
            "global_protected_predicted_flipped": int((post_global[global_protected] <= 0).sum()),
            "global_total_predicted_wins": int((post_global > 0).sum()),
            "local_wrong_direction_improved": int((delta_local[local_wrong] > 0).sum()),
            "local_wrong_predicted_crossed": int((post_local[local_wrong] > 0).sum()),
            "local_protected_direction_regressed": int((delta_local[local_protected] < 0).sum()),
            "local_protected_predicted_flipped": int((post_local[local_protected] <= 0).sum()),
            "local_total_predicted_wins": int((post_local > 0).sum()),
            "median_linearised_L_D_change": float(np.median(delta_ld)),
            "L_D_increase_count": int((delta_ld > 0).sum()),
            "median_linearised_L_P_change": float(np.median(delta_lp)),
            "L_P_increase_count": int((delta_lp > 0).sum()),
        })
    interval_path = args.output_dir / "displacement_mixture_intervals.csv"
    write_csv(interval_path, interval_rows)

    dense_lambda = np.linspace(0.0, 1.0, 10001)
    dense_global_wins = []
    dense_local_wins = []
    dense_global_repairs = []
    dense_global_flips = []
    dense_local_repairs = []
    dense_local_flips = []
    dense_ld_median = []
    dense_lp_median = []
    for lam in dense_lambda:
        post_global = global_initial + interpolate(global_g, global_l, float(lam))
        post_local = local_initial + interpolate(local_g, local_l, float(lam))
        dense_global_wins.append(int((post_global > 0).sum()))
        dense_local_wins.append(int((post_local > 0).sum()))
        dense_global_repairs.append(int((post_global[global_wrong] > 0).sum()))
        dense_global_flips.append(int((post_global[global_protected] <= 0).sum()))
        dense_local_repairs.append(int((post_local[local_wrong] > 0).sum()))
        dense_local_flips.append(int((post_local[local_protected] <= 0).sum()))
        dense_ld_median.append(float(np.median(interpolate(ld_g, ld_l, float(lam)))))
        dense_lp_median.append(float(np.median(interpolate(lp_g, lp_l, float(lam)))))

    strict_joint = [
        row for row in interval_rows
        if row["global_total_predicted_wins"] > int(global_protected.sum())
        and row["local_total_predicted_wins"] > int(local_protected.sum())
    ]
    local_gain_with_any_global_repair = [
        row for row in interval_rows
        if row["global_wrong_predicted_crossed"] > 0
        and row["local_total_predicted_wins"] > int(dense_local_wins[0])
    ]
    baseline_preserving_local = [
        row for row in interval_rows
        if row["global_total_predicted_wins"] >= int(global_protected.sum())
        and row["local_total_predicted_wins"] >= int(local_protected.sum())
    ]
    baseline_lambda_min = (
        None if not baseline_preserving_local
        else min(float(row["lambda_left_open"]) for row in baseline_preserving_local)
    )
    baseline_lambda_max = (
        None if not baseline_preserving_local
        else max(float(row["lambda_right_open"]) for row in baseline_preserving_local)
    )
    global_repair_intervals = [
        row for row in interval_rows if row["global_wrong_predicted_crossed"] > 0
    ]
    local_gain_intervals = [
        row for row in interval_rows
        if row["local_total_predicted_wins"] > int(dense_local_wins[0])
    ]
    summary = {
        "schema_version": "s09-e013-displacement-mixture-v1",
        "source_receipt_sha256": sha256(args.receipt),
        "common_initial_model_state_sha256": identity["model_state_sha256"],
        "common_initial_optimizer_state_sha256": identity["optimizer_state_sha256"],
        "model_forward_performed": False,
        "autograd_performed": False,
        "optimizer_step_performed": False,
        "mixture_definition": "delta(lambda)=(1-lambda)*delta_G25+lambda*delta_L25",
        "proxy_boundary": (
            "Recorded first-order inner products for a linear mixture of two known "
            "next-AdamW parameter displacements. This is not a newly merged loss "
            "passed through AdamW and is not a post-step field evaluation."
        ),
        "margin_breakpoint_count_including_endpoints": len(margin_breakpoints),
        "all_breakpoint_event_count": len(breakpoint_rows),
        "initial_B25_counts": {
            "global_wins": int(global_protected.sum()),
            "local_wins": int(local_protected.sum()),
        },
        "lambda_0_G25_counts": {
            "global_wins": dense_global_wins[0],
            "local_wins": dense_local_wins[0],
        },
        "lambda_1_L25_counts": {
            "global_wins": dense_global_wins[-1],
            "local_wins": dense_local_wins[-1],
        },
        "strict_joint_count_improvement_over_initial_exists": bool(strict_joint),
        "local_count_gain_over_G25_while_any_global_loss_is_repaired_exists": bool(
            local_gain_with_any_global_repair
        ),
        "baseline_count_preserving_interval_exists": bool(baseline_preserving_local),
        "baseline_count_preserving_open_lambda_min": baseline_lambda_min,
        "baseline_count_preserving_open_lambda_max": baseline_lambda_max,
        "last_open_interval_boundary_with_any_global_loss_repair": (
            None if not global_repair_intervals
            else max(float(row["lambda_right_open"]) for row in global_repair_intervals)
        ),
        "first_open_interval_boundary_with_local_count_gain_over_G25": (
            None if not local_gain_intervals
            else min(float(row["lambda_left_open"]) for row in local_gain_intervals)
        ),
        "maximum_global_plus_local_win_count": int(max(
            gw + lw for gw, lw in zip(dense_global_wins, dense_local_wins)
        )),
        "interpretation": (
            "Along this recorded displacement segment there is no count-level "
            "Pareto improvement over the initial B25 global/local win counts, and "
            "no local-count gain over G25 while retaining any of G25's predicted "
            "global-loss repairs. A narrow interval only recovers both initial "
            "count totals. This conclusion is limited to this first-order segment."
        ),
    }
    summary_path = args.output_dir / "displacement_mixture_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(15.4, 4.8), constrained_layout=True)
    ax = axes[0]
    ax.step(dense_lambda, dense_global_wins, where="post", label="total global wins", color="#2a6f97", linewidth=2.2)
    ax.step(dense_lambda, dense_global_repairs, where="post", label="old 8 losses crossed", color="#2a9d8f", linewidth=1.8)
    ax.step(dense_lambda, dense_global_flips, where="post", label="old 17 wins flipped", color="#d1495b", linewidth=1.8)
    ax.axhline(17, color="#64748b", linestyle="--", linewidth=1)
    ax.set(title="A  Global-amplitude trade-off", xlabel=r"Mixture $\lambda$ (G25 $\rightarrow$ L25)", ylabel="Pair count")
    ax.set_ylim(-0.5, 25.8)
    ax.legend(frameon=False, fontsize=9)

    ax = axes[1]
    ax.step(dense_lambda, dense_local_wins, where="post", label="total local wins", color="#7b2cbf", linewidth=2.2)
    ax.step(dense_lambda, dense_local_repairs, where="post", label="old 17 losses crossed", color="#9d4edd", linewidth=1.8)
    ax.step(dense_lambda, dense_local_flips, where="post", label="old 8 wins flipped", color="#f4a261", linewidth=1.8)
    ax.axhline(8, color="#64748b", linestyle="--", linewidth=1)
    if baseline_lambda_min is not None and baseline_lambda_max is not None:
        ax.axvspan(
            baseline_lambda_min, baseline_lambda_max,
            color="#a7c957", alpha=0.18, label="initial totals recovered",
        )
    ax.set(title="B  Local-support trade-off", xlabel=r"Mixture $\lambda$ (G25 $\rightarrow$ L25)", ylabel="Pair count")
    ax.set_ylim(-0.5, 25.8)
    ax.legend(frameon=False, fontsize=9)

    ax = axes[2]
    ax.plot(dense_lambda, dense_ld_median, label=r"median $\Delta L_D$", color="#264653", linewidth=2)
    ax.plot(dense_lambda, dense_lp_median, label=r"median $\Delta L_P$", color="#e76f51", linewidth=2)
    ax.axhline(0, color="#64748b", linewidth=1)
    ax.set(title="C  Recorded linearised side effects", xlabel=r"Mixture $\lambda$ (G25 $\rightarrow$ L25)", ylabel="Median predicted change")
    ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
    ax.legend(frameon=False, fontsize=9)

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(color="#e5e7eb", linewidth=0.65, alpha=0.8)
        ax.set_axisbelow(True)
    fig.suptitle(
        "S09-E013 recorded displacement segment: no joint count-level improvement",
        fontsize=15, fontweight="bold",
    )
    figure_path = args.output_dir / "displacement_mixture_tradeoff.png"
    fig.savefig(figure_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(json.dumps({
        "summary": str(summary_path),
        "breakpoints": str(breakpoint_path),
        "intervals": str(interval_path),
        "figure": str(figure_path),
        "result": summary,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
