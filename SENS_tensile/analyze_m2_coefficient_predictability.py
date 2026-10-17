#!/usr/bin/env python3
"""S04-E015: complete-Umax M2 coefficient ridge-feasibility audit."""

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

import analyze_raw_driver_mechanisms as mechanism
import analyze_three_umax_residual_sufficiency as base


ALPHAS = (1.0e-6, 1.0e-4, 1.0e-2, 1.0, 1.0e2, 1.0e4)
RANK = 20
FEATURE_DIMENSION = 99
PRIMARY_SEED = 20261150


def weighted_stats(field: np.ndarray, areas: np.ndarray) -> list[float]:
    total = float(areas.sum())
    mean = float(np.sum(areas * field) / total)
    std = float(np.sqrt(np.sum(areas * (field - mean) ** 2) / total))
    return [mean, std, base.weighted_quantile(field, areas, 0.90),
            base.weighted_quantile(field, areas, 0.99)]


def pidl_fields(case, index: int) -> dict[str, np.ndarray]:
    return {
        "damage": np.asarray(case["pidl_fields"]["damage"][index], dtype=np.float64),
        "history": np.asarray(case["pidl_fields"]["history"][index], dtype=np.float64),
        "raw_log10": np.asarray(case["pidl_fields"]["raw_log10"][index], dtype=np.float64),
        "active_log10": np.log10(
            np.maximum(np.asarray(case["pidl_fields"]["active"][index], dtype=np.float64), base.LOG_FLOOR)
        ),
    }


def outer_field_means(cases, train_ids: list[str]) -> dict[str, np.ndarray]:
    accumulators: dict[str, np.ndarray] = {}
    count = 0
    for tid in train_ids:
        for index in range(len(cases[tid]["cycles"])):
            fields = pidl_fields(cases[tid], index)
            for name, field in fields.items():
                accumulators[name] = accumulators.get(name, np.zeros_like(field)) + field
            count += 1
    return {name: values / count for name, values in accumulators.items()}


def feature_vector(case, index: int, areas: np.ndarray, sqrtw: np.ndarray,
                   basis: np.ndarray, field_means: dict[str, np.ndarray]) -> np.ndarray:
    cycle = int(case["cycles"][index])
    values = [float(case["spec"]["umax"]), cycle / 100.0, float(np.log1p(cycle))]
    fields = pidl_fields(case, index)
    for name in ("damage", "history", "raw_log10", "active_log10"):
        values.extend(weighted_stats(fields[name], areas))
    for name in ("damage", "history", "raw_log10", "active_log10"):
        projection = np.einsum(
            "i,ki->k", (fields[name] - field_means[name]) * sqrtw, basis, optimize=False
        )
        values.extend(projection.tolist())
    vector = np.asarray(values, dtype=np.float64)
    if vector.shape != (FEATURE_DIMENSION,) or np.any(~np.isfinite(vector)):
        raise ValueError(f"invalid feature vector: {vector.shape}")
    return vector


def masked_coefficients(target: np.ndarray, mean: np.ndarray, sqrtw: np.ndarray,
                        basis: np.ndarray, areas: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, int]:
    physical_basis = basis[:, mask] / sqrtw[mask]
    design = physical_basis.T * np.sqrt(areas[mask])[:, None]
    response = (target[mask] - mean[mask]) * np.sqrt(areas[mask])
    coefficients, _, rank, _ = np.linalg.lstsq(design, response, rcond=None)
    return coefficients, int(rank)


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float):
    x_mean, x_std = x.mean(axis=0), x.std(axis=0)
    y_mean, y_std = y.mean(axis=0), y.std(axis=0)
    x_std = np.where(x_std > 1.0e-12, x_std, 1.0)
    y_std = np.where(y_std > 1.0e-12, y_std, 1.0)
    xs, ys = (x - x_mean) / x_std, (y - y_mean) / y_std
    gram = np.einsum("ni,nj->ij", xs, xs, optimize=False) + alpha * np.eye(xs.shape[1])
    cross = np.einsum("ni,nk->ik", xs, ys, optimize=False)
    weights = np.linalg.solve(gram, cross)
    return {"x_mean": x_mean, "x_std": x_std, "y_mean": y_mean,
            "y_std": y_std, "weights": weights}


def ridge_predict(model, x: np.ndarray) -> np.ndarray:
    standardized = (x - model["x_mean"]) / model["x_std"]
    return np.einsum("ni,ik->nk", standardized, model["weights"], optimize=False) * model["y_std"] + model["y_mean"]


