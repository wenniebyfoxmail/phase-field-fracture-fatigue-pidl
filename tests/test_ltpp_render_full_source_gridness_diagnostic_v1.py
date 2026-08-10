from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts import ltpp_render_full_source_gridness_diagnostic_v1 as subject


def test_grid_region_has_stronger_response_than_blank_region():
    image = np.full((400, 400), 255, dtype=np.uint8)
    for x in range(50, 351, 20):
        cv2.line(image, (x, 50), (x, 350), 0, 1)
    for y in range(50, 351, 20):
        cv2.line(image, (50, y), (350, y), 0, 1)
    response = subject.gridness(image)
    assert response[200, 200] > response[15, 15]


def test_run_requires_new_directory(tmp_path: Path):
    with pytest.raises(FileExistsError, match="must be new"):
        subject.run(tmp_path, tmp_path)
