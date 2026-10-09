from pathlib import Path
import sys
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pavetrack_tiled_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from contracts import validate_data_lock, validate_tile_manifest_contract  # noqa: E402


class DataLockContractTests(unittest.TestCase):
    def setUp(self):
        self.lock = {
            "train_locations": ["1"],
            "validation_locations": ["2"],
            "confirmatory_test_locations": ["3"],
            "consumed_or_excluded_locations": ["4"],
            "reserve_test_locations": ["5"],
            "independence_unit": "reid",
            "selection_uses_pixels": False,
        }

    def test_disjoint_lock_passes(self):
        validate_data_lock(self.lock)

    def test_overlap_fails(self):
        self.lock["confirmatory_test_locations"] = ["1"]
        with self.assertRaisesRegex(ValueError, "overlaps"):
            validate_data_lock(self.lock)

    def test_pixel_selected_holdout_fails(self):
        self.lock["selection_uses_pixels"] = True
        with self.assertRaisesRegex(ValueError, "must not use image pixels"):
            validate_data_lock(self.lock)

    def test_validation_tile_manifest_requires_source_binding(self):
        manifest = {
            "protocol": "S01-E002-v1",
            "data_lock_sha256": "lock",
            "run_config_sha256": "config",
            "workbook_sha256": "workbook",
            "source_manifest_sha256": "development",
        }
        validate_tile_manifest_contract(
            manifest,
            data_lock_sha256="lock",
            run_config_sha256="config",
            workbook_sha256="workbook",
            source_manifest_sha256="development",
        )
        with self.assertRaisesRegex(ValueError, "source_manifest_sha256"):
            validate_tile_manifest_contract(
                manifest,
                data_lock_sha256="lock",
                run_config_sha256="config",
                workbook_sha256="workbook",
                source_manifest_sha256="test",
            )

    def test_test_path_accepts_frozen_development_tile_manifest(self):
        manifest = {
            "protocol": "S01-E002-v1",
            "data_lock_sha256": "lock",
            "run_config_sha256": "config",
            "workbook_sha256": "workbook",
            "source_manifest_sha256": "development",
        }
        validate_tile_manifest_contract(
            manifest,
            data_lock_sha256="lock",
            run_config_sha256="config",
            workbook_sha256="workbook",
            source_manifest_sha256=None,
        )


if __name__ == "__main__":
    unittest.main()
