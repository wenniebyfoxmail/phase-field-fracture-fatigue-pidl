from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts import ltpp_run_full_source_panel_mvp_v1 as subject


def make_two_panel_page() -> np.ndarray:
    image = np.full((1200, 1000), 255, dtype=np.uint8)
    for x0, x1 in ((120, 400), (560, 840)):
        cv2.rectangle(image, (x0, 120), (x1, 1060), 0, 4)
        for y in range(180, 1060, 80):
            cv2.line(image, (x0 + 2, y), (x1 - 2, y), 0, 1)
    return image


def test_synthetic_pair_is_found_in_left_to_right_order():
    pair = subject.select_panel_pair(subject.rectangle_candidates(make_two_panel_page()))
    assert pair is not None
    assert pair[0].x0 < pair[1].x0
    assert pair[0].height / pair[0].width == pytest.approx(940 / 280, rel=0.1)


def test_no_pair_when_only_one_frame_exists():
    image = make_two_panel_page()
    image[:, 500:] = 255
    assert subject.select_panel_pair(subject.rectangle_candidates(image)) is None


def test_line_cap_is_length_ranked_then_coordinate_ranked():
    lines = [(3, 10), (1, 10), (2, 12), (4, 9)]
    assert subject.cap_lines(lines, limit=3) == [(1, 10), (2, 12), (3, 10)]


def test_run_requires_a_new_output_directory(tmp_path: Path):
    with pytest.raises(FileExistsError, match="must be new"):
        subject.run(tmp_path, tmp_path)
