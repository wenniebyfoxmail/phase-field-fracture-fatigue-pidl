#!/usr/bin/env python3
"""Prepare independent blind annotation packets for qualified LTPP maps."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_SECTION_COUNT = 6
EXPECTED_MAP_COUNT = 37
EXTENT_M = [0.0, 0.0, 15.24, 5.0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_qualified_maps(gate_path: Path, project_root: Path) -> list[dict]:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    sections: set[str] = set()
    for candidate in gate.get("candidates", []):
        if not candidate.get("passes_minimum_geometry_climate_gate"):
            continue
        section = str(candidate["section"])
        sections.add(section)
        rectification_result = project_root / candidate["rectification_result"]
        rectification_root = rectification_result.parent
        for survey_date in candidate["climate_complete_prefix_dates"]:
            compact_date = survey_date.replace("-", "")
            source = rectification_root / compact_date / "rectified_grid.png"
            if not source.is_file():
                raise SystemExit(f"missing qualified image: {source}")
            rows.append(
                {
                    "asset_key": f"{section}|{candidate['construction_number']}|0|{survey_date}",
                    "section": section,
                    "construction_number": int(candidate["construction_number"]),
                    "panel_start_ft": 0,
                    "panel_end_ft": 50,
                    "survey_date": survey_date,
                    "source_path": str(source.resolve()),
                    "source_sha256": sha256(source),
                }
            )
    if len(sections) != EXPECTED_SECTION_COUNT or len(rows) != EXPECTED_MAP_COUNT:
        raise SystemExit(
            "qualified inventory mismatch: "
            f"expected {EXPECTED_SECTION_COUNT} sections/{EXPECTED_MAP_COUNT} maps, "
            f"found {len(sections)} sections/{len(rows)} maps"
        )
    asset_keys = [row["asset_key"] for row in rows]
    if len(asset_keys) != len(set(asset_keys)):
        raise SystemExit("qualified inventory contains duplicate asset keys")
    return sorted(rows, key=lambda row: row["asset_key"])


def blank_geojson(blind_id: str, role: str, image_name: str) -> dict:
    return {
        "type": "FeatureCollection",
        "name": f"ltpp_geoforecast_{role}_{blind_id}",
        "schema_version": "line_area_v3",
        "coordinate_reference": {
            "origin": "lower_left",
            "units": "metres",
            "extent": EXTENT_M,
            "image_to_physical": {
                "x_m": "x_pixel / 100",
                "y_m": "(500 - y_pixel) / 100",
            },
        },
        "properties": {
            "blind_map_id": blind_id,
            "annotator_role": role,
            "source_image": image_name,
            "locked": False,
            "automatic_candidates_seen": False,
            "other_dates_seen": False,
        },
        "features": [],
    }


def make_role_packet(
    role: str,
    inventory: list[dict],
    output_root: Path,
    seed: int,
) -> list[dict]:
    role_root = output_root / role
    image_root = role_root / "images"
    label_root = role_root / "geojson"
    image_root.mkdir(parents=True, exist_ok=False)
    label_root.mkdir(parents=True, exist_ok=False)
    shuffled = list(inventory)
    random.Random(seed).shuffle(shuffled)
    mapping = []
    prefix = "P" if role == "primary" else "S"
    for index, row in enumerate(shuffled, start=1):
        blind_id = f"{prefix}{index:03d}"
        source = Path(row["source_path"])
        image_name = f"{blind_id}.png"
        destination = image_root / image_name
        shutil.copyfile(source, destination)
        template = blank_geojson(blind_id, role, image_name)
        (label_root / f"{blind_id}.geojson").write_text(
            json.dumps(template, indent=2) + "\n", encoding="utf-8"
        )
        mapping.append(
            {
                "blind_id": blind_id,
                **row,
                "packet_image_sha256": sha256(destination),
            }
        )
    readme = """# Blind semantic-vectorization packet

Annotate only the image matching the blind ID. Do not open the other role,
the sealed directory, automatic candidate overlays, or chronological maps.

Trace visible crack centrelines in metres. Trace an area only when the source
explicitly maps an areal distress. Mark genuinely unresolved strokes as
`uncertain`; do not infer geometry from another survey. Grid, frames, road
boundaries, labels, circles, and calculations are not cracks. If a confusable
non-crack stroke needs an explicit disposition, use the matching non-crack
category. Set `locked=true` only after the map has been reviewed completely.

Coordinates use `x_m=x_pixel/100` and `y_m=(500-y_pixel)/100`.
"""
    (role_root / "README.md").write_text(readme, encoding="utf-8")
    return mapping


def write_hash_manifest(root: Path, name: str, paths: list[Path]) -> None:
    with (root / name).open("w", encoding="ascii") as handle:
        for path in sorted(paths):
            handle.write(f"{sha256(path)}  {path.relative_to(root)}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-json", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260805)
    args = parser.parse_args()

    if args.output_root.exists():
        raise SystemExit(f"refusing to overwrite packet root: {args.output_root}")
    inventory = load_qualified_maps(args.gate_json.resolve(), args.project_root.resolve())
    args.output_root.mkdir(parents=True)
    primary_mapping = make_role_packet("primary", inventory, args.output_root, args.seed)
    secondary_mapping = make_role_packet(
        "secondary", inventory, args.output_root, args.seed + 1
    )
    sealed_root = args.output_root / "sealed_do_not_open_during_annotation"
    sealed_root.mkdir()
    mapping_payload = {
        "contract": "ltpp_geoforecast_semantic_vectorization_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "source_gate": str(args.gate_json.resolve()),
        "source_gate_sha256": sha256(args.gate_json),
        "expected_sections": EXPECTED_SECTION_COUNT,
        "expected_maps_per_role": EXPECTED_MAP_COUNT,
        "unseal_condition": "both independent annotation passes locked",
        "primary": primary_mapping,
        "secondary": secondary_mapping,
    }
    mapping_path = sealed_root / "blind_id_asset_mapping.json"
    mapping_path.write_text(json.dumps(mapping_payload, indent=2) + "\n", encoding="utf-8")

    image_paths = list(args.output_root.glob("*/images/*.png"))
    template_paths = list(args.output_root.glob("*/geojson/*.geojson"))
    write_hash_manifest(args.output_root, "input_images.sha256", image_paths)
    write_hash_manifest(args.output_root, "initial_label_templates.sha256", template_paths)
    write_hash_manifest(args.output_root, "sealed_mapping.sha256", [mapping_path])
    print(
        json.dumps(
            {
                "status": "packet_frozen",
                "sections": EXPECTED_SECTION_COUNT,
                "primary_maps": len(primary_mapping),
                "secondary_maps": len(secondary_mapping),
                "mapping_status": "sealed",
                "seed": args.seed,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
