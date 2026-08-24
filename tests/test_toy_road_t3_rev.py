from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/toy_road_p0_repeatability_20260802/QUALIFIED_TRAJECTORY_REGISTRY_20260824.json"
BASE = ROOT / "producer_handoffs/toy_road_p0_repeatability_20260803"


def load_module(name: str):
    path = ROOT / "analysis/toy_road_t3_rev_20260824" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_extension_adds_only_t3_rev_and_preserves_base(tmp_path: Path) -> None:
    module = load_module("build_t3_rev_extension")
    before = module.inventory_tree(BASE)
    result = module.build_extension(BASE, tmp_path / "extension", "a" * 40)
    after = module.inventory_tree(BASE)
    assert before == after
    assert result["case_id"] == "T3_rev_loading_order"
    assert result["loading_blocks"] == [[1, 30, 0.126], [31, 60, 0.108], [61, 150, 0.120]]
    assert result["base_source_manifest_sha256"] == \
        "61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e"
    assert set(result["changed_source_files"]) == set(module.ALLOWED_SHADOW_FILES)
    assert {
        path.relative_to(tmp_path / "extension").as_posix()
        for path in (tmp_path / "extension").rglob("*")
        if path.is_file()
    } == {
        *module.ALLOWED_SHADOW_FILES,
        "EXTENSION_SOURCE_MANIFEST.json",
        "SOURCE_DIFF_INVENTORY.json",
    }


def test_extension_rejects_duplicate_json_and_unexpected_base_text(tmp_path: Path) -> None:
    module = load_module("build_t3_rev_extension")
    bad = tmp_path / "base"
    shutil.copytree(BASE, bad)
    path = bad / "build_toy_road_family_case.m"
    path.write_text(path.read_text().replace("T3_loading_history", "T3_changed", 1))
    with pytest.raises(module.ExtensionError, match="base source identity|exact patch count"):
        module.build_extension(bad, tmp_path / "extension", "a" * 40)


@pytest.mark.parametrize("bad_payload", [
    '{"case_id":"T3_rev_loading_order","case_id":"duplicate"}',
    '{"loading_blocks":NaN}',
    '{"resume_allowed":0}',
])
def test_extension_contract_rejects_noncanonical_json(tmp_path: Path, bad_payload: str) -> None:
    module = load_module("build_t3_rev_extension")
    path = tmp_path / "bad.json"
    path.write_text(bad_payload)
    with pytest.raises(module.ExtensionError):
        module.read_strict_contract(path)
