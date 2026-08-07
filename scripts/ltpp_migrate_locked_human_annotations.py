#!/usr/bin/env python3
"""Migrate hash-identical locked human annotations into a new blind packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-packet", type=Path, required=True)
    parser.add_argument("--new-packet", type=Path, required=True)
    parser.add_argument("--old-role", choices=("primary", "secondary"), required=True)
    parser.add_argument("--new-role", choices=("primary", "secondary"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    old_mapping_path = (
        args.old_packet
        / "sealed_do_not_open_during_annotation"
        / "blind_id_date_mapping.json"
    )
    new_mapping_path = (
        args.new_packet
        / "sealed_do_not_open_during_annotation"
        / "blind_id_asset_mapping.json"
    )
    old_mapping = json.loads(old_mapping_path.read_text(encoding="utf-8"))
    new_mapping = json.loads(new_mapping_path.read_text(encoding="utf-8"))
    new_by_hash = {row["source_sha256"]: row for row in new_mapping[args.new_role]}

    staged: list[tuple[Path, dict, dict]] = []
    skipped: list[dict] = []
    for old_row in old_mapping[args.old_role]:
        new_row = new_by_hash.get(old_row["source_sha256"])
        if new_row is None:
            skipped.append(
                {
                    "old_blind_id": old_row["blind_id"],
                    "survey_date": old_row["survey_date"],
                    "reason": "source hash is not in the new qualified inventory",
                }
            )
            continue
        old_label_path = (
            args.old_packet / args.old_role / "geojson" / f"{old_row['blind_id']}.geojson"
        )
        new_label_path = (
            args.new_packet / args.new_role / "geojson" / f"{new_row['blind_id']}.geojson"
        )
        old_label = json.loads(old_label_path.read_text(encoding="utf-8"))
        current = json.loads(new_label_path.read_text(encoding="utf-8"))
        if not old_label.get("properties", {}).get("locked"):
            raise SystemExit(f"old annotation is not locked: {old_label_path}")
        if current.get("properties", {}).get("locked") or current.get("features"):
            raise SystemExit(f"refusing to overwrite nonblank destination: {new_label_path}")
        if sha256(args.new_packet / args.new_role / "images" / f"{new_row['blind_id']}.png") != old_row["source_sha256"]:
            raise SystemExit(f"new packet image hash mismatch: {new_row['blind_id']}")

        migrated = json.loads(json.dumps(old_label))
        old_blind_id = old_row["blind_id"]
        new_blind_id = new_row["blind_id"]
        migrated["name"] = f"ltpp_geoforecast_{args.new_role}_{new_blind_id}"
        migrated["schema_version"] = "line_area_v3"
        migrated["properties"].update(
            {
                "blind_map_id": new_blind_id,
                "annotator_role": args.new_role,
                "source_image": f"{new_blind_id}.png",
                "locked": True,
                "annotation_source": "locked_human_annotation_confirmed_by_user",
                "migration_only": True,
                "migrated_from_blind_id": old_blind_id,
                "migrated_from_sha256": sha256(old_label_path),
            }
        )
        line_index = 0
        area_index = 0
        for feature in migrated.get("features", []):
            geometry_type = feature["geometry"]["type"]
            if geometry_type == "LineString":
                line_index += 1
                feature_id = f"{new_blind_id}-L{line_index:03d}"
            elif geometry_type == "Polygon":
                area_index += 1
                feature_id = f"{new_blind_id}-A{area_index:03d}"
            else:
                raise SystemExit(f"unsupported geometry type: {geometry_type}")
            properties = feature["properties"]
            properties["original_feature_id"] = properties.get(
                "feature_id", properties.get("line_id")
            )
            properties["original_review_status"] = properties.get("review_status")
            properties["blind_map_id"] = new_blind_id
            properties["feature_id"] = feature_id
            properties["line_id"] = feature_id
            properties["review_status"] = "human_locked_migrated"
        staged.append((new_label_path, migrated, {"old": old_row, "new": new_row, "old_path": old_label_path}))

    if len(staged) != 8:
        raise SystemExit(f"expected exactly 8 hash-identical qualified maps, found {len(staged)}")

    records = []
    for destination, payload, context in staged:
        destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        records.append(
            {
                "old_blind_id": context["old"]["blind_id"],
                "new_blind_id": context["new"]["blind_id"],
                "asset_key": context["new"]["asset_key"],
                "source_sha256": context["new"]["source_sha256"],
                "old_label_sha256": sha256(context["old_path"]),
                "new_label_sha256": sha256(destination),
                "features": len(payload.get("features", [])),
            }
        )
    receipt = {
        "status": "PASS_HASH_IDENTICAL_HUMAN_LABEL_MIGRATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "old_packet": str(args.old_packet.resolve()),
        "new_packet": str(args.new_packet.resolve()),
        "old_role": args.old_role,
        "new_role": args.new_role,
        "annotator_identity_boundary": "user confirmed the old nine-map pass was human annotation",
        "migrated_count": len(records),
        "skipped_count": len(skipped),
        "migrated": records,
        "skipped": skipped,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "migrated": len(records), "skipped": len(skipped)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
