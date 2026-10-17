#!/usr/bin/env python3
"""Build HOLD-only blind Tier B review packets for frozen cross-state candidates.

The automatic grid rectangle is used only to choose an unrectified evidence
window. It is never an audit control and cannot contribute to a residual.
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


FINAL = ((0, 0), (10, 0), (0, 5), (10, 5), (2, 2), (8, 2), (2, 3), (8, 3))
DEVELOPMENT = ((5, 0), (5, 5), (0, 2), (0, 3), (10, 2), (10, 3), (3, 1), (7, 4))
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


def crop_bounds(row: dict, shape: tuple[int, ...]) -> tuple[int, int, int, int]:
    height, width = shape[:2]
    values = [float(row[key]) for key in ("x0", "y0", "x1", "y1")]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("grid-window coordinates must be finite")
    x0, y0, x1, y1 = values
    if not (x0 < x1 and y0 < y1):
        raise ValueError("grid-window coordinates are unordered")
    left = max(0, math.floor(x0) - MARGIN_PX)
    top = max(0, math.floor(y0) - MARGIN_PX)
    right = min(width, math.ceil(x1) + MARGIN_PX + 1)
    bottom = min(height, math.ceil(y1) + MARGIN_PX + 1)
    if right - left < 100 or bottom - top < 100:
        raise ValueError("grid-window crop is implausibly small")
    return left, top, right, bottom


def blank_record(blind_map_id: str, task_order: list[str]) -> dict:
    return {
        "schema_version": "ltpp_cross_state_registration_tier_b_review_v1",
        "packet_status": STATUS,
        "blind_map_id": blind_map_id,
        "locked": False,
        "other_maps_seen": False,
        "prior_registration_outcomes_seen": False,
        "tasks": {
            candidate: {"status": None, "click_crop_px": None, "note": ""}
            for candidate in task_order
        },
    }


def load_rows(project_root: Path, gate_specs: list[tuple[Path, str, int]]) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    receipts: list[dict] = []
    for gate_path, expected_section, expected_count in gate_specs:
        gate_hash = sha256(gate_path)
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        results = gate.get("results", [])
        if gate.get("section") != expected_section:
            raise ValueError(f"section mismatch in {gate_path}")
        if gate.get("all_passed") is not True or gate.get("passed") != expected_count or len(results) != expected_count:
            raise ValueError(f"exact all-date pass inventory required for {expected_section}")
        if any(result.get("passed") is not True for result in results):
            raise ValueError(f"non-passing date found for {expected_section}")
        for result in results:
            source = Path(result["source_path"])
            if not source.is_absolute():
                source = project_root / source
            source = source.resolve()
            if sha256(source) != result["source_sha256"]:
                raise ValueError(f"source hash mismatch: {expected_section} {result['survey_date']}")
            rows.append({**result, "section": expected_section, "source_path": str(source)})
        receipts.append({
            "section": expected_section,
            "dates": [row["survey_date"] for row in results],
            "grid_gate_path": str(gate_path.resolve()),
            "grid_gate_sha256": gate_hash,
            "expected_count": expected_count,
        })
    keys = {(row["section"], row["survey_date"]) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("duplicate section-date key")
    return rows, receipts


def build_role_packet(role: str, rows: list[dict], packet: Path, seed: int) -> list[dict]:
    role_root = packet / role
    images = role_root / "images"
    records = role_root / "records"
    images.mkdir(parents=True)
    records.mkdir()
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    mapping = []
    prefix = role[-1].upper()
    for index, row in enumerate(shuffled, start=1):
        blind_map_id = f"{prefix}{index:02d}"
        source = Path(row["source_path"])
        image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot read source image: {source}")
        left, top, right, bottom = crop_bounds(row, image.shape)
        target = images / f"{blind_map_id}.png"
        if not cv2.imwrite(str(target), image[top:bottom, left:right]):
            raise ValueError(f"cannot write packet image: {target}")
        task_order = candidates()
        random.Random(seed + index * 97).shuffle(task_order)
        record_path = records / f"{blind_map_id}.json"
        record_path.write_text(
            json.dumps(blank_record(blind_map_id, task_order), indent=2) + "\n",
            encoding="utf-8",
        )
        mapping.append({
            "blind_map_id": blind_map_id,
            "section": row["section"],
            "survey_date": row["survey_date"],
            "source_path": str(source),
            "source_sha256": sha256(source),
            "automatic_window_source_px": {
                key: row[key] for key in ("x0", "y0", "x1", "y1")
            },
            "crop_source_px": {"left": left, "top": top, "right": right, "bottom": bottom},
            "packet_image": f"{role}/images/{blind_map_id}.png",
            "packet_image_sha256": sha256(target),
            "task_order": task_order,
        })
    (role_root / "README.md").write_text(
        "# Blind cross-state Tier B packet — HOLD\n\n"
        f"Status: `{STATUS}`. Do not open the annotation UI, edit records, or annotate before written external approval.\n\n"
        "After approval, follow the frozen Tier B protocol and use printed grid/frame/tick ink only. "
        "Never use cracks, handwriting, WIM, repairs, distress marks, circles, or arrows. "
        "Inspect one blind map at a time; do not compare maps.\n",
        encoding="utf-8",
    )
    return mapping


def write_manifest(root: Path, destination: Path, paths: list[Path]) -> None:
    destination.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in sorted(paths)),
        encoding="ascii",
    )


def run(
    project_root: Path,
    gate_specs: list[tuple[Path, str, int]],
    protocol: Path,
    amendment: Path,
    output: Path,
    seed: int,
) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite packet root: {output}")
    rows, gate_receipts = load_rows(project_root, gate_specs)
    output.mkdir(parents=True)
    a_mapping = build_role_packet("annotator_a", rows, output, seed)
    b_mapping = build_role_packet("annotator_b", rows, output, seed + 1)
    sealed = output / "custodian_sealed_do_not_open"
    sealed.mkdir()
    mapping_path = sealed / "blind_mapping_and_roles.json"
    mapping_path.write_text(json.dumps({
        "schema_version": "ltpp_cross_state_registration_tier_b_custodian_v1",
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "gate_receipts": gate_receipts,
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
        "sections": sorted({row["section"] for row in rows}),
        "maps_per_annotator": len(rows),
        "candidates_per_map": len(candidates()),
        "crop_margin_source_px": MARGIN_PX,
        "gate_receipts": gate_receipts,
        "protocol_sha256": sha256(protocol),
        "amendment_sha256": sha256(amendment),
        "all_records_empty_unlocked": True,
        "annotation_authorized": False,
        "consensus_authorized": False,
        "transform_fit_authorized": False,
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


def parse_gate_spec(value: str) -> tuple[Path, str, int]:
    path, section, count = value.rsplit("::", 2)
    return Path(path).resolve(), section, int(count)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--gate", action="append", type=parse_gate_spec, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--amendment", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260812)
    args = parser.parse_args()
    summary = run(
        args.project_root.resolve(), args.gate, args.protocol.resolve(),
        args.amendment.resolve(), args.output_root.resolve(), args.seed,
    )
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