def select_alpha(x_by_tid, y_by_tid, train_ids: list[str]):
    rows = []
    for alpha in ALPHAS:
        scores = []
        for fit_id, validate_id in ((train_ids[0], train_ids[1]), (train_ids[1], train_ids[0])):
            model = ridge_fit(x_by_tid[fit_id], y_by_tid[fit_id], alpha)
            prediction = ridge_predict(model, x_by_tid[validate_id])
            scale = np.where(model["y_std"] > 1.0e-12, model["y_std"], 1.0)
            score = float(np.mean(((prediction - y_by_tid[validate_id]) / scale) ** 2))
            scores.append(score)
            rows.append({"alpha": alpha, "fit_umax": fit_id, "validate_umax": validate_id,
                         "standardized_coefficient_mse": score})
        rows.append({"alpha": alpha, "fit_umax": "mean", "validate_umax": "mean",
                     "standardized_coefficient_mse": float(np.mean(scores))})
    means = [row for row in rows if row["fit_umax"] == "mean"]
    selected = min(means, key=lambda row: (row["standardized_coefficient_mse"], row["alpha"]))["alpha"]
    for row in rows:
        row["selected"] = row["alpha"] == selected
    return float(selected), rows


def phase_bin(cycle: int, event: int, tau: float) -> str:
    return mechanism.phase_bin(cycle, event, tau)


def run_folds(cases, areas: np.ndarray):
    per_cycle, alpha_rows, coefficient_rows, oracle_summary = [], [], [], []
    tids = list(cases)
    for fold_index, heldout in enumerate(tids):
        train_ids = [tid for tid in tids if tid != heldout]
        m2_matrix = mechanism.build_training_matrices(cases, train_ids, areas)["M2_support_pod"]
        mean, sqrtw, basis, _, _ = base.pod_basis(m2_matrix, areas, RANK)
        if len(basis) != RANK:
            raise ValueError(f"{heldout}: M2 basis rank {len(basis)}")
        field_means = outer_field_means(cases, train_ids)
        x_by_tid, y_by_tid = {}, {}
        for tid in train_ids:
            x_rows, y_rows = [], []
            case = cases[tid]
            for index in range(len(case["cycles"])):
                x_rows.append(feature_vector(case, index, areas, sqrtw, basis, field_means))
                residual = np.asarray(case["residuals"]["raw_log10"][index], dtype=np.float64)
                mask = mechanism.active_mask(case, index, areas)
                coefficients, effective_rank = masked_coefficients(
                    residual, mean, sqrtw, basis, areas, mask
                )
                y_rows.append(coefficients)
            x_by_tid[tid], y_by_tid[tid] = np.asarray(x_rows), np.asarray(y_rows)
        selected_alpha, fold_alpha_rows = select_alpha(x_by_tid, y_by_tid, train_ids)
        for row in fold_alpha_rows:
            alpha_rows.append({"heldout": heldout, **row})
        train_x = np.concatenate([x_by_tid[tid] for tid in train_ids])
        train_y = np.concatenate([y_by_tid[tid] for tid in train_ids])
        model = ridge_fit(train_x, train_y, selected_alpha)

        case = cases[heldout]
        test_x = np.asarray([
            feature_vector(case, index, areas, sqrtw, basis, field_means)
            for index in range(len(case["cycles"]))
        ])
        predicted_coefficients = ridge_predict(model, test_x)
        if predicted_coefficients.shape != (len(case["cycles"]), RANK) or np.any(~np.isfinite(predicted_coefficients)):
            raise ValueError(f"{heldout}: invalid predicted coefficient matrix")

        predicted_ratios, oracle_ratios = [], []
        event = int(case["spec"]["event_cycle"])
        for index, (cycle, tau) in enumerate(zip(case["cycles"], case["tau"])):
            residual = np.asarray(case["residuals"]["raw_log10"][index], dtype=np.float64)
            mask = mechanism.active_mask(case, index, areas)
            baseline = base.weighted_rmse(residual, areas, mask)
            predicted_correction = mean + np.einsum(
                "k,ki->i", predicted_coefficients[index], basis, optimize=False
            ) / sqrtw
            predicted_error = base.weighted_rmse(residual - predicted_correction, areas, mask)
            predicted_ratio = predicted_error / baseline if baseline > np.finfo(float).tiny else float("nan")

            oracle_coefficients, oracle_rank = masked_coefficients(
                residual, mean, sqrtw, basis, areas, mask
            )
            oracle_correction = mean + np.einsum(
                "k,ki->i", oracle_coefficients, basis, optimize=False
            ) / sqrtw
            oracle_error = base.weighted_rmse(residual - oracle_correction, areas, mask)
            oracle_ratio = oracle_error / baseline if baseline > np.finfo(float).tiny else float("nan")
            mean_coefficient_correction = mean + np.einsum(
                "k,ki->i", model["y_mean"], basis, optimize=False
            ) / sqrtw
            mean_error = base.weighted_rmse(residual - mean_coefficient_correction, areas, mask)
            mean_ratio = mean_error / baseline if baseline > np.finfo(float).tiny else float("nan")
            predicted_ratios.append(predicted_ratio)
            oracle_ratios.append(oracle_ratio)
            per_cycle.append(
                {"heldout": heldout, "train_ids": "+".join(train_ids), "cycle": int(cycle),
                 "tau": float(tau), "phase": phase_bin(int(cycle), event, float(tau)),
                 "selected_alpha": selected_alpha, "baseline_rmse": baseline,
                 "predicted_rmse": predicted_error, "predicted_error_ratio": predicted_ratio,
                 "oracle_rmse": oracle_error, "oracle_error_ratio": oracle_ratio,
                 "mean_coefficient_error_ratio": mean_ratio, "oracle_effective_rank": oracle_rank}
            )
            for mode in range(RANK):
                coefficient_rows.append(
                    {"heldout": heldout, "cycle": int(cycle), "mode": mode + 1,
                     "predicted_coefficient": float(predicted_coefficients[index, mode]),
                     "oracle_coefficient": float(oracle_coefficients[mode])}
                )
        oracle_median, oracle_upper = base.moving_block_upper(
            np.asarray(oracle_ratios), 20262300 + fold_index * 10
        )
        oracle_summary.append(
            {"heldout": heldout, "median_error_ratio": oracle_median,
             "bootstrap_upper97p5": oracle_upper}
        )
    return per_cycle, alpha_rows, coefficient_rows, oracle_summary


