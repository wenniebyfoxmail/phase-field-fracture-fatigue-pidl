#!/usr/bin/env python3
"""Read-only Stage-1 audit for the LTPP distress-map recognition track.

The script only reads the frozen image/label packet and writes a new audit
directory under local_archive. It does not open the sealed blind mapping and
does not modify any frozen packet.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import struct
from typing import Any, Iterable


CRACK_FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_metadata(path: pathlib.Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        signature = fh.read(8)
        length = struct.unpack(">I", fh.read(4))[0]
        chunk = fh.read(4)
        if signature != b"\x89PNG\r\n\x1a\n" or chunk != b"IHDR" or length < 13:
            raise ValueError(f"not a readable PNG IHDR: {path}")
        width, height, bit_depth, colour_type, compression, filter_method, interlace = struct.unpack(
            ">IIBBBBB", fh.read(13)
        )
    modes = {0: "grayscale", 2: "truecolour", 3: "indexed", 4: "grayscale_alpha", 6: "truecolour_alpha"}
    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "colour_type": colour_type,
        "mode": modes.get(colour_type, f"unknown_{colour_type}"),
        "interlace": interlace,
        "compression": compression,
        "filter_method": filter_method,
    }


def walk_coords(geometry: dict[str, Any]) -> Iterable[tuple[float, float]]:
    def rec(obj: Any) -> Iterable[tuple[float, float]]:
        if isinstance(obj, (list, tuple)):
            if len(obj) == 2 and all(isinstance(x, (int, float)) for x in obj):
                yield float(obj[0]), float(obj[1])
            else:
                for item in obj:
                    yield from rec(item)

    yield from rec(geometry.get("coordinates"))


def json_dump(path: pathlib.Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()

    repo = args.repo_root.resolve()
    packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"
    image_dir = packet / "primary/images"
    geo_dir = packet / "adjudicated/geojson"
    manifest_path = packet / "adjudicated/adjudicated_manifest.json"
    primary_freeze_path = packet / "primary/primary_role_freeze_manifest.json"
    transition_manifest_path = packet / "adjudicated_transitions/transition_manifest.json"
    baseline_manifest_path = packet / "frozen_baselines/baseline_manifest.json"

    manifest = json.loads(manifest_path.read_text())
    primary_freeze = json.loads(primary_freeze_path.read_text())
    transition_manifest = json.loads(transition_manifest_path.read_text())
    baseline_manifest = json.loads(baseline_manifest_path.read_text())
    expected_images = {x["blind_id"]: x for x in primary_freeze["files"]}
    # The adjudicated manifest stores paths relative to its own `adjudicated/`
    # directory, while this audit indexes files relative to the packet root.
    expected_labels = {str(pathlib.Path("adjudicated") / x["file"]): x for x in manifest["files"]}

    images = sorted(image_dir.glob("P*.png"))
    labels = sorted(geo_dir.glob("*.geojson"))
    image_rows = []
    image_issues = []
    for path in images:
        blind_id = path.stem
        digest = sha256(path)
        meta = png_metadata(path)
        row = {"file": str(path.relative_to(packet)), "blind_id": blind_id, "sha256": digest, **meta}
        image_rows.append(row)
        expected = expected_images.get(blind_id)
        if expected is None or expected.get("image_sha256") != digest:
            image_issues.append({"blind_id": blind_id, "reason": "image_hash_not_in_primary_freeze"})
        if (meta["width"], meta["height"], meta["bit_depth"], meta["colour_type"]) != (1524, 500, 8, 0):
            image_issues.append({"blind_id": blind_id, "reason": "unexpected_png_metadata", "metadata": meta})

    type_counts = collections.Counter()
    family_counts = collections.Counter()
    section_counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    coordinate_reference = collections.Counter()
    coordinate_values: list[tuple[float, float]] = []
    label_issues = []
    mapping_rows = []
    for path in labels:
        rel = str(path.relative_to(packet))
        digest = sha256(path)
        data = json.loads(path.read_text())
        expected = expected_labels.get(rel)
        if expected is None or expected.get("sha256") != digest:
            label_issues.append({"file": rel, "reason": "label_hash_not_in_adjudicated_manifest"})
        ref = data.get("coordinate_reference")
        coordinate_reference[json.dumps(ref, sort_keys=True)] += 1
        props = data.get("properties") or {}
        asset_key = props.get("asset_key")
        blind_id = props.get("primary_blind_id")
        if not asset_key or not blind_id:
            label_issues.append({"file": rel, "reason": "missing_deterministic_asset_or_image_mapping"})
        mapping_rows.append({"label_file": rel, "asset_key": asset_key, "primary_blind_id": blind_id, "image_file": f"primary/images/{blind_id}.png" if blind_id else None})
        section = props.get("section") or (asset_key or "MISSING").split("|")[0]
        for feature in data.get("features", []):
            geom = feature.get("geometry") or {}
            typ = geom.get("type")
            family = (feature.get("properties") or {}).get("distress_family") or "MISSING"
            type_counts[typ] += 1
            family_counts[family] += 1
            section_counts[section][family] += 1
            for x, y in walk_coords(geom):
                coordinate_values.append((x, y))
                if not (math.isfinite(x) and math.isfinite(y)):
                    label_issues.append({"file": rel, "reason": "nonfinite_coordinate", "x": x, "y": y})
                if not (0.0 <= x <= 15.2400001 and 0.0 <= y <= 5.0000001):
                    label_issues.append({"file": rel, "reason": "coordinate_outside_declared_frame", "x": x, "y": y})
                if typ not in {"LineString", "Polygon"}:
                    label_issues.append({"file": rel, "reason": "unsupported_geometry_type", "type": typ})

    sections = sorted(section_counts)
    loso = [x for x in baseline_manifest["split_receipts"] if x.get("axis") == "leave_one_section_out"]
    folds = [{"fold": x["fold"], "held_out_section": x["held_out_section"], "test_transition_count": len(x["test_transition_ids"])} for x in loso]
    primary_confounders = {k: v for k, v in primary_freeze["family_counts"].items() if k in {
        "handwritten_code_or_calculation", "lane_or_reference_boundary", "other_noncrack_distress", "water_bleeding_and_pumping", "uncertain"
    }}
    confounder_inventory = {
        "handwriting": {"count": primary_confounders.get("handwritten_code_or_calculation", 0), "source": "primary role lock manifest"},
        "frame_or_road_boundaries": {"count": primary_confounders.get("lane_or_reference_boundary", 0), "source": "primary role lock manifest; frame itself not separately coded"},
        "other_distress": {"count": manifest["family_counts"].get("other_noncrack_distress", 0), "source": "adjudicated manifest"},
        "water_bleeding_and_pumping": {"count": manifest["family_counts"].get("water_bleeding_and_pumping", 0), "source": "adjudicated manifest"},
        "grid": {"count": None, "status": "present_in_source_but_not_independently enumerated in frozen label schema"},
        "arrows_or_dimensions": {"count": None, "status": "present_in_source but not independently enumerated in frozen label schema"},
        "wim_or_patch_boxes": {"count": None, "status": "present in source; semantic adjudication notes exist but no complete category count"},
        "hatching_or_x_symbols": {"count": None, "status": "present in source but not independently enumerated in frozen label schema"},
    }
    report = {
        "status": "PASS_STAGE1_READ_ONLY" if not image_issues and not label_issues and len(images) == 37 and len(labels) == 37 else "BLOCKED_BEFORE_FIT",
        "claim_boundary": "Current-map crack geometry recognition only; no future-map forecast, material-point identity, physical width, or spatial-registration claim.",
        "packet": str(packet),
        "manifest_status": manifest["status"],
        "manifest_sha256": sha256(manifest_path),
        "image_count": len(images),
        "label_count": len(labels),
        "image_metadata_summary": {"dimensions": "1524x500", "bit_depth": 8, "mode": "grayscale", "all_identical": len({(x["width"], x["height"], x["bit_depth"], x["colour_type"]) for x in image_rows}) == 1},
        "images": image_rows,
        "image_issues": image_issues,
        "label_issues": label_issues,
        "label_geometry_types": dict(type_counts),
        "label_family_counts": dict(family_counts),
        "section_family_counts": {k: dict(v) for k, v in sorted(section_counts.items())},
        "coordinate_reference_values": [json.loads(k) for k in coordinate_reference],
        "coordinate_range": {"x_min": min((x for x, _ in coordinate_values), default=None), "x_max": max((x for x, _ in coordinate_values), default=None), "y_min": min((y for _, y in coordinate_values), default=None), "y_max": max((y for _, y in coordinate_values), default=None)},
        "rasterization": {"status": "PASS" if not label_issues else "FAIL", "image_frame": [0, 0, 15.24, 5.0], "pixel_scale": "100 px per metre", "origin": "lower_left physical frame; image row orientation must be inverted at render time"},
        "image_label_mapping": {"status": "PASS" if not any(x.get("reason") == "missing_deterministic_asset_or_image_mapping" for x in label_issues) else "FAIL", "rows": mapping_rows, "uses_currently_sealed_mapping": False, "basis": "primary_blind_id and asset_key embedded in locked adjudicated GeoJSON properties; image hashes verified against primary role lock"},
        "sections": sections,
        "loso_folds": folds,
        "transition_manifest": {"status": transition_manifest["status"], "section_count": transition_manifest["section_count"], "state_count": transition_manifest["state_count"], "transition_count": transition_manifest["transition_count"], "development_transition_count": transition_manifest["development_transition_count"], "future_time_test_transition_count": transition_manifest["future_time_test_transition_count"]},
        "confounder_inventory": confounder_inventory,
        "mutability_checks": {"frozen_manifest_status": manifest["status"], "all_manifest_hashes_match": not label_issues, "all_image_hashes_match": not image_issues, "sealed_mapping_opened": False},
        "next_gate": "Create canonical track and preregistration; freeze B0 protocol only after explicitly recording the unenumerated confounder categories and their treatment.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    json_dump(args.output / "stage1_read_only_audit.json", report)
    (args.output / "stage1_read_only_audit.md").write_text(render_markdown(report))
    json_dump(args.output / "input_receipt.json", {"manifest": {"path": str(manifest_path), "sha256": sha256(manifest_path)}, "images": image_rows, "labels": [{"file": x["file"], "sha256": x["sha256"]} for x in manifest["files"]]})
    return 0 if report["status"] == "PASS_STAGE1_READ_ONLY" else 2


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# LTPP crack-recognition Stage 1 read-only qualification",
        "",
        f"Status: `{report['status']}`",
        "",
        report["claim_boundary"],
        "",
        "## Deterministic inputs",
        "",
        f"- Images: {report['image_count']} files; all `{report['image_metadata_summary']['dimensions']}`, 8-bit grayscale; image and label hash checks: `{not report['image_issues'] and not report['label_issues']}`.",
        f"- Adjudicated manifest: `{report['manifest_status']}`; SHA-256 `{report['manifest_sha256']}`.",
        f"- Labels: {report['label_count']} GeoJSON FeatureCollections; geometry types `{report['label_geometry_types']}`; coordinate range `{report['coordinate_range']}`.",
        f"- Rasterization: `{report['rasterization']['status']}`; declared physical frame `[0,0,15.24,5.0] m`; 100 px/m.",
        f"- Image-label mapping: `{report['image_label_mapping']['status']}` from locked GeoJSON `primary_blind_id` + `asset_key`; sealed mapping opened: `{report['image_label_mapping']['uses_currently_sealed_mapping']}`.",
        "",
        "## Gold families",
        "",
        f"- Pooled: `{report['label_family_counts']}`.",
        "- Section counts:",
    ]
    for sec, counts in report["section_family_counts"].items():
        lines.append(f"  - `{sec}`: `{counts}`")
    lines += ["", "## Exact LOSO folds", ""]
    for fold in report["loso_folds"]:
        lines.append(f"- `{fold['fold']}` holds out `{fold['held_out_section']}` with {fold['test_transition_count']} transitions.")
    lines += ["", "## Confounder inventory", "", "Counts are only claimed where the frozen label schema independently records them."]
    for name, value in report["confounder_inventory"].items():
        if value.get("count") is None:
            lines.append(f"- `{name}`: count not independently enumerated; {value['status']}.")
        else:
            lines.append(f"- `{name}`: {value['count']} ({value['source']}).")
    lines += ["", "## Gate result", "", f"No image/label hash, mapping, coordinate, or rasterization issue was found: `{not report['image_issues'] and not report['label_issues']}`.", "", report["next_gate"], ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
