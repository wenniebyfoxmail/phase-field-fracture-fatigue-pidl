#!/usr/bin/env python3
"""Audit S09-E008 transition metadata without decoding scientific arrays."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


EXPECTED_LOADS = {0: 0.0, 1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0, 5: 0.0}
EXPECTED_FIELDS = {
    "u_node",
    "d_node",
    "history_gp",
    "strain_en_undgr_gp",
    "strain_en_degr_gp",
    "state_metadata",
}
SHA256 = re.compile(r"[0-9a-f]{64}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(metadata_dir: Path) -> dict[str, object]:
    index = read_csv(metadata_dir / "state_index.csv")
    inventory = read_csv(metadata_dir / "field_inventory.csv")
    summary = json.loads((metadata_dir / "run_summary.json").read_text())
    validation = json.loads((metadata_dir / "validation_receipt.json").read_text())
    source = json.loads((metadata_dir / "source_receipt.json").read_text())

    require(len(index) == 73 * 6, "expected 438 logical states")
    by_key = {row["state_key"]: row for row in index}
    require(len(by_key) == len(index), "state keys must be unique")

    for cycle in range(1, 74):
        for substep, load in EXPECTED_LOADS.items():
            key = f"c{cycle:04d}_s{substep:02d}"
            require(key in by_key, f"missing {key}")
            row = by_key[key]
            require(int(row["cycle"]) == cycle, f"cycle mismatch for {key}")
            require(int(row["substep"]) == substep, f"substep mismatch for {key}")
            require(math.isclose(float(row["nominal_load_factor"]), load),
                    f"load mismatch for {key}")
            require(row["converged"] == "1", f"unconverged state {key}")
            require(SHA256.fullmatch(row["payload_sha256"]) is not None,
                    f"invalid payload hash for {key}")
            if substep == 0:
                require(row["timing"] == "pre_cycle_committed",
                        f"pre-state timing mismatch for {key}")
            else:
                require(row["timing"] == "post_history_commit",
                        f"post-state timing mismatch for {key}")
                for column in ("equilibrium_residual", "phase_residual"):
                    require(math.isfinite(float(row[column])),
                            f"nonfinite {column} for {key}")

        pre = by_key[f"c{cycle:04d}_s00"]
        if cycle == 1:
            require(pre["is_alias"] == "0", "cycle 1 pre-state cannot be an alias")
            require(pre["source_state_key"] == "c0001_s00",
                    "cycle 1 source-state mismatch")
        else:
            previous = by_key[f"c{cycle - 1:04d}_s05"]
            require(pre["is_alias"] == "1", f"cycle {cycle} pre-state must alias")
            require(pre["source_state_key"] == previous["state_key"],
                    f"alias key mismatch at cycle {cycle}")
            require(pre["payload_file"] == previous["payload_file"],
                    f"alias path mismatch at cycle {cycle}")
            require(pre["payload_sha256"] == previous["payload_sha256"],
                    f"alias hash mismatch at cycle {cycle}")

    fields = {row["name"] for row in inventory}
    require(fields == EXPECTED_FIELDS, "field inventory mismatch")
    require(summary["sealed"] is True, "source run is not sealed")
    require(summary["logical_state_count"] == 438, "summary logical count mismatch")
    require(summary["unique_payload_count"] == 366, "summary payload count mismatch")
    require(summary["cycle_count"] == 73, "summary cycle count mismatch")
    require(validation["passed"] is True, "producer validation did not pass")
    require(validation["cycles"] == list(range(1, 74)), "validated cycle set mismatch")
    require(all(row["passed"] for row in validation["gate_rows"]),
            "one or more producer validation gates failed")
    require(summary["provenance"]["source_commit"] == source["source_commit"],
            "source commit mismatch")
    require(source["source_dirty"] is False, "producer source was dirty")

    return {
        "verdict": "METADATA_CAPABILITY_PASS",
        "scope": "metadata_only_no_scientific_array_decode",
        "cycles": 73,
        "logical_states": 438,
        "unique_payloads": 366,
        "pre_to_previous_post_aliases": 72,
        "load_path": [EXPECTED_LOADS[i] for i in range(6)],
        "field_names": sorted(fields),
        "producer_source_commit": source["source_commit"],
        "remaining_gates": [
            "verify every full-path payload hash before decode",
            "verify decoded shapes, finiteness, native order and s00/s05 equality",
            "qualify producer update semantics and causal state sufficiency",
            "apply frozen P1 selection and scaling only after those gates pass",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.metadata_dir)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
