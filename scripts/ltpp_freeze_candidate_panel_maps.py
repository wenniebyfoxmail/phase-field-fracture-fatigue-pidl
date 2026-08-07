#!/usr/bin/env python3
"""Freeze the first fixed 50-ft panel for ranked InfoPave candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url: str, destination: Path, timeout: float) -> None:
    request = urllib.request.Request(
        url, headers={"User-Agent": "ltpp-geo-forecast-panel-freeze/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        destination.write_bytes(response.read())


def composite_on_white(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        white.convert("RGB").save(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--candidate-start", type=int, default=0)
    parser.add_argument("--candidate-count", type=int, default=7)
    parser.add_argument("--panel-index", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    audit_path = args.audit_root / "candidate_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        requested = {row["section"] for row in config["candidates"]}
        by_section = {row["section"]: row for row in audit["passing_candidates"]}
        missing = sorted(requested - set(by_section))
        if missing:
            raise RuntimeError(f"Configured sections missing from audit: {missing}")
        candidates = [by_section[row["section"]] for row in config["candidates"]]
    else:
        candidates = audit["passing_candidates"][
            args.candidate_start : args.candidate_start + args.candidate_count
        ]
    records = []
    for candidate in candidates:
        section = candidate["section"]
        viewer_path = args.audit_root / "distress_viewer" / f"{section}.json"
        viewer = json.loads(viewer_path.read_text(encoding="utf-8"))
        passing_numbers = set(candidate["passing_construction_numbers"])
        for construction in viewer.get("ConstructionDateList") or []:
            if construction.get("ConstructionNumber") not in passing_numbers:
                continue
            for survey in construction.get("Surveys") or []:
                items = survey.get("DistressItems") or []
                if not items:
                    continue
                if args.panel_index >= len(items):
                    raise RuntimeError(
                        f"{section} {survey['SurveyDate']} has only {len(items)} panels"
                    )
                selected = items[args.panel_index]
                label_numbers = re.findall(r"\d+", selected.get("ImageDescription") or "")
                if len(label_numbers) != 2:
                    raise RuntimeError(
                        f"Cannot derive panel bounds: {selected.get('ImageDescription')!r}"
                    )
                panel_slug = f"{label_numbers[0]}_{label_numbers[1]}"
                date = datetime.strptime(survey["SurveyDate"], "%m/%d/%Y").strftime(
                    "%Y%m%d"
                )
                date_root = args.output / section / date
                date_root.mkdir(parents=True, exist_ok=True)
                source = date_root / f"segment_{panel_slug}_source.png"
                destination = date_root / f"segment_{panel_slug}_white.png"
                download(selected["imgURL"], source, args.timeout_seconds)
                composite_on_white(source, destination)
                records.append(
                    {
                        "section": section,
                        "ldw_section_id": candidate["ldw_section_id"],
                        "construction_number": construction.get("ConstructionNumber"),
                        "construction_description": construction.get(
                            "ConstructionDescription"
                        ),
                        "survey_date": survey["SurveyDate"],
                        "survey_date_compact": date,
                        "survey_event_description": survey.get(
                            "SurveyEventDescription"
                        ),
                        "panel_index": args.panel_index,
                        "panel_description": selected.get("ImageDescription"),
                        "source_url": selected["imgURL"],
                        "source_local_path": str(source.relative_to(args.output)),
                        "source_sha256": sha256(source),
                        "local_path": str(destination.relative_to(args.output)),
                        "sha256": sha256(destination),
                        "bytes": destination.stat().st_size,
                    }
                )

    manifest = {
        "protocol_id": "ltpp_candidate_first_panel_freeze_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_audit": str(audit_path.resolve()),
        "candidate_audit_sha256": sha256(audit_path),
        "candidate_count": len(candidates),
        "candidate_start": args.candidate_start,
        "panel_index": args.panel_index,
        "sections": [candidate["section"] for candidate in candidates],
        "record_count": len(records),
        "scope": (
            "One fixed nominal panel per survey, for physical-grid and semantic "
            "qualification; images are not crack masks."
        ),
        "records": records,
    }
    manifest_path = args.output / "panel_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hash_path = args.output / "raw_files.sha256"
    files = sorted(path for path in args.output.rglob("*") if path.is_file())
    hash_path.write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(args.output)}\n" for path in files
        ),
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "candidate_count": len(candidates),
                "record_count": len(records),
                "sections": manifest["sections"],
            }
        )
    )


if __name__ == "__main__":
    main()