def summarize(per_cycle):
    primary, phases = [], []
    tids = sorted({row["heldout"] for row in per_cycle})
    for fold_index, tid in enumerate(tids):
        rows = [row for row in per_cycle if row["heldout"] == tid]
        ratios = np.asarray([row["predicted_error_ratio"] for row in rows])
        median, upper = base.moving_block_upper(ratios, PRIMARY_SEED + fold_index)
        primary.append(
            {"heldout": tid, "cycle_count": len(rows), "median_predicted_error_ratio": median,
             "bootstrap_upper97p5": upper, "identified": bool(np.isfinite(upper)),
             "pass_upper97p5_lt_0p90": bool(np.isfinite(upper) and upper < base.PRIMARY_RATIO_THRESHOLD)}
        )
        for phase in ("c1_c20", "c21_c40", "middle_after_c40", "late_pre_event", "event"):
            selected = [row["predicted_error_ratio"] for row in rows if row["phase"] == phase]
            if selected:
                phases.append(
                    {"heldout": tid, "phase": phase, "cycle_count": len(selected),
                     "median_predicted_error_ratio": float(np.median(selected)),
                     "p90_predicted_error_ratio": float(np.quantile(selected, 0.9))}
                )
    return primary, phases


def decide(primary):
    identified_fail = any(row["identified"] and not row["pass_upper97p5_lt_0p90"] for row in primary)
    all_pass = len(primary) == 3 and all(row["identified"] and row["pass_upper97p5_lt_0p90"] for row in primary)
    return "negative" if identified_fail else ("supports" if all_pass else "inconclusive")


def load_e014_m2(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["heldout"]: (float(row["median_error_ratio"]), float(row["bootstrap_upper97p5"]))
        for row in rows if row["arm"] == "M2_support_pod" and int(row["rank"]) == RANK
    }


def reproduction_rows(oracle_summary, reference):
    return [
        {"heldout": row["heldout"],
         "median_abs_delta": abs(row["median_error_ratio"] - reference[row["heldout"]][0]),
         "upper_abs_delta": abs(row["bootstrap_upper97p5"] - reference[row["heldout"]][1]),
         "pass_abs_1e_10": abs(row["median_error_ratio"] - reference[row["heldout"]][0]) <= 1e-10
         and abs(row["bootstrap_upper97p5"] - reference[row["heldout"]][1]) <= 1e-10}
        for row in oracle_summary
    ]


def coefficient_summary(rows):
    output = []
    for tid in sorted({row["heldout"] for row in rows}):
        selected = [row for row in rows if row["heldout"] == tid]
        predicted = np.asarray([row["predicted_coefficient"] for row in selected])
        oracle = np.asarray([row["oracle_coefficient"] for row in selected])
        correlation = float(np.corrcoef(predicted, oracle)[0, 1]) if np.std(predicted) and np.std(oracle) else float("nan")
        output.append({"heldout": tid, "coefficient_rmse": float(np.sqrt(np.mean((predicted - oracle) ** 2))),
                       "coefficient_correlation": correlation})
    return output


