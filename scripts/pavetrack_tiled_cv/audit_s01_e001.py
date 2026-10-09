#!/usr/bin/env python3
"""Recompute the frozen S01-E001 candidate-coverage failure audit."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from geometry import box_iou


def maximum_match_count(
    targets: Sequence[Sequence[float]], proposals: Sequence[Sequence[float]]
) -> int:
    adjacency = [
        [index for index, proposal in enumerate(proposals) if box_iou(target, proposal) >= 0.5]
        for target in targets
    ]
    proposal_to_target: dict[int, int] = {}

    def augment(target_index: int, seen: set[int]) -> bool:
        for proposal_index in adjacency[target_index]:
            if proposal_index in seen:
                continue
            seen.add(proposal_index)
            if proposal_index not in proposal_to_target or augment(
                proposal_to_target[proposal_index], seen
            ):
                proposal_to_target[proposal_index] = target_index
                return True
        return False

    return sum(augment(index, set()) for index in range(len(targets)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    proposals_by_image: dict[str, list[dict]] = defaultdict(list)
    for proposal in evaluation["proposals"]:
        proposals_by_image[proposal["image_id"]].append(proposal)

    location_rows: dict[str, dict[str, int]] = defaultdict(
        lambda: {"targets": 0, "covered": 0}
    )
    individually_covered = 0
    proposer_selected = 0
    fused_selected = 0
    proposer_threshold = evaluation["proposer"]["global_score_threshold"]
    fused_threshold = evaluation["two_stage"]["global_score_threshold"]
    for record in manifest["records"]:
        targets = record["crack_boxes_xyxy"]
        proposals = proposals_by_image[record["image_id"]]
        proposal_boxes = [proposal["box_xyxy"] for proposal in proposals]
        covered = maximum_match_count(targets, proposal_boxes)
        row = location_rows[str(record["reid"])]
        row["targets"] += len(targets)
        row["covered"] += covered
        for target in targets:
            covering = [
                proposal
                for proposal in proposals
                if box_iou(target, proposal["box_xyxy"]) >= 0.5
            ]
            individually_covered += bool(covering)
            proposer_selected += any(
                proposal["proposer_score"] >= proposer_threshold for proposal in covering
            )
            fused_selected += any(
                proposal["two_stage_score"] >= fused_threshold for proposal in covering
            )

    output_rows = []
    for location, row in sorted(location_rows.items()):
        output_rows.append(
            {
                "location": location,
                **row,
                "oracle_recall": row["covered"] / row["targets"] if row["targets"] else None,
            }
        )
    recalls = [row["oracle_recall"] for row in output_rows if row["oracle_recall"] is not None]
    payload = {
        "source_protocol": evaluation["protocol"],
        "evaluation_manifest_sha256": evaluation["manifest_sha256"],
        "targets": sum(row["targets"] for row in output_rows),
        "oracle_maximum_matching_covered": sum(row["covered"] for row in output_rows),
        "oracle_macro_location_recall": sum(recalls) / len(recalls),
        "individually_covered_targets": individually_covered,
        "targets_with_covering_proposer_above_frozen_threshold": proposer_selected,
        "targets_with_covering_fused_score_above_frozen_threshold": fused_selected,
        "locations": output_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

