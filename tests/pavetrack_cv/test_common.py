from pathlib import Path
import sys
import types
import unittest
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pavetrack_cv"
sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    Detection,
    box_iou,
    boxes_overlap,
    clip_xyxy,
    greedy_match_count,
    locations_for_splits,
    module_graph_sha256,
    recall_at_fp_per_image,
    validate_data_lock,
    validate_producer_runtime,
    yolo_architecture_sha256,
    xywh_to_xyxy,
    xyxy_to_yolo,
)


class DataLockTests(unittest.TestCase):
    def setUp(self):
        self.lock = {
            "train_locations": ["1", "2"],
            "validation_locations": ["3"],
            "confirmatory_test_locations": ["4"],
            "previously_viewed_test_locations_excluded_from_confirmation": ["5"],
            "reserve_test_locations": ["6"],
        }

    def test_valid_lock_and_selection(self):
        validate_data_lock(self.lock)
        self.assertEqual(locations_for_splits(self.lock, ["train", "validation"]), {"1", "2", "3"})
        self.assertNotIn("4", locations_for_splits(self.lock, ["train", "validation"]))

    def test_overlap_fails(self):
        self.lock["confirmatory_test_locations"] = ["2"]
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_data_lock(self.lock)

    def test_previously_viewed_confirmation_fails(self):
        self.lock["confirmatory_test_locations"] = ["5"]
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_data_lock(self.lock)

    def test_reserve_overlap_fails(self):
        self.lock["reserve_test_locations"] = ["2"]
        with self.assertRaisesRegex(ValueError, "reserve_test_locations"):
            validate_data_lock(self.lock)


