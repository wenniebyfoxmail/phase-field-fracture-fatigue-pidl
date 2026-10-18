#!/usr/bin/env python3
"""Reconstruct and plot S09-E010 update-500 damage fields without training."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import torch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from s09_e009_four_arm import atomic_losses  # noqa: E402
from s09_stage0a_p1_trainer import build_runtime  # noqa: E402


RUN_ID = "S09-E010-R001-support-amplitude-three-arm"
RUN_ROOT = ROOT / "local_archive/experiments/S09-E010/runs" / RUN_ID
PACKET = (
    ROOT
    / "local_archive/experiments/S09-E008/runs/"
    "S09-E008-P1-R001-stage0a-memorisation/packet"
)
CONFIG = ROOT / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
PRODUCER = RUN_ROOT / "remote_run"
OUTPUT = ROOT / "docs/research/S09/S09-E010/results/field_visualisation"

ARMS = (
    "A25_exact_e009_replay",
    "B25_support_amplitude_beta0p25",
    "B0_support_amplitude_beta0",
)
SHORT = {
    "A25_exact_e009_replay": "A25",
    "B25_support_amplitude_beta0p25": "B25",
    "B0_support_amplitude_beta0": "B0",
}
ZOOM_Y = (-0.055, 0.055)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nearest_raster_indices(
    xy: np.ndarray,
    *,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    width: int,
    height: int,
) -> tuple[np.ndarray, list[float]]:
    x = np.linspace(*xlim, width)
    y = np.linspace(*ylim, height)
    xx, yy = np.meshgrid(x, y)
    _, indices = cKDTree(xy).query(np.column_stack([xx.ravel(), yy.ravel()]), k=1)
    return indices.reshape(height, width), [xlim[0], xlim[1], ylim[0], ylim[1]]


def read_frozen_per_cycle() -> dict[tuple[str, int], dict[str, float]]:
    path = PRODUCER / "per_cycle_metrics.csv"
    rows: dict[tuple[str, int], dict[str, float]] = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if int(row["update"]) != 500:
                continue
            rows[(row["arm"], int(row["cycle"]))] = {
                "predicted_amplitude": float(row["predicted_damage_increment_abs_mean"]),
                "true_amplitude": float(row["true_damage_increment_abs_mean"]),
                "mae": float(row["damage_increment_mae"]),
                "false_growth": float(row["false_growth"]),
                "spatial": float(row["predicted_target_spatial_correlation"]),
            }
    expected = len(ARMS) * 16
    if len(rows) != expected:
        raise ValueError(f"expected {expected} update-500 arm/cycle rows, found {len(rows)}")
    return rows


def reconstruct_fields() -> tuple[dict[str, np.ndarray], dict[str, object]]:
    runtime = build_runtime(
        packet_dir=PACKET,
        config_path=CONFIG,
        device=torch.device("cpu"),
        executable=False,
    )
    frozen = read_frozen_per_cycle()
    nodal_weight = np.asarray(runtime.arrays["nodal_weight"], dtype=np.float64)
    predictions: dict[str, np.ndarray] = {}
    maximum_amplitude_difference = 0.0
    checkpoint_records: dict[str, dict[str, object]] = {}

    for arm in ARMS:
        checkpoint = PRODUCER / arm / "checkpoint_update500.pt"
        payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if payload["update"] != 500 or payload["arm"] != arm:
            raise ValueError(f"checkpoint identity mismatch: {arm}")
        runtime.model.load_state_dict(payload["model"], strict=True)
        runtime.model.eval()
        fields = []
        with torch.no_grad():
            for index, cycle in enumerate(runtime.arrays["cycles"].tolist()):
                _, context = atomic_losses(runtime, index)
                predicted_peak = context["output"]["d_peak"].detach().cpu().numpy()
                predicted_increment = predicted_peak - runtime.arrays["d_pre"][index]
                observed_amplitude = float(
                    np.sum(np.abs(predicted_increment) * nodal_weight)
                    / np.sum(nodal_weight)
                )
                expected_amplitude = frozen[(arm, int(cycle))]["predicted_amplitude"]
                maximum_amplitude_difference = max(
                    maximum_amplitude_difference,
                    abs(observed_amplitude - expected_amplitude),
                )
                fields.append(predicted_peak.copy())
        predictions[arm] = np.stack(fields)
        checkpoint_records[arm] = {
            "path": str(checkpoint.relative_to(ROOT)),
            "sha256": sha256(checkpoint),
            "update": 500,
        }

    tolerance = 1e-12
    if maximum_amplitude_difference > tolerance:
        raise ValueError(
            "field reconstruction differs from frozen per-cycle amplitudes: "
            f"{maximum_amplitude_difference} > {tolerance}"
        )
    receipt = {
        "schema_version": "s09-e010-field-visualisation-v1",
        "run_id": RUN_ID,
        "purpose": "read-only update-500 damage-field reconstruction for visualisation",
        "packet_manifest_sha256": json.loads((PACKET / "packet_identity.json").read_text())[
            "manifest_sha256"
        ],
        "packet_path": str(PACKET.relative_to(ROOT)),
        "checkpoints": checkpoint_records,
        "cycles": [int(value) for value in runtime.arrays["cycles"]],
        "operator_output_state": "s04 peak only",
        "intermediate_load_states_available": False,
        "optimizer_steps_performed": 0,
        "maximum_update500_amplitude_replay_abs_difference": maximum_amplitude_difference,
        "replay_tolerance": tolerance,
        "rasterisation": {
            "method": "nearest native node for display pixels only",
            "source_fields_unchanged": True,
            "crack_band_y_limits": list(ZOOM_Y),
        },
    }
    return predictions, {"runtime": runtime, "frozen": frozen, "receipt": receipt}


def save_both(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def add_shared_colorbar(fig: plt.Figure, image, axes, label: str) -> None:
    bar = fig.colorbar(image, ax=np.asarray(axes).ravel().tolist(), shrink=0.84, pad=0.02)
    bar.set_label(label)


def final_cycle_figure(
    runtime,
    predictions: dict[str, np.ndarray],
    frozen: dict[tuple[str, int], dict[str, float]],
    full_index: np.ndarray,
    full_extent: list[float],
    zoom_index: np.ndarray,
    zoom_extent: list[float],
) -> None:
    cycle = 73
    index = int(np.where(runtime.arrays["cycles"] == cycle)[0][0])
    pre = runtime.arrays["d_pre"][index]
    target = runtime.arrays["d_peak"][index]
    peak_fields = [pre, target] + [predictions[arm][index] for arm in ARMS]
    peak_titles = ["FEM pre-state", "FEM peak target", "A25 peak", "B25 peak", "B0 peak"]
    increments = [target - pre] + [predictions[arm][index] - pre for arm in ARMS]
    increment_titles = ["FEM increment", "A25 increment", "B25 increment", "B0 increment"]
    vmax = max(float(np.max(field)) for field in increments)

    fig = plt.figure(figsize=(17.8, 7.0), constrained_layout=True)
    grid = fig.add_gridspec(2, 5)
    top_axes = [fig.add_subplot(grid[0, column]) for column in range(5)]
    bottom_axes = [fig.add_subplot(grid[1, column]) for column in range(4)]
    note_ax = fig.add_subplot(grid[1, 4])
    note_ax.axis("off")

    peak_images = []
    for ax, field, title in zip(top_axes, peak_fields, peak_titles):
        im = ax.imshow(
            field[full_index], origin="lower", extent=full_extent, cmap="magma",
            vmin=0, vmax=1, interpolation="nearest", aspect="equal",
        )
        peak_images.append(im)
        ax.set_title(title)
        ax.set_xlabel("x")
        if ax is top_axes[0]:
            ax.set_ylabel("y")
        else:
            ax.set_yticks([])
    add_shared_colorbar(fig, peak_images[-1], top_axes, "damage d (fixed 0–1)")

    increment_images = []
    for ax, field, title in zip(bottom_axes, increments, increment_titles):
        im = ax.imshow(
            field[zoom_index], origin="lower", extent=zoom_extent, cmap="viridis",
            vmin=0, vmax=vmax, interpolation="nearest", aspect="auto",
        )
        increment_images.append(im)
        ax.set_title(title)
        ax.set_xlabel("x")
        if ax is bottom_axes[0]:
            ax.set_ylabel("crack-band y")
        else:
            ax.set_yticks([])
    add_shared_colorbar(fig, increment_images[-1], bottom_axes, "increment Δd (shared physical scale)")

    lines = [f"FEM mean |Δd| = {frozen[(ARMS[0], cycle)]['true_amplitude']:.3e}"]
    for arm in ARMS:
        metrics = frozen[(arm, cycle)]
        lines.append(
            f"{SHORT[arm]} mean |Δd| = {metrics['predicted_amplitude']:.3e}\n"
            f"  spatial r = {metrics['spatial']:.3f}"
        )
    note_ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=10.5)
    fig.suptitle(
        "S09-E010 final listed transition, cycle 73, update 500\n"
        "Top: total peak fields; bottom: newly predicted damage relative to the supplied pre-state",
        fontsize=13,
    )
    save_both(fig, OUTPUT / "S09-E010-R001-cycle73-final-fields")


def growth_cycle_figure(
    runtime,
    predictions: dict[str, np.ndarray],
    frozen: dict[tuple[str, int], dict[str, float]],
    zoom_index: np.ndarray,
    zoom_extent: list[float],
) -> None:
    cycle = 69
    index = int(np.where(runtime.arrays["cycles"] == cycle)[0][0])
    pre = runtime.arrays["d_pre"][index]
    plotted = [runtime.arrays["d_peak"][index] - pre] + [
        predictions[arm][index] - pre for arm in ARMS
    ]
    titles = ["FEM target", "A25", "B25", "B0"]
    vmax = max(float(np.max(field)) for field in plotted)

    fig, axes = plt.subplots(2, 4, figsize=(15.0, 6.3), constrained_layout=True)
    physical_images = []
    for ax, field, title in zip(axes[0], plotted, titles):
        im = ax.imshow(
            field[zoom_index], origin="lower", extent=zoom_extent, cmap="viridis",
            vmin=0, vmax=vmax, interpolation="nearest", aspect="auto",
        )
        physical_images.append(im)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_yticks([])
    axes[0, 0].set_ylabel("physical Δd\ncrack-band y")
    add_shared_colorbar(fig, physical_images[-1], axes[0], "Δd (shared across panels)")

    normalized_images = []
    for ax, field, title in zip(axes[1], plotted, titles):
        field_max = max(float(np.max(field)), 1e-15)
        im = ax.imshow(
            field[zoom_index] / field_max,
            origin="lower", extent=zoom_extent, cmap="viridis", vmin=0, vmax=1,
            interpolation="nearest", aspect="auto",
        )
        normalized_images.append(im)
        ax.set_title(f"{title} shape; max={field_max:.2e}", fontsize=9)
        ax.set_xlabel("x")
        ax.set_yticks([])
    axes[1, 0].set_ylabel("per-panel normalized\n(shape only)")
    add_shared_colorbar(fig, normalized_images[-1], axes[1], "field / panel maximum")

    summary = ", ".join(
        f"{SHORT[arm]}={frozen[(arm, cycle)]['predicted_amplitude']:.2e}" for arm in ARMS
    )
    fig.suptitle(
        "S09-E010 cycle 69 growth transition, update 500\n"
        f"weighted mean |Δd|: FEM={frozen[(ARMS[0], cycle)]['true_amplitude']:.2e}; {summary}",
        fontsize=12.5,
    )
    save_both(fig, OUTPUT / "S09-E010-R001-cycle69-three-arm-increments")


def sequence_gif(
    runtime,
    predictions: dict[str, np.ndarray],
    frozen: dict[tuple[str, int], dict[str, float]],
    zoom_index: np.ndarray,
    zoom_extent: list[float],
) -> None:
    frame_dir = OUTPUT / "_gif_frames"
    frame_dir.mkdir(exist_ok=True)
    frames: list[Image.Image] = []
    titles = ["FEM target", "A25", "B25", "B0"]
    for index, cycle in enumerate(runtime.arrays["cycles"].tolist()):
        pre = runtime.arrays["d_pre"][index]
        increments = [runtime.arrays["d_peak"][index] - pre] + [
            predictions[arm][index] - pre for arm in ARMS
        ]
        vmax = max(float(np.max(field)) for field in increments)
        fig, axes = plt.subplots(2, 4, figsize=(14.7, 6.3), constrained_layout=True)
        for column, (ax, field, title) in enumerate(zip(axes[0], increments, titles)):
            im = ax.imshow(
                field[zoom_index], origin="lower", extent=zoom_extent, cmap="viridis",
                vmin=0, vmax=vmax, interpolation="nearest", aspect="auto",
            )
            ax.set_title(title)
            ax.set_xlabel("x")
            ax.set_yticks([])
        axes[0, 0].set_ylabel("physical Δd\ncrack-band y")
        add_shared_colorbar(fig, im, axes[0], "cycle-local shared Δd scale")

        peak_fields = [runtime.arrays["d_peak"][index]] + [
            predictions[arm][index] for arm in ARMS
        ]
        for column, (ax, field, title) in enumerate(zip(axes[1], peak_fields, titles)):
            im_peak = ax.imshow(
                field[zoom_index], origin="lower", extent=zoom_extent, cmap="magma",
                vmin=0, vmax=1, interpolation="nearest", aspect="auto",
            )
            ax.set_title(f"{title} total peak", fontsize=10)
            ax.set_xlabel("x")
            ax.set_yticks([])
        axes[1, 0].set_ylabel("total damage d\ncrack-band y")
        add_shared_colorbar(fig, im_peak, axes[1], "damage d (fixed 0–1)")

        means = [frozen[(ARMS[0], int(cycle))]["true_amplitude"]] + [
            frozen[(arm, int(cycle))]["predicted_amplitude"] for arm in ARMS
        ]
        mean_text = ", ".join(f"{name}={value:.2e}" for name, value in zip(titles, means))
        fig.suptitle(
            f"S09-E010 update-500 selected cycle {cycle}: s00→s04 only\n"
            f"weighted mean |Δd|: {mean_text}",
            fontsize=12,
        )
        path = frame_dir / f"frame_{index:02d}_cycle_{int(cycle):03d}.png"
        fig.savefig(path, dpi=125, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        frames.append(Image.open(path).convert("RGB"))
    frames[0].save(
        OUTPUT / "S09-E010-R001-all-selected-cycles-fields.gif",
        save_all=True,
        append_images=frames[1:],
        duration=1100,
        loop=0,
        optimize=False,
    )
    for frame in frames:
        frame.close()
    for path in frame_dir.glob("*.png"):
        path.unlink()
    frame_dir.rmdir()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    predictions, context = reconstruct_fields()
    runtime = context["runtime"]
    frozen = context["frozen"]
    xy = np.asarray(runtime.arrays["xy"], dtype=np.float64)
    full_index, full_extent = nearest_raster_indices(
        xy, xlim=(-0.5, 0.5), ylim=(-0.5, 0.5), width=600, height=600
    )
    zoom_index, zoom_extent = nearest_raster_indices(
        xy, xlim=(-0.5, 0.5), ylim=ZOOM_Y, width=1000, height=120
    )
    final_cycle_figure(
        runtime, predictions, frozen, full_index, full_extent, zoom_index, zoom_extent
    )
    growth_cycle_figure(runtime, predictions, frozen, zoom_index, zoom_extent)
    sequence_gif(runtime, predictions, frozen, zoom_index, zoom_extent)

    receipt = context["receipt"]
    receipt["outputs"] = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file() and path.name != "field_reconstruction_receipt.json"
    }
    (OUTPUT / "field_reconstruction_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
