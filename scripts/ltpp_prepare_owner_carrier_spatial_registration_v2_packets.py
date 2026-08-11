#!/usr/bin/env python3
"""Build review-candidate blind Tier B packets from locked owner source windows.

The owner corners select only an unrectified source crop. They never become
fit, development, or final audit controls. Annotation is forbidden until the
source-window amendment receives external approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

import cv2


DATES = (
    "19910610", "19951024", "19970228", "19980407",
    "20010913", "20030514", "20071106", "20120417",
)
FINAL = ((0, 0), (10, 0), (0, 5), (10, 5), (2, 2), (8, 2), (2, 3), (8, 3))
DEVELOPMENT = ((5, 0), (5, 5), (0, 2), (0, 3), (10, 2), (10, 3), (3, 1), (7, 4))
EXPECTED_OWNER_SHA256 = "3f86fc7c0d28d578387d5e8d99295faf8e9bc4d45e437f4d1e181940e96a4803"
EXPECTED_OWNER_MANIFEST_SHA256 = "b609aba4d3026929e8120e06ae81116cdbf1e1e898f64b403a564cacab8233f2"
MARGIN_PX = 48
STATUS = "PENDING_EXTERNAL_REVIEW__DO_NOT_ANNOTATE"


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


def crop_bounds(points: list[list[float]], shape: tuple[int, ...]) -> tuple[int, int, int, int]:
    if len(points) != 4 or any(len(point) != 2 for point in points):
        raise ValueError("exactly four two-dimensional owner points are required")
    height, width = shape[:2]
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    if not all(math.isfinite(value) for value in xs + ys):
        raise ValueError("owner points must be finite")
    left = max(0, math.floor(min(xs)) - MARGIN_PX)
    top = max(0, math.floor(min(ys)) - MARGIN_PX)
    right = min(width, math.ceil(max(xs)) + MARGIN_PX + 1)
    bottom = min(height, math.ceil(max(ys)) + MARGIN_PX + 1)
    if right - left < 100 or bottom - top < 100:
        raise ValueError("owner-carrier crop is implausibly small")
    return left, top, right, bottom


def blank_record(blind_map_id: str, task_order: list[str]) -> dict:
    return {
        "schema_version": "ltpp_spatial_registration_tier_b_owner_carrier_v2",
        "packet_status": STATUS,
        "blind_map_id": blind_map_id,
        "locked": False,
        "other_dates_seen": False,
        "v1_candidates_seen": False,
        "tasks": {
            candidate: {"status": None, "click_crop_px": None, "note": ""}
            for candidate in task_order
        },
    }


def build_role_packet(role: str, rows: list[dict], packet: Path, seed: int) -> list[dict]:
    role_root = packet / role
    images = role_root / "images"
    records = role_root / "records"
    images.mkdir(parents=True)
    records.mkdir()
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    mapping = []
    for index, row in enumerate(shuffled, start=1):
        blind_map_id = f"{role[-1].upper()}{index:02d}"
        source = Path(row["source_path"])
        image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot read source image: {source}")
        left, top, right, bottom = crop_bounds(row["points_source_px"], image.shape)
        target = images / f"{blind_map_id}.png"
        if not cv2.imwrite(str(target), image[top:bottom, left:right]):
            raise ValueError(f"cannot write packet image: {target}")
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
            "packet_image": f"{role}/images/{blind_map_id}.png",
            "packet_image_sha256": sha256(target),
            "task_order": task_order,
        })
    (role_root / "README.md").write_text(
        "# Blind Tier B owner-carrier packet — HOLD\n\n"
        "Status: `PENDING_EXTERNAL_REVIEW__DO_NOT_ANNOTATE`. Do not open the annotation UI or edit/lock records before written external approval.\n\n"
        "After approval, annotate printed grid/frame/tick ink only under the frozen Tier B protocol. "
        "Never use cracks, handwriting, WIM, repairs, distress marks, circles, or arrows. "
        "`G[i,j]` has i=0 at the printed left frame and i=10 at the printed right frame; "
        "j=0 is the printed bottom frame and j=5 is the printed top frame.\n",
        encoding="utf-8",
    )
    return mapping


def write_manifest(root: Path, destination: Path, paths: list[Path]) -> None:
    destination.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in sorted(paths)),
        encoding="ascii",
    )


def run(owner_packet: Path, protocol: Path, amendment: Path, output: Path, seed: int) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite packet root: {output}")
    owner_file = owner_packet / "owner_corners.json"
    owner_manifest = owner_packet / "manifest.sha256"
    if sha256(owner_file) != EXPECTED_OWNER_SHA256 or sha256(owner_manifest) != EXPECTED_OWNER_MANIFEST_SHA256:
        raise ValueError("owner packet receipt does not match the frozen amendment")
    owner = json.loads(owner_file.read_text(encoding="utf-8"))
    records = {row["survey_date"]: row for row in owner.get("records", [])}
    if tuple(records) != DATES or any(not records[date].get("locked") for date in DATES):
        raise ValueError("exact locked eight-date owner packet is required")
    rows = []
    for date in DATES:
        record = records[date]
        source = owner_packet / "images" / f"{date}.png"
        if sha256(source) != record["source_sha256"]:
            raise ValueError(f"source hash mismatch: {date}")
        rows.append({**record, "source_path": str(source.resolve())})
    output.mkdir(parents=True)
    a_mapping = build_role_packet("annotator_a", rows, output, seed)
    b_mapping = build_role_packet("annotator_b", rows, output, seed + 1)
    sealed = output / "custodian_sealed_do_not_open"
    sealed.mkdir()
    mapping_path = sealed / "blind_mapping_and_roles.json"
    mapping_path.write_text(json.dumps({
        "schema_version": "ltpp_spatial_registration_tier_b_owner_carrier_custodian_v2",
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "owner_corners_sha256": sha256(owner_file),
        "owner_manifest_sha256": sha256(owner_manifest),
        "protocol": str(protocol.resolve()),
        "protocol_sha256": sha256(protocol),
        "amendment": str(amendment.resolve()),
        "amendment_sha256": sha256(amendment),
        "crop_margin_source_px": MARGIN_PX,
        "candidate_roles": {candidate: role_for(candidate) for candidate in candidates()},
        "annotator_a": a_mapping,
        "annotator_b": b_mapping,
        "unseal_condition": "external amendment approval plus both eligible roles locked; custodian only",
    }, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": STATUS,
        "maps_per_annotator": len(rows),
        "candidates_per_map": len(candidates()),
        "crop_margin_source_px": MARGIN_PX,
        "owner_corners_sha256": sha256(owner_file),
        "owner_manifest_sha256": sha256(owner_manifest),
        "protocol_sha256": sha256(protocol),
        "amendment_sha256": sha256(amendment),
        "all_records_empty_unlocked": True,
        "annotation_authorized": False,
        "consensus_authorized": False,
        "final_gate_run": False,
    }
    status_path = output / "packet_status.json"
    status_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    public_files = (
        list(output.glob("annotator_*/images/*.png"))
        + list(output.glob("annotator_*/records/*.json"))
        + list(output.glob("annotator_*/README.md"))
        + [status_path]
    )
    write_manifest(output, output / "public_packet_manifest.sha256", public_files)
    write_manifest(sealed, sealed / "sealed_manifest.sha256", [mapping_path])
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-packet", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--amendment", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260807)
    args = parser.parse_args()
    summary = run(
        args.owner_packet.resolve(), args.protocol.resolve(), args.amendment.resolve(),
        args.output_root.resolve(), args.seed,
    )
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
