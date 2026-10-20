"""Rendering of explicitly artificial Boolean fixtures only; no native states."""
import json
from pathlib import Path

import numpy as np
import pytest

from tools.plot_synthetic_history import render_synthetic_history


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
