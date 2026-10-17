#!/usr/bin/env python3
"""Run exactly one authorized Taobo LOSO crack-recognition challenger.

The executable is intentionally fail closed.  The only Mac-safe mode is
``--preflight-only``; the training path requires a matching external approval,
the Taobo filesystem identity, one CUDA device, a fresh output directory, and
an atomically claimed one-use authorization id before the first optimizer step.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import random
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from skimage.morphology import skeletonize


FREEZE_SHA256 = "0c7d176eb1b707ec39e811fcdeec490ef03fdab006f3f73b420cb17327badaf3"
STATIC_SOURCE_SHA256 = "3f55a626a22680190249f51a7a64754afbcf769a0d836d284d551aa16f47aac8"
B0_SOURCE_SHA256 = "615a57fd16cd8ba81021ee213c95f0b95fdba9d9d73f92f7eff5d1edb4b3a4be"
B1_SOURCE_SHA256 = "435acc2e9c370aca47f5e88b9d65cf5373d319617c139d2ae765e9654bebd01c"
VALIDATOR_SHA256 = "4f4674ff3e6c6781f9e116fc31df9db8ab6dbfa93e143e7045786a513165d6d1"
NO_FIT_RECEIPT_SHA256 = "55ba471d53fc1af09c19ef8768e02746301660784e31d2716dd0e516b90e2800"
MANIFEST_SHA256 = "6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad"
B0_METRICS_SHA256 = "e4757d61011ad151e7e2fcec03b917f5ee01658e8f4bf70b5ec66c86dacdc1e9"
SECTIONS = ("06-1253", "06-2041", "06-2647", "06-8149", "06-8150", "06-8201")
ZERO_CRACK_IDS = ("P002", "P006", "P007", "P031", "P032", "P035", "P036")
PREVIEW_IDS = ("P020", "P008", "P002", "P009")
FULL_SHAPE = (500, 1524)
MODEL_SHAPE = (250, 762)
SEED = 20260807
EPOCHS = 80
BATCH_SIZE = 2
THRESHOLD = 0.35
POS_WEIGHT = 8.0
LEARNING_RATE = 1e-3
FPA_NUMERATOR_MAX = 315
MIN_COMPONENT_SKELETON_PX = 45
TAOBO_CODE_ROOT = Path("/mnt/data2/drtao/wennie")
TAOBO_ARCHIVE_ROOT = Path("/mnt/data2/drtao/pidl_archives")
TAOBO_CLAIM_ROOT = Path("/mnt/data2/drtao/wennie/ltpp_recognition_authorizations")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Block(torch.nn.Module):
    def __init__(self, channels_in: int, channels_out: int):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(channels_in, channels_out, 3, padding=1),
            torch.nn.ReLU(),
            torch.nn.Conv2d(channels_out, channels_out, 3, padding=1),
            torch.nn.ReLU(),
        )

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        return self.net(tensor)


class FrozenTwoChannelTinyUNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.e1, self.e2, self.e3 = Block(2, 8), Block(8, 16), Block(16, 32)
        self.pool = torch.nn.MaxPool2d(2)
        self.u2, self.u1 = torch.nn.Conv2d(32, 16, 1), torch.nn.Conv2d(16, 8, 1)
        self.d2, self.d1 = Block(32, 16), Block(16, 8)
        self.out = torch.nn.Conv2d(8, 1, 1)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        level1 = self.e1(tensor)
        level2 = self.e2(self.pool(level1))
        level3 = self.e3(self.pool(level2))
        decoded2 = torch.nn.functional.interpolate(
            self.u2(level3), size=level2.shape[-2:], mode="bilinear", align_corners=False
        )
        decoded2 = self.d2(torch.cat([decoded2, level2], dim=1))
        decoded1 = torch.nn.functional.interpolate(
            self.u1(decoded2), size=level1.shape[-2:], mode="bilinear", align_corners=False
        )
        return self.out(self.d1(torch.cat([decoded1, level1], dim=1)))


def seed_all() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.use_deterministic_algorithms(True)


def build_channels(gray: np.ndarray, candidate) -> torch.Tensor:
    raw = cv2.resize(gray, (MODEL_SHAPE[1], MODEL_SHAPE[0]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    static_full = candidate.static_line_mask(ink)
    static_small = cv2.resize(static_full, (MODEL_SHAPE[1], MODEL_SHAPE[0]), interpolation=cv2.INTER_NEAREST)
    cue = (static_small > 0).astype(np.float32)
    return torch.from_numpy(np.stack([raw, cue], axis=0))


def make_target(b0, label: Path) -> torch.Tensor:
    line, polygon, _, _ = b0.gold_masks(label, FULL_SHAPE)
    target = cv2.dilate(cv2.bitwise_or(line, polygon), np.ones((3, 3), np.uint8), iterations=1)
    target = cv2.resize(target, (MODEL_SHAPE[1], MODEL_SHAPE[0]), interpolation=cv2.INTER_NEAREST)
    return torch.from_numpy((target > 0).astype(np.float32)[None])


def dice_loss(logit: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    probability = torch.sigmoid(logit)
    intersection = (probability * target).sum(dim=(1, 2, 3))
    return (1 - (2 * intersection + 1) / (probability.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3)) + 1)).mean()


def exact_authorization_spec(runner_hash: str) -> dict:
    return {
        "schema": "ltpp_nondestructive_training_authorization_v1",
        "decision": "APPROVE_ONE_TAOBO_TRAINING",
        "authorization_id": "ltpp-recognition-nondestructive-v1-taobo-once",
        "runner_sha256": runner_hash,
        "freeze_sha256": FREEZE_SHA256,
        "static_source_sha256": STATIC_SOURCE_SHA256,
        "validator_sha256": VALIDATOR_SHA256,
        "no_fit_receipt_sha256": NO_FIT_RECEIPT_SHA256,
        "producer": "taobo",
        "map_count": 37,
        "sections": list(SECTIONS),
        "zero_crack_ids": list(ZERO_CRACK_IDS),
        "seed": SEED,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "optimizer": {"name": "Adam", "learning_rate": LEARNING_RATE, "weight_decay": 0.0},
        "loss": {"bce_pos_weight": POS_WEIGHT, "dice_smoothing": 1},
        "threshold": THRESHOLD,
        "final_epoch_only": True,
        "one_complete_six_fold_execution_only": True,
        "no_restart_or_rescue": True,
    }


def validate_authorization(path: Path, runner_hash: str) -> dict:
    require(path.is_file(), "training authorization file is required")
    authorization = json.loads(path.read_text())
    expected = exact_authorization_spec(runner_hash)
    for key, value in expected.items():
        require(authorization.get(key) == value, f"authorization mismatch for {key}")
    require(isinstance(authorization.get("review_text"), str) and "APPROVE_ONE_TAOBO_TRAINING" in authorization["review_text"], "authorization review_text is missing approval decision")
    return authorization


def validate_frozen_inputs(code_root: Path, data_root: Path, no_fit_receipt: Path, b0_metrics: Path) -> dict:
    paths = {
        "freeze": code_root / "docs/experiments/ltpp_geoforecast_crack_recognition_nondestructive_freeze_candidate_20260810.md",
        "static_source": code_root / "scripts/ltpp_extract_crack_candidates.py",
        "b0_source": code_root / "scripts/ltpp_run_crack_recognition_b0.py",
        "b1_source": code_root / "scripts/ltpp_run_crack_recognition_b1.py",
        "validator": code_root / "scripts/ltpp_validate_nondestructive_recognition_freeze.py",
        "manifest": data_root / "adjudicated/adjudicated_manifest.json",
        "no_fit_receipt": no_fit_receipt,
        "b0_metrics": b0_metrics,
    }
    expected = {
        "freeze": FREEZE_SHA256,
        "static_source": STATIC_SOURCE_SHA256,
        "b0_source": B0_SOURCE_SHA256,
        "b1_source": B1_SOURCE_SHA256,
        "validator": VALIDATOR_SHA256,
        "manifest": MANIFEST_SHA256,
        "no_fit_receipt": NO_FIT_RECEIPT_SHA256,
        "b0_metrics": B0_METRICS_SHA256,
    }
    observed = {name: sha256(path) for name, path in paths.items()}
    require(observed == expected, f"frozen input hash mismatch: {observed}")
    receipt = json.loads(no_fit_receipt.read_text())
    require(receipt.get("status") == "PASS_NONDESTRUCTIVE_IMPLEMENTATION_NO_FIT", "no-fit receipt did not pass")
    require(receipt.get("optimizer_steps") == 0 and receipt.get("weights_saved") is False, "no-fit receipt is not zero-fit")
    return observed


def load_samples(data_root: Path, b0, candidate) -> list[dict]:
    manifest = json.loads((data_root / "adjudicated/adjudicated_manifest.json").read_text())
    labels = {}
    sections = {}
    for entry in manifest["files"]:
        label = data_root / "adjudicated" / entry["file"]
        payload = json.loads(label.read_text())
        blind_id = payload["properties"]["primary_blind_id"]
        labels[blind_id] = label
        sections[blind_id] = payload["properties"]["section"]
    samples = []
    for image in sorted((data_root / "primary/images").glob("P*.png")):
        gray = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
        require(gray is not None and gray.shape == FULL_SHAPE and gray.dtype == np.uint8, f"invalid image {image}")
        blind_id = image.stem
        line, polygon, _, gold_lines = b0.gold_masks(labels[blind_id], FULL_SHAPE)
        full_gold = cv2.bitwise_or(line, polygon)
        samples.append({
            "blind_id": blind_id,
            "section": sections[blind_id],
            "image": image,
            "label": labels[blind_id],
            "gray": gray,
            "x": build_channels(gray, candidate),
            "y": make_target(b0, labels[blind_id]),
            "gold_line": line,
            "full_gold": full_gold,
            "gold_lines": gold_lines,
        })
    observed_zero = sorted(sample["blind_id"] for sample in samples if int(sample["full_gold"].sum()) == 0)
    require(len(samples) == 37, "map count is not 37")
    require(tuple(sorted({sample["section"] for sample in samples})) == SECTIONS, "LOSO sections mismatch")
    require(tuple(observed_zero) == ZERO_CRACK_IDS, "zero-crack ids mismatch")
    return samples


def validate_taobo_runtime(output: Path) -> dict:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    require(platform.system() == "Linux", "training is restricted to Taobo Linux")
    require(os.environ.get("LTPP_PRODUCER_ID") == "taobo", "LTPP_PRODUCER_ID must equal taobo")
    require(TAOBO_CODE_ROOT.is_dir(), "Taobo identity root is absent")
    require(output.resolve().is_relative_to(TAOBO_ARCHIVE_ROOT), "output must be under the Taobo archive root")
    require(visible.isdigit(), "CUDA_VISIBLE_DEVICES must name exactly one numeric GPU")
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1, "exactly one visible CUDA device is required")
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "producer_id": os.environ["LTPP_PRODUCER_ID"],
        "cuda_visible_devices": visible,
        "torch": torch.__version__,
        "cuda_device": torch.cuda.get_device_name(0),
    }


def claim_once(authorization: dict, runner_hash: str, output: Path) -> Path:
    TAOBO_CLAIM_ROOT.mkdir(parents=True, exist_ok=True)
    claim = TAOBO_CLAIM_ROOT / f"{authorization['authorization_id']}.claimed.json"
    payload = {
        "status": "AUTHORIZATION_CONSUMED_BEFORE_FIRST_OPTIMIZER_STEP",
        "authorization_id": authorization["authorization_id"],
        "runner_sha256": runner_hash,
        "output": str(output),
        "hostname": socket.gethostname(),
        "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return claim


def sentinel_metrics(binary: np.ndarray) -> dict:
    occupancy = binary.astype(bool)
    count, labels = cv2.connectedComponents(occupancy.astype(np.uint8), connectivity=8)
    qualifying = sum(int(skeletonize(labels == component).sum()) >= MIN_COMPONENT_SKELETON_PX for component in range(1, count))
    pixels = int(occupancy.sum())
    return {
        "occupancy_pixels": pixels,
        "fpa": pixels / float(FULL_SHAPE[0] * FULL_SHAPE[1]),
        "qualifying_component_count": int(qualifying),
        "pass": pixels <= FPA_NUMERATOR_MAX and qualifying == 0,
    }


def evaluate_one(model, sample: dict, b0, device: torch.device) -> tuple[dict, np.ndarray]:
    model.eval()
    with torch.no_grad():
        probability = torch.sigmoid(model(sample["x"][None].to(device))).cpu().numpy()[0, 0]
    probability = cv2.resize(probability, (FULL_SHAPE[1], FULL_SHAPE[0]), interpolation=cv2.INTER_LINEAR)
    occupancy = (probability >= THRESHOLD).astype(np.uint8)
    centerline = skeletonize(occupancy > 0).astype(np.uint8) * 255
    center = b0.distance_metrics(centerline, sample["gold_line"], 10)
    buffered = b0.distance_metrics(occupancy * 255, sample["full_gold"], 10)
    return ({
        "blind_id": sample["blind_id"],
        "section": sample["section"],
        "centerline": center,
        "buffered_mask": buffered,
        "endpoint_distance_m": b0.endpoint_distance(sample["gold_lines"], centerline),
        "sentinel": sentinel_metrics(occupancy) if sample["blind_id"] in ZERO_CRACK_IDS else None,
    }, centerline)


def finite_mean(values: list[float | None]) -> float | None:
    kept = [value for value in values if value is not None and np.isfinite(value)]
    return float(np.mean(kept)) if kept else None


def summarize(rows: list[dict], b0_metrics: dict) -> tuple[dict, dict]:
    pred_weight = sum(max(1, row["centerline"]["pred_pixels"]) for row in rows)
    gold_weight = sum(max(1, row["centerline"]["gold_pixels"]) for row in rows)
    precision = sum(row["centerline"]["precision"] * max(1, row["centerline"]["pred_pixels"]) for row in rows) / pred_weight
    recall = sum(row["centerline"]["recall"] * max(1, row["centerline"]["gold_pixels"]) for row in rows) / gold_weight
    pooled = {
        "centerline_precision_weighted": float(precision),
        "centerline_recall_weighted": float(recall),
        "centerline_f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
        "mean_matched_centerline_distance_m": finite_mean([row["centerline"]["mean_matched_distance_m"] for row in rows]),
        "mean_matched_endpoint_distance_m": finite_mean([row["endpoint_distance_m"] for row in rows]),
    }
    sections = {}
    improved = 0
    for section in SECTIONS:
        group = [row for row in rows if row["section"] == section]
        f1 = float(np.mean([row["centerline"]["f1"] for row in group]))
        recall_mean = float(np.mean([row["centerline"]["recall"] for row in group]))
        b0_f1 = float(b0_metrics["section_summary"][section]["centerline_f1_mean"])
        is_improved = f1 > b0_f1
        improved += int(is_improved)
        sections[section] = {"map_count": len(group), "centerline_f1_mean": f1, "centerline_recall_mean": recall_mean, "b0_f1_mean": b0_f1, "improved_over_b0": is_improved}
    sentinel_rows = {row["blind_id"]: row["sentinel"] for row in rows if row["sentinel"] is not None}
    gates = {
        "pooled_centerline_f1_ge_0_80": pooled["centerline_f1"] >= 0.80,
        "mean_centerline_distance_le_0_10m": pooled["mean_matched_centerline_distance_m"] is not None and pooled["mean_matched_centerline_distance_m"] <= 0.10,
        "mean_endpoint_distance_le_0_20m": pooled["mean_matched_endpoint_distance_m"] is not None and pooled["mean_matched_endpoint_distance_m"] <= 0.20,
        "at_least_four_sections_improve_over_b0": improved >= 4,
        "no_section_recall_below_0_70": all(item["centerline_recall_mean"] >= 0.70 for item in sections.values()),
        "zero_crack_and_sentinel": len(sentinel_rows) == 7 and all(item["pass"] for item in sentinel_rows.values()),
    }
    return {"pooled": pooled, "sections": sections, "zero_crack_sentinel": sentinel_rows, "gates": gates, "pass": all(gates.values())}, gates


def render_review_panel(previews: dict, output: Path) -> None:
    figure, axes = plt.subplots(len(PREVIEW_IDS), 4, figsize=(16, 7.5), constrained_layout=True)
    for column, title in enumerate(("Raw grayscale", "Adjudicated gold", "Frozen challenger", "Green=TP Red=FP Blue=FN")):
        axes[0, column].set_title(title, fontweight="bold")
    for row_index, blind_id in enumerate(PREVIEW_IDS):
        sample, prediction = previews[blind_id]
        gray = sample["gray"]
        gold = sample["full_gold"] > 0
        pred = prediction > 0
        gold_panel = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB); gold_panel[gold] = (0, 180, 0)
        pred_panel = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB); pred_panel[pred] = (220, 0, 0)
        overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        overlay[gold & pred] = (0, 180, 0); overlay[~gold & pred] = (220, 0, 0); overlay[gold & ~pred] = (0, 90, 220)
        for column, panel in enumerate((gray, gold_panel, pred_panel, overlay)):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None, aspect="auto")
            axes[row_index, column].axis("off")
        axes[row_index, 0].text(0.01, 0.95, blind_id, transform=axes[row_index, 0].transAxes, va="top", bbox={"facecolor": "white", "alpha": 0.9})
    figure.savefig(output, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    output.with_suffix(".md").write_text(
        "# Frozen challenger review panel\n\n"
        "## Figure question\nDoes the single authorized challenger recognize current-map crack geometry on the four owner-audited maps?\n\n"
        "## Data provenance\nFrozen 37-map carrier, adjudicated crack gold, and final-epoch LOSO predictions from the exact hash-locked runner.\n\n"
        "## How to read\nRows are P020, P008, P002, and P009. Columns show raw map, gold, prediction, and TP/FP/FN overlay. Green is TP, red is FP, blue is FN.\n\n"
        "## Limitation and claim boundary\nThis is current-map scanned-form recognition only. It is not forecasting, physical-width measurement, or ordinary road-photo validation.\n"
    )


def preflight_payload(code_root: Path, data_root: Path, no_fit_receipt: Path, b0_metrics: Path) -> dict:
    runner_hash = sha256(Path(__file__).resolve())
    frozen_hashes = validate_frozen_inputs(code_root, data_root, no_fit_receipt, b0_metrics)
    candidate = load_module("ltpp_candidate_nondestructive_preflight", code_root / "scripts/ltpp_extract_crack_candidates.py")
    b0 = load_module("ltpp_b0_nondestructive_preflight", code_root / "scripts/ltpp_run_crack_recognition_b0.py")
    samples = load_samples(data_root, b0, candidate)
    return {
        "status": "PASS_RUNNER_PREFLIGHT_NO_FIT__TRAINING_AUTHORIZATION_REQUIRED",
        "runner_sha256": runner_hash,
        "frozen_hashes": frozen_hashes,
        "map_count": len(samples),
        "sections": list(SECTIONS),
        "zero_crack_ids": list(ZERO_CRACK_IDS),
        "parameter_count": sum(parameter.numel() for parameter in FrozenTwoChannelTinyUNet().parameters()),
        "optimizer_steps": 0,
        "real_image_model_forward_passes": 0,
        "weights_saved": False,
        "authorization_spec": exact_authorization_spec(runner_hash),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--no-fit-receipt", type=Path, required=True)
    parser.add_argument("--b0-metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--training-authorization", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    code_root = args.code_root.resolve()
    data_root = args.data_root.resolve()
    payload = preflight_payload(code_root, data_root, args.no_fit_receipt.resolve(), args.b0_metrics.resolve())
    if args.preflight_only:
        print(json.dumps(payload, indent=2))
        return 0

    require(args.output is not None, "--output is required for authorized training")
    require(args.training_authorization is not None, "--training-authorization is required")
    output = args.output.resolve()
    require(not output.exists(), "fresh non-existing output directory is required; restart/resume is prohibited")
    authorization = validate_authorization(args.training_authorization.resolve(), payload["runner_sha256"])
    runtime = validate_taobo_runtime(output)
    claim = claim_once(authorization, payload["runner_sha256"], output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "RUN_PROVENANCE.json").write_text(json.dumps({**runtime, **payload, "authorization_path": str(args.training_authorization.resolve()), "authorization_sha256": sha256(args.training_authorization.resolve()), "claim_path": str(claim)}, indent=2) + "\n")

    candidate = load_module("ltpp_candidate_nondestructive_train", code_root / "scripts/ltpp_extract_crack_candidates.py")
    b0 = load_module("ltpp_b0_nondestructive_train", code_root / "scripts/ltpp_run_crack_recognition_b0.py")
    samples = load_samples(data_root, b0, candidate)
    baseline = json.loads(args.b0_metrics.read_text())
    device = torch.device("cuda")
    torch.set_num_threads(2)
    rows = []
    previews = {}
    optimizer_steps = 0
    started = time.time()
    for held_section in SECTIONS:
        seed_all()
        model = FrozenTwoChannelTinyUNet().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=0.0)
        bce = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(POS_WEIGHT, device=device))
        training = [sample for sample in samples if sample["section"] != held_section]
        for _epoch in range(EPOCHS):
            model.train()
            random.shuffle(training)
            for index in range(0, len(training), BATCH_SIZE):
                batch = training[index:index + BATCH_SIZE]
                inputs = torch.stack([sample["x"] for sample in batch]).to(device)
                targets = torch.stack([sample["y"] for sample in batch]).to(device)
                optimizer.zero_grad(set_to_none=True)
                logits = model(inputs)
                loss = bce(logits, targets) + dice_loss(logits, targets)
                require(torch.isfinite(loss).item(), "non-finite training loss")
                loss.backward()
                optimizer.step()
                optimizer_steps += 1
        fold_dir = output / "folds" / f"LOSO-{held_section}"
        fold_dir.mkdir(parents=True, exist_ok=False)
        torch.save(model.state_dict(), fold_dir / "final_epoch_model.pt")
        for sample in samples:
            if sample["section"] != held_section:
                continue
            row, prediction = evaluate_one(model, sample, b0, device)
            rows.append(row)
            cv2.imwrite(str(fold_dir / f"{sample['blind_id']}__prediction_centerline.png"), prediction)
            if sample["blind_id"] in PREVIEW_IDS:
                previews[sample["blind_id"]] = (sample, prediction)

    summary, gates = summarize(rows, baseline)
    status = "RECOGNITION_QUALIFIED" if all(gates.values()) else "RECOGNITION_GATE_FAILED"
    metrics = {
        "status": status,
        "runner_sha256": payload["runner_sha256"],
        "authorization_id": authorization["authorization_id"],
        "optimizer_steps": optimizer_steps,
        "fold_count": len(SECTIONS),
        "elapsed_seconds": time.time() - started,
        "summary": summary,
        "rows": rows,
        "claim_boundary": "Current-map recognition on the frozen scanned-form carrier only.",
    }
    metrics_path = output / "metrics_receipt.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")
    panel_path = output / "four_map_visual_panel.png"
    render_review_panel(previews, panel_path)
    decision = output / "decision.md"
    decision.write_text(
        f"# Non-destructive crack-recognition decision\n\nStatus: `{status}`\n\n"
        "This is the terminal result of the single authorized six-fold execution. No restart, rescue run, threshold change, or model variant is authorized.\n\n"
        "Claim boundary: current-map recognition on the frozen scanned-form carrier only.\n"
    )
    assets = [path for path in output.rglob("*") if path.is_file()]
    (output / "output_sha256.json").write_text(json.dumps({str(path.relative_to(output)): sha256(path) for path in sorted(assets)}, indent=2) + "\n")
    print(json.dumps({"status": status, "optimizer_steps": optimizer_steps, "metrics": str(metrics_path), "decision": str(decision)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "FAIL_CLOSED_BEFORE_OR_DURING_AUTHORIZED_EXECUTION", "error": str(error)}), file=sys.stderr)
        raise
