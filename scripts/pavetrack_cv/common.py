#!/usr/bin/env python3
"""Pure helpers for the PaveTrack two-stage localisation experiment."""

from __future__ import annotations

import ast
import hashlib
import itertools
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence
import zipfile


CRACK_CLASSES = frozenset({"Alligator Crack", "Transverse Crack"})
BACKGROUND_DISTRESS_CLASSES = frozenset({"Pothole", "Patch"})
SPLIT_KEYS = ("train_locations", "validation_locations", "confirmatory_test_locations")
PARTITION_KEYS = (
    *SPLIT_KEYS,
    "previously_viewed_test_locations_excluded_from_confirmation",
    "reserve_test_locations",
)


@dataclass(frozen=True)
class Detection:
    image_id: str
    location: str
    box: tuple[float, float, float, float]
    score: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


PROTOCOL = "S01-E001-v7"


def validate_torch_checkpoint_container(path: Path) -> None:
    """Cheap preflight only; semantic validators below are the authorization gate."""

    if not zipfile.is_zipfile(path):
        raise ValueError(f"model artifact is not a PyTorch ZIP checkpoint: {path}")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if not any(name.endswith("/data.pkl") or name == "data.pkl" for name in names):
        raise ValueError(f"PyTorch checkpoint lacks data.pkl: {path}")
    if not any("/data/" in name and not name.endswith("/") for name in names):
        raise ValueError(f"PyTorch checkpoint lacks tensor storage: {path}")


