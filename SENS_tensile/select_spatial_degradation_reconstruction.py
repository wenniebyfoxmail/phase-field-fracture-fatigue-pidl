#!/usr/bin/env python3
"""Lock architecture and representative seed from pre-c86 audit metrics only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = []
    for run_dir in sorted(path for path in args.runs.iterdir() if path.is_dir()):
        manifest_path = run_dir / "RUN_MANIFEST.json"
        lock_path = run_dir / "SEALED_C86_RECONSTRUCTION.json"
        reconstruction_path = run_dir / "sealed_c86_reconstruction.npz"
        metrics_path = run_dir / "prelock_metrics.csv"
        if not all(
            path.is_file()
            for path in (manifest_path, lock_path, reconstruction_path, metrics_path)
        ):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if manifest["c86_hidden_damage_opened"] or manifest["c87_c89_targets_opened"]:
            raise RuntimeError(f"{run_dir.name} violated the pre-lock firewall")
        if sha256(reconstruction_path) != lock["reconstruction_sha256"]:
            raise RuntimeError(f"{run_dir.name} reconstruction hash mismatch")
        rows = list(csv.DictReader(metrics_path.open(encoding="utf-8")))
        audit = [
            float(row["selection_score"]) for row in rows if row["split"] == "audit"
        ]
        if len(audit) != 5:
            raise ValueError(f"{run_dir.name} does not contain five audit cycles")
        records.append(
            {
                "tag": run_dir.name,
                "architecture": manifest["model"],
                "seed": int(manifest["seed"]),
                "best_validation_score": float(manifest["best_validation_score"]),
                "audit_mean_selection_score": statistics.mean(audit),
                "audit_cycle_scores": audit,
                "reconstruction": reconstruction_path,
                "reconstruction_sha256": sha256(reconstruction_path),
                "checkpoint_sha256": lock["checkpoint_sha256"],
            }
        )
    if len(records) != 6:
        raise ValueError(f"expected six complete runs, found {len(records)}")
    by_architecture: dict[str, list[dict[str, object]]] = {}
    for record in records:
        by_architecture.setdefault(str(record["architecture"]), []).append(record)
    if set(by_architecture) != {"pointwise", "one_ring"}:
        raise ValueError("selection requires pointwise and one_ring architectures")
    medians = {
        architecture: statistics.median(
            float(record["audit_mean_selection_score"]) for record in rows
        )
        for architecture, rows in by_architecture.items()
    }
    winner = min(
        medians, key=lambda architecture: (medians[architecture], architecture)
    )
    representative = min(
        by_architecture[winner],
        key=lambda record: (
            abs(float(record["audit_mean_selection_score"]) - medians[winner]),
            int(record["seed"]),
        ),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "selection_status": "locked_before_c86_truth",
        "selection_basis": (
            "minimum architecture median of mean c81-c85 audit selection score; "
            "representative seed closest to winning median"
        ),
        "architecture_median_audit_score": medians,
        "winning_architecture": winner,
        "primary_tag": representative["tag"],
        "primary_seed": representative["seed"],
        "primary_reconstruction": str(
            Path(representative["reconstruction"]).relative_to(args.out.parent)
        ),
        "primary_reconstruction_sha256": representative["reconstruction_sha256"],
        "all_runs": [
            {key: value for key, value in record.items() if key != "reconstruction"}
            for record in records
        ],
        "c86_hidden_damage_opened": False,
        "c87_c89_targets_opened": False,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
