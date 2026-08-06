#!/usr/bin/env python3
"""Build the outcome-free 29-row load-only input and split receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


FEATURES = (
    "G1_source_crack_length_m",
    "G2_source_crack_area_m2",
    "G3_forecast_horizon_years",
    "T1_annual_esal_trend",
)
EXCLUDED = "06-1253-T07"
REQUIRED_SOURCE_FIELDS = {
    "transition_id", "section", "source_cutoff_date", "target_survey_date",
    "development_transition", "future_time_test", *FEATURES,
    "traffic_year", "ESAL_SOURCE",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or ())
        missing = REQUIRED_SOURCE_FIELDS - fields
        if missing:
            raise ValueError(f"source feature table missing fields: {sorted(missing)}")
        return list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validate(rows: list[dict[str, str]]) -> None:
    if len(rows) != 30:
        raise ValueError(f"expected 30 source rows, found {len(rows)}")
    if sum(row["transition_id"] == EXCLUDED for row in rows) != 1:
        raise ValueError(f"expected exactly one source row {EXCLUDED}")
    kept = [row for row in rows if row["transition_id"] != EXCLUDED]
    if len(kept) != 29:
        raise ValueError(f"expected 29 retained rows, found {len(kept)}")
    ids = [row["transition_id"] for row in kept]
    if len(ids) != len(set(ids)):
        raise ValueError("retained transition IDs are not unique")
    for row in kept:
        for name in FEATURES:
            value = float(row[name])
            if not math.isfinite(value):
                raise ValueError(f"non-finite {name} at {row['transition_id']}")
        if float(row["T1_annual_esal_trend"]) <= 0:
            raise ValueError(f"T1 must be positive at {row['transition_id']}")
    for section in sorted({row["section"] for row in kept}):
        values = {row["T1_annual_esal_trend"] for row in kept if row["section"] == section}
        if len(values) < 2:
            raise ValueError(f"T1 is constant in section {section}")


def split_receipt(rows: list[dict[str, str]]) -> dict:
    sections = sorted({row["section"] for row in rows})
    ids_by_section = {
        section: [row["transition_id"] for row in rows if row["section"] == section]
        for section in sections
    }
    loso = []
    all_ids = [row["transition_id"] for row in rows]
    for held_out in sections:
        test = ids_by_section[held_out]
        train = [item for item in all_ids if item not in test]
        loso.append({
            "held_out_section": held_out,
            "train_transition_ids": train,
            "test_transition_ids": test,
            "train_count": len(train),
            "test_count": len(test),
        })
    development = [row["transition_id"] for row in rows if row["development_transition"] == "True"]
    future = [row["transition_id"] for row in rows if row["future_time_test"] == "True"]
    if len(development) != 24 or len(future) != 5:
        raise ValueError(f"expected 24 development + 5 future rows, got {len(development)} + {len(future)}")
    return {
        "status": "PASS_FIXED_OUTCOME_FREE_LOAD_ONLY_SPLITS",
        "protocol": "load_only_29_row_single_esal_channel",
        "transition_count": len(rows),
        "transition_ids": all_ids,
        "excluded_transition_ids": [EXCLUDED],
        "loso": loso,
        "future_time": {
            "train_transition_ids": development,
            "test_transition_ids": future,
            "train_count": len(development),
            "test_count": len(future),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--episode-audit", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.source)
    validate(rows)
    kept = [row for row in rows if row["transition_id"] != EXCLUDED]
    fields = [
        "transition_id", "section", "source_cutoff_date", "target_survey_date",
        "development_transition", "future_time_test", *FEATURES,
        "traffic_year", "ESAL_SOURCE",
    ]
    feature_path = args.output / "load_only_features_29x4.csv"
    join_path = args.output / "load_only_t1_join_receipt.csv"
    split_path = args.output / "load_only_split_receipt.json"
    write_csv(feature_path, fields, [{key: row[key] for key in fields} for row in kept])
    write_csv(
        join_path,
        ["transition_id", "section", "source_cutoff_date", "traffic_year", "construction_rule", "T1_annual_esal_trend", "ESAL_SOURCE", "join_status"],
        [{
            "transition_id": row["transition_id"],
            "section": row["section"],
            "source_cutoff_date": row["source_cutoff_date"],
            "traffic_year": row["traffic_year"],
            "construction_rule": "source-active CONSTRUCTION_NO from frozen v3 table",
            "T1_annual_esal_trend": row["T1_annual_esal_trend"],
            "ESAL_SOURCE": row["ESAL_SOURCE"],
            "join_status": "PASS",
        } for row in kept],
    )
    splits = split_receipt(kept)
    split_path.write_text(json.dumps(splits, indent=2) + "\n", encoding="utf-8")
    episode = json.loads(args.episode_audit.read_text(encoding="utf-8"))
    manifest = {
        "status": "PASS_29_BY_4_LOAD_ONLY_INPUT_PREFLIGHT__NO_OUTCOMES__NO_FIT",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "load_only_29_row_single_esal_channel",
        "source_feature_table_sha256": sha256(args.source),
        "source_feature_table": str(args.source),
        "excluded_transition_ids": [EXCLUDED],
        "transition_count": len(kept),
        "feature_columns": list(FEATURES),
        "feature_table": feature_path.name,
        "feature_table_sha256": sha256(feature_path),
        "t1_join_receipt": join_path.name,
        "t1_join_receipt_sha256": sha256(join_path),
        "split_receipt": split_path.name,
        "split_receipt_sha256": sha256(split_path),
        "episode_audit": str(args.episode_audit),
        "episode_audit_sha256": sha256(args.episode_audit),
        "episode_exception_handling": "exclude named T07 before any outcome fitting",
        "future_time_train_count": splits["future_time"]["train_count"],
        "future_time_test_count": splits["future_time"]["test_count"],
        "outcome_columns_present": False,
        "claim_boundary": "Outcome-free input preflight only; posterior fitting remains unauthorized.",
        "code": str(Path(__file__).resolve()),
        "code_sha256": sha256(Path(__file__).resolve()),
        "environment": {"python": sys.version, "platform": platform.platform()},
    }
    manifest_path = args.output / "load_only_input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "rows": len(kept),
        "development": splits["future_time"]["train_count"],
        "future_time": splits["future_time"]["test_count"],
        "excluded": EXCLUDED,
        "feature_table_sha256": manifest["feature_table_sha256"],
        "join_receipt_sha256": manifest["t1_join_receipt_sha256"],
        "split_receipt_sha256": manifest["split_receipt_sha256"],
        "manifest": str(manifest_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
