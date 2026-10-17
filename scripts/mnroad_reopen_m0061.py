#!/usr/bin/env python3
"""Reopen M0061 phase 1 and invalidate the dependent phase-2 lock.

This deliberately preserves all user geometry.  M0061's phase-2 identity
fields are removed so the phase-1 validator can accept the owner's revised
FL/NWP classification.  Other records retain their candidate lineage fields,
but every phase-2 lock is removed because the lineage graph must be rebuilt
after M0061 is relocked.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PHASE2_FEATURE_FIELDS = {
    "crack_id",
    "change_type",
    "lineage_id",
    "relation_type",
    "mapping_confidence",
    "predecessor_segment_ids",
    "predecessor_lineage_ids",
    "lineage_method",
    "phase2_review_status",
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
    args = parser.parse_args()
    packet = args.packet.resolve()
    records = sorted((packet / "records").glob("M*.geojson"))
    if not records:
        raise SystemExit(f"no records found under {packet}")

    timestamp = datetime.now(timezone.utc).isoformat()
    reopened = None
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        record["phase2_locked"] = False
        record.pop("phase2_locked_at_utc", None)
        record.pop("phase2_lock_status", None)
        record["phase2_invalidated_at_utc"] = timestamp
        record["phase2_invalidated_reason"] = (
            "M0061 phase 1 reopened by owner for FL/NWP reclassification"
        )

        if record.get("task_id") == "M0061":
            reopened = record
            record["phase1_locked"] = False
            record.pop("phase1_locked_at_utc", None)
            record.pop("trajectory_eligibility", None)
            record.pop("trajectory_censor_reason", None)
            record["phase1_reopened_at_utc"] = timestamp
            record["phase1_reopened_reason"] = (
                "Owner requested reannotation after FL and NWP were not distinguished"
            )
            for feature in record.get("features", []):
                props = feature.get("properties", {})
                for field in PHASE2_FEATURE_FIELDS:
                    props.pop(field, None)
                # Keep explicit empty phase-1 placeholders used by the UI.
                props["crack_id"] = ""
                props["change_type"] = ""
        atomic_json(path, record)

    if reopened is None:
        raise SystemExit("M0061 record not found")

    work = packet / "phase2_work"
    amendment = work / "phase2_reopen_amendment.md"
    amendment.write_text(
        "# Phase 2 reopening amendment\n\n"
        f"- Invalidated at UTC: `{timestamp}`\n"
        "- Trigger: the owner reported that FL and NWP were not distinguished on M0061.\n"
        "- Action: M0061 phase 1 was reopened without changing or deleting its geometry.\n"
        "- Dependency consequence: all phase-2 locks were removed; the existing lineage and "
        "canonical files are superseded candidates until M0061 is relocked and phase 2 is rebuilt.\n"
        "- Scientific boundary: the prior maintenance-censor assignment is withdrawn; it cannot "
        "substitute for correcting the observed distress class.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "records": len(records),
        "phase2_locks_removed": len(records),
        "reopened_task": "M0061",
        "m0061_geometry_preserved": len(reopened.get("features", [])),
        "amendment": str(amendment),
    }, indent=2))


if __name__ == "__main__":
    main()
