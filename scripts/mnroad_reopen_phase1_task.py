#!/usr/bin/env python3
"""Safely reopen one MnROAD phase-1 record without altering its geometry."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PHASE2_FIELDS = {
    "crack_id", "change_type", "lineage_id", "relation_type",
    "mapping_confidence", "predecessor_segment_ids", "predecessor_lineage_ids",
    "lineage_method", "phase2_review_status",
}


def atomic_json(path: Path, payload: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("task_id")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--clear-no-target-confirmed", action="store_true")
    args = parser.parse_args()
    packet = args.packet.resolve()
    path = packet / "records" / f"{args.task_id}.geojson"
    record = json.loads(path.read_text(encoding="utf-8"))
    timestamp = datetime.now(timezone.utc).isoformat()

    record["phase1_locked"] = False
    record["phase2_locked"] = False
    record.pop("phase1_locked_at_utc", None)
    record.pop("phase2_locked_at_utc", None)
    record.pop("phase2_lock_status", None)
    record["phase1_reopened_at_utc"] = timestamp
    record["phase1_reopened_reason"] = args.reason
    record["phase2_invalidated_at_utc"] = timestamp
    record["phase2_invalidated_reason"] = f"{args.task_id} phase 1 reopened: {args.reason}"
    if args.clear_no_target_confirmed:
        record["no_target_confirmed"] = False
    for feature in record.get("features", []):
        props = feature["properties"]
        for field in PHASE2_FIELDS:
            props.pop(field, None)
        props["crack_id"] = ""
        props["change_type"] = ""
    atomic_json(path, record)

    amendment = packet / "phase2_work" / f"{args.task_id.lower()}_reannotation_amendment.md"
    amendment.write_text(
        f"# {args.task_id} reannotation amendment\n\n"
        f"- Reopened at UTC: `{timestamp}`\n"
        f"- Owner reason: {args.reason}\n"
        f"- Preserved geometry: {len(record.get('features', []))} source segments.\n"
        "- Phase-2 identity fields were removed from this record so phase 1 can be edited.\n"
        "- No geometry or distress class was changed automatically.\n"
        "- Existing canonical outputs are superseded until the revised phase 1 is locked and phase 2 is rebuilt.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "task_id": args.task_id,
        "phase1_locked": record["phase1_locked"],
        "geometry_preserved": len(record.get("features", [])),
        "amendment": str(amendment),
    }, indent=2))


if __name__ == "__main__":
    main()
