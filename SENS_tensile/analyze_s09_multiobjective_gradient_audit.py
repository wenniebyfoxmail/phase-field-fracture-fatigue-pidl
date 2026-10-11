#!/usr/bin/env python3
"""Build the decision-facing S09-E005 gradient audit evidence."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


GROUPS = ("global", "encoder", "local", "coarse", "decoder")


def dump(path: Path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.run / "output" / "receipt.json").read_text())
    audit = json.loads((args.run / "output" / "gradient_audit.json").read_text())
    states = audit["states"]
    if receipt["execution_status"] != "succeeded" or not all(
        receipt[key] for key in ("no_update_identity_pass", "finite_output_pass", "completeness_pass")
    ):
        raise RuntimeError("producer evidence is incomplete")
    if len(states) != 16 or [row["cycle"] for row in states] != [1,7,14,21,28,35,41,48,55,62,69,75,82,89,96,103]:
        raise RuntimeError("state identity mismatch")
    args.out.mkdir(parents=True, exist_ok=True)

    summary = {
        "experiment_id": "S09-E005",
        "run_id": receipt["run_id"],
        "execution": {
            "status": receipt["execution_status"], "optimizer_updates": receipt["optimizer_updates"],
            "states": receipt["audited_states"], "no_update_identity_pass": receipt["no_update_identity_pass"],
            "finite_output_pass": receipt["finite_output_pass"],
            "completeness_pass": receipt["completeness_pass"],
        },
        "groups": {},
    }
    for group in GROUPS:
        cosine = np.array([row["gradient"][group]["cosine"] for row in states])
        ratio = np.array([row["gradient"][group]["physics_to_data_norm"] for row in states])
        summary["groups"][group] = {
            "cosine_min": float(cosine.min()), "cosine_median": float(np.median(cosine)),
            "cosine_max": float(cosine.max()), "negative_cosine_states": int((cosine < 0).sum()),
            "norm_ratio_min": float(ratio.min()), "norm_ratio_median": float(np.median(ratio)),
            "norm_ratio_max": float(ratio.max()),
        }
    target = np.array([row["target_force_rms_ratio_to_affine"] for row in states])
    prediction = np.array([row["prediction_force_rms_ratio_to_affine"] for row in states])
    global_ratio = np.array([row["gradient"]["global"]["physics_to_data_norm"] for row in states])
    summary["e004_weighted_physics_to_data_norm"] = {
        "initial_weight": audit["weights"]["initial"],
        "initial_min_median_max": [float(x) for x in (
            (audit["weights"]["initial"] * global_ratio).min(),
            np.median(audit["weights"]["initial"] * global_ratio),
            (audit["weights"]["initial"] * global_ratio).max())],
        "first_assessment_weight": audit["weights"]["first_assessment"],
        "first_assessment_min_median_max": [float(x) for x in (
            (audit["weights"]["first_assessment"] * global_ratio).min(),
            np.median(audit["weights"]["first_assessment"] * global_ratio),
            (audit["weights"]["first_assessment"] * global_ratio).max())],
    }
    summary["observed_target_residual_ratio"] = {
        "min": float(target.min()), "median": float(np.median(target)), "max": float(target.max())}
    summary["checkpoint_prediction_residual_ratio"] = {
        "min": float(prediction.min()), "median": float(np.median(prediction)), "max": float(prediction.max())}
    summary["linearized_direction_signs"] = {}
    for name in states[0]["linearized"]:
        dd = np.array([row["linearized"][name]["delta_data_per_unit_lr"] for row in states])
        dp = np.array([row["linearized"][name]["delta_physics_per_unit_lr"] for row in states])
        summary["linearized_direction_signs"][name] = {
            "data_increase_states": int((dd > 0).sum()),
            "physics_increase_states": int((dp > 0).sum()),
        }
    summary["diagnosis"] = (
        "At the common checkpoint, global gradients are aligned but the physics gradient is four to five "
        "orders of magnitude larger. Decoder-level conflicts occur in a minority of states. The observed "
        "FEM-target residual is small relative to affine and does not support a large target/operator floor. "
        "E004's later accuracy degradation is therefore not explained by an instantaneous global negative "
        "cosine at step 300; scale dominance and subsequent optimizer/curvature dynamics remain the leading "
        "mechanism. Test a fresh gradient-balanced, data-anchored Pareto rescue."
    )
    dump(args.out / "summary.json", summary)

    with (args.out / "group_summary.csv").open("w", newline="") as stream:
        fields = ["group", "cosine_min", "cosine_median", "cosine_max", "negative_cosine_states",
                  "norm_ratio_min", "norm_ratio_median", "norm_ratio_max"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for group in GROUPS:
            writer.writerow({"group": group, **summary["groups"][group]})

    cycles = np.array([row["cycle"] for row in states])
    colors = {"global": "#172554", "encoder": "#2563eb", "local": "#0f766e",
              "coarse": "#ca8a04", "decoder": "#dc2626"}
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.8), constrained_layout=True)
    for group in GROUPS:
        axes[0].plot(cycles, [row["gradient"][group]["physics_to_data_norm"] for row in states],
                     marker="o", ms=3, lw=1.5, color=colors[group], label=group)
        axes[1].plot(cycles, [row["gradient"][group]["cosine"] for row in states],
                     marker="o", ms=3, lw=1.5, color=colors[group], label=group)
    axes[0].set_yscale("log")
    axes[0].set_title("A  Physics/data gradient scale")
    axes[0].set_ylabel(r"$\|g_{physics}\|/\|g_{data}\|$")
    axes[0].set_xlabel("Training-state cycle")
    axes[0].legend(frameon=False, fontsize=8, ncol=2)
    axes[1].axhline(0, color="black", lw=.8)
    axes[1].set_ylim(-1.05, 1.05)
    axes[1].set_title("B  Gradient directional agreement")
    axes[1].set_ylabel("Cosine similarity")
    axes[1].set_xlabel("Training-state cycle")
    axes[2].semilogy(cycles, prediction, marker="o", color="#7c3aed", label="checkpoint prediction")
    axes[2].semilogy(cycles, target, marker="o", color="#059669", label="FEM export target")
    axes[2].axhline(1, color="black", lw=.8, ls="--", label="affine reference")
    axes[2].set_title("C  Free-force residual / affine")
    axes[2].set_ylabel("RMS ratio")
    axes[2].set_xlabel("Training-state cycle")
    axes[2].legend(frameon=False, fontsize=8)
    fig.suptitle("S09-E005 zero-update audit: scale dominance with localized conflict", fontsize=12)
    fig.savefig(args.out / "gradient_audit_decision.png", dpi=220)
    fig.savefig(args.out / "gradient_audit_decision.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
