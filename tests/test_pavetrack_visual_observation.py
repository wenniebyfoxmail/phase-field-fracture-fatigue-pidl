from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "SENS_tensile" / "analyze_pavetrack_visual_observation.py"
SPEC = importlib.util.spec_from_file_location("pavetrack_visual", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_parse_filename_preserves_unknown_timezone() -> None:
    parsed = MODULE.parse_filename("2023-06-14_06-41-37-971-n00088.jpg")
    assert parsed is not None
    timestamp, camera = parsed
    assert timestamp.tzinfo is None
    assert timestamp.isoformat(timespec="milliseconds") == "2023-06-14T06:41:37.971"
    assert camera == "n00088"


def test_unique_manifest_rows_are_deduplicated(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "reid,date,category,img_path,mask_path,img_name\n"
        "1,2023-01-01,Transverse Crack,x,y,2023-01-01_01-02-03-004-n00088.jpg\n"
        "1,2023-01-01,Transverse Crack,x,y,2023-01-01_01-02-03-004-n00088.jpg\n",
        encoding="utf-8",
    )
    records, rows = MODULE.load_unique_records(manifest)
    assert rows == 2
    assert len(records) == 1


def test_mask_features_stay_in_image_space(tmp_path: Path) -> None:
    mask = np.zeros((10, 20), dtype=np.uint8)
    mask[2:6, 5:15] = 255
    path = tmp_path / "mask.png"
    Image.fromarray(mask).save(path)
    features = MODULE.mask_features(path)
    assert features["mask_area_fraction"] == 0.2
    assert features["bbox_width_fraction"] == 0.5
    assert features["bbox_height_fraction"] == 0.4


def test_sequences_are_split_by_camera_suffix() -> None:
    records = [
        {
            "reid": "1",
            "category": "Transverse Crack",
            "img_name": f"2023-01-0{day}_01-02-03-004-{camera}.jpg",
        }
        for day, camera in ((1, "n00088"), (2, "n00088"), (3, "000126"))
    ]
    sequences = MODULE.build_sequences(records)
    assert len(sequences) == 2
    assert sequences[0]["record_count"] == 2