def yolo_architecture_sha256(model_yaml: Mapping[str, object]) -> str:
    keys = ("backbone", "head", "scales", "scale", "yaml_file", "ch")
    payload = {key: model_yaml.get(key) for key in keys}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def module_graph_sha256(model: object) -> str:
    """Fingerprint instantiated module types, connectivity and tensor shapes."""

    def frozen_attribute(value: object) -> object:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, (list, tuple)):
            converted = [frozen_attribute(item) for item in value]
            return converted if all(item is not _UNSUPPORTED for item in converted) else _UNSUPPORTED
        if isinstance(value, dict) and all(isinstance(key, (str, int)) for key in value):
            converted = {str(key): frozen_attribute(item) for key, item in value.items()}
            return converted if all(item is not _UNSUPPORTED for item in converted.values()) else _UNSUPPORTED
        return _UNSUPPORTED

    rows = []
    for name, module in model.named_modules():
        attributes = {}
        for attribute_name, value in vars(module).items():
            if attribute_name.startswith("_") or attribute_name == "training":
                continue
            converted = frozen_attribute(value)
            if converted is not _UNSUPPORTED:
                attributes[attribute_name] = converted
        rows.append(
            {
                "name": name,
                "class": f"{module.__class__.__module__}.{module.__class__.__name__}",
                "parameters": [
                    (parameter_name, list(parameter.shape))
                    for parameter_name, parameter in module.named_parameters(recurse=False)
                ],
                "buffers": [
                    (buffer_name, list(buffer.shape))
                    for buffer_name, buffer in module.named_buffers(recurse=False)
                ],
                "f": getattr(module, "f", None),
                "i": getattr(module, "i", None),
                "extra_repr": module.extra_repr(),
                "attributes": attributes,
                "instance_forward_override": "forward" in vars(module),
                "hook_counts": {
                    hook_name: len(getattr(module, hook_name, {}))
                    for hook_name in (
                        "_forward_hooks",
                        "_forward_pre_hooks",
                        "_backward_hooks",
                        "_state_dict_hooks",
                        "_load_state_dict_pre_hooks",
                    )
                },
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_UNSUPPORTED = object()


def validate_proposer_checkpoint(path: Path, config: Mapping[str, object]) -> None:
    """Load the artifact as an Ultralytics detector and verify the frozen head."""

    validate_torch_checkpoint_container(path)
    try:
        from ultralytics import YOLO

        detector = YOLO(str(path.resolve()), task="detect")
    except Exception as error:
        raise ValueError(f"proposer is not a loadable Ultralytics checkpoint: {path}") from error
    names = {int(key): str(value) for key, value in detector.names.items()}
    if names != {0: "Crack"}:
        raise ValueError(f"proposer class mapping is not the frozen binary head: {names}")
    head = detector.model.model[-1]
    if int(getattr(head, "nc", -1)) != 1:
        raise ValueError("proposer detection head does not have exactly one class")
    model_yaml = getattr(detector.model, "yaml", None)
    if not isinstance(model_yaml, dict):
        raise ValueError("proposer checkpoint lacks Ultralytics architecture metadata")
    observed_architecture = yolo_architecture_sha256(model_yaml)
    expected_architecture = config["proposer"]["architecture_sha256"]
    if observed_architecture != expected_architecture:
        raise ValueError(
            "proposer architecture differs from frozen YOLO11n: "
            f"expected={expected_architecture}, observed={observed_architecture}"
        )
    observed_graph = module_graph_sha256(detector.model)
    expected_graph = config["proposer"]["instantiated_graph_sha256"]
    if observed_graph != expected_graph:
        raise ValueError(
            "proposer instantiated graph differs from frozen one-class YOLO11n: "
            f"expected={expected_graph}, observed={observed_graph}"
        )


def validate_reranker_checkpoint(path: Path, expected_lineage: Mapping[str, object] | None = None) -> dict:
    """Load and structurally validate the exact MobileNetV3-small artifact."""

    validate_torch_checkpoint_container(path)
    try:
        import torch
        from torch import nn
        from torchvision import models

        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as error:
        raise ValueError(f"reranker is not a loadable weights-only checkpoint: {path}") from error
    required = {"state_dict", "class_to_idx", "epoch", "validation_loss", "lineage"}
    if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
        raise ValueError("reranker checkpoint lacks the frozen training schema")
    if checkpoint["class_to_idx"] != {"background": 0, "crack": 1}:
        raise ValueError("reranker checkpoint has the wrong class mapping")
    model = models.mobilenet_v3_small(weights=None)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 2)
    expected_state = model.state_dict()
    observed_state = checkpoint["state_dict"]
    if set(observed_state) != set(expected_state):
        raise ValueError("reranker state_dict keys differ from MobileNetV3-small")
    for key, expected_tensor in expected_state.items():
        tensor = observed_state[key]
        if not isinstance(tensor, torch.Tensor) or tensor.shape != expected_tensor.shape:
            raise ValueError(f"reranker tensor shape differs at {key}")
        if tensor.is_floating_point() and not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"reranker contains non-finite parameters at {key}")
    lineage = checkpoint["lineage"]
    if not isinstance(lineage, dict):
        raise ValueError("reranker checkpoint lacks lineage")
    if expected_lineage is not None:
        for field, expected in expected_lineage.items():
            if lineage.get(field) != expected:
                raise ValueError(f"reranker checkpoint lineage mismatch at {field}")
    return checkpoint


