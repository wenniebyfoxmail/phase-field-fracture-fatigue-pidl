from pathlib import Path
import sys
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pavetrack_tiled_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from geometry import Candidate, clip_target_to_tile, deterministic_nms, tile_origins, to_full_image  # noqa: E402
from audit_s01_e001 import maximum_match_count  # noqa: E402


class TileGeometryTests(unittest.TestCase):
    def test_origins_cover_far_edge_without_duplicate(self):
        self.assertEqual(tile_origins(1920, 640, 480), [0, 480, 960, 1280])
        self.assertEqual(tile_origins(1080, 640, 480), [0, 440])
        self.assertEqual(tile_origins(320, 640, 480), [0])

    def test_target_assignment_accepts_center_or_quarter_area(self):
        self.assertEqual(
            clip_target_to_tile((600, 100, 700, 200), 0, 0, 640),
            (600.0, 100.0, 640, 200.0),
        )
        self.assertIsNone(clip_target_to_tile((630, 100, 730, 200), 0, 0, 640))
        self.assertEqual(
            clip_target_to_tile((620, 100, 660, 200), 0, 0, 640),
            (620.0, 100.0, 640, 200.0),
        )

    def test_mapping_clips_and_drops_empty_boxes(self):
        self.assertEqual(
            to_full_image((-5, 10, 100, 200), 480, 440, 1920, 1080),
            (475.0, 450.0, 580.0, 640.0),
        )
        self.assertIsNone(to_full_image((700, 10, 800, 20), 1280, 0, 1920, 1080))

    def test_nms_is_input_order_independent_and_global(self):
        low = Candidate((0, 0, 100, 100), 0.5, 0, 0)
        high = Candidate((2, 2, 102, 102), 0.9, 480, 0)
        separate = Candidate((300, 300, 350, 350), 0.4, 0, 440)
        expected = [high, separate]
        self.assertEqual(deterministic_nms([low, high, separate], 0.5, 10), expected)
        self.assertEqual(deterministic_nms([separate, high, low], 0.5, 10), expected)

    def test_oracle_matching_does_not_reuse_one_proposal(self):
        targets = [(0, 0, 10, 10), (0, 0, 10, 10)]
        proposals = [(0, 0, 10, 10)]
        self.assertEqual(maximum_match_count(targets, proposals), 1)


if __name__ == "__main__":
    unittest.main()
