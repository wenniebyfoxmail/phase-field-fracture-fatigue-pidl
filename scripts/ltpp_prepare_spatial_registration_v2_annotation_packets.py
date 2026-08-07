#!/usr/bin/env python3
"""Create sealed, blind Tier B printed-grid annotation packets for v2.

This is availability work only. It creates no transform, reads no crack label,
and keeps the date mapping and final-control roles in a custodian-only folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

import cv2


DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
FINAL = ((0, 0), (10, 0), (0, 5), (10, 5), (2, 2), (8, 2), (2, 3), (8, 3))
DEVELOPMENT = ((5, 0), (5, 5), (0, 2), (0, 3), (10, 2), (10, 3), (3, 1), (7, 4))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_id(i: int, j: int) -> str:
    return f"G[{i},{j}]"


def candidates() -> list[str]:
    return [candidate_id(i, j) for j in range(6) for i in range(11)]


def role_for(candidate: str) -> str:
    if candidate in {candidate_id(i, j) for i, j in FINAL}:
        return "final_audit"
    if candidate in {candidate_id(i, j) for i, j in DEVELOPMENT}:
        return "development"
    return "fit"


def crop_bounds(row: dict, shape: tuple[int, int]) -> tuple[int, int, int, int]:
    """Return the visible printed map rectangle without using individual candidates."""
    height, width = shape
    left = max(0, int(row["x0"]))
    top = max(0, int(row["y0"]))
    right = min(width, int(row["x1"]) + 1)
    bottom = min(height, int(row["y1"]) + 1)
    if right - left < 100 or bottom - top < 100:
        raise ValueError("invalid printed-map crop bounds")
    return left, top, right, bottom


def blank_record(blind_map_id: str, candidates_for_map: list[str]) -> dict:
    return {
        "schema_version": "ltpp_spatial_registration_tier_b_v1",
        "blind_map_id": blind_map_id,
        "locked": False,
        "other_dates_seen": False,
        "v1_candidates_seen": False,
        "tasks": {
            candidate: {"status": None, "click_crop_px": None, "note": ""}
            for candidate in candidates_for_map
        },
    }


def build_role_packet(
    role: str,
    source_rows: list[dict],
    output_root: Path,
    seed: int,
) -> list[dict]:
    role_root = output_root / role
    images = role_root / "images"
    records = role_root / "records"
    images.mkdir(parents=True)
    records.mkdir()
    shuffled = list(source_rows)
    random.Random(seed).shuffle(shuffled)
    mapping = []
    for index, row in enumerate(shuffled, start=1):
        blind_map_id = f"{role[-1].upper()}{index:02d}"
        source = Path(row["source_path"])
        image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot read source image: {source}")
        left, top, right, bottom = crop_bounds(row, image.shape)
        cropped = image[top:bottom, left:right]
        image_name = f"{blind_map_id}.png"
        target_image = images / image_name
        if not cv2.imwrite(str(target_image), cropped):
            raise ValueError(f"cannot write packet image: {target_image}")
        task_order = candidates()
        random.Random(seed + index * 97).shuffle(task_order)
        (records / f"{blind_map_id}.json").write_text(
            json.dumps(blank_record(blind_map_id, task_order), indent=2) + "\n",
            encoding="utf-8",
        )
        mapping.append({
            "blind_map_id": blind_map_id,
            "survey_date": row["survey_date"],
            "source_path": str(source.resolve()),
            "source_sha256": sha256(source),
            "crop_source_px": {"left": left, "top": top, "right": right, "bottom": bottom},
            "packet_image": f"{role}/images/{image_name}",
            "packet_image_sha256": sha256(target_image),
            "task_order": task_order,
        })
    (role_root / "README.md").write_text(
        "# Blind Tier B printed-grid packet\n\n"
        "Annotate the visible printed grid only. Do not use handwriting, distress, WIM, repair, circles, arrows, or another date. "
        "A candidate is usable only when the protocol's four 12-pixel printed-stroke arms are visible. Lock only after all 66 candidates have one status.\n",
        encoding="utf-8",
    )
    return mapping


def write_manifest(root: Path, filename: str, paths: list[Path]) -> None:
    with (root / filename).open("w", encoding="ascii") as handle:
        for path in sorted(paths):
            handle.write(f"{sha256(path)}  {path.relative_to(root)}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-results", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260807)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite packet root: {output_root}")
    grid_results = args.grid_results.resolve()
    protocol = args.protocol.resolve()
    gate = json.loads(grid_results.read_text(encoding="utf-8"))
    rows = {row["survey_date"]: row for row in gate["results"]}
    if any(date not in rows for date in DATES):
        raise SystemExit("the exact frozen eight-date receipt is required")
    source_rows = [rows[date] for date in DATES]
    output_root.mkdir(parents=True)
    a_mapping = build_role_packet("annotator_a", source_rows, output_root, args.seed)
    b_mapping = build_role_packet("annotator_b", source_rows, output_root, args.seed + 1)
    sealed = output_root / "custodian_sealed_do_not_open"
    sealed.mkdir()
    sealed_payload = {
        "schema_version": "ltpp_spatial_registration_tier_b_custodian_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "grid_results": str(grid_results),
        "grid_results_sha256": sha256(grid_results),
        "protocol": str(protocol),
        "protocol_sha256": sha256(protocol),
        "candidate_roles": {candidate: role_for(candidate) for candidate in candidates()},
        "annotator_a": a_mapping,
        "annotator_b": b_mapping,
        "unseal_condition": "both roles locked; consensus run by the annotation custodian only",
    }
    mapping_path = sealed / "blind_mapping_and_roles.json"
    mapping_path.write_text(json.dumps(sealed_payload, indent=2) + "\n", encoding="utf-8")
    public_files = list(output_root.glob("annotator_*/images/*.png")) + list(output_root.glob("annotator_*/records/*.json")) + list(output_root.glob("annotator_*/README.md"))
    write_manifest(output_root, "public_packet_manifest.sha256", public_files)
    write_manifest(sealed, "sealed_manifest.sha256", [mapping_path])
    print(json.dumps({
        "status": "TIER_B_BLIND_PACKETS_FROZEN",
        "maps_per_annotator": len(source_rows),
        "candidates_per_map": len(candidates()),
        "sealed_mapping": "custodian_sealed_do_not_open/blind_mapping_and_roles.json",
        "authorization": "availability_and_adjudication_only",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
