from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/toy_road_p0_repeatability_20260802/QUALIFIED_TRAJECTORY_REGISTRY_20260824.json"


def strict_json(path: Path) -> dict[str, object]:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def load_registry(path: Path) -> dict[str, object]:
    return strict_json(path)


def test_t3_review_and_trajectory_registry_are_non_authorizing() -> None:
    receipt = (ROOT / "docs/toy_road_p0_repeatability_20260802/"
               "t3_loading_history_20260818/"
               "T3_INDEPENDENT_REVIEW_RECEIPT_20260821.md").read_text()
    registry = strict_json(REGISTRY)
    assert "PASS, with one provenance-layer discrepancy disclosed" in receipt
    assert "97/97" in receipt and "2,960,514,298" in receipt
    assert "LOCAL_MIRROR_NOT_YET_BUILT" in receipt
    assert "ONEDRIVE_UPLOAD_VERIFIED" in receipt
    assert registry["authorization_capability"] is None
    assert registry["trajectories"]["P0_parent"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T1_initial_defect"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T3_loading_history"]["status"] == "QUALIFIED"
    assert registry["trajectories"]["T2_material_state"]["status"] == \
        "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4"
