#!/usr/bin/env python3
"""Build a conservative many-to-many temporal lineage graph for MnROAD maps."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def interval_gap(first: dict, second: dict) -> float:
    return max(0.0, second["x_min_ft"] - first["x_max_ft"], first["x_min_ft"] - second["x_max_ft"])


def compatible_gap(first: dict, second: dict) -> bool:
    return abs(first["y_mean_px"] - second["y_mean_px"]) <= 10.0 and interval_gap(first, second) <= 2.0


def unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--annotator", type=Path, required=True)
    parser.add_argument("--candidate-builder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8776")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    packet = args.packet.resolve()
    annotator = load_module("mnroad_annotator", args.annotator.resolve())
    helper = load_module("mnroad_candidate_helper", args.candidate_builder.resolve())
    manifest = json.loads((packet / "manifest.json").read_text())
    private = json.loads((packet / "private_repeat_key.json").read_text())["tasks"]
    records = {
        row["task_id"]: json.loads((packet / "records" / f"{row['task_id']}.geojson").read_text())
        for row in manifest["tasks"]
    }
    if not all(record.get("phase1_locked") for record in records.values()):
        raise RuntimeError("all phase-1 records must be locked")
    if any(record.get("phase2_locked") for record in records.values()):
        raise RuntimeError("phase 2 is partly or fully locked; refusing bulk rewrite")

    primary = {
        (row["survey_date"], row["page"]): task_id
        for task_id, row in private.items() if not row["is_repeat"]
    }
    descriptors: dict[str, list[dict]] = {}
    for (date, _page), task_id in primary.items():
        row = private[task_id]
        width, height = annotator.image_size(packet / "images" / row["image"])
        rotation = annotator.landscape_rotation_degrees(date)
        descriptors[task_id] = [
            helper.descriptor(feature, date, width, height, rotation)
            for feature in annotator._target_features(records[task_id])
        ]

    next_lineage = 1
    relation_rows = []
    cross_page_candidates = []

    def create_lineage() -> str:
        nonlocal next_lineage
        lineage = f"L{next_lineage:03d}"
        next_lineage += 1
        return lineage

    def set_relation(item: dict, lineage: str, relation: str, confidence: str, predecessors: list[dict]) -> None:
        properties = item["feature"]["properties"]
        predecessor_segments = unique([old["segment_id"] for old in predecessors])
        predecessor_lineages = unique([old["feature"]["properties"].get("lineage_id", "") for old in predecessors])
        legacy_change = {
            "nucleation": "nucleation",
            "continuation": "persistent",
            "extension": "extension",
        }.get(relation, "unresolvable")
        properties.update({
            "lineage_id": lineage,
            "crack_id": lineage,
            "relation_type": relation,
            "change_type": legacy_change,
            "mapping_confidence": confidence,
            "predecessor_segment_ids": predecessor_segments,
            "predecessor_lineage_ids": predecessor_lineages,
            "lineage_method": "registered_same_station_temporal_graph_v1",
        })
        relation_rows.append({
            "task_id": properties["segment_id"].split("-S")[0],
            "segment_id": properties["segment_id"],
            "survey_date": properties["survey_date"],
            "page_start_ft": properties["page_start_ft"],
            "lineage_id": lineage,
            "relation_type": relation,
            "mapping_confidence": confidence,
            "predecessor_segment_ids": predecessor_segments,
            "predecessor_lineage_ids": predecessor_lineages,
        })

    for task_id, record in records.items():
        for feature in record["features"]:
            properties = feature["properties"]
            for key in (
                "lineage_id", "relation_type", "mapping_confidence",
                "predecessor_segment_ids", "predecessor_lineage_ids", "lineage_method",
                "link_confidence", "link_method", "link_reference_segment_ids",
                "link_reference_survey_date", "excluded_concealed_repeat",
            ):
                properties.pop(key, None)
            properties["crack_id"] = ""
            properties["change_type"] = "unresolvable"
            if properties["lane"] != "Driving" or properties["distress_class"] != "NWP":
                properties["relation_type"] = "excluded_non_target"
                properties["lineage_method"] = "excluded_non_target_feature"

    for page in range(1, 11):
        history: list[tuple[str, list[dict]]] = []
        for date in helper.DATES:
            task_id = primary[(date, page)]
            current = descriptors[task_id]
            if not current:
                history.append((date, current))
                continue

            previous = history[-1][1] if history else []
            previous_date = history[-1][0] if history else None
            direct_edges = []
            for old_index, old in enumerate(previous):
                for new_index, new in enumerate(current):
                    evidence = helper.candidate_edge(old, new)
                    if evidence:
                        direct_edges.append((old_index, new_index))
            old_degree = Counter(old_index for old_index, _ in direct_edges)
            new_degree = Counter(new_index for _, new_index in direct_edges)

            for new_index, item in enumerate(current):
                direct = [previous[old_index] for old_index, candidate_index in direct_edges if candidate_index == new_index]
                predecessors = direct
                relation = ""
                confidence = "high"

                if direct:
                    parent_lineages = unique([old["feature"]["properties"].get("lineage_id", "") for old in direct])
                    split = any(old_degree[old_index] > 1 for old_index, candidate_index in direct_edges if candidate_index == new_index)
                    if len(parent_lineages) > 1:
                        lineage = create_lineage()
                        relation, confidence = "bridging_merge", "medium"
                    else:
                        lineage = parent_lineages[0]
                        if len(direct) > 1:
                            relation, confidence = "redraw", "medium"
                        elif split:
                            relation, confidence = "split_redraw", "medium"
                        else:
                            relation = "extension" if helper.is_extension(direct[0], item) else "continuation"
                else:
                    nearby = [old for old in previous if compatible_gap(old, item)]
                    if nearby:
                        predecessors = nearby
                        parent_lineages = unique([old["feature"]["properties"].get("lineage_id", "") for old in nearby])
                        if len(parent_lineages) == 1:
                            lineage = parent_lineages[0]
                            relation, confidence = "redraw", "low"
                        else:
                            lineage = create_lineage()
                            relation, confidence = "bridging_merge", "low"
                    else:
                        older = []
                        for _older_date, older_items in reversed(history[:-1] if history else []):
                            matches = [old for old in older_items if helper.candidate_edge(old, item) or compatible_gap(old, item)]
                            if matches:
                                older = matches
                                break
                        if older:
                            predecessors = older
                            parent_lineages = unique([old["feature"]["properties"].get("lineage_id", "") for old in older])
                            lineage = parent_lineages[0] if len(parent_lineages) == 1 else create_lineage()
                            relation, confidence = "reappearance_or_redraw", "low"
                        else:
                            lineage = create_lineage()
                            relation, confidence = "nucleation", "high"
                set_relation(item, lineage, relation, confidence, predecessors)
            history.append((date, current))

    # Flag possible continuities across adjacent 50-ft pages without merging
    # them automatically; cross-page identity has weaker evidence than the
    # within-page map registration used above.
    for date in helper.DATES:
        for page in range(1, 10):
            left_task = primary[(date, page)]
            right_task = primary[(date, page + 1)]
            for left in descriptors[left_task]:
                for right in descriptors[right_task]:
                    left_end_gap = 50.0 - left["x_max_ft"]
                    right_start_gap = right["x_min_ft"]
                    if left_end_gap <= 2.0 and right_start_gap <= 2.0 and abs(left["y_mean_px"] - right["y_mean_px"]) <= 10.0:
                        cross_page_candidates.append({
                            "survey_date": date,
                            "left_segment_id": left["segment_id"],
                            "right_segment_id": right["segment_id"],
                            "left_lineage_id": left["feature"]["properties"]["lineage_id"],
                            "right_lineage_id": right["feature"]["properties"]["lineage_id"],
                            "reason": "possible_boundary_continuity_not_auto_merged",
                        })

    # Concealed repeats remain excluded.  Unique primary matches inherit the
    # primary lineage only so repeatability can be audited without creating a
    # second temporal observation.
    for repeat_task_id, row in private.items():
        if not row["is_repeat"]:
            continue
        primary_task_id = row["primary_task_id"]
        repeat_record = records[repeat_task_id]
        width, height = annotator.image_size(packet / "images" / row["image"])
        rotation = annotator.landscape_rotation_degrees(row["survey_date"])
        repeat_desc = [
            helper.descriptor(feature, row["survey_date"], width, height, rotation)
            for feature in annotator._target_features(repeat_record)
        ]
        primary_desc = descriptors[primary_task_id]
        edges = []
        for primary_index, old in enumerate(primary_desc):
            for repeat_index, new in enumerate(repeat_desc):
                if helper.candidate_edge(old, new):
                    edges.append((primary_index, repeat_index))
        primary_degree = Counter(primary_index for primary_index, _ in edges)
        repeat_degree = Counter(repeat_index for _, repeat_index in edges)
        for feature in repeat_record["features"]:
            properties = feature["properties"]
            properties["excluded_concealed_repeat"] = True
            properties["relation_type"] = "excluded_repeat"
            properties["lineage_method"] = "excluded_concealed_repeat"
        for primary_index, repeat_index in edges:
            if primary_degree[primary_index] != 1 or repeat_degree[repeat_index] != 1:
                continue
            source = primary_desc[primary_index]["feature"]["properties"]
            target = repeat_desc[repeat_index]["feature"]["properties"]
            target.update({
                "lineage_id": source["lineage_id"],
                "crack_id": source["lineage_id"],
                "change_type": source["change_type"],
                "mapping_confidence": "high",
                "predecessor_segment_ids": [primary_desc[primary_index]["segment_id"]],
                "predecessor_lineage_ids": [source["lineage_id"]],
                "lineage_method": "concealed_repeat_unique_primary_inheritance",
            })

    relation_counts = Counter(row["relation_type"] for row in relation_rows)
    confidence_counts = Counter(row["mapping_confidence"] for row in relation_rows)
    report = {
        "status": "PHASE2_LINEAGE_CANDIDATE_NOT_LOCKED",
        "protocol": "LINEAGE_MAPPING_PROTOCOL.md",
        "primary_nwp_feature_count": len(relation_rows),
        "lineage_count": len({row["lineage_id"] for row in relation_rows}),
        "relation_counts": dict(sorted(relation_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "low_confidence_rows": [row for row in relation_rows if row["mapping_confidence"] == "low"],
        "complex_relation_rows": [row for row in relation_rows if row["relation_type"] in {"redraw", "split_redraw", "bridging_merge", "reappearance_or_redraw"}],
        "cross_page_candidates": cross_page_candidates,
        "limitations": [
            "Lineage is an observation graph, not guaranteed physical crack identity.",
            "Cross-page candidates are reported but not automatically merged.",
            "Concealed repeats are excluded from temporal counts.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "phase2_lineage_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.apply:
        for task_id, record in records.items():
            helper.save_record(args.base_url.rstrip("/"), task_id, record)
    print(json.dumps({
        "applied": args.apply,
        "primary_nwp_features": report["primary_nwp_feature_count"],
        "lineages": report["lineage_count"],
        "relations": report["relation_counts"],
        "confidence": report["confidence_counts"],
        "cross_page_candidates": len(cross_page_candidates),
        "report": str(report_path.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
