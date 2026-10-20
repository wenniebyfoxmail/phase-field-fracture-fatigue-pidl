"""Rendering of explicitly artificial Boolean fixtures only; no native states."""
import json
from pathlib import Path

import numpy as np
import pytest

from tools.plot_synthetic_history import _load_outputs, render_synthetic_history


@pytest.mark.parametrize("has_future", [False, True])
def test_render_complete_saved_fixture_without_scientific_execution(tmp_path, has_future):
    origin = np.zeros((3, 2, 64, 64), dtype=bool)
    origin[:, :, 31:33, 8:24] = True
    if not has_future:
        origin[2, 1, 32, 25] = True
    np.savez(tmp_path / "origin_observations.npz", masks=origin)
    match = dict(anchor_valid=True, identical=has_future, differing_pixels=0 if has_future else 1)
    (tmp_path / "current_match.json").write_text(json.dumps(match))
    result = dict(verdict="supports" if has_future else "inconclusive", future_executed=has_future)
    if has_future:
        result.update(full_state_restart="exact", horizons={})
        for h in (5, 10, 20):
            masks = origin.copy()
            masks[:, 1, 33, 25] = True
            masks[2, 1, 34, 26] = True
            robust = np.zeros((64, 64), dtype=bool); robust[33, 25] = True
            unstable = np.zeros((64, 64), dtype=bool); unstable[34, 26] = True
            np.savez(tmp_path / f"future_h{h:02d}.npz", masks=masks, robust=robust, unstable=unstable)
            result["horizons"][str(h)] = dict(robust_pixels=1, unstable_pixels=1)
    (tmp_path / "result.json").write_text(json.dumps(result))
    report = render_synthetic_history(tmp_path)
    assert len(report["figures"]) == (3 if has_future else 1)
    assert report["primary_conditions_met"] is has_future
    for item in report["figures"]:
        path = Path(item)
        assert path.parent == tmp_path / "figures"
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert path.stat().st_size > 10000
        assert path.with_suffix(".md").is_file()
    text = Path(report["readme"]).read_text()
    assert "H20稳健差像素数>0" in text and "不是学习模型null" in text
    assert "不等于真实可见裂缝" in text
    if not has_future:
        assert "未来未执行" in text and not (tmp_path / "figures/continuation_h20.png").exists()


def _paired_fixture(root, has_future):
    """Three artificial pair matches can coexist with eight cross-grid pixels."""
    origin = np.zeros((3, 2, 64, 64), dtype=bool)
    origin[:, :, 31:33, 8:24] = True
    origin[1, :, 10, 10:18] = True
    settle = origin.copy()
    if not has_future:
        origin[2, 1, 32, 25] = True
    pair_xor = origin[:, 0] != origin[:, 1]
    counts = np.sum(pair_xor, axis=(1, 2)).tolist()
    match = dict(matching_scope="within_each_variant", anchor_valid=True,
                 identical=all(count == 0 for count in counts),
                 pair_identical=[count == 0 for count in counts], pair_xor_pixels=counts,
                 differing_pixels=int(np.any(pair_xor, axis=0).sum()),
                 cross_variant_v1=dict(anchor_valid=True, identical=False,
                     differing_pixels=int(np.any(origin != origin[0, 0], axis=(0, 1)).sum())))
    np.savez(root / "origin_observations.npz", masks=origin)
    if has_future:
        np.savez(root / "zero_settle_observations.npz", masks=settle)
    result = dict(protocol="2.0", verdict="supports" if has_future else "inconclusive",
                  future_executed=has_future)
    if has_future:
        result.update(full_state_restart="exact", horizons={})
        for horizon in (5, 10, 20):
            masks = origin.copy()
            masks[:, 1, 33, 25] = True
            masks[2, 1, 34, 26] = True
            robust = np.zeros((64, 64), dtype=bool); robust[33, 25] = True
            unstable = np.zeros((64, 64), dtype=bool)
            unstable[10, 10:18] = True; unstable[34, 26] = True
            np.savez(root / f"future_h{horizon:02d}.npz", masks=masks,
                     robust=robust, unstable=unstable)
            result["horizons"][str(horizon)] = dict(robust_pixels=1, unstable_pixels=9)
    (root / "current_match.json").write_text(json.dumps(match))
    (root / "result.json").write_text(json.dumps(result))
    return result, match


@pytest.mark.parametrize("has_future", [False, True])
def test_render_v2_paired_match_preserves_cross_grid_diagnostic(tmp_path, has_future):
    _paired_fixture(tmp_path, has_future)
    report = render_synthetic_history(tmp_path)
    assert report["primary_conditions_met"] is has_future
    assert len(report["figures"]) == (3 if has_future else 1)
    for filename in report["figures"]:
        assert Path(filename).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert Path(filename).stat().st_size > 10000
    readme = Path(report["readme"]).read_text()
    sidecar = (tmp_path / "figures/origin_masks.md").read_text()
    assert "三配置各自的当前low/high全图严格相同" in readme
    assert "不是完全未见数据的独立复现" in readme
    assert "不把v1改写为通过" in sidecar
    assert "H5/H10、阈值敏感性" in readme
    if has_future:
        assert "不同像素并集为8" in sidecar
        assert "零载settle文件的六图差异并集为8像素" in sidecar
        assert "zero_settle_observations.npz" in readme
        h20 = (tmp_path / "figures/continuation_h20.md").read_text()
        assert "H20稳健差异为1像素" in h20 and "不稳定区域为9像素" in h20
        assert "每种配置内部" in h20
    else:
        assert "各对XOR像素数为[0, 0, 1]" in sidecar
        assert "配置内XOR并集为1" in sidecar
        assert "不同像素并集为9" in sidecar
        assert "未来未执行" in readme
        assert not (tmp_path / "figures/continuation_h20.png").exists()


@pytest.mark.parametrize("corruption", ["scope", "pair_bool", "pair_count", "union",
                                        "cross_grid", "legacy_protocol", "missing_protocol"])
def test_v2_loader_rejects_inconsistent_or_ambiguous_match_schema(tmp_path, corruption):
    result, match = _paired_fixture(tmp_path, False)
    if corruption == "scope":
        match["matching_scope"] = "all_six"
    elif corruption == "pair_bool":
        match["pair_identical"][2] = True
    elif corruption == "pair_count":
        match["pair_xor_pixels"][2] = 0
    elif corruption == "union":
        match["differing_pixels"] = 9
    elif corruption == "cross_grid":
        match["cross_variant_v1"]["differing_pixels"] = 1
    elif corruption == "legacy_protocol":
        result["protocol"] = "1.0"
    else:
        result.pop("protocol")
    (tmp_path / "current_match.json").write_text(json.dumps(match))
    (tmp_path / "result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="current_match.json"):
        _load_outputs(tmp_path)
    assert not (tmp_path / "figures").exists()
