from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pavetrack_tiled_cv" / "prepare_confirmatory.py"


class ConfirmatoryFirewallTests(unittest.TestCase):
    def test_invalid_authorization_fails_before_workbook_or_image_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {}
            for name in (
                "workbook.xlsx",
                "config.json",
                "lock.json",
                "validation.json",
                "baseline.pt",
                "tiled.pt",
                "receipt.json",
                "reranker.pt",
            ):
                path = root / name
                path.write_bytes(b"untrusted-placeholder")
                files[name] = path
            workbook_hash = hashlib.sha256(files["workbook.xlsx"].read_bytes()).hexdigest()
            files["lock.json"].write_text(
                json.dumps({"workbook_sha256": workbook_hash}), encoding="utf-8"
            )
            files["config.json"].write_text(
                json.dumps({"protocol": "S01-E002-v1"}), encoding="utf-8"
            )
            authorization = root / "authorization.json"
            authorization.write_text(
                json.dumps(
                    {
                        "protocol": "S01-E002-v1",
                        "status": "not_authorized",
                    }
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                str(SCRIPT),
                "--workbook", str(files["workbook.xlsx"]),
                "--data-lock", str(files["lock.json"]),
                "--config", str(files["config.json"]),
                "--image-root", str(root / "images"),
                "--output", str(root / "output"),
                "--test-authorization", str(authorization),
                "--validation-evaluation", str(files["validation.json"]),
                "--baseline-proposer", str(files["baseline.pt"]),
                "--tiled-proposer", str(files["tiled.pt"]),
                "--tiled-proposer-receipt", str(files["receipt.json"]),
                "--reranker", str(files["reranker.pt"]),
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("test authorization mismatch at status", result.stderr)
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
