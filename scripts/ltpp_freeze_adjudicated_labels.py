#!/usr/bin/env python3
"""Freeze canonical LTPP labels only after every blind-pairing item is adjudicated."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


CRACK_FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def feature_by_id(payload: dict) -> dict[str, dict]:
    result = {}
    for feature in payload.get("features", []):
        feature_id = feature.get("properties", {}).get("feature_id")
        if not feature_id or feature_id in result:
            raise ValueError(f"Missing or duplicate feature_id: {feature_id}")
        result[feature_id] = feature
    return result


def canonicalize(feature: dict, state_id: str, role: str, index: int, area_index: int) -> tuple[dict, int, int]:
    item = copy.deepcopy(feature)
    props = item["properties"]
    original_id = props["feature_id"]
    if item["geometry"]["type"] == "Polygon":
        area_index += 1
        canonical_id = f"{state_id}-A{area_index:03d}"
    else:
        index += 1
        canonical_id = f"{state_id}-L{index:03d}"
    props["source_feature_id"] = original_id
    props["source_role"] = role
    props["feature_id"] = canonical_id
    props["line_id"] = canonical_id
    props["blind_map_id"] = state_id
    props["review_status"] = "adjudicated_locked"
    return item, index, area_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_root = args.packet_root.resolve()
    queue_path = (args.queue or packet_root / "adjudication_queue.json").resolve()
    output_root = (args.output or packet_root / "adjudicated").resolve()
    queue = load_json(queue_path)
    items = queue.get("items", [])
    pending = [item["queue_id"] for item in items if item.get("disposition") is None]
    if pending or queue.get("completed_items") != len(items) or queue.get("status") != "ADJUDICATION_COMPLETE_PENDING_FREEZE":
        print(
            json.dumps(
                {
                    "status": "BLOCKED_INCOMPLETE_ADJUDICATION",
                    "completed": len(items) - len(pending),
                    "total": len(items),
                    "pending": len(pending),
                }
            )
        )
        return 42
    if len(items) != 139 or len({item["queue_id"] for item in items}) != 139:
        raise ValueError("Adjudication queue must contain 139 unique items")
    if output_root.exists():
        raise ValueError(f"Refusing to overwrite frozen adjudicated package: {output_root}")

    pairing_path = packet_root / "pairing_result.json"
    pairing = load_json(pairing_path)
    mapping_path = packet_root / "sealed_do_not_open_during_annotation" / "blind_id_asset_mapping.json"
    mapping = load_json(mapping_path)
    primary_rows = {row["asset_key"]: row for row in mapping["primary"]}
    secondary_rows = {row["asset_key"]: row for row in mapping["secondary"]}
    if set(primary_rows) != set(secondary_rows) or len(primary_rows) != 37:
        raise ValueError("Blind mapping must contain the same 37 assets in each role")


    queue_by_asset: dict[str, list[dict]] = {}
    for item in items:
        if item["disposition"] not in item["allowed_dispositions"]:
            raise ValueError(f"Invalid disposition for {item['queue_id']}")
        queue_by_asset.setdefault(item["asset_key"], []).append(item)

    built: list[tuple[str, dict]] = []
    semantic_corrections = []
    global_families: Counter[str] = Counter()
    disposition_counts = Counter(item["disposition"] for item in items)
    for state_number, asset_key in enumerate(sorted(primary_rows), start=1):
        state_id = f"A{state_number:03d}"
        primary_row = primary_rows[asset_key]
        secondary_row = secondary_rows[asset_key]
        primary_path = packet_root / "primary" / "geojson" / f"{primary_row['blind_id']}.geojson"
        secondary_path = packet_root / "secondary" / "geojson" / f"{secondary_row['blind_id']}.geojson"
        primary_payload = load_json(primary_path)
        secondary_payload = load_json(secondary_path)
        if not primary_payload["properties"].get("locked") or not secondary_payload["properties"].get("locked"):
            raise ValueError(f"Role label unexpectedly unlocked for {asset_key}")
        primary_features = feature_by_id(primary_payload)
        secondary_features = feature_by_id(secondary_payload)

        remove_secondary: set[str] = set()
        uncertain_secondary: set[str] = set()
        additions: list[tuple[dict, str, str]] = []
        for item in queue_by_asset.get(asset_key, []):
            kind = item["kind"]
            disposition = item["disposition"]
            if kind == "unmatched_secondary":
                feature_id = item["secondary_feature_id"]
                if disposition == "reject":
                    remove_secondary.add(feature_id)
                elif disposition == "uncertain":
                    uncertain_secondary.add(feature_id)
            elif kind == "unmatched_primary":
                feature_id = item["primary_feature_id"]
                if disposition in {"accept_primary", "uncertain"}:
                    feature = copy.deepcopy(primary_features[feature_id])
                    if disposition == "uncertain":
                        feature["properties"]["distress_family"] = "uncertain"
                    additions.append((feature, "primary", item["queue_id"]))
            elif kind == "family_disagreement":
                primary_id = item["primary_feature_id"]
                secondary_id = item["secondary_feature_id"]
                if disposition == "accept_primary":
                    remove_secondary.add(secondary_id)
                    additions.append((copy.deepcopy(primary_features[primary_id]), "primary", item["queue_id"]))
                elif disposition == "uncertain":
                    uncertain_secondary.add(secondary_id)
            elif kind == "semantic_candidate":
                semantic_corrections.append(
                    {
                        "queue_id": item["queue_id"],
                        "asset_key": asset_key,
                        "source_feature_id": item["primary_feature_id"],
                        "disposition": disposition,
                        "candidate_family": item["candidate_family"],
                        "review_note": item.get("review_note", ""),
                    }
                )
            else:
                raise ValueError(f"Unknown queue item kind: {kind}")

        selected: list[tuple[dict, str, str | None]] = []
        for feature in secondary_payload.get("features", []):
            feature_id = feature["properties"]["feature_id"]
            if feature_id in remove_secondary:
                continue
            chosen = copy.deepcopy(feature)
            if feature_id in uncertain_secondary:
                chosen["properties"]["distress_family"] = "uncertain"
            selected.append((chosen, "secondary", None))
        selected.extend(additions)

        canonical_features = []
        line_index = 0
        area_index = 0
        for feature, role, queue_id in selected:
            canonical, line_index, area_index = canonicalize(
                feature, state_id, role, line_index, area_index
            )
            canonical["properties"]["adjudication_queue_id"] = queue_id
            canonical_features.append(canonical)
            global_families[canonical["properties"]["distress_family"]] += 1

        output_name = (
            f"{state_id}__{primary_row['section']}__c{primary_row['construction_number']}"
            f"__p{primary_row['panel_start_ft']:03d}__{primary_row['survey_date']}.geojson"
        )
        payload = {
            "type": "FeatureCollection",
            "name": f"ltpp_geoforecast_adjudicated_{state_id}",
            "schema_version": "adjudicated_line_area_v1",
            "coordinate_reference": secondary_payload.get("coordinate_reference"),
            "properties": {
                "state_id": state_id,
                "asset_key": asset_key,
                "section": primary_row["section"],
                "construction_number": primary_row["construction_number"],
                "panel_start_ft": primary_row["panel_start_ft"],
                "panel_end_ft": primary_row["panel_end_ft"],
                "survey_date": primary_row["survey_date"],
                "locked": True,
                "adjudicated": True,
                "canonical_rule": "human_secondary_baseline_plus_item_level_adjudication",
                "primary_blind_id": primary_row["blind_id"],
                "secondary_blind_id": secondary_row["blind_id"],
                "primary_label_sha256": sha256(primary_path),
                "secondary_label_sha256": sha256(secondary_path),
            },
            "features": canonical_features,
        }
        built.append((output_name, payload))

    temporary_root = Path(
        tempfile.mkdtemp(prefix="ltpp_adjudicated_", dir=output_root.parent)
    )
    try:
        geojson_root = temporary_root / "geojson"
        geojson_root.mkdir()
        files = []
        crack_feature_count = 0
        uncertain_feature_count = 0
        for output_name, payload in built:
            path = geojson_root / output_name
            atomic_json(path, payload)
            families = Counter(
                feature["properties"]["distress_family"] for feature in payload["features"]
            )
            crack_count = sum(families[family] for family in CRACK_FAMILIES)
            uncertain_count = families["uncertain"]
            crack_feature_count += crack_count
            uncertain_feature_count += uncertain_count
            files.append(
                {
                    "file": f"geojson/{output_name}",
                    "asset_key": payload["properties"]["asset_key"],
                    "features": len(payload["features"]),
                    "crack_features": crack_count,
                    "uncertain_features": uncertain_count,
                    "sha256": sha256(path),
                }
            )
        manifest = {
            "status": "PASS_ADJUDICATED_LABELS_FROZEN",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "packet_root": str(packet_root),
            "canonical_rule": "human_secondary_baseline_plus_item_level_adjudication",
            "state_count": len(files),
            "queue_item_count": len(items),
            "queue_sha256": sha256(queue_path),
            "pairing_result_sha256": sha256(pairing_path),
            "sealed_mapping_sha256": sha256(mapping_path),
            "primary_manifest_sha256": sha256(packet_root / "primary" / "primary_role_freeze_manifest.json"),
            "secondary_manifest_sha256": sha256(packet_root / "secondary_human_locked_manifest.json"),
            "total_features": sum(row["features"] for row in files),
            "crack_features": crack_feature_count,
            "uncertain_features": uncertain_feature_count,
            "family_counts": dict(sorted(global_families.items())),
            "disposition_counts": dict(sorted(disposition_counts.items())),
            "semantic_corrections": semantic_corrections,
            "files": files,
            "qualification_boundary": "Frozen adjudicated observations are labels, not forecasting evidence.",
        }
        atomic_json(temporary_root / "adjudicated_manifest.json", manifest)
        temporary_root.replace(output_root)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    print(
        json.dumps(
            {
                "status": "PASS_ADJUDICATED_LABELS_FROZEN",
                "states": len(built),
                "features": manifest["total_features"],
                "crack_features": manifest["crack_features"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