class RuntimeFreezeTests(unittest.TestCase):
    def test_instantiated_graph_fingerprint_detects_same_shape_stride_change(self):
        class Leaf:
            def __init__(self, stride):
                self.training = False
                self.stride = stride

            def named_parameters(self, recurse=False):
                return []

            def named_buffers(self, recurse=False):
                return []

            def extra_repr(self):
                return f"stride={self.stride}"

        class Graph:
            def __init__(self, stride):
                self.training = False
                self.leaf = Leaf(stride)

            def named_modules(self):
                return [("", self), ("leaf", self.leaf)]

            def named_parameters(self, recurse=False):
                return []

            def named_buffers(self, recurse=False):
                return []

            def extra_repr(self):
                return ""

        self.assertNotEqual(module_graph_sha256(Graph(2)), module_graph_sha256(Graph(1)))

    def test_yolo_architecture_fingerprint_is_scale_sensitive(self):
        base = {
            "backbone": [[-1, 1, "Conv", [64, 3, 2]]],
            "head": [[[0], 1, "Detect", ["nc"]]],
            "scales": {"n": [0.5, 0.25, 1024], "s": [0.5, 0.5, 1024]},
            "scale": "n",
            "yaml_file": "yolo11n.yaml",
            "ch": 3,
        }
        changed = {**base, "scale": "s", "yaml_file": "yolo11s.yaml"}
        self.assertNotEqual(yolo_architecture_sha256(base), yolo_architecture_sha256(changed))

    def test_runtime_version_drift_fails(self):
        config = {
            "producer_runtime": {
                "hostname": "D-26-09",
                "python": "3.12.14",
                "python_executable": "/frozen/python",
                "torch": "2.11.0+cu128",
                "torchvision": "0.26.0+cu128",
                "ultralytics": "8.3.205",
                "pandas": "2.3.3",
                "openpyxl": "3.1.5",
                "cuda_runtime": "12.8",
                "device": "cuda:1",
                "gpu_physical_index": 1,
                "gpu_name": "GPU",
                "gpu_uuid": "UUID",
                "gpu_pci_bus_id": "BUS",
                "nvidia_driver": "DRIVER",
            }
        }
        versions = {
            "torch": "WRONG",
            "torchvision": "0.26.0+cu128",
            "ultralytics": "8.3.205",
            "pandas": "2.3.3",
            "openpyxl": "3.1.5",
        }
        fake_torch = types.SimpleNamespace(version=types.SimpleNamespace(cuda="12.8"))
        with (
            mock.patch("common.platform.node", return_value="D-26-09"),
            mock.patch("common.platform.python_version", return_value="3.12.14"),
            mock.patch("common.importlib.metadata.version", side_effect=lambda name: versions[name]),
            mock.patch.dict(sys.modules, {"torch": fake_torch}),
        ):
            with self.assertRaisesRegex(RuntimeError, "mismatch at torch"):
                validate_producer_runtime(config, "cuda:1")

    def test_unavailable_physical_gpu_fails_even_when_device_text_matches(self):
        versions = {
            "torch": "2.11.0+cu128",
            "torchvision": "0.26.0+cu128",
            "ultralytics": "8.3.205",
            "pandas": "2.3.3",
            "openpyxl": "3.1.5",
        }
        config = {
            "producer_runtime": {
                "hostname": "D-26-09",
                "python": "3.12.14",
                "python_executable": sys.executable,
                **versions,
                "cuda_runtime": "12.8",
                "device": "cuda:1",
                "gpu_physical_index": 1,
                "gpu_name": "GPU",
                "gpu_uuid": "UUID",
                "gpu_pci_bus_id": "BUS",
                "nvidia_driver": "DRIVER",
            }
        }
        fake_cuda = types.SimpleNamespace(is_available=lambda: False)
        fake_torch = types.SimpleNamespace(
            version=types.SimpleNamespace(cuda="12.8"), cuda=fake_cuda
        )
        with (
            mock.patch("common.platform.node", return_value="D-26-09"),
            mock.patch("common.platform.python_version", return_value="3.12.14"),
            mock.patch("common.importlib.metadata.version", side_effect=lambda name: versions[name]),
            mock.patch.dict(sys.modules, {"torch": fake_torch}),
        ):
            with self.assertRaisesRegex(RuntimeError, "CUDA device is unavailable"):
                validate_producer_runtime(config, "cuda:1")

    def test_cuda_visible_devices_remapping_fails(self):
        versions = {
            "torch": "2.11.0+cu128",
            "torchvision": "0.26.0+cu128",
            "ultralytics": "8.3.205",
            "pandas": "2.3.3",
            "openpyxl": "3.1.5",
        }
        config = {
            "producer_runtime": {
                "hostname": "D-26-09", "python": "3.12.14",
                "python_executable": sys.executable, **versions,
                "cuda_runtime": "12.8", "device": "cuda:1",
                "gpu_physical_index": 1, "gpu_name": "GPU", "gpu_uuid": "UUID",
                "gpu_pci_bus_id": "BUS", "nvidia_driver": "DRIVER",
            }
        }
        fake_cuda = types.SimpleNamespace(is_available=lambda: True)
        fake_torch = types.SimpleNamespace(
            version=types.SimpleNamespace(cuda="12.8"), cuda=fake_cuda
        )
        with (
            mock.patch("common.platform.node", return_value="D-26-09"),
            mock.patch("common.platform.python_version", return_value="3.12.14"),
            mock.patch("common.importlib.metadata.version", side_effect=lambda name: versions[name]),
            mock.patch.dict(sys.modules, {"torch": fake_torch}),
            mock.patch.dict("common.os.environ", {"CUDA_VISIBLE_DEVICES": "1,0"}, clear=True),
        ):
            with self.assertRaisesRegex(RuntimeError, "remapping is forbidden"):
                validate_producer_runtime(config, "cuda:1")


