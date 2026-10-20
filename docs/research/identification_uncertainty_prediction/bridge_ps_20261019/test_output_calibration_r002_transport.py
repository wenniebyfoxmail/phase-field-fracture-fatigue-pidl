"""Small source-transport tests only; no real data, fits, remote access or launch."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import output_calibration_r002_transport as t

ARCHIVE_PATH = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/preparations/OUTPUT-CALIBRATION-20261020-R002/source.tar')
AUTHORITY_PATH = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-OUTPUT-CALIBRATION-C27A25-20261020-R002/execution_authority.json')


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ARCHIVE_PATH.read_bytes()
        cls.authority = json.loads(AUTHORITY_PATH.read_bytes())

    def test_payload_roundtrip_preserves_quote_unicode_and_archive_status(self):
        authority = {**self.authority, 'transport_test_text': "ARCHIVE AUTHORITY ' \" 中文 $() `literal`"}
        framed = t.frame(self.raw, authority)
        raw, restored = t.decode(io.BytesIO(framed))
        self.assertEqual(raw, self.raw)
        self.assertEqual(restored, authority)
        self.assertLess(len(framed), len(self.raw))
        self.assertIn('EXACT_REVIEWED_ARCHIVE_DEPLOYED_NO_LAUNCH_YET', Path(t.__file__).read_text())

    def test_wire_corruption_is_rejected(self):
        framed = bytearray(t.frame(self.raw, self.authority))
        framed[-12] ^= 1
        with self.assertRaisesRegex(ValueError, 'wire hash'):
            t.decode(io.BytesIO(framed))

    def test_truncation_is_rejected(self):
        with self.assertRaises(EOFError):
            t.decode(io.BytesIO(t.frame(self.raw, self.authority)[:-10]))

    def test_real_source_only_deployment_matches_all_bytes_without_launch(self):
        with tempfile.TemporaryDirectory() as d, patch.object(t.subprocess, 'Popen', side_effect=AssertionError('no local launch')):
            root = Path(d) / 'fresh'
            result = t.deploy(root, self.raw, self.authority)
            files = t.source_members(self.raw, self.authority)
            for name, data in files.items():
                self.assertEqual((root / 'code' / name).read_bytes(), data)
            self.assertEqual((root / 'source_package.tar').read_bytes(), self.raw)
            self.assertEqual(json.loads((root / 'execution_authority.json').read_bytes()), self.authority)
            self.assertEqual(result['status'], 'EXACT_REVIEWED_ARCHIVE_DEPLOYED_NO_LAUNCH_YET')
            self.assertFalse(result['launch_submitted'])
            self.assertFalse(result['scientific_inputs_read'])

    def test_existing_root_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sentinel = root / 'existing'
            sentinel.write_text('preserve')
            with self.assertRaises(FileExistsError):
                t.deploy(root, self.raw, self.authority)
            self.assertEqual(list(root.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), 'preserve')

    def test_authority_mismatch_fails_before_first_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'not-created'
            with self.assertRaisesRegex(ValueError, 'authority identity'):
                t.deploy(root, self.raw, {**self.authority, 'package_sha256': 'wrong'})
            self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()