def validate_producer_runtime(config: Mapping[str, object], device: str | None = None) -> None:
    """Fail before claim-bearing work if the frozen producer runtime drifts."""

    expected = config["producer_runtime"]
    observed = {
        "hostname": platform.node(),
        "python": platform.python_version(),
        "torch": importlib.metadata.version("torch"),
        "torchvision": importlib.metadata.version("torchvision"),
        "ultralytics": importlib.metadata.version("ultralytics"),
        "pandas": importlib.metadata.version("pandas"),
        "openpyxl": importlib.metadata.version("openpyxl"),
    }
    import torch

    observed["cuda_runtime"] = str(torch.version.cuda)
    for field, value in observed.items():
        if str(expected[field]).lower() != str(value).lower():
            raise RuntimeError(
                f"producer runtime mismatch at {field}: expected={expected[field]!r}, observed={value!r}"
            )
    expected_executable = Path(str(expected["python_executable"])).resolve()
    if Path(sys.executable).resolve() != expected_executable:
        raise RuntimeError(
            f"producer Python mismatch: expected={expected_executable}, observed={Path(sys.executable).resolve()}"
        )
    if device is not None:
        normalized = device if device.startswith("cuda:") else f"cuda:{device}"
        if normalized != expected["device"]:
            raise RuntimeError(
                f"producer device mismatch: expected={expected['device']!r}, observed={normalized!r}"
            )
        if not torch.cuda.is_available():
            raise RuntimeError("frozen CUDA device is unavailable")
        if "CUDA_VISIBLE_DEVICES" in os.environ:
            raise RuntimeError("CUDA_VISIBLE_DEVICES remapping is forbidden for this frozen run")
        device_index = int(normalized.split(":", 1)[1])
        if torch.cuda.device_count() <= device_index:
            raise RuntimeError(
                f"frozen CUDA index {device_index} is absent; count={torch.cuda.device_count()}"
            )
        properties = torch.cuda.get_device_properties(device_index)
        torch_name = properties.name
        if torch_name != expected["gpu_name"]:
            raise RuntimeError(
                f"GPU name mismatch: expected={expected['gpu_name']!r}, observed={torch_name!r}"
            )
        query = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,uuid,pci.bus_id,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        rows = [tuple(part.strip() for part in line.split(",")) for line in query.stdout.splitlines()]
        torch_uuid = f"GPU-{properties.uuid}"
        if torch_uuid.lower() != str(expected["gpu_uuid"]).lower():
            raise RuntimeError(
                f"Torch-visible GPU UUID mismatch: expected={expected['gpu_uuid']!r}, "
                f"observed={torch_uuid!r}"
            )
        matching = [row for row in rows if len(row) == 5 and row[2].lower() == torch_uuid.lower()]
        if len(matching) != 1 or len(matching[0]) != 5:
            raise RuntimeError(f"could not resolve Torch cuda:{device_index} by physical UUID")
        physical_index, gpu_name, gpu_uuid, pci_bus_id, driver_version = matching[0]
        observed_gpu = {
            "gpu_physical_index": physical_index,
            "gpu_name": gpu_name,
            "gpu_uuid": gpu_uuid,
            "gpu_pci_bus_id": pci_bus_id.upper(),
            "nvidia_driver": driver_version,
        }
        for field, value in observed_gpu.items():
            if str(expected[field]).upper() != str(value).upper():
                raise RuntimeError(
                    f"producer runtime mismatch at {field}: "
                    f"expected={expected[field]!r}, observed={value!r}"
                )


def validate_prepared_record_hashes(payload: Mapping[str, object]) -> None:
    """Bind every materialized image and detector label to the manifest bytes."""

    required = {"prepared_image", "prepared_image_sha256", "prepared_label", "prepared_label_sha256"}
    for record in payload["records"]:
        missing = required - set(record)
        if missing:
            raise ValueError(f"prepared record lacks content identity: {sorted(missing)}")
        image_path = Path(record["prepared_image"])
        label_path = Path(record["prepared_label"])
        if sha256_file(image_path) != record["prepared_image_sha256"]:
            raise ValueError(f"prepared image content hash mismatch: {image_path}")
        if sha256_file(label_path) != record["prepared_label_sha256"]:
            raise ValueError(f"prepared label content hash mismatch: {label_path}")


