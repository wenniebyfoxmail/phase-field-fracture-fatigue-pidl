from pathlib import Path
import sys
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pavetrack_tiled_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from prepare_development_tiles import yolo_line  # noqa: E402


class PrepareTilesTests(unittest.TestCase):
    def test_yolo_line_uses_tile_coordinates(self):
        self.assertEqual(
            yolo_line((64.0, 128.0, 192.0, 256.0), 640),
            "0 0.20000000 0.30000000 0.20000000 0.20000000",
        )


if __name__ == "__main__":
    unittest.main()
