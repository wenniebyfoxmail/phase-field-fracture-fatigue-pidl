"""Synthetic-only tests; no archived data or photographs are accessed."""
import importlib.util
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

import numpy as np

SPEC = importlib.util.spec_from_file_location("independent_d01_halfdepth", Path(__file__).parents[1] / "scripts" / "independent_d01_halfdepth.py")
d01 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d01)


class HalfDepthTests(unittest.TestCase):
    def setUp(self):
        self.s = np.arange(-60, 60.25, 0.25)

    def test_triangle_sloping_background(self):
        deficit = 40 * np.maximum(0, 1 - np.abs(self.s - 2) / 8)
        profile = (170 + 0.5 * self.s - deficit).astype(np.float32)
        result = d01.measure(self.s, profile)
        self.assertTrue(result["valid"])
        self.assertAlmostEqual(result["left_px"], -2, places=12)
        self.assertAlmostEqual(result["right_px"], 6, places=12)
        self.assertAlmostEqual(result["width_px"], 8, places=12)
        self.assertEqual(result["noise"], 0)

    def test_first_equal_peak(self):
        profile = np.full_like(self.s, 200, dtype=np.float32)
        profile[np.abs(self.s) <= 2] = 160
        result = d01.measure(self.s, profile)
        self.assertEqual(result["peak_px"], -2)
        self.assertAlmostEqual(result["width_px"], 4.25, places=12)

    def test_depth_and_resolution(self):
        shallow = 200 - 9 * np.maximum(0, 1 - np.abs(self.s) / 8)
        self.assertEqual(d01.measure(self.s, shallow.astype(np.float32))["reason"], "insufficient_depth")
        narrow = 200 - 40 * np.maximum(0, 1 - np.abs(self.s) / 0.5)
        result = d01.measure(self.s, narrow.astype(np.float32))
        self.assertEqual(result["reason"], "resolution_limited")
        self.assertTrue(np.isnan(result["width_px"]))
        at_threshold = 200 - 10 * np.maximum(0, 1 - np.abs(self.s) / 8)
        self.assertTrue(d01.measure(self.s, at_threshold.astype(np.float32))["valid"])

    def test_shoulder_noise_threshold(self):
        profile = np.full_like(self.s, 200, dtype=np.float32)
        for shoulder in (self.s <= -45, self.s >= 45):
            indices = np.flatnonzero(shoulder)
            profile[indices] += np.concatenate((np.full(30, -15), [0], np.full(30, 15)))
        profile[np.abs(self.s) <= 3] = 170
        result = d01.measure(self.s, profile)
        self.assertGreater(3 * result["noise"], result["depth"])
        self.assertEqual(result["reason"], "insufficient_depth")

    def test_endpoint_censored(self):
        # Isolate endpoint handling using a sparse synthetic offset grid.
        result = d01.measure([-60, -1, 0, 1, 60], np.array([0, -40, -40, -40, 0], dtype=np.float32))
        self.assertEqual(result["reason"], "censored")

    def test_coordinate_separate_path(self):
        shape, working = (1000, 2000), (333, 700)
        H = np.array([[1.02, 0.03, 4], [-0.02, 0.97, -3], [1e-5, -2e-5, 1]])
        inverse = np.linalg.inv(H)
        points = d01.sampling_grid([1000, 500], [0.6, 0.8], self.s)
        for variant in d01.VARIANTS:
            p = d01.sampling_grid([1000, 500], [0.6, 0.8], self.s, variant)
            source = d01.native_to_source(p, inverse, shape, working)
            np.testing.assert_allclose(source, d01.conjugated_check(p, inverse, shape, working), atol=1e-10, rtol=0)
            np.testing.assert_allclose(d01.source_to_origin(source, H, shape, working), p, atol=1e-10, rtol=0)
        np.testing.assert_allclose(d01.native_to_source(points, np.eye(3), shape, working), points, atol=1e-12, rtol=0)

    def test_bilinear_float32_nearest_even(self):
        yy, xx = np.mgrid[:12, :12]
        image = (2 * xx + 3 * yy).astype(np.float32)
        points = np.array([[2 + 1 / 64, 3], [2 + 3 / 64, 3], [2 + 63 / 64, 3], [2.2, 3.3]])
        quantised = d01.bilinear(image, points)
        np.testing.assert_array_equal(quantised[:3], np.array([13, 13.125, 15], dtype=np.float32))
        continuous = d01.bilinear(image, points, quantised=False)
        np.testing.assert_allclose(continuous, 2 * points[:, 0] + 3 * points[:, 1], atol=2e-6, rtol=0)
        self.assertEqual(quantised.dtype, np.float32)
        with self.assertRaisesRegex(ValueError, "sample_out_of_bounds"):
            d01.bilinear(image, [[-0.1, 2]])

    def test_pointwise_median(self):
        image = np.full((20, 20), 100, dtype=np.float32)
        image[8, :] = 0
        image[12, :] = 255
        points = d01.sampling_grid([10, 10], [1, 0], np.array([-2, 0, 2]))
        np.testing.assert_array_equal(d01.median_source_profile(image, points), [100, 100, 100])

    def make_synthetic_inputs(self, root):
        from PIL import Image
        root.mkdir()
        x = np.arange(256)
        intensity = (180 - 40 * np.maximum(0, 1 - np.abs(x - 128) / 8)).astype(np.uint8)
        image_path = root / "synthetic.png"
        Image.fromarray(np.tile(intensity, (256, 1))).save(image_path)
        raw = image_path.read_bytes()
        geometry = {"beams": {}}
        # Analytic stored profile independently interpolates the synthetic ramp.
        profile = np.interp(128 + self.s, x, intensity).astype(np.float32)
        for beam, count in ((4, 4), (5, 6), (6, 4)):
            loads = np.arange(count, dtype=np.float64) * 10 + 10
            geometry["beams"][str(beam)] = dict(native_shape=[256, 256], working_shape=[80, 91],
                transects=[dict(id=i + 1, center=[128, 128], normal=[1, 0]) for i in range(12)],
                stages=[dict(beam=beam, nominal_load_kN=float(load), source_image=str(image_path),
                             bytes=len(raw), crc32=f"{zlib.crc32(raw) & 0xffffffff:08x}") for load in loads])
            np.savez(root / f"Beam{beam}_inputs.npz", normal_offsets_native_px=self.s,
                     profiles=np.broadcast_to(profile, (count, 12, len(self.s))).copy(), loads_kN=loads,
                     homographies=np.broadcast_to(np.eye(3), (count, 3, 3)).copy())
        (root / "geometry.json").write_text(json.dumps(geometry))

    def test_complete_synthetic_execution_schema(self):
        with tempfile.TemporaryDirectory(prefix="independent_d01_synthetic_") as tmp:
            root = Path(tmp)
            self.make_synthetic_inputs(root / "inputs")
            d01.execute(root / "inputs", root / "output", 120)
            output = root / "output"
            receipt = json.loads((output / "runtime_receipt.json").read_text())
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(receipt["completed_rows"], 168)
            for filename, expected in (("independent_measurements.csv", 168), ("source_replay.csv", 168), ("location_variants.csv", 840)):
                with (output / filename).open() as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), expected)
            self.assertTrue(all(row["valid"] == "True" for row in rows))
            with (output / "source_replay.csv").open() as handle:
                replays = list(csv.DictReader(handle))
            self.assertTrue(all(float(row["quantised_profile_max_abs_diff"]) == 0 for row in replays))
            self.assertEqual(len(json.loads((output / "examples.json").read_text())), 6)
            with np.load(output / "examples.npz", allow_pickle=False) as arrays:
                self.assertEqual(arrays["beam4_stage0_t6_strip"].shape, (49, 121))
            coordinate = json.loads((output / "coordinate_summary.json").read_text())
            self.assertEqual(coordinate["sample_points"], 168 * 5 * 5 * 481)
            self.assertLess(coordinate["max_roundtrip_abs_px"], 1e-10)
            with self.assertRaises(FileExistsError):
                d01.execute(root / "inputs", root / "output", 120)

    def test_budget_partial_output(self):
        with tempfile.TemporaryDirectory(prefix="independent_d01_budget_synthetic_") as tmp:
            root = Path(tmp)
            self.make_synthetic_inputs(root / "inputs")
            ticks = iter(np.arange(0, 10, 0.01))
            with patch.object(d01.time, "monotonic", side_effect=lambda: float(next(ticks))):
                with self.assertRaises(d01.BudgetExceeded):
                    d01.execute(root / "inputs", root / "output", 0.15)
            receipt = json.loads((root / "output" / "runtime_receipt.json").read_text())
            self.assertEqual(receipt["status"], "budget_stopped")
            self.assertLess(receipt["completed_rows"], 168)
            self.assertTrue((root / "output" / "location_variants.csv").exists())

    def test_identity_mismatch_stops_before_measurements(self):
        with tempfile.TemporaryDirectory(prefix="independent_d01_identity_synthetic_") as tmp:
            root = Path(tmp)
            self.make_synthetic_inputs(root / "inputs")
            geometry_path = root / "inputs" / "geometry.json"
            geometry = json.loads(geometry_path.read_text())
            geometry["beams"]["4"]["stages"][0]["crc32"] = "00000000"
            geometry_path.write_text(json.dumps(geometry))
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                d01.execute(root / "inputs", root / "output", 120)
            receipt = json.loads((root / "output" / "runtime_receipt.json").read_text())
            self.assertEqual(receipt["status"], "stopped")
            self.assertEqual(receipt["completed_rows"], 0)

    def test_geometry_and_load_identity_checks(self):
        for case in ("beam_keys", "transect_order", "transect_duplicate", "stage_count", "loads_nonincreasing"):
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="independent_d01_schema_synthetic_") as tmp:
                root = Path(tmp)
                self.make_synthetic_inputs(root / "inputs")
                geometry_path = root / "inputs" / "geometry.json"
                geometry = json.loads(geometry_path.read_text())
                if case == "beam_keys":
                    geometry["beams"]["7"] = geometry["beams"].pop("6")
                elif case == "transect_order":
                    geometry["beams"]["4"]["transects"].reverse()
                elif case == "transect_duplicate":
                    geometry["beams"]["4"]["transects"][1]["id"] = 1
                elif case == "stage_count":
                    geometry["beams"]["4"]["stages"].pop()
                else:
                    npz_path = root / "inputs" / "Beam4_inputs.npz"
                    with np.load(npz_path, allow_pickle=False) as archive:
                        arrays = {k: archive[k].copy() for k in archive.files}
                    arrays["loads_kN"][1] = arrays["loads_kN"][0]
                    np.savez(npz_path, **arrays)
                geometry_path.write_text(json.dumps(geometry))
                with self.assertRaises(ValueError):
                    d01.execute(root / "inputs", root / "output", 120)
                receipt = json.loads((root / "output" / "runtime_receipt.json").read_text())
                self.assertEqual(receipt["status"], "stopped")
                self.assertEqual(receipt["completed_rows"], 0)


if __name__ == "__main__":
    unittest.main()
