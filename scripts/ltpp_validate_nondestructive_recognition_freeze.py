#!/usr/bin/env python3
"""Validate the approved non-destructive recognition freeze without fitting."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from skimage.morphology import skeletonize


FREEZE_SHA256 = "0c7d176eb1b707ec39e811fcdeec490ef03fdab006f3f73b420cb17327badaf3"
STATIC_SOURCE_SHA256 = "3f55a626a22680190249f51a7a64754afbcf769a0d836d284d551aa16f47aac8"
B1_SOURCE_SHA256 = "435acc2e9c370aca47f5e88b9d65cf5373d319617c139d2ae765e9654bebd01c"
MANIFEST_SHA256 = "6a9422bdcef707fa861b05ad0c817d6deaa4e4ad03ea636c46c5820f8b01f4ad"
ZERO_CRACK_IDS = {"P002", "P006", "P007", "P031", "P032", "P035", "P036"}
PREVIEW_IDS = ("P020", "P008", "P002", "P009")
FULL_SHAPE = (500, 1524)
MODEL_SHAPE = (250, 762)
FPA_NUMERATOR_MAX = 315
MIN_COMPONENT_SKELETON_PX = 45


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
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
        self.e1 = Block(2, 8)
        self.e2 = Block(8, 16)
        self.e3 = Block(16, 32)
        self.pool = torch.nn.MaxPool2d(2)
        self.u2 = torch.nn.Conv2d(32, 16, 1)
        self.u1 = torch.nn.Conv2d(16, 8, 1)
        self.d2 = Block(32, 16)
        self.d1 = Block(16, 8)
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


def build_channels(gray: np.ndarray, candidate) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = cv2.resize(gray, (MODEL_SHAPE[1], MODEL_SHAPE[0]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    static_full = candidate.static_line_mask(ink)
    static_small = cv2.resize(static_full, (MODEL_SHAPE[1], MODEL_SHAPE[0]), interpolation=cv2.INTER_NEAREST)
    cue = (static_small > 0).astype(np.float32)
    return np.stack([raw, cue], axis=0), static_full, cue


def sentinel_metrics(binary_occupancy: np.ndarray) -> dict:
    occupancy = binary_occupancy.astype(bool)
    count, labels = cv2.connectedComponents(occupancy.astype(np.uint8), connectivity=8)
    qualifying = 0
    for label in range(1, count):
        component = labels == label
        skeleton_length = int(skeletonize(component).sum())
        if skeleton_length >= MIN_COMPONENT_SKELETON_PX:
            qualifying += 1
    occupancy_pixels = int(occupancy.sum())
    return {
        "occupancy_pixels": occupancy_pixels,
        "fpa": occupancy_pixels / float(FULL_SHAPE[0] * FULL_SHAPE[1]),
        "qualifying_component_count": qualifying,
        "pass": occupancy_pixels <= FPA_NUMERATOR_MAX and qualifying == 0,
    }


def synthetic_sentinel_tests() -> dict:
    empty = np.zeros(FULL_SHAPE, np.uint8)
    long_line = np.zeros(FULL_SHAPE, np.uint8)
    cv2.line(long_line, (100, 100), (144, 100), 1, 7)
    tiny_burden = np.zeros(FULL_SHAPE, np.uint8)
    for index in range(40):
        x = 20 + (index % 20) * 60
        y = 20 + (index // 20) * 200
        cv2.line(tiny_burden, (x, y), (x + 9, y), 1, 1)
    cases = {
        "empty_must_pass": sentinel_metrics(empty),
        "qualifying_line_must_fail": sentinel_metrics(long_line),
        "fragment_burden_must_fail": sentinel_metrics(tiny_burden),
    }
    expected = (
        cases["empty_must_pass"]["pass"]
        and not cases["qualifying_line_must_fail"]["pass"]
        and not cases["fragment_burden_must_fail"]["pass"]
    )
    return {"pass": bool(expected), "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"
    freeze_path = repo / "upload code/docs/experiments/ltpp_geoforecast_crack_recognition_nondestructive_freeze_candidate_20260810.md"
    candidate_path = repo / "upload code/scripts/ltpp_extract_crack_candidates.py"
    b1_path = repo / "upload code/scripts/ltpp_run_crack_recognition_b1.py"
    b0_path = repo / "upload code/scripts/ltpp_run_crack_recognition_b0.py"
    manifest_path = packet / "adjudicated/adjudicated_manifest.json"

    observed_hashes = {
        "freeze": sha256(freeze_path),
        "static_source": sha256(candidate_path),
        "b1_source": sha256(b1_path),
        "manifest": sha256(manifest_path),
    }
    expected_hashes = {
        "freeze": FREEZE_SHA256,
        "static_source": STATIC_SOURCE_SHA256,
        "b1_source": B1_SOURCE_SHA256,
        "manifest": MANIFEST_SHA256,
    }
    hash_pass = observed_hashes == expected_hashes
    if not hash_pass:
        raise RuntimeError(f"freeze hash mismatch: observed={observed_hashes}")

    candidate = load_module("ltpp_candidate_no_fit_freeze", candidate_path)
    b1 = load_module("ltpp_b1_no_fit_freeze", b1_path)
    b0 = load_module("ltpp_b0_no_fit_freeze", b0_path)

    manifest = json.loads(manifest_path.read_text())
    labels: dict[str, Path] = {}
    sections: dict[str, str] = {}
    for entry in manifest["files"]:
        label_path = packet / "adjudicated" / entry["file"]
        payload = json.loads(label_path.read_text())
        blind_id = payload["properties"]["primary_blind_id"]
        labels[blind_id] = label_path
        sections[blind_id] = payload["properties"]["section"]

    rows = []
    preview_payload = {}
    for image_path in sorted((packet / "primary/images").glob("P*.png")):
        blind_id = image_path.stem
        gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if gray is None or gray.shape != FULL_SHAPE or gray.dtype != np.uint8:
            raise RuntimeError(f"invalid source image: {image_path}")
        channels, static_full, cue = build_channels(gray, candidate)
        target = b1.make_target(b0, labels[blind_id]).astype(np.float32)
        line, polygon, _, _ = b0.gold_masks(labels[blind_id], FULL_SHAPE)
        full_gold = cv2.bitwise_or(line, polygon)
        direct_raw = cv2.resize(gray, (MODEL_SHAPE[1], MODEL_SHAPE[0]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        checks = {
            "channels_shape": list(channels.shape) == [2, MODEL_SHAPE[0], MODEL_SHAPE[1]],
            "channels_dtype": str(channels.dtype) == "float32",
            "raw_exact": bool(np.array_equal(channels[0], direct_raw)),
            "raw_range": bool(0.0 <= float(channels[0].min()) <= float(channels[0].max()) <= 1.0),
            "cue_binary": set(np.unique(cue).tolist()).issubset({0.0, 1.0}),
            "target_shape": list(target.shape) == [MODEL_SHAPE[0], MODEL_SHAPE[1]],
            "target_binary": set(np.unique(target).tolist()).issubset({0.0, 1.0}),
        }
        if not all(checks.values()):
            raise RuntimeError(f"channel/target validation failed for {blind_id}: {checks}")
        gold_pixels = int((full_gold > 0).sum())
        rows.append({
            "blind_id": blind_id,
            "section": sections[blind_id],
            "image_sha256": sha256(image_path),
            "label_sha256": sha256(labels[blind_id]),
            "gold_crack_pixels_full_resolution": gold_pixels,
            "zero_crack": gold_pixels == 0,
            "cue_fraction_model_frame": float(cue.mean()),
            "checks": checks,
        })
        if blind_id in PREVIEW_IDS:
            preview_payload[blind_id] = (gray, static_full, full_gold)

    observed_zero = {row["blind_id"] for row in rows if row["zero_crack"]}
    zero_map_pass = observed_zero == ZERO_CRACK_IDS

    torch.manual_seed(20260807)
    torch.use_deterministic_algorithms(True)
    model = FrozenTwoChannelTinyUNet().eval()
    synthetic_input = torch.zeros((1, 2, MODEL_SHAPE[0], MODEL_SHAPE[1]), dtype=torch.float32)
    with torch.no_grad():
        synthetic_output = model(synthetic_input)
    architecture = {
        "input_shape": list(synthetic_input.shape),
        "output_shape": list(synthetic_output.shape),
        "input_channels": model.e1.net[0].in_channels,
        "output_channels": model.out.out_channels,
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "synthetic_only": True,
        "weights_saved": False,
    }
    architecture_pass = (
        architecture["input_channels"] == 2
        and architecture["output_channels"] == 1
        and architecture["output_shape"] == [1, 1, MODEL_SHAPE[0], MODEL_SHAPE[1]]
    )
    sentinel_tests = synthetic_sentinel_tests()

    figure, axes = plt.subplots(len(PREVIEW_IDS), 4, figsize=(15.5, 1.8 * len(PREVIEW_IDS)), constrained_layout=True)
    titles = ("Raw grayscale (preserved)", "Static cue only", "Two-channel overlay", "Adjudicated crack target")
    for column, title in enumerate(titles):
        axes[0, column].set_title(title, fontsize=11, fontweight="bold")
    for row_index, blind_id in enumerate(PREVIEW_IDS):
        gray, static_full, full_gold = preview_payload[blind_id]
        cue_panel = np.full((*FULL_SHAPE, 3), 255, np.uint8)
        cue_panel[static_full > 0] = (0, 170, 215)
        overlay_panel = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        overlay_panel[static_full > 0] = (0, 170, 215)
        gold_panel = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        gold_panel[full_gold > 0] = (0, 170, 75)
        panels = (gray, cue_panel, overlay_panel, gold_panel)
        for column, panel in enumerate(panels):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None, aspect="auto")
            axes[row_index, column].axis("off")
        axes[row_index, 0].text(
            0.012, 0.95, f"{blind_id} | {sections[blind_id]}",
            transform=axes[row_index, 0].transAxes, fontsize=7.5, va="top",
            bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.9, "pad": 2.5},
        )
    figure_path = output / "nondestructive_two_channel_preview.png"
    figure.savefig(figure_path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    all_row_checks = all(all(row["checks"].values()) for row in rows)
    passed = hash_pass and len(rows) == 37 and all_row_checks and zero_map_pass and architecture_pass and sentinel_tests["pass"]
    receipt = {
        "status": "PASS_NONDESTRUCTIVE_IMPLEMENTATION_NO_FIT" if passed else "FAIL_NONDESTRUCTIVE_IMPLEMENTATION_NO_FIT",
        "created_at": "2026-08-10",
        "fit_performed": False,
        "optimizer_steps": 0,
        "real_image_model_forward_passes": 0,
        "weights_saved": False,
        "observed_hashes": observed_hashes,
        "expected_hashes": expected_hashes,
        "map_count": len(rows),
        "zero_crack_ids": sorted(observed_zero),
        "zero_crack_ids_match_freeze": zero_map_pass,
        "architecture": architecture,
        "synthetic_sentinel_tests": sentinel_tests,
        "rows": rows,
        "figure": str(figure_path),
        "claim_boundary": "Implementation and deterministic no-fit validation only; no trained weights or empirical challenger result exist.",
    }
    (output / "nondestructive_no_fit_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "status": receipt["status"],
        "maps": len(rows),
        "zero_crack_ids": sorted(observed_zero),
        "architecture": architecture,
        "synthetic_sentinel_pass": sentinel_tests["pass"],
        "figure": str(figure_path),
    }, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
