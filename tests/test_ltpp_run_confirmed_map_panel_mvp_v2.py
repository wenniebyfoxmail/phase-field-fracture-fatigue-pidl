from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts import ltpp_run_confirmed_map_panel_mvp_v2 as subject


def synthetic_map_page() -> np.ndarray:
    image = np.full((1100, 850), 255, dtype=np.uint8)
    # A wide, shallow summary table that must not qualify as a tall panel.
    cv2.rectangle(image, (170, 50), (680, 180), 0, 2)
    for x in range(200, 681, 60):
        cv2.line(image, (x, 50), (x, 180), 0, 1)
    for y in range(80, 181, 30):
        cv2.line(image, (170, y), (680, y), 0, 1)
    for x0, x1 in ((120, 340), (500, 720)):
        cv2.rectangle(image, (x0, 260), (x1, 990), 0, 3)
        for x in range(x0 + 20, x1, 20):
            cv2.line(image, (x, 260), (x, 990), 0, 1)
        for y in range(280, 990, 25):
            cv2.line(image, (x0, y), (x1, y), 0, 1)
    return image


def test_synthetic_map_pair_excludes_shallow_table():
    image = synthetic_map_page()
    _, candidates = subject.printed_grid_components(image)
    pair = subject.select_pair(candidates, image.shape[0])
    assert pair is not None
    assert pair[0].x0 < 200
    assert pair[1].x0 > 400
    assert pair[0].y0 > 200


def test_confirmed_ranges_are_exactly_five_pages_each():
    assert all(len(pages) == 5 for pages in subject.CONFIRMED_PAGE_RANGES.values())
    assert subject.CONFIRMED_PAGE_RANGES["19910610"] == (6, 7, 8, 9, 10)
    assert subject.CONFIRMED_PAGE_RANGES["20120417"] == (3, 4, 5, 6, 7)


def test_run_requires_new_output_root(tmp_path: Path):
    with pytest.raises(FileExistsError, match="must be new"):
        subject.run(tmp_path, tmp_path)


def test_rendered_page_lookup_accepts_padded_and_unpadded_names(tmp_path: Path):
    unpadded = tmp_path / "page-4.png"
    unpadded.write_bytes(b"png")
    assert subject.find_rendered_page(tmp_path, 4) == unpadded
