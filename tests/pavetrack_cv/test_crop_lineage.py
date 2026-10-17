from pathlib import Path
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "pavetrack_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from train_reranker import validate_crop_manifest  # noqa: E402


class CropLineageTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        background = root / "train" / "background" / "a.jpg"
        crack = root / "train" / "crack" / "b.jpg"
        background.parent.mkdir(parents=True)
        crack.parent.mkdir(parents=True)
        background.write_bytes(b"background")
        crack.write_bytes(b"crack")
        payload = {
            "protocol": "S01-E001-v11",
            "proposer_receipt_sha256": "proposer-receipt",
            "run_config_sha256": "run-config",
            "split": "train",
            "manifest_sha256": "development",
            "data_lock_sha256": "lock",
            "workbook_sha256": "workbook",
            "proposer_sha256": "proposer",
            "records": [
                {
                    "split": "train", "label": 0, "image_id": "image-a",
                    "path": str(background), "sha256": __import__("hashlib").sha256(background.read_bytes()).hexdigest()
                },
                {
                    "split": "train", "label": 1, "image_id": "image-b",
                    "path": str(crack), "sha256": __import__("hashlib").sha256(crack.read_bytes()).hexdigest()
                },
            ],
        }
        manifest = root / "crop_manifest_train.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        return manifest

    def test_exact_manifest_files_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_fixture(root)
            payload = validate_crop_manifest(manifest, "train", root)
            self.assertEqual(len(payload["records"]), 2)

    def test_unrecorded_stale_crop_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_fixture(root)
            (root / "train" / "background" / "stale.jpg").write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError, "differ"):
                validate_crop_manifest(manifest, "train", root)

    def test_same_path_content_replacement_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_fixture(root)
            (root / "train" / "background" / "a.jpg").write_bytes(b"replacement")
            with self.assertRaisesRegex(ValueError, "content hash"):
                validate_crop_manifest(manifest, "train", root)

    def test_class_directory_must_match_label(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_fixture(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["records"][0]["label"] = 1
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "class directory"):
                validate_crop_manifest(manifest, "train", root)


if __name__ == "__main__":
    unittest.main()