def make_figure(path: Path, per_cycle) -> None:
    colors = {"hard5_u011": "#0072B2", "hard5_u012": "#E69F00", "hard5_u013": "#009E73"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for ax, tid in zip(axes, sorted(colors)):
        rows = [row for row in per_cycle if row["heldout"] == tid]
        ax.plot([row["tau"] for row in rows], [row["predicted_error_ratio"] for row in rows],
                color=colors[tid], label="predicted coefficients")
        ax.plot([row["tau"] for row in rows], [row["oracle_error_ratio"] for row in rows],
                color="black", alpha=0.7, label="M2 oracle ceiling")
        ax.axhline(1.0, color="black", linestyle=":", linewidth=1)
        ax.axhline(base.PRIMARY_RATIO_THRESHOLD, color="black", linestyle="--", linewidth=1)
        ax.set(title=f"held out {tid}", xlabel="normalized progress tau",
               ylabel="p99-support error ratio", ylim=(0, None))
    axes[0].legend(frameon=False)
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
    hash_rows = []
    for record in (lock["base_input_lock"], lock["e014_decision"], lock["e014_arm_summary"]):
        actual = base.sha256(Path(record["path"]))
        if actual != record["sha256"]:
            raise ValueError(f"hash mismatch: {record['path']}")
        hash_rows.append({"path": record["path"], "sha256": actual})
    base_lock = json.loads(Path(lock["base_input_lock"]["path"]).read_text())
    cases, _, areas, validation = base.load_and_validate(base_lock)
    validation.update({"status": "PASS", "e015_hashes": hash_rows,
                       "declared_feature_dimension": FEATURE_DIMENSION})
    (out / "input_validation.json").write_text(json.dumps(validation, indent=2) + "\n")

    try:
        per_cycle, alpha_rows, coefficient_rows, oracle_summary = run_folds(cases, areas)
    except (ValueError, np.linalg.LinAlgError) as error:
        decision = {"experiment_id": "S04-E015", "run_id": args.run_id,
                    "execution_status": "succeeded", "retrieval_status": "verified",
                    "scientific_verdict": "inadmissible", "reason": str(error)}
        (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
        print(json.dumps(decision, indent=2))
        return
    reproduction = reproduction_rows(
        oracle_summary, load_e014_m2(Path(lock["e014_arm_summary"]["path"]))
    )
    base.write_csv(out / "tables" / "e014_m2_reproduction.csv", reproduction)
    if len(reproduction) != 3 or not all(row["pass_abs_1e_10"] for row in reproduction):
        decision = {"experiment_id": "S04-E015", "run_id": args.run_id,
                    "execution_status": "succeeded", "retrieval_status": "verified",
                    "scientific_verdict": "inadmissible", "reason": "E014 M2 reproduction failed"}
        (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
        print(json.dumps(decision, indent=2))
        return

    primary, phases = summarize(per_cycle)
    verdict = decide(primary)
    base.write_csv(out / "tables" / "alpha_selection.csv", alpha_rows)
    base.write_csv(out / "tables" / "per_cycle_prediction.csv", per_cycle)
    base.write_csv(out / "tables" / "primary_summary.csv", primary)
    base.write_csv(out / "tables" / "phase_summary.csv", phases)
    base.write_csv(out / "tables" / "coefficient_summary.csv", coefficient_summary(coefficient_rows))
    make_figure(out / "figures" / "predicted_vs_oracle_error_ratio.png", per_cycle)
    decision = {
        "experiment_id": "S04-E015", "run_id": args.run_id,
        "execution_status": "succeeded", "retrieval_status": "verified",
        "scientific_verdict": verdict, "primary_gate": "PASS" if verdict == "supports" else (
            "FAIL" if verdict == "negative" else "UNIDENTIFIED"),
        "primary_pass_count": sum(bool(row["pass_upper97p5_lt_0p90"]) for row in primary),
        "primary_clause_count": len(primary),
        "allowed_conclusion": (
            "authorise a separately gated Taobo neural coefficient-model comparison"
            if verdict == "supports" else (
                "do not escalate model architecture with only these three trajectories"
                if verdict == "negative" else "no route decision is authorised"
            )
        ),
        "blocked_conclusions": ["independent confirmation", "neural corrector success",
                                "online PINN improvement", "FEM physical truth", "real-road validity"],
        "runtime": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()},
    }
    (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    (out / "decision.md").write_text(
        f"# {args.run_id} decision\n\nVerdict: **{verdict}**.\n\n"
        f"Predicted-coefficient folds passing: {decision['primary_pass_count']}/{decision['primary_clause_count']}.\n\n"
        f"Allowed: {decision['allowed_conclusion']}.\n"
    )
    (out / "README_analysis.md").write_text(
        "# S04-E015 analysis\n\nM2 rank-20 coefficients are predicted from 99 same-cycle PINN-only features "
        "using outer-Umax-held-out ridge regression. Held-out FEM is used only for scoring; the oracle curve is diagnostic.\n\n"
        f"Verdict: **{verdict}**. See `decision.md` and `tables/primary_summary.csv`.\n"
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
