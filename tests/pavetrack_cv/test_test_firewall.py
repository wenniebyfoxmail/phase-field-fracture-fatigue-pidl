from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "pavetrack_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from common import sha256_file  # noqa: E402


class ConfirmatoryFirewallTests(unittest.TestCase):
    @staticmethod
    def write_checkpoint(path: Path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("archive/data.pkl", b"synthetic-test-checkpoint")

    def test_test_preparation_requires_authorization_before_dependency_import(self):
        command = [
            sys.executable,
            str(SCRIPT_DIR / "prepare_dataset.py"),
            "--workbook",
            "missing.xlsx",
            "--data-lock",
            "missing.json",
            "--config",
            "missing-config.json",
            "--image-root",
            "missing_images",
            "--output",
            "unused",
            "--splits",
            "test",
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--test-authorization", result.stderr)

    def test_minimal_status_json_cannot_prepare_test(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization = root / "authorization.json"
            authorization.write_text(
                json.dumps({"status": "authorized_after_model_freeze"}), encoding="utf-8"
            )
            for name in ("proposer.pt", "reranker.pt", "validation.json", "receipt.json"):
                (root / name).write_bytes(b"arbitrary")
            (root / "lock.json").write_text("{}", encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT_DIR / "prepare_dataset.py"),
                "--workbook", "missing.xlsx",
                "--data-lock", str(root / "lock.json"),
                "--config", str(root / "config.json"),
                "--image-root", "missing_images",
                "--output", "unused",
                "--splits", "test",
                "--test-authorization", str(authorization),
                "--proposer", str(root / "proposer.pt"),
                "--reranker", str(root / "reranker.pt"),
                "--validation-evaluation", str(root / "validation.json"),
                "--proposer-receipt", str(root / "receipt.json"),
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lacks fields", result.stderr)

    def test_fake_zip_checkpoints_cannot_freeze_for_test(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_lock = root / "lock.json"
            proposer = root / "proposer.pt"
            reranker = root / "reranker.pt"
            validation = root / "validation.json"
            output = root / "authorization.json"
            data_lock.write_text("{}", encoding="utf-8")
            self.write_checkpoint(proposer)
            self.write_checkpoint(reranker)
            config = root / "config.json"
            config.write_text(json.dumps({"protocol": "S01-E001-v11"}), encoding="utf-8")
            proposer_receipt = root / "proposer_receipt.json"
            proposer_receipt.write_text(
                json.dumps(
                    {
            "protocol": "S01-E001-v11",
                        "best_model_sha256": sha256_file(proposer),
                        "development_manifest_sha256": "development-manifest-hash",
                        "run_config_sha256": sha256_file(config),
                    }
                ),
                encoding="utf-8",
            )
            validation.write_text(
                json.dumps(
                    {
                        "protocol": "S01-E001-v11",
                        "split": "validation",
                        "primary_pass": None,
                        "manifest_sha256": "development-manifest-hash",
                        "validation_manifest_sha256": "development-manifest-hash",
                        "data_lock_sha256": sha256_file(data_lock),
                        "workbook_sha256": "workbook-hash",
                        "proposer_sha256": sha256_file(proposer),
                        "reranker_sha256": sha256_file(reranker),
                        "proposer_receipt_sha256": sha256_file(proposer_receipt),
                        "run_config_sha256": sha256_file(config),
                        "reranker_lineage": {
                            "manifest_sha256": "development-manifest-hash",
                            "data_lock_sha256": sha256_file(data_lock),
                            "workbook_sha256": "workbook-hash",
                            "proposer_sha256": sha256_file(proposer),
                            "proposer_receipt_sha256": sha256_file(proposer_receipt),
                            "run_config_sha256": sha256_file(config),
                            "train_crop_manifest_sha256": "train-crops",
                            "validation_crop_manifest_sha256": "validation-crops"
                        },
                        "frozen_two_stage_score": "sqrt(proposer_confidence * reranker_crack_probability)"
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "freeze_for_test.py"),
                    "--data-lock",
                    str(data_lock),
                    "--config",
                    str(config),
                    "--proposer",
                    str(proposer),
                    "--reranker",
                    str(reranker),
                    "--proposer-receipt",
                    str(proposer_receipt),
                    "--validation-evaluation",
                    str(validation),
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lacks tensor storage", result.stderr)
            self.assertFalse(output.exists())

    def test_complete_forged_authorization_with_arbitrary_model_bytes_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "lock.json"
            proposer = root / "proposer.pt"
            reranker = root / "reranker.pt"
            validation = root / "validation.json"
            receipt = root / "receipt.json"
            authorization = root / "authorization.json"
            config = root / "config.json"
            config.write_text(json.dumps({"protocol": "S01-E001-v11"}), encoding="utf-8")
            lock.write_text("{}", encoding="utf-8")
            proposer.write_bytes(b"arbitrary proposer bytes")
            reranker.write_bytes(b"arbitrary reranker bytes")
            receipt.write_text(
                json.dumps(
                    {
                        "protocol": "S01-E001-v11",
                        "best_model_sha256": sha256_file(proposer),
                    }
                ),
                encoding="utf-8",
            )
            validation_payload = {
                "manifest_sha256": "manifest",
                "data_lock_sha256": sha256_file(lock),
                "workbook_sha256": "workbook",
                "proposer_sha256": sha256_file(proposer),
                "reranker_sha256": sha256_file(reranker),
                "proposer_receipt_sha256": sha256_file(receipt),
                "run_config_sha256": sha256_file(config),
            }
            validation.write_text(json.dumps(validation_payload), encoding="utf-8")
            authorization.write_text(
                json.dumps(
                    {
                        "protocol": "S01-E001-v11",
                        "status": "authorized_after_model_freeze",
                        **validation_payload,
                        "validation_evaluation_sha256": sha256_file(validation),
                        "validation_manifest_sha256": "manifest",
                        "scoring_rule": "sqrt(proposer_confidence * reranker_crack_probability)",
                        "primary_metric": "macro-location R@1FP/image, one global threshold, IoU>=0.50",
                        "primary_pass_delta": 0.10,
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT_DIR / "prepare_dataset.py"),
                    "--workbook", "missing.xlsx", "--data-lock", str(lock),
                    "--config", str(config),
                    "--image-root", "missing_images", "--output", "unused",
                    "--splits", "test", "--test-authorization", str(authorization),
                    "--proposer", str(proposer), "--reranker", str(reranker),
                    "--validation-evaluation", str(validation),
                    "--proposer-receipt", str(receipt),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a PyTorch ZIP checkpoint", result.stderr)

    def test_minimal_validation_json_cannot_authorize_test(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in {
                "lock.json": "{}",
                "proposer.pt": "proposer",
                "reranker.pt": "reranker",
                "validation.json": json.dumps(
                    {"protocol": "S01-E001-v11", "split": "validation", "primary_pass": None}
                ),
                "receipt.json": "{}",
            }.items():
                (root / name).write_text(content, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "freeze_for_test.py"),
                    "--data-lock", str(root / "lock.json"),
                    "--config", str(root / "config.json"),
                    "--proposer", str(root / "proposer.pt"),
                    "--reranker", str(root / "reranker.pt"),
                    "--proposer-receipt", str(root / "receipt.json"),
                    "--validation-evaluation", str(root / "validation.json"),
                    "--output", str(root / "authorization.json"),
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lacks fields", result.stderr)


if __name__ == "__main__":
    unittest.main()
