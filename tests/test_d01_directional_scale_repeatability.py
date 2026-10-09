from __future__ import annotations

import importlib.util
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "d01_directional_scale_repeatability.py"
SPEC = importlib.util.spec_from_file_location("d01_directional_scale_repeatability", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def synthetic_ruler() -> np.ndarray:
    image = np.full((800, 1200, 3), 205, dtype=np.uint8)
    x_start, x_stop = 80, 1120
    slope = 0.025
    y_start = 500
    y_stop = int(round(y_start + slope * (x_stop - x_start)))
    cv2.line(image, (x_start, y_start), (x_stop, y_stop), (20, 20, 20), 5)
    for x in range(100, 1101, 15):
        y = int(round(y_start + slope * (x - x_start)))
        length = 75 if ((x - 100) // 15) % 10 == 0 else 48
        cv2.line(image, (x, y + 5), (x, y + length), (10, 10, 10), 2)
    return image


def test_synthetic_ruler_returns_valid_monotone_sequence() -> None:
    metrics, arrays = MODULE.analyze_image(synthetic_ruler())
    assert metrics["validity_pass"]
    assert metrics["tick_count"] >= 50
    assert metrics["max_tick_step"] <= 2
    assert metrics["lomo_p95_mm"] <= 1.0
    assert np.all(np.diff(arrays["tick_index"]) > 0)


def test_development_mode_filters_reference2_before_image_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    files = []
    for beam in ("Beam 4", "Beam 5", "Beam 6"):
        for reference in ("ref1", "ref2"):
            files.append(
                {
                    "saved_as": f"{beam}/G/{reference}.JPG",
                    "bytes": 1,
                    "crc32": "00",
                    "sha256": "00",
                    "height_px": 1,
                    "width_px": 1,
                }
            )
    manifest = tmp_path / "selection.json"
    manifest.write_text(json.dumps({"files": files}))
    seen: list[str] = []

    def stop_at_first_file(path: Path) -> str:
        seen.append(str(path))
        raise RuntimeError("stop")

    monkeypatch.setattr(MODULE, "crc32_file", stop_at_first_file)
    raw = tmp_path / "raw"
    first = raw / "Beam 4/G/ref1.JPG"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="stop"):
        MODULE.run(
            raw_root=raw,
            selection_manifest=manifest,
            output=tmp_path / "out",
            mode="development",
            repo=Path(__file__).resolve().parents[1],
        )
    assert seen and all("ref2" not in item for item in seen)


def test_formal_mode_requires_review_pass(tmp_path: Path) -> None:
    manifest = tmp_path / "selection.json"
    manifest.write_text(json.dumps({"files": []}))
    with pytest.raises(PermissionError, match="review-pass"):
        MODULE.run(
            raw_root=tmp_path,
            selection_manifest=manifest,
            output=tmp_path / "out",
            mode="formal",
            repo=Path(__file__).resolve().parents[1],
        )


def test_dirty_checkout_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_check_output(command: list[str], **_: object) -> str:
        assert command[:2] == ["git", "status"]
        return " M scripts/d01_directional_scale_repeatability.py\n"

    monkeypatch.setattr(MODULE.subprocess, "check_output", fake_check_output)
    assert not MODULE.checkout_is_clean(tmp_path)


def test_exact_csv_contains_image_and_beam_rows(tmp_path: Path) -> None:
    detection = MODULE.Detection(
        beam="Beam 4",
        reference="ref1",
        saved_as="Beam 4/ref1.JPG",
        sha256="abc",
        boundary_x1=1.0,
        boundary_y1=2.0,
        boundary_x2=3.0,
        boundary_y2=4.0,
        boundary_angle_deg=0.0,
        nominal_period_px=15.0,
        tick_count=60,
        max_tick_step=1,
        ransac_inlier_count=60,
        lomo_count=6,
        lomo_p95_mm=0.2,
        lomo_median_mm=0.1,
        spacing_cv=0.02,
        monotone=True,
        finite=True,
        validity_pass=True,
    )
    target = tmp_path / "metrics.csv"
    MODULE._write_csv(target, [detection], {"Beam 4": 0.3})
    with target.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["row_type"] for row in rows] == ["image", "beam"]
    assert rows[1]["reference"] == "worse_of_ref1_ref2"
    assert float(rows[1]["beam_worst_lomo_p95_mm"]) == pytest.approx(0.3)
