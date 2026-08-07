#!/usr/bin/env python3
"""Validate and freeze a completed role in an LTPP blind annotation packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
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
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--role", choices=("primary", "secondary"), required=True)
    parser.add_argument("--expected-maps", type=int, required=True)
    parser.add_argument("--annotation-source", required=True)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    label_paths = sorted((args.packet_root / args.role / "geojson").glob("*.geojson"))
    if len(label_paths) != args.expected_maps:
        raise SystemExit(
            f"expected {args.expected_maps} labels for {args.role}, found {len(label_paths)}"
        )

    families: Counter[str] = Counter()
    rows = []
    unlocked = []
    total_features = 0
    total_lines = 0
    total_polygons = 0
    for label_path in label_paths:
        payload = json.loads(label_path.read_text(encoding="utf-8"))
        blind_id = payload.get("properties", {}).get("blind_map_id")
        if blind_id != label_path.stem:
            raise SystemExit(f"blind ID/path mismatch: {label_path}")
        locked = bool(payload.get("properties", {}).get("locked"))
        if not locked:
            unlocked.append(blind_id)
        features = payload.get("features", [])
        lines = sum(
            feature.get("geometry", {}).get("type") == "LineString"
            for feature in features
        )
        polygons = sum(
            feature.get("geometry", {}).get("type") == "Polygon"
            for feature in features
        )
        if lines + polygons != len(features):
            raise SystemExit(f"unsupported geometry in {label_path}")
        for feature in features:
            families[str(feature.get("properties", {}).get("distress_family"))] += 1
        image_path = args.packet_root / args.role / "images" / f"{blind_id}.png"
        if not image_path.is_file():
            raise SystemExit(f"missing packet image: {image_path}")
        rows.append(
            {
                "blind_id": blind_id,
                "locked": locked,
                "features": len(features),
                "lines": lines,
                "polygons": polygons,
                "label_sha256": sha256(label_path),
                "image_sha256": sha256(image_path),
            }
        )
        total_features += len(features)
        total_lines += lines
        total_polygons += polygons

    if unlocked:
        raise SystemExit(f"role is not fully locked: {', '.join(unlocked)}")
    receipt = {
        "status": "PASS_ROLE_FULLY_LOCKED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet_root": str(args.packet_root.resolve()),
        "role": args.role,
        "annotation_source": args.annotation_source,
        "backup": str(args.backup.resolve()) if args.backup else None,
        "all_locked": True,
        "map_count": len(rows),
        "empty_reviewed_map_count": sum(row["features"] == 0 for row in rows),
        "total_features": total_features,
        "total_lines": total_lines,
        "total_polygons": total_polygons,
        "family_counts": dict(sorted(families.items())),
        "files": rows,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "maps": len(rows),
                "features": total_features,
                "empty_reviewed_maps": receipt["empty_reviewed_map_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
