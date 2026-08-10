import cv2
import numpy as np

from scripts import ltpp_run_confirmed_outer_frame_mvp_v3 as subject


def synthetic_page() -> np.ndarray:
    image = np.full((1100, 850), 255, dtype=np.uint8)
    cv2.rectangle(image, (100, 40), (750, 170), 0, 2)
    for x0, x1 in ((105, 345), (505, 745)):
        cv2.rectangle(image, (x0, 250), (x1, 990), 0, 4)
        for x in range(x0 + 20, x1, 20):
            cv2.line(image, (x, 250), (x, 990), 0, 1)
        for y in range(270, 990, 30):
            cv2.line(image, (x0, y), (x1, y), 0, 1)
    return image


def test_outer_frames_are_selected_over_page_table():
    image = synthetic_page()
    pair = subject.select_pair(subject.frame_candidates(image), image.shape[0])
    assert pair is not None
    assert pair[0].x0 < 200
    assert pair[1].x0 > 400
    assert pair[0].y0 > 200


def test_line_clustering_is_length_ranked_and_bounded():
    lines = [(index, index + 1) for index in range(50)]
    clustered = subject.cluster_lines(lines, tolerance=0, limit=10)
    assert len(clustered) == 10
    assert max(length for _, length in clustered) == 50
