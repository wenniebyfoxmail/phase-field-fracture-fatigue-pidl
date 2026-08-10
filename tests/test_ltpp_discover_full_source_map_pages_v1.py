from pathlib import Path

import cv2
import numpy as np

from scripts import ltpp_discover_full_source_map_pages_v1 as subject


def test_large_grid_has_more_coverage_than_small_table_grid():
    large = np.full((500, 500), 255, dtype=np.uint8)
    small = large.copy()
    for image, start, end in ((large, 30, 470), (small, 180, 320)):
        for coordinate in range(start, end + 1, 20):
            cv2.line(image, (coordinate, start), (coordinate, end), 0, 1)
            cv2.line(image, (start, coordinate), (end, coordinate), 0, 1)
    assert subject.grid_coverage(large)[0] > subject.grid_coverage(small)[0]


def test_contact_sheet_has_three_columns_for_two_pages():
    image = np.full((30, 20), 255, dtype=np.uint8)
    sheet = subject.contact_sheet([(image, "p1"), (image, "p2")])
    assert sheet.shape == (294, 612)
