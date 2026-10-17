#!/usr/bin/env python3
"""S04-E014: offline raw-driver progress/support mechanism diagnostic."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import analyze_three_umax_residual_sufficiency as base


ARMS = (
    "M0_pooled_global_pod",
    "M1_progress_global_pod",
    "M2_support_pod",
    "M3_progress_support_pod",
)
PRIMARY_ARM = "M3_progress_support_pod"
AFFINE_ARM = "M4_affine_umax_progress_mean"
RANKS = base.POD_RANKS
PRIMARY_THRESHOLD = base.PRIMARY_RATIO_THRESHOLD
PRIMARY_SEED = 20261080


class MechanismValidityError(RuntimeError):
    pass


def interpolate_field(tau: np.ndarray, fields: np.ndarray, target: float) -> np.ndarray:
    if target <= tau[0]:
        return np.asarray(fields[0], dtype=np.float64)
    if target >= tau[-1]:
        return np.asarray(fields[-1], dtype=np.float64)
    upper = int(np.searchsorted(tau, target, side="right"))
    lower = upper - 1
    fraction = float((target - tau[lower]) / (tau[upper] - tau[lower]))
    return (1.0 - fraction) * fields[lower] + fraction * fields[upper]


def progress_mean(cases, train_ids: list[str], target_tau: float) -> np.ndarray:
    fields = [
        interpolate_field(cases[tid]["tau"], cases[tid]["residuals"]["raw_log10"], target_tau)
        for tid in train_ids
    ]
    return np.mean(fields, axis=0, dtype=np.float64)


def affine_umax_progress_mean(cases, train_ids: list[str], target_tau: float, target_umax: float) -> np.ndarray:
    ordered = sorted(train_ids, key=lambda tid: float(cases[tid]["spec"]["umax"]))
    left, right = ordered
    left_u, right_u = float(cases[left]["spec"]["umax"]), float(cases[right]["spec"]["umax"])
    weight = (target_umax - left_u) / (right_u - left_u)
    left_field = interpolate_field(
        cases[left]["tau"], cases[left]["residuals"]["raw_log10"], target_tau
    )
    right_field = interpolate_field(
        cases[right]["tau"], cases[right]["residuals"]["raw_log10"], target_tau
    )
    return left_field + weight * (right_field - left_field)


def active_mask(case, index: int, areas: np.ndarray) -> np.ndarray:
    active = case["fem_fields"]["active"][index]
    threshold = base.weighted_quantile(active, areas, 0.99)
    return active >= threshold


def build_training_matrices(cases, train_ids: list[str], areas: np.ndarray):
    raw_rows, progress_rows, support_rows, progress_support_rows = [], [], [], []
    for tid in train_ids:
        case = cases[tid]
        for index, tau in enumerate(case["tau"]):
            residual = np.asarray(case["residuals"]["raw_log10"][index], dtype=np.float64)
            pmean = progress_mean(cases, train_ids, float(tau))
            deviation = residual - pmean
            mask = active_mask(case, index, areas)
            raw_rows.append(residual)
            progress_rows.append(deviation)
            support_rows.append(np.where(mask, residual, 0.0))
            progress_support_rows.append(np.where(mask, deviation, 0.0))
    return {
        "M0_pooled_global_pod": np.asarray(raw_rows, dtype=np.float32),
        "M1_progress_global_pod": np.asarray(progress_rows, dtype=np.float32),
        "M2_support_pod": np.asarray(support_rows, dtype=np.float32),
        "M3_progress_support_pod": np.asarray(progress_support_rows, dtype=np.float32),
    }


def phase_bin(cycle: int, event: int, tau: float) -> str:
    if cycle == event:
        return "event"
    if cycle <= 20:
        return "c1_c20"
    if cycle <= 40:
        return "c21_c40"
    if tau < 0.8:
        return "middle_after_c40"
    return "late_pre_event"


def evaluate(cases, areas: np.ndarray):
    per_cycle, spectra = [], []
    tids = list(cases)
    for fold_index, heldout in enumerate(tids):
        train_ids = [tid for tid in tids if tid != heldout]
        matrices = build_training_matrices(cases, train_ids, areas)
        models = {}
        for arm, matrix in matrices.items():
            mean, sqrtw, basis, singular, total_energy = base.pod_basis(matrix, areas, max(RANKS))
            if len(basis) < max(RANKS):
                raise MechanismValidityError(
                    f"{heldout}/{arm}: numerical POD rank {len(basis)} below {max(RANKS)}"
                )
            models[arm] = (mean, sqrtw, basis)
            for rank, captured in enumerate(np.cumsum(singular * singular) / total_energy, start=1):
                spectra.append(
                    {"heldout": heldout, "train_ids": "+".join(train_ids), "arm": arm,
                     "rank": rank, "training_energy_fraction": float(captured)}
                )

        case = cases[heldout]
        event = int(case["spec"]["event_cycle"])
        target_umax = float(case["spec"]["umax"])
        for index, (cycle, tau) in enumerate(zip(case["cycles"], case["tau"])):
            residual = np.asarray(case["residuals"]["raw_log10"][index], dtype=np.float64)
            mask = active_mask(case, index, areas)
            baseline = base.weighted_rmse(residual, areas, mask)
            pmean = progress_mean(cases, train_ids, float(tau))
            for arm in ARMS:
                mean, sqrtw, basis = models[arm]
                target = residual if arm in {"M0_pooled_global_pod", "M2_support_pod"} else residual - pmean
                offset = 0.0 if arm in {"M0_pooled_global_pod", "M2_support_pod"} else pmean
                for rank in RANKS:
                    if len(basis) < rank:
                        error, ratio, effective_rank = float("nan"), float("nan"), 0
                    else:
                        reconstructed, effective_rank = base.oracle_projection(
                            target, mean, sqrtw, basis[:rank], areas, mask
                        )
                        correction = offset + reconstructed
                        error = base.weighted_rmse(residual - correction, areas, mask)
                        ratio = error / baseline if baseline > np.finfo(float).tiny else float("nan")
                    per_cycle.append(
                        {"heldout": heldout, "train_ids": "+".join(train_ids), "arm": arm,
                         "rank": rank, "cycle": int(cycle), "tau": float(tau),
                         "phase": phase_bin(int(cycle), event, float(tau)),
                         "baseline_rmse": baseline, "corrected_rmse": error,
                         "error_ratio": ratio, "effective_projection_rank": effective_rank}
                    )
            affine = affine_umax_progress_mean(cases, train_ids, float(tau), target_umax)
            affine_error = base.weighted_rmse(residual - affine, areas, mask)
            per_cycle.append(
                {"heldout": heldout, "train_ids": "+".join(train_ids), "arm": AFFINE_ARM,
                 "rank": 0, "cycle": int(cycle), "tau": float(tau),
                 "phase": phase_bin(int(cycle), event, float(tau)),
                 "baseline_rmse": baseline, "corrected_rmse": affine_error,
                 "error_ratio": affine_error / baseline if baseline > np.finfo(float).tiny else float("nan"),
                 "effective_projection_rank": 0}
            )
    finite_required = [
        row[value]
        for row in per_cycle
        for value in ("baseline_rmse", "corrected_rmse")
    ]
    if np.any(~np.isfinite(np.asarray(finite_required, dtype=np.float64))):
        raise MechanismValidityError("non-finite baseline or corrected RMSE")
    return per_cycle, spectra


def summarize(per_cycle):
    summary, phases = [], []
    keys = sorted({(row["heldout"], row["arm"], row["rank"]) for row in per_cycle})
    fold_order = {tid: index for index, tid in enumerate(sorted({row["heldout"] for row in per_cycle}))}
    seed_offsets = {arm: index * 100 for index, arm in enumerate((*ARMS, AFFINE_ARM))}
    for heldout, arm, rank in keys:
        selected = [
            row for row in per_cycle
            if row["heldout"] == heldout and row["arm"] == arm and row["rank"] == rank
        ]
        ratios = np.asarray([row["error_ratio"] for row in selected], dtype=np.float64)
        if arm == "M0_pooled_global_pod" and rank == 20:
            seed = base.BOOTSTRAP_SEED + fold_order[heldout] * 10 + 2
        elif arm == PRIMARY_ARM and rank == 20:
            seed = PRIMARY_SEED + fold_order[heldout]
        else:
            seed = PRIMARY_SEED + 1000 + seed_offsets[arm] + fold_order[heldout] * 10 + rank
        median, upper = base.moving_block_upper(ratios, seed)
        summary.append(
            {"heldout": heldout, "arm": arm, "rank": rank, "valid_cycles": int(np.isfinite(ratios).sum()),
             "median_error_ratio": median, "bootstrap_upper97p5": upper,
             "identified": bool(np.isfinite(upper)),
             "pass_upper97p5_lt_0p90": bool(np.isfinite(upper) and upper < PRIMARY_THRESHOLD)}
        )
        for phase in ("c1_c20", "c21_c40", "middle_after_c40", "late_pre_event", "event"):
            values = [row["error_ratio"] for row in selected if row["phase"] == phase]
            if values:
                phases.append(
                    {"heldout": heldout, "arm": arm, "rank": rank, "phase": phase,
                     "cycle_count": len(values), "median_error_ratio": float(np.median(values)),
                     "p90_error_ratio": float(np.quantile(values, 0.9))}
                )
    return summary, phases


def load_e013_raw_summary(path: Path) -> dict[str, dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["heldout"]: {
            "median_error_ratio": float(row["median_error_ratio"]),
            "bootstrap_upper97p5": float(row["bootstrap_upper97p5"]),
        }
        for row in rows if row["channel"] == "raw_log10" and int(row["rank"]) == 20
    }


def reproduce_e013(summary, reference: dict[str, dict[str, float]]):
    rows = []
    for row in summary:
        if row["arm"] != "M0_pooled_global_pod" or row["rank"] != 20:
            continue
        expected = reference[row["heldout"]]
        median_delta = abs(row["median_error_ratio"] - expected["median_error_ratio"])
        upper_delta = abs(row["bootstrap_upper97p5"] - expected["bootstrap_upper97p5"])
        rows.append(
            {"heldout": row["heldout"], "median_abs_delta": median_delta,
             "upper_abs_delta": upper_delta, "pass_abs_1e_10": median_delta <= 1e-10 and upper_delta <= 1e-10}
        )
    return rows


def decide(summary):
    primary = [row for row in summary if row["arm"] == PRIMARY_ARM and row["rank"] == 20]
    identified_fail = any(row["identified"] and not row["pass_upper97p5_lt_0p90"] for row in primary)
    all_pass = len(primary) == 3 and all(row["identified"] and row["pass_upper97p5_lt_0p90"] for row in primary)
    verdict = "negative" if identified_fail else ("supports" if all_pass else "inconclusive")
    return primary, verdict


def make_figure(path: Path, summary, phases) -> None:
    colors = {
        "M0_pooled_global_pod": "#777777", "M1_progress_global_pod": "#0072B2",
        "M2_support_pod": "#E69F00", "M3_progress_support_pod": "#009E73",
        "M4_affine_umax_progress_mean": "#CC79A7",
    }
    tids = sorted({row["heldout"] for row in summary})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), constrained_layout=True)
    for ax, tid in zip(axes, tids):
        for arm in ARMS:
            rows = [row for row in summary if row["heldout"] == tid and row["arm"] == arm]
            ax.plot([row["rank"] for row in rows], [row["median_error_ratio"] for row in rows],
                    marker="o", color=colors[arm], label=arm)
        affine = [row for row in summary if row["heldout"] == tid and row["arm"] == AFFINE_ARM][0]
        ax.axhline(affine["median_error_ratio"], color=colors[AFFINE_ARM], linestyle="-.", label=AFFINE_ARM)
        ax.axhline(1.0, color="black", linestyle=":", linewidth=1)
        ax.axhline(PRIMARY_THRESHOLD, color="black", linestyle="--", linewidth=1)
        ax.set(title=f"held out {tid}", xlabel="POD rank", ylabel="median oracle error ratio", xscale="log")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir()
    (out / "figures").mkdir()

    lock = json.loads(args.input_lock.read_text())
    locked = [lock["base_input_lock"], lock["e013_decision"], lock["e013_primary_summary"]]
    hash_rows = []
    for record in locked:
        actual = base.sha256(Path(record["path"]))
        if actual != record["sha256"]:
            raise ValueError(f"hash mismatch: {record['path']}")
        hash_rows.append({"path": record["path"], "sha256": actual})
    base_lock = json.loads(Path(lock["base_input_lock"]["path"]).read_text())
    cases, _, areas, validation = base.load_and_validate(base_lock)
    validation.update({"status": "PASS", "e014_hashes": hash_rows})
    (out / "input_validation.json").write_text(json.dumps(validation, indent=2) + "\n")

    try:
        per_cycle, spectra = evaluate(cases, areas)
    except (MechanismValidityError, ValueError, np.linalg.LinAlgError) as error:
        decision = {"experiment_id": "S04-E014", "run_id": args.run_id,
                    "execution_status": "succeeded", "retrieval_status": "verified",
                    "scientific_verdict": "inadmissible", "reason": str(error)}
        (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
        print(json.dumps(decision, indent=2))
        return
    summary, phases = summarize(per_cycle)
    reproduction = reproduce_e013(summary, load_e013_raw_summary(Path(lock["e013_primary_summary"]["path"])))
    base.write_csv(out / "tables" / "per_cycle_arm_metrics.csv", per_cycle)
    base.write_csv(out / "tables" / "arm_summary.csv", summary)
    base.write_csv(out / "tables" / "phase_summary.csv", phases)
    base.write_csv(out / "tables" / "training_spectrum.csv", spectra)
    base.write_csv(out / "tables" / "e013_reproduction.csv", reproduction)
    if len(reproduction) != 3 or not all(row["pass_abs_1e_10"] for row in reproduction):
        decision = {"experiment_id": "S04-E014", "run_id": args.run_id,
                    "execution_status": "succeeded", "retrieval_status": "verified",
                    "scientific_verdict": "inadmissible", "reason": "E013 M0 reproduction failed"}
        (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
        print(json.dumps(decision, indent=2))
        return

    primary, verdict = decide(summary)
    make_figure(out / "figures" / "raw_driver_mechanism_comparison.png", summary, phases)
    decision = {
        "experiment_id": "S04-E014", "run_id": args.run_id,
        "execution_status": "succeeded", "retrieval_status": "verified",
        "scientific_verdict": verdict, "primary_arm": PRIMARY_ARM,
        "primary_gate": "PASS" if verdict == "supports" else ("FAIL" if verdict == "negative" else "UNIDENTIFIED"),
        "primary_pass_count": sum(bool(row["pass_upper97p5_lt_0p90"]) for row in primary),
        "primary_clause_count": len(primary),
        "allowed_conclusion": (
            "advance the specified progress-support representation to a separate retrospective event-time-conditioned offline coefficient experiment"
            if verdict == "supports" else (
                "do not train the specified M3 representation; use component arms only as exploratory diagnostics"
                if verdict == "negative" else "no route decision is authorised"
            )
        ),
        "blocked_conclusions": ["online availability of event-normalized progress", "independent confirmation", "predictive generalization", "neural correction success",
                                "online PINN improvement", "FEM physical truth", "real-road validity"],
        "runtime": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
    }
    (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    (out / "decision.md").write_text(
        f"# {args.run_id} decision\n\nVerdict: **{verdict}**.\n\n"
        f"Primary M3 folds passing: {decision['primary_pass_count']}/{decision['primary_clause_count']}.\n\n"
        f"Allowed: {decision['allowed_conclusion']}.\n\n"
        "Blocked: independent confirmation, prediction, neural/online success, FEM truth, and real-road validity.\n"
    )
    (out / "README_analysis.md").write_text(
        "# S04-E014 analysis\n\nExploratory raw-driver mechanism selection after E013. "
        "M3 alone is primary; M1, M2, and M4 explain components and cannot rescue it. "
        "Progress uses each held-out FEM own-first-event and is a retrospective event-time oracle. "
        "POD coefficients remain held-out oracle fits, not predictions.\n\n"
        f"Verdict: **{verdict}**. See `decision.md` and `tables/arm_summary.csv`.\n"
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
