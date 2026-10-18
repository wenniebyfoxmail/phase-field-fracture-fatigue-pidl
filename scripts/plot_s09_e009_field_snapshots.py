#!/usr/bin/env python3
"""Reconstruct and plot S09-E009 update-500 damage fields without training."""

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


RUN_ROOT = (
    ROOT
    / "local_archive/experiments/S09-E009/runs/"
    "S09-E009-R001-four-arm-damage-separation"
)
PACKET = (
    ROOT
    / "local_archive/experiments/S09-E008/runs/"
    "S09-E008-P1-R001-stage0a-memorisation/packet"
)
CONFIG = ROOT / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
PRODUCER = (
    RUN_ROOT
    / "retrieval/extracted/mnt/data2/drtao/wennie/"
    "S09-E009-R001-four-arm-damage-separation"
)
OUTPUT = ROOT / "docs/research/S09/S09-E009/results/field_visualisation"

ARMS = (
    "R_current_pino_replay",
    "S_data_only_scalar",
    "A0_damage_anchor_beta0",
    "A25_damage_anchor_beta0p25",
)
SHORT = {
    "R_current_pino_replay": "R",
    "S_data_only_scalar": "S",
    "A0_damage_anchor_beta0": "A0",
    "A25_damage_anchor_beta0p25": "A25",
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
    if len(rows) != 64:
        raise ValueError(f"expected 64 update-500 arm/cycle rows, found {len(rows)}")
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
        "schema_version": "s09-e009-field-visualisation-v1",
        "run_id": "S09-E009-R001-four-arm-damage-separation",
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
    bar = fig.colorbar(image, ax=np.asarray(axes).ravel().tolist(), shrink=0.86, pad=0.02)
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
    true = runtime.arrays["d_peak"][index]
    pred = predictions["A25_damage_anchor_beta0p25"][index]
    true_increment = true - pre
    pred_increment = pred - pre
    error = pred_increment - true_increment

    fig, axes = plt.subplots(2, 3, figsize=(13.2, 6.9), constrained_layout=True)
    top_fields = (pre, true, pred)
    top_titles = ("FEM pre-state $d_{s00}$", "FEM peak $d_{s04}$", "A25 peak prediction")
    top_images = []
    for ax, field, title in zip(axes[0], top_fields, top_titles):
        im = ax.imshow(
            field[full_index], origin="lower", extent=full_extent, cmap="magma", vmin=0, vmax=1,
            interpolation="nearest", aspect="equal",
        )
        top_images.append(im)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    add_shared_colorbar(fig, top_images[-1], axes[0], "damage $d$")

    increment_max = max(float(np.max(true_increment)), float(np.max(pred_increment)), 1e-12)
    error_max = max(float(np.max(np.abs(error))), 1e-12)
    lower = (true_increment, pred_increment, error)
    lower_titles = ("FEM increment", "A25 predicted increment", "A25 − FEM increment")
    lower_images = []
    for column, (ax, field, title) in enumerate(zip(axes[1], lower, lower_titles)):
        if column < 2:
            im = ax.imshow(
                field[zoom_index], origin="lower", extent=zoom_extent, cmap="viridis",
                vmin=0, vmax=increment_max, interpolation="nearest", aspect="auto",
            )
        else:
            im = ax.imshow(
                field[zoom_index], origin="lower", extent=zoom_extent, cmap="RdBu_r",
                norm=TwoSlopeNorm(vmin=-error_max, vcenter=0, vmax=error_max),
                interpolation="nearest", aspect="auto",
            )
        lower_images.append(im)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y (crack-band zoom)")
    add_shared_colorbar(fig, lower_images[1], axes[1, :2], r"$\Delta d$ (cycle-local shared scale)")
    fig.colorbar(lower_images[2], ax=axes[1, 2], shrink=0.86, pad=0.02).set_label(
        "signed increment error"
    )
    metrics = frozen[("A25_damage_anchor_beta0p25", cycle)]
    fig.suptitle(
        "S09-E009 A25 final listed transition: cycle 73, update 500\n"
        f"true mean |Δd|={metrics['true_amplitude']:.3e}, "
        f"predicted={metrics['predicted_amplitude']:.3e}, "
        f"spatial r={metrics['spatial']:.3f}",
        fontsize=13,
    )
    save_both(fig, OUTPUT / "S09-E009-R001-A25-cycle73-final-fields")


def four_arm_growth_figure(
    runtime,
    predictions: dict[str, np.ndarray],
    frozen: dict[tuple[str, int], dict[str, float]],
    zoom_index: np.ndarray,
    zoom_extent: list[float],
) -> None:
    cycle = 69
    index = int(np.where(runtime.arrays["cycles"] == cycle)[0][0])
    pre = runtime.arrays["d_pre"][index]
    true_increment = runtime.arrays["d_peak"][index] - pre
    plotted = [true_increment] + [predictions[arm][index] - pre for arm in ARMS]
    vmax = max(float(np.max(field)) for field in plotted)

    fig, axes = plt.subplots(2, 5, figsize=(17.2, 6.15), constrained_layout=True)
    titles = ["FEM target", "R replay", "S data-only", "A0 anchor", "A25 PINO"]
    images = []
    for ax, field, title in zip(axes[0], plotted, titles):
        im = ax.imshow(
            field[zoom_index], origin="lower", extent=zoom_extent, cmap="viridis",
            vmin=0, vmax=vmax, interpolation="nearest", aspect="auto",
        )
        images.append(im)
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_yticks([])
    axes[0, 0].set_ylabel(r"physical $\Delta d$" + "\ncrack-band y")
    add_shared_colorbar(
        fig, images[-1], axes[0], r"$\Delta d$ (shared across all panels)"
    )
    normalized_images = []
    for ax, field, title in zip(axes[1], plotted, titles):
        field_max = max(float(np.max(field)), 1e-15)
        im = ax.imshow(
            field[zoom_index] / field_max,
            origin="lower",
            extent=zoom_extent,
            cmap="viridis",
            vmin=0,
            vmax=1,
            interpolation="nearest",
            aspect="auto",
        )
        normalized_images.append(im)
        ax.set_title(f"shape only; max={field_max:.2e}", fontsize=9)
        ax.set_xlabel("x")
        ax.set_yticks([])
    axes[1, 0].set_ylabel("per-panel normalized\n(not an amplitude comparison)")
    add_shared_colorbar(fig, normalized_images[-1], axes[1], "field / panel maximum")
    summary = ", ".join(
        f"{SHORT[arm]} mean={frozen[(arm, cycle)]['predicted_amplitude']:.2e}"
        for arm in ARMS
    )
    fig.suptitle(
        "Cycle 69 growth transition at update 500\n"
        f"FEM mean |Δd|={frozen[(ARMS[0], cycle)]['true_amplitude']:.2e}; {summary}",
        fontsize=12.5,
    )
    save_both(fig, OUTPUT / "S09-E009-R001-cycle69-four-arm-increments")


def contact_sheet(
    runtime,
    predictions: dict[str, np.ndarray],
    zoom_index: np.ndarray,
    zoom_extent: list[float],
) -> None:
    selected = (1, 21, 46, 58, 69, 73)
    a25 = predictions["A25_damage_anchor_beta0p25"]
    fig, axes = plt.subplots(3, len(selected), figsize=(18.2, 7.0), constrained_layout=True)
    error_max = 0.0
    errors = []
    for cycle in selected:
        index = int(np.where(runtime.arrays["cycles"] == cycle)[0][0])
        error = a25[index] - runtime.arrays["d_peak"][index]
        errors.append(error)
        error_max = max(error_max, float(np.max(np.abs(error))))
    error_max = max(error_max, 1e-12)

    for column, cycle in enumerate(selected):
        index = int(np.where(runtime.arrays["cycles"] == cycle)[0][0])
        fields = (runtime.arrays["d_peak"][index], a25[index], errors[column])
        for row, field in enumerate(fields):
            ax = axes[row, column]
            if row < 2:
                im = ax.imshow(
                    field[zoom_index], origin="lower", extent=zoom_extent, cmap="magma",
                    vmin=0, vmax=1, interpolation="nearest", aspect="auto",
                )
            else:
                im = ax.imshow(
                    field[zoom_index], origin="lower", extent=zoom_extent, cmap="RdBu_r",
                    norm=TwoSlopeNorm(vmin=-error_max, vcenter=0, vmax=error_max),
                    interpolation="nearest", aspect="auto",
                )
            if row == 0:
                ax.set_title(f"cycle {cycle}")
            if column == 0:
                ax.set_ylabel(("FEM peak", "A25 peak", "A25 − FEM")[row])
            else:
                ax.set_yticks([])
            if row == 2:
                ax.set_xlabel("x")
            else:
                ax.set_xticks([])
    add_shared_colorbar(fig, axes[1, -1].images[0], axes[:2, :], "damage $d$ (fixed 0–1)")
    add_shared_colorbar(fig, axes[2, -1].images[0], axes[2, :], "signed peak-state error")
    fig.suptitle(
        "A25 peak-state fields over representative selected cycle transitions\n"
        "Each column is an independent s00→s04 mapping on the exposed development packet",
        fontsize=13,
    )
    save_both(fig, OUTPUT / "S09-E009-R001-A25-selected-cycle-peak-fields")


def sequence_gif(
    runtime,
    predictions: dict[str, np.ndarray],
    zoom_index: np.ndarray,
    zoom_extent: list[float],
) -> None:
    a25 = predictions["A25_damage_anchor_beta0p25"]
    all_error = a25 - runtime.arrays["d_peak"]
    error_max = max(float(np.max(np.abs(all_error))), 1e-12)
    frame_dir = OUTPUT / "_gif_frames"
    frame_dir.mkdir(exist_ok=True)
    frames: list[Image.Image] = []
    for index, cycle in enumerate(runtime.arrays["cycles"].tolist()):
        fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.3), constrained_layout=True)
        fields = (runtime.arrays["d_peak"][index], a25[index], all_error[index])
        titles = ("FEM peak", "A25 peak", "A25 − FEM")
        for column, (ax, field, title) in enumerate(zip(axes, fields, titles)):
            if column < 2:
                im = ax.imshow(
                    field[zoom_index], origin="lower", extent=zoom_extent, cmap="magma",
                    vmin=0, vmax=1, interpolation="nearest", aspect="auto",
                )
            else:
                im = ax.imshow(
                    field[zoom_index], origin="lower", extent=zoom_extent, cmap="RdBu_r",
                    norm=TwoSlopeNorm(vmin=-error_max, vcenter=0, vmax=error_max),
                    interpolation="nearest", aspect="auto",
                )
            ax.set_title(title)
            ax.set_xlabel("x")
            if column == 0:
                ax.set_ylabel("crack-band y")
            else:
                ax.set_yticks([])
            fig.colorbar(im, ax=ax, shrink=0.78, pad=0.02)
        fig.suptitle(f"S09-E009 A25 update-500 peak field — selected cycle {cycle}")
        path = frame_dir / f"frame_{index:02d}_cycle_{cycle:03d}.png"
        fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        frames.append(Image.open(path).convert("RGB"))
    frames[0].save(
        OUTPUT / "S09-E009-R001-A25-all-selected-cycles.gif",
        save_all=True,
        append_images=frames[1:],
        duration=900,
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
    four_arm_growth_figure(runtime, predictions, frozen, zoom_index, zoom_extent)
    contact_sheet(runtime, predictions, zoom_index, zoom_extent)
    sequence_gif(runtime, predictions, zoom_index, zoom_extent)

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
