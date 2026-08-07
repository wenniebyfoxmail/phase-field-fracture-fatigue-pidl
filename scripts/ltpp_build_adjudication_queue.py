#!/usr/bin/env python3
"""Build a deterministic, review-only queue from frozen blind pairing output."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SEMANTIC_CANDIDATES = {
    "P011-L007": ("water_bleeding_and_pumping", "definite"),
    "P009-L006": ("other_noncrack_distress", "definite"),
    "P009-L007": ("other_noncrack_distress", "definite"),
    "P009-L008": ("other_noncrack_distress", "definite"),
    "P009-L009": ("other_noncrack_distress", "definite"),
    "P018-L005": ("other_noncrack_distress", "definite"),
    "P018-L006": ("other_noncrack_distress", "definite"),
    "P018-L007": ("other_noncrack_distress", "definite"),
    "P018-L008": ("other_noncrack_distress", "definite"),
    "P018-L009": ("other_noncrack_distress", "definite"),
    "P018-L010": ("other_noncrack_distress", "definite"),
    "P019-L001": ("other_noncrack_distress", "definite"),
    "P019-L002": ("other_noncrack_distress", "definite"),
    "P019-L003": ("other_noncrack_distress", "definite"),
    "P019-L004": ("other_noncrack_distress", "definite"),
    "P019-L005": ("other_noncrack_distress", "lower_confidence"),
    "P019-L006": ("other_noncrack_distress", "lower_confidence"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def feature_index(role_root: Path) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for path in sorted((role_root / "geojson").glob("*.geojson")):
        payload = load_json(path)
        for feature in payload.get("features", []):
            feature_id = feature.get("properties", {}).get("feature_id")
            if not feature_id:
                raise ValueError(f"Feature without feature_id: {path}")
            if feature_id in index:
                raise ValueError(f"Duplicate feature_id: {feature_id}")
            index[feature_id] = feature
    return index


def image_path(packet_root: Path, role: str, feature_id: str) -> str:
    blind_id = feature_id.split("-", 1)[0]
    candidates = sorted((packet_root / role / "images").glob(f"{blind_id}.*"))
    if len(candidates) != 1:
        raise ValueError(f"Expected one image for {role}/{blind_id}, found {len(candidates)}")
    return str(candidates[0].relative_to(packet_root))


def feature_payload(index: dict[str, dict], feature_id: str) -> dict:
    if feature_id not in index:
        raise ValueError(f"Missing feature: {feature_id}")
    return index[feature_id]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--pairing-result", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_root = args.packet_root.resolve()
    pairing_path = (args.pairing_result or packet_root / "pairing_result.json").resolve()
    output_path = (args.output or packet_root / "adjudication_queue.json").resolve()
    if output_path.exists() and not args.force:
        existing = load_json(output_path)
        if existing.get("completed_items", 0) or any(
            item.get("disposition") is not None for item in existing.get("items", [])
        ):
            raise ValueError("Refusing to overwrite a queue with saved adjudication progress; use --force only after preserving it")
    pairing = load_json(pairing_path)
    if pairing.get("status") != "requires_adjudication":
        raise ValueError("Pairing result must have status requires_adjudication")
    if pairing.get("sealed_mapping_read") is not True:
        raise ValueError("Pairing result did not pass the sealed-mapping gate")

    mapping_path = packet_root / "sealed_do_not_open_during_annotation" / "blind_id_asset_mapping.json"
    mapping = load_json(mapping_path)
    primary_asset_by_blind = {row["blind_id"]: row for row in mapping["primary"]}

    primary = feature_index(packet_root / "primary")
    secondary = feature_index(packet_root / "secondary")
    items: list[dict] = []

    for asset in pairing.get("assets", []):
        asset_fields = {
            key: asset[key]
            for key in ("asset_key", "section", "construction_number", "panel_start_ft", "survey_date")
        }
        for feature_id in asset.get("unmatched_primary", []):
            items.append(
                {
                    "queue_id": f"unmatched-primary-{feature_id}",
                    "kind": "unmatched_primary",
                    **asset_fields,
                    "primary_feature_id": feature_id,
                    "secondary_feature_id": None,
                    "primary_feature": feature_payload(primary, feature_id),
                    "secondary_feature": None,
                    "primary_image": image_path(packet_root, "primary", feature_id),
                    "secondary_image": None,
                    "allowed_dispositions": ["accept_primary", "reject", "uncertain"],
                    "disposition": None,
                    "review_note": "",
                }
            )
        for feature_id in asset.get("unmatched_secondary", []):
            items.append(
                {
                    "queue_id": f"unmatched-secondary-{feature_id}",
                    "kind": "unmatched_secondary",
                    **asset_fields,
                    "primary_feature_id": None,
                    "secondary_feature_id": feature_id,
                    "primary_feature": None,
                    "secondary_feature": feature_payload(secondary, feature_id),
                    "primary_image": None,
                    "secondary_image": image_path(packet_root, "secondary", feature_id),
                    "allowed_dispositions": ["accept_secondary", "reject", "uncertain"],
                    "disposition": None,
                    "review_note": "",
                }
            )
        for disagreement in asset.get("family_disagreements", []):
            first_id = disagreement["primary_feature_id"]
            second_id = disagreement["secondary_feature_id"]
            items.append(
                {
                    "queue_id": f"family-{first_id}-{second_id}",
                    "kind": "family_disagreement",
                    **asset_fields,
                    "primary_feature_id": first_id,
                    "secondary_feature_id": second_id,
                    "primary_feature": feature_payload(primary, first_id),
                    "secondary_feature": feature_payload(secondary, second_id),
                    "primary_image": image_path(packet_root, "primary", first_id),
                    "secondary_image": image_path(packet_root, "secondary", second_id),
                    "pairing_metrics": disagreement,
                    "allowed_dispositions": ["accept_primary", "accept_secondary", "uncertain"],
                    "disposition": None,
                    "review_note": "",
                }
            )

    asset_by_primary: dict[str, dict] = {}
    for asset in pairing.get("assets", []):
        for match in asset.get("line_matches", []) + asset.get("area_matches", []):
            asset_by_primary[match["primary_feature_id"]] = asset
        for feature_id in asset.get("unmatched_primary", []):
            asset_by_primary[feature_id] = asset

    # Semantic candidates do not affect crack pairing metrics, but they need a
    # visible disposition before the adjudicated package is frozen.
    for feature_id, (candidate_family, confidence) in SEMANTIC_CANDIDATES.items():
        feature = feature_payload(primary, feature_id)
        asset = asset_by_primary.get(feature_id)
        if asset is None:
            blind_id = feature_id.split("-", 1)[0]
            mapping_row = primary_asset_by_blind.get(blind_id)
            if mapping_row is None:
                raise ValueError(f"Cannot resolve asset for semantic candidate {feature_id}")
            matches = [
                a for a in pairing.get("assets", []) if a["asset_key"] == mapping_row["asset_key"]
            ]
            if len(matches) != 1:
                raise ValueError(f"Pairing asset mismatch for semantic candidate {feature_id}")
            asset = matches[0]
        items.append(
            {
                "queue_id": f"semantic-{feature_id}",
                "kind": "semantic_candidate",
                **{
                    key: asset[key]
                    for key in ("asset_key", "section", "construction_number", "panel_start_ft", "survey_date")
                },
                "primary_feature_id": feature_id,
                "secondary_feature_id": None,
                "primary_feature": feature,
                "secondary_feature": None,
                "primary_image": image_path(packet_root, "primary", feature_id),
                "secondary_image": None,
                "candidate_family": candidate_family,
                "candidate_confidence": confidence,
                "allowed_dispositions": ["accept_candidate", "keep_current", "uncertain"],
                "disposition": None,
                "review_note": "",
            }
        )

    counts = {
        kind: sum(item["kind"] == kind for item in items)
        for kind in (
            "unmatched_primary",
            "unmatched_secondary",
            "family_disagreement",
            "semantic_candidate",
        )
    }
    expected = {
        "unmatched_primary": 27,
        "unmatched_secondary": 94,
        "family_disagreement": 1,
        "semantic_candidate": 17,
    }
    if counts != expected:
        raise ValueError(f"Queue count mismatch: expected {expected}, got {counts}")
    queue = {
        "status": "PENDING_HUMAN_ADJUDICATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet_root": str(packet_root),
        "pairing_result": str(pairing_path),
        "pairing_result_sha256": sha256(pairing_path),
        "sealed_mapping_sha256": sha256(mapping_path),
        "counts": counts,
        "total_items": len(items),
        "completed_items": 0,
        "qualification_boundary": "This queue is not adjudicated ground truth until every item has a reviewed disposition.",
        "items": items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": queue["status"], "total_items": len(items), "counts": counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