class BoxTests(unittest.TestCase):
    def test_conversion_and_clipping(self):
        self.assertEqual(xywh_to_xyxy((10, 20, 30, 40)), (10.0, 20.0, 40.0, 60.0))
        self.assertEqual(clip_xyxy((-1, 2, 110, 90), 100, 80), (0.0, 2.0, 100.0, 80.0))
        self.assertEqual(xyxy_to_yolo((0, 0, 100, 50), 200, 100), (0.25, 0.25, 0.5, 0.5))

    def test_iou_and_greedy_matching(self):
        self.assertAlmostEqual(box_iou((0, 0, 10, 10), (5, 0, 15, 10)), 1 / 3)
        predicted = [(0, 0, 10, 10), (20, 20, 30, 30), (0, 0, 9, 9)]
        targets = [(0, 0, 10, 10), (20, 20, 30, 30)]
        self.assertEqual(greedy_match_count(predicted, targets), 2)

    def test_overlap_is_stricter_than_iou_for_background_crop(self):
        broad_crop = (0, 0, 100, 100)
        thin_label = (45, 0, 46, 100)
        self.assertLess(box_iou(broad_crop, thin_label), 0.05)
        self.assertTrue(boxes_overlap(broad_crop, thin_label))


class FixedBudgetMetricTests(unittest.TestCase):
    def test_false_positive_budget_stops_ranked_prefix(self):
        targets = {"a": [(0, 0, 10, 10)], "b": [(0, 0, 10, 10)]}
        locations = {"a": "L1", "b": "L1"}
        detections = [
            Detection("a", "L1", (20, 20, 30, 30), 0.9),  # FP 1
            Detection("a", "L1", (0, 0, 10, 10), 0.8),    # TP 1
            Detection("b", "L1", (20, 20, 30, 30), 0.7),  # FP 2
            Detection("b", "L1", (30, 30, 40, 40), 0.6),  # would exceed budget
            Detection("b", "L1", (0, 0, 10, 10), 0.5),    # cannot be recovered
        ]
        result = recall_at_fp_per_image(detections, targets, locations)
        self.assertEqual(result["budget_fp"], 2)
        self.assertEqual(result["locations"][0]["true_positives"], 1)
        self.assertEqual(result["locations"][0]["false_positives"], 2)
        self.assertEqual(result["macro_location_recall"], 0.5)

    def test_one_global_threshold_prevents_location_specific_optimism(self):
        targets = {"a": [(0, 0, 10, 10)], "b": [(0, 0, 10, 10)]}
        locations = {"a": "A", "b": "B"}
        detections = [
            Detection("a", "A", (20, 20, 30, 30), 0.99),
            Detection("a", "A", (30, 30, 40, 40), 0.98),
            Detection("a", "A", (40, 40, 50, 50), 0.97),
            Detection("b", "B", (0, 0, 10, 10), 0.10),
        ]
        result = recall_at_fp_per_image(detections, targets, locations)
        self.assertEqual(result["budget_fp"], 2)
        self.assertEqual(result["macro_location_recall"], 0.0)

    def test_tied_detection_order_cannot_change_metric(self):
        targets = {"a": [(0, 0, 10, 10)]}
        locations = {"a": "A"}
        tied = [
            Detection("a", "A", (0, 0, 10, 10), 0.5),
            Detection("a", "A", (1, 1, 11, 11), 0.5),
            Detection("a", "A", (20, 20, 30, 30), 0.5),
        ]
        forward = recall_at_fp_per_image(tied, targets, locations)
        reverse = recall_at_fp_per_image(list(reversed(tied)), targets, locations)
        self.assertEqual(forward, reverse)

    def test_negative_location_reports_burden_not_macro_recall(self):
        targets = {"positive": [(0, 0, 10, 10)], "negative": []}
        locations = {"positive": "P", "negative": "N"}
        detections = [Detection("positive", "P", (0, 0, 10, 10), 0.9)]
        result = recall_at_fp_per_image(detections, targets, locations)
        self.assertEqual(result["macro_location_recall"], 1.0)
        negative_row = next(row for row in result["locations"] if row["location"] == "N")
        self.assertIsNone(negative_row["recall"])


if __name__ == "__main__":
    unittest.main()
