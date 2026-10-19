"""Independent arithmetic and integrity audit of the retrieved matrix outputs."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
RETRIEVED = HERE / "retrieved_2026-10-19"
RAW = RETRIEVED / "HQ-ROAD-UQ-MATRIX-001-R001"
RUNS = HERE.parent
NUMERIC = [
    "dice", "error", "U_LC", "U_H", "target_fg_fraction", "pred_fg_fraction", "U_Z",
    "tol2_precision", "tol2_recall", "tol2_f1", "tol4_precision", "tol4_recall", "tol4_f1",
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def boolean(value):
    return value.lower() == "true"


def read_rows(name):
    with open(RAW / name, newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in NUMERIC:
            row[key] = float(row[key])
        for key in ["pred_empty", "pred_full", "target_empty"]:
            row[key] = boolean(row[key])
    return rows


def risk(rows, key):
    ordered = sorted(rows, key=lambda row: (row[key], row["id"]))
    values = np.asarray([row["error"] for row in ordered], dtype=float)
    return np.cumsum(values) / np.arange(1, len(values) + 1)


def summarize(rows):
    primary = [row for row in rows if not row["target_empty"]]
    accepted = math.floor(0.25 * len(primary))
    full = float(np.mean([row["error"] for row in primary]))
    scores = {}
    for key in ["U_LC", "U_H", "U_Z"]:
        curve = risk(primary, key)
        scores[key] = {
            "risk_at_25": float(curve[accepted - 1]),
            "risk_reduction": float(full - curve[accepted - 1]),
            "aurc": float(np.mean(curve)),
        }
    return {
        "n_all": len(rows),
        "n_nonempty": len(primary),
        "n_empty": len(rows) - len(primary),
        "unique_ids": len({row["id"] for row in rows}),
        "finite_numeric_values": bool(all(np.isfinite(row[key]) for row in rows for key in NUMERIC)),
        "full_risk": full,
        "mean_dice": float(np.mean([row["dice"] for row in primary])),
        "median_dice": float(np.median([row["dice"] for row in primary])),
        "dice_positive": sum(row["dice"] > 0 for row in primary),
        "degenerate": sum(row["pred_empty"] or row["pred_full"] for row in primary),
        "mean_tol2_f1": float(np.mean([row["tol2_f1"] for row in primary])),
        "mean_tol4_f1": float(np.mean([row["tol4_f1"] for row in primary])),
        "pred_fg_fraction": {
            "mean": float(np.mean([row["pred_fg_fraction"] for row in primary])),
            "median": float(np.median([row["pred_fg_fraction"] for row in primary])),
            "p90": float(np.quantile([row["pred_fg_fraction"] for row in primary], 0.9)),
        },
        "accepted_n": accepted,
        "scores": scores,
        "empty_reference_rows": [
            {key: row[key] for key in ["id", "dice", "error", "pred_empty", "pred_full", "pred_fg_fraction"]}
            for row in rows if row["target_empty"]
        ],
    }


def paired(old_rows, new_rows):
    old = {row["id"]: row for row in old_rows if not row["target_empty"]}
    new = {row["id"]: row for row in new_rows if not row["target_empty"]}
    identities = sorted(old.keys() & new.keys())
    delta = np.asarray([new[key]["error"] - old[key]["error"] for key in identities])
    rng = np.random.default_rng(20261019)
    boot = np.asarray([delta[rng.integers(0, len(delta), len(delta))].mean() for _ in range(5000)])
    return {
        "n": len(identities),
        "new_minus_old_mean_error": float(delta.mean()),
        "new_minus_old_median_error": float(np.median(delta)),
        "bootstrap_95_interval": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
        "repair_better_cases": int((delta < 0).sum()),
        "repair_worse_cases": int((delta > 0).sum()),
        "ties": int((delta == 0).sum()),
        "mean_tol2_f1_delta": float(np.mean([new[key]["tol2_f1"] - old[key]["tol2_f1"] for key in identities])),
        "mean_tol4_f1_delta": float(np.mean([new[key]["tol4_f1"] - old[key]["tol4_f1"] for key in identities])),
    }


def verify_diagonal(recomputed_rows, frozen_path):
    with open(frozen_path, newline="") as stream:
        frozen = {row["id"]: row for row in csv.DictReader(stream)}
    differences = []
    for row in recomputed_rows:
        if row["id"] not in frozen:
            continue
        differences.append(max(abs(row[key] - float(frozen[row["id"]][key])) for key in ["dice", "U_LC", "U_H", "U_Z"]))
    return {
        "matched_ids": len(differences),
        "max_abs_metric_difference": max(differences),
        "comparable": len(differences) > 0 and max(differences) <= 1e-5,
    }


def max_summary_difference(observed, reproduced):
    differences = []
    for cell in ["old_CFD", "old_GAPS384", "repair_CFD", "repair_GAPS384"]:
        for key in ["full_risk", "mean_dice", "mean_tol2_f1", "mean_tol4_f1"]:
            differences.append(abs(observed[cell][key] - reproduced[cell][key]))
        for score in ["U_LC", "U_H", "U_Z"]:
            for key in ["risk_at_25", "risk_reduction", "aurc"]:
                differences.append(abs(observed[cell]["scores"][score][key] - reproduced[cell]["scores"][score][key]))
    return max(differences)


def main():
    files = {
        "old_CFD": "old_cfd_metrics.csv",
        "old_GAPS384": "old_gaps384_metrics.csv",
        "repair_CFD": "repair_cfd_metrics.csv",
        "repair_GAPS384": "repair_gaps384_metrics.csv",
    }
    rows = {key: read_rows(name) for key, name in files.items()}
    reproduced = {key: summarize(value) for key, value in rows.items()}
    paired_result = {
        "CFD": paired(rows["old_CFD"], rows["repair_CFD"]),
        "GAPS384": paired(rows["old_GAPS384"], rows["repair_GAPS384"]),
    }
    observed = json.loads((RAW / "matrix_summary.json").read_text())
    remote_manifest = json.loads((RETRIEVED / "remote_sha256_manifest.json").read_text(encoding="utf-8-sig"))
    remote_hashes = {
        item["name"]: {
            "bytes_match": (RAW / item["name"]).stat().st_size == item["bytes"],
            "sha256_match": sha256(RAW / item["name"]) == item["sha256"],
        }
        for item in remote_manifest
    }
    diagonal = {
        "old_CFD": verify_diagonal(
            rows["old_CFD"],
            RUNS / "HQ-ROAD-UQ-FEAS-001-R001/retrieved_2026-10-11/HQ-ROAD-UQ-FEAS-001-R001/cfd_metrics.csv",
        ),
        "repair_GAPS384": verify_diagonal(
            rows["repair_GAPS384"],
            RUNS / "HQ-ROAD-UQ-FEAS-002-R001/retrieved_2026-10-19/HQ-ROAD-UQ-FEAS-002-R001/gaps384_nonempty_metrics.csv",
        ),
    }
    result = {
        "status": "PASS_COMPLETE_RETRIEVED_AND_RECOMPUTED",
        "remote_formal_files": len(remote_manifest),
        "remote_hashes_all_match": all(v["bytes_match"] and v["sha256_match"] for v in remote_hashes.values()),
        "remote_hashes": remote_hashes,
        "cells": reproduced,
        "paired_delta": paired_result,
        "producer_summary_max_abs_recompute_difference": max_summary_difference(observed, reproduced),
        "producer_bootstrap_exact_match": {
            source: paired_result[source]["bootstrap_95_interval"] == observed["paired_delta"][source]["bootstrap_95_interval"]
            for source in ["CFD", "GAPS384"]
        },
        "diagonal_verification": diagonal,
        "receipt": json.loads((RAW / "receipt.json").read_text()),
        "task": json.loads((RETRIEVED / "task_status.json").read_text(encoding="utf-8-sig")),
        "scheduled_exitcode": (RETRIEVED / "scheduled.exitcode.txt").read_text().strip(),
        "scheduled_stderr_bytes": (RETRIEVED / "scheduled.stderr.log").stat().st_size,
        "training_steps": 0,
        "road420_access": False,
        "audit_scope": "integrity plus independent arithmetic from exported per-image rows; no second model inference",
    }
    assert result["remote_hashes_all_match"]
    assert result["producer_summary_max_abs_recompute_difference"] < 1e-12
    assert all(result["producer_bootstrap_exact_match"].values())
    assert diagonal == observed["diagonal_verification"]
    assert result["scheduled_exitcode"] == "0" and result["scheduled_stderr_bytes"] == 0
    assert all(cell["unique_ids"] == cell["n_all"] and cell["finite_numeric_values"] for cell in reproduced.values())
    assert reproduced["old_CFD"]["n_all"] == reproduced["repair_CFD"]["n_all"] == 118
    assert reproduced["old_GAPS384"]["n_nonempty"] == reproduced["repair_GAPS384"]["n_nonempty"] == 382
    assert reproduced["old_GAPS384"]["n_empty"] == reproduced["repair_GAPS384"]["n_empty"] == 2
    (RETRIEVED / "independent_recomputation.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
