#!/usr/bin/env python3
"""Custodian-only mechanical consensus for blinded Tier B registration controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def consensus(a: dict, b: dict, origin_a: dict, origin_b: dict) -> dict:
    if a["status"] == b["status"] == "usable":
        pa, pb = a["click_crop_px"], b["click_crop_px"]
        distance = math.dist(pa, pb)
        if distance <= 4.0:
            return {"status": "eligible", "agreement_distance_px": distance, "source_px": [(pa[0] + pb[0]) / 2 + origin_a["left"], (pa[1] + pb[1]) / 2 + origin_a["top"]], "reason_codes": []}
        return {"status": "missing_or_ambiguous", "agreement_distance_px": distance, "source_px": None, "reason_codes": ["click_distance_gt_4px"]}
    return {"status": "missing_or_ambiguous", "agreement_distance_px": None, "source_px": None, "reason_codes": [a["status"], b["status"]]}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--packet-root", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    root = args.packet_root.resolve(); sealed = root / "custodian_sealed_do_not_open" / "blind_mapping_and_roles.json"
    mapping = json.loads(sealed.read_text())
    for role in ("annotator_a", "annotator_b"):
        for row in mapping[role]:
            record = json.loads((root / role / "records" / f"{row['blind_map_id']}.json").read_text())
            if not record.get("locked"): raise SystemExit(f"unlocked annotation record: {role}/{row['blind_map_id']}")
    a_by_date = {row["survey_date"]: row for row in mapping["annotator_a"]}; b_by_date = {row["survey_date"]: row for row in mapping["annotator_b"]}
    result = {"status": "TIER_B_CONSENSUS_COMPLETE", "packet_sha256": sha256(sealed), "dates": {}}
    for date in sorted(a_by_date):
        ra, rb = a_by_date[date], b_by_date[date]
        a = json.loads((root / "annotator_a" / "records" / f"{ra['blind_map_id']}.json").read_text())
        b = json.loads((root / "annotator_b" / "records" / f"{rb['blind_map_id']}.json").read_text())
        rows = {candidate: consensus(a["tasks"][candidate], b["tasks"][candidate], ra["crop_source_px"], rb["crop_source_px"]) for candidate in a["tasks"]}
        role_map = mapping["candidate_roles"]
        summary = {role: sum(rows[candidate]["status"] == "eligible" for candidate in rows if role_map[candidate] == role) for role in ("fit", "development", "final_audit")}
        result["dates"][date] = {"summary": summary, "controls": rows}
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    (output / "sealed_consensus_controls.json").write_text(json.dumps(result, indent=2) + "\n")
    public = {"status": "TIER_B_AVAILABILITY_PENDING_REVIEW", "dates": {date: {"fit_eligible_count": value["summary"]["fit"], "development_all_eligible": value["summary"]["development"] == 8, "final_all_eligible": value["summary"]["final_audit"] == 8} for date, value in result["dates"].items()}}
    (output / "availability_summary.json").write_text(json.dumps(public, indent=2) + "\n")
    (output / "manifest.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in sorted(output.iterdir()) if path.name != "manifest.sha256"))
    print(json.dumps({"status": public["status"], "dates": len(public["dates"])}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