def verify_test_authorization_chain(
    authorization_path: Path,
    data_lock_path: Path,
    proposer_path: Path,
    reranker_path: Path,
    validation_evaluation_path: Path,
    proposer_receipt_path: Path,
    run_config_path: Path,
) -> dict:
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    required = {
        "protocol",
        "status",
        "data_lock_sha256",
        "workbook_sha256",
        "proposer_sha256",
        "reranker_sha256",
        "validation_evaluation_sha256",
        "validation_manifest_sha256",
        "proposer_receipt_sha256",
        "run_config_sha256",
        "scoring_rule",
        "primary_metric",
        "primary_pass_delta",
    }
    missing = required - set(authorization)
    if missing:
        raise ValueError(f"test authorization lacks fields: {sorted(missing)}")
    if authorization["protocol"] != PROTOCOL:
        raise ValueError("test authorization has the wrong protocol")
    if authorization["status"] != "authorized_after_model_freeze":
        raise ValueError("test authorization has the wrong status")
    bound_files = {
        "data_lock_sha256": data_lock_path,
        "proposer_sha256": proposer_path,
        "reranker_sha256": reranker_path,
        "validation_evaluation_sha256": validation_evaluation_path,
        "proposer_receipt_sha256": proposer_receipt_path,
        "run_config_sha256": run_config_path,
    }
    for field, path in bound_files.items():
        if authorization[field] != sha256_file(path):
            raise ValueError(f"test authorization mismatch at {field}")
    config = json.loads(run_config_path.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    validate_proposer_checkpoint(proposer_path, config)
    receipt = json.loads(proposer_receipt_path.read_text(encoding="utf-8"))
    if receipt.get("protocol") != PROTOCOL:
        raise ValueError("proposer receipt has the wrong protocol")
    receipt_required = {
        "best_model_sha256",
        "development_manifest_sha256",
        "data_lock_sha256",
        "workbook_sha256",
        "run_config_sha256",
    }
    if not receipt_required.issubset(receipt):
        raise ValueError("proposer receipt lacks the frozen training lineage")
    if receipt.get("best_model_sha256") != authorization["proposer_sha256"]:
        raise ValueError("proposer receipt is not bound to the frozen proposer")
    validation = json.loads(validation_evaluation_path.read_text(encoding="utf-8"))
    if (
        validation.get("protocol") != PROTOCOL
        or validation.get("split") != "validation"
        or validation.get("primary_pass") is not None
    ):
        raise ValueError("authorization source is not a frozen validation evaluation")
    if not isinstance(validation.get("reranker_lineage"), dict):
        raise ValueError("validation evaluation lacks reranker lineage")
    validate_reranker_checkpoint(reranker_path, validation.get("reranker_lineage"))
    for field in (
        "data_lock_sha256",
        "workbook_sha256",
        "proposer_sha256",
        "reranker_sha256",
        "run_config_sha256",
    ):
        if validation.get(field) != authorization[field]:
            raise ValueError(f"validation evaluation differs from authorization at {field}")
    if validation.get("proposer_receipt_sha256") != authorization["proposer_receipt_sha256"]:
        raise ValueError("validation evaluation has a different proposer receipt")
    if validation.get("manifest_sha256") != authorization["validation_manifest_sha256"]:
        raise ValueError("validation manifest differs from authorization")
    return authorization


def load_data_lock(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_data_lock(payload)
    return payload


def validate_data_lock(payload: Mapping[str, object]) -> None:
    groups = {key: {str(value) for value in payload.get(key, [])} for key in PARTITION_KEYS}
    if any(not values for values in groups.values()):
        raise ValueError("every frozen location partition must be present and non-empty")
    for left_index, left_key in enumerate(PARTITION_KEYS):
        for right_key in PARTITION_KEYS[left_index + 1 :]:
            overlap = groups[left_key] & groups[right_key]
            if overlap:
                raise ValueError(f"location overlap between {left_key} and {right_key}: {overlap}")


def locations_for_splits(payload: Mapping[str, object], splits: Sequence[str]) -> set[str]:
    mapping = {
        "train": "train_locations",
        "validation": "validation_locations",
        "test": "confirmatory_test_locations",
    }
    unknown = set(splits) - set(mapping)
    if unknown:
        raise ValueError(f"unknown split names: {sorted(unknown)}")
    selected: set[str] = set()
    for split in splits:
        selected.update(str(value) for value in payload[mapping[split]])
    return selected


def validate_evaluation_membership(payload: Mapping[str, object], lock: Mapping[str, object], split: str) -> list[dict]:
    expected_locations = locations_for_splits(lock, [split])
    header_locations = {str(value) for value in payload["locations"]}
    allowed_header_locations = (
        expected_locations
        if split == "test"
        else locations_for_splits(lock, ["train", "validation"])
    )
    if not expected_locations.issubset(header_locations) or not header_locations.issubset(
        allowed_header_locations
    ):
        raise ValueError("evaluation manifest location header differs from data lock")
    split_records = [record for record in payload["records"] if record["split"] == split]
    if {str(record["reid"]) for record in split_records} != expected_locations:
        raise ValueError("evaluation record locations differ from data lock")
    if any(str(record["reid"]) not in expected_locations for record in split_records):
        raise ValueError("evaluation includes a record outside the frozen split")
    if split == "test" and len(split_records) != len(payload["records"]):
        raise ValueError("confirmatory manifest contains a non-test record")
    return split_records


def parse_numeric_list(cell: object) -> list[float]:
    values = ast.literal_eval(str(cell))
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"expected list or tuple, received {type(values).__name__}")
    return [float(value) for value in values]


def xywh_to_xyxy(box: Sequence[float]) -> tuple[float, float, float, float]:
    if len(box) != 4:
        raise ValueError(f"xywh box must contain four values, received {len(box)}")
    x, y, width, height = (float(value) for value in box)
    return x, y, x + width, y + height


def clip_xyxy(
    box: Sequence[float], width: int, height: int
) -> tuple[float, float, float, float]:
    if len(box) != 4:
        raise ValueError(f"xyxy box must contain four values, received {len(box)}")
    x1, y1, x2, y2 = (float(value) for value in box)
    clipped = (
        min(float(width), max(0.0, x1)),
        min(float(height), max(0.0, y1)),
        min(float(width), max(0.0, x2)),
        min(float(height), max(0.0, y2)),
    )
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        raise ValueError(f"box is empty after clipping: {clipped}")
    return clipped


def xyxy_to_yolo(
    box: Sequence[float], width: int, height: int
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = clip_xyxy(box, width, height)
    return (
        ((x1 + x2) / 2.0) / width,
        ((y1 + y2) / 2.0) / height,
        (x2 - x1) / width,
        (y2 - y1) / height,
    )


def pad_box(
    box: Sequence[float], width: int, height: int, fraction: float = 0.10
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = (float(value) for value in box)
    pad_x = (x2 - x1) * fraction
    pad_y = (y2 - y1) * fraction
    return clip_xyxy((x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y), width, height)


def box_iou(left: Sequence[float], right: Sequence[float]) -> float:
    lx1, ly1, lx2, ly2 = (float(value) for value in left)
    rx1, ry1, rx2, ry2 = (float(value) for value in right)
    intersection = max(0.0, min(lx2, rx2) - max(lx1, rx1)) * max(
        0.0, min(ly2, ry2) - max(ly1, ry1)
    )
    left_area = max(0.0, lx2 - lx1) * max(0.0, ly2 - ly1)
    right_area = max(0.0, rx2 - rx1) * max(0.0, ry2 - ry1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def boxes_overlap(left: Sequence[float], right: Sequence[float]) -> bool:
    lx1, ly1, lx2, ly2 = (float(value) for value in left)
    rx1, ry1, rx2, ry2 = (float(value) for value in right)
    return min(lx2, rx2) > max(lx1, rx1) and min(ly2, ry2) > max(ly1, ry1)


def greedy_match_count(
    predicted_boxes: Sequence[Sequence[float]],
    target_boxes: Sequence[Sequence[float]],
    iou_threshold: float = 0.50,
) -> int:
    unmatched = set(range(len(target_boxes)))
    matches = 0
    for predicted in predicted_boxes:
        candidates = [
            (box_iou(predicted, target_boxes[index]), index) for index in unmatched
        ]
        if not candidates:
            continue
        best_iou, best_index = max(candidates)
        if best_iou >= iou_threshold:
            unmatched.remove(best_index)
            matches += 1
    return matches


def recall_at_fp_per_image(
    detections: Iterable[Detection],
    targets: Mapping[str, Sequence[Sequence[float]]],
    image_locations: Mapping[str, str],
    fp_per_image: float = 1.0,
    iou_threshold: float = 0.50,
) -> dict:
    """Compute location-macro recall at one global ranked operating point.

    A single score threshold is selected for the whole split. The accepted
    prefix is the longest one whose total false positives do not exceed
    ``fp_per_image * number_of_images``. Recall is then computed per location
    and macro-averaged over locations that contain crack targets.
    """

    detections = list(detections)
    images_by_location: dict[str, set[str]] = {}
    for image_id, location in image_locations.items():
        images_by_location.setdefault(location, set()).add(image_id)
    for detection in detections:
        if detection.image_id not in image_locations:
            raise ValueError(f"detection has unknown image_id: {detection.image_id}")
        if image_locations[detection.image_id] != detection.location:
            raise ValueError(f"location mismatch for {detection.image_id}")
    total_images = len(image_locations)
    budget = math.floor(fp_per_image * total_images + 1e-12)
    unmatched = {
        image_id: set(range(len(targets.get(image_id, ())))) for image_id in image_locations
    }
    true_positives_by_location = {location: 0 for location in images_by_location}
    false_positives_by_location = {location: 0 for location in images_by_location}
    false_positives = 0
    used = 0
    threshold = math.inf
    ranked = sorted(
        detections,
        key=lambda item: (
            -item.score,
            item.location,
            item.image_id,
            tuple(float(value) for value in item.box),
        ),
    )
    for score, score_group_iterator in itertools.groupby(ranked, key=lambda item: item.score):
        score_group = list(score_group_iterator)
        trial_unmatched = {image_id: set(indices) for image_id, indices in unmatched.items()}
        outcomes = []
        group_false_positives = 0
        for detection in score_group:
            available = trial_unmatched[detection.image_id]
            candidates = [
                (box_iou(detection.box, targets.get(detection.image_id, ())[index]), index)
                for index in available
            ]
            best_iou, best_index = max(candidates, default=(0.0, -1))
            is_true_positive = best_iou >= iou_threshold
            outcomes.append((detection, is_true_positive, best_index))
            if is_true_positive:
                available.remove(best_index)
            else:
                group_false_positives += 1
        if false_positives + group_false_positives > budget:
            break
        unmatched = trial_unmatched
        used += len(score_group)
        threshold = score
        false_positives += group_false_positives
        for detection, is_true_positive, _ in outcomes:
            if is_true_positive:
                true_positives_by_location[detection.location] += 1
            else:
                false_positives_by_location[detection.location] += 1

    location_rows = []
    for location in sorted(images_by_location):
        images = images_by_location[location]
        target_count = sum(len(targets.get(image_id, ())) for image_id in images)
        true_positives = true_positives_by_location[location]
        recall = true_positives / target_count if target_count else None
        location_rows.append(
            {
                "location": location,
                "images": len(images),
                "targets": target_count,
                "true_positives": true_positives,
                "false_positives": false_positives_by_location[location],
                "recall": recall,
            }
        )
    recalls = [row["recall"] for row in location_rows if row["recall"] is not None]
    return {
        "macro_location_recall": sum(recalls) / len(recalls) if recalls else None,
        "fp_per_image": fp_per_image,
        "images": total_images,
        "budget_fp": budget,
        "detections_used": used,
        "false_positives": false_positives,
        "global_score_threshold": threshold if used else None,
        "iou_threshold": iou_threshold,
        "locations": location_rows,
    }
