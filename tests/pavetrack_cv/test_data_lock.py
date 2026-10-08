from pathlib import Path
import json
import hashlib
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "pavetrack_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    locations_for_splits,
    load_data_lock,
    validate_evaluation_membership,
    validate_prepared_record_hashes,
)


class FrozenProjectDataLockTests(unittest.TestCase):
    def test_prepared_image_and_label_same_path_replacement_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / "image.jpg"
            label = root / "image.txt"
            image.write_bytes(b"frozen-image")
            label.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
            payload = {
                "records": [{
                    "prepared_image": str(image),
                    "prepared_image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                    "prepared_label": str(label),
                    "prepared_label_sha256": hashlib.sha256(label.read_bytes()).hexdigest(),
                }]
            }
            validate_prepared_record_hashes(payload)
            image.write_bytes(b"replacement")
            with self.assertRaisesRegex(ValueError, "image content hash"):
                validate_prepared_record_hashes(payload)
            image.write_bytes(b"frozen-image")
            label.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "label content hash"):
                validate_prepared_record_hashes(payload)

    def test_repository_lock_is_disjoint_and_test_is_not_preparation_default(self):
        path = ROOT / "docs" / "research" / "S01" / "S01-E001" / "data_lock.json"
        lock = load_data_lock(path)
        development = locations_for_splits(lock, ["train", "validation"])
        confirmation = locations_for_splits(lock, ["test"])
        self.assertTrue(development.isdisjoint(confirmation))
        self.assertEqual(confirmation, {"1059", "2227", "2291", "6227"})
        self.assertFalse(lock["selection_uses_pixels"])

    def test_manifest_contract_names_location_as_independence_unit(self):
        path = ROOT / "docs" / "research" / "S01" / "S01-E001" / "data_lock.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["independence_unit"], "reid")

    def test_confirmatory_membership_rejects_reserve_retagging(self):
        path = ROOT / "docs" / "research" / "S01" / "S01-E001" / "data_lock.json"
        lock = load_data_lock(path)
        test_locations = lock["confirmatory_test_locations"]
        payload = {
            "locations": test_locations,
            "records": [
                {"split": "test", "reid": location, "image_id": f"image-{location}"}
                for location in test_locations
            ],
        }
        validate_evaluation_membership(payload, lock, "test")
        payload["records"][0]["reid"] = lock["reserve_test_locations"][0]
        with self.assertRaisesRegex(ValueError, "differ"):
            validate_evaluation_membership(payload, lock, "test")


if __name__ == "__main__":
    unittest.main()
