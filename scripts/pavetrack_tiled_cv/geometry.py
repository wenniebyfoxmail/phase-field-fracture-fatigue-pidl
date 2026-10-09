#!/usr/bin/env python3
"""Pure, deterministic geometry for tiled PaveTrack localisation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Candidate:
    box: tuple[float, float, float, float]
    score: float
    tile_left: int
    tile_top: int


def tile_origins(length: int, tile_size: int, stride: int) -> list[int]:
    if length <= 0 or tile_size <= 0 or stride <= 0:
        raise ValueError("length, tile_size and stride must be positive")
    last = max(0, length - tile_size)
    origins = list(range(0, last + 1, stride))
    if not origins or origins[-1] != last:
        origins.append(last)
    return origins


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


def clip_target_to_tile(
    box: Sequence[float],
    left: int,
    top: int,
    tile_size: int,
    minimum_intersection_fraction: float = 0.25,
    minimum_side_pixels: float = 4.0,
) -> tuple[float, float, float, float] | None:
    x1, y1, x2, y2 = (float(value) for value in box)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("target box must have positive area")
    ix1, iy1 = max(x1, left), max(y1, top)
    ix2, iy2 = min(x2, left + tile_size), min(y2, top + tile_size)
    if ix2 <= ix1 or iy2 <= iy1:
        return None
    original_area = (x2 - x1) * (y2 - y1)
    intersection_fraction = (ix2 - ix1) * (iy2 - iy1) / original_area
    center_x, center_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    center_inside = (
        left <= center_x < left + tile_size
        and top <= center_y < top + tile_size
    )
    if not center_inside and intersection_fraction < minimum_intersection_fraction:
        return None
    if ix2 - ix1 < minimum_side_pixels or iy2 - iy1 < minimum_side_pixels:
        return None
    return ix1 - left, iy1 - top, ix2 - left, iy2 - top


def to_full_image(
    box: Sequence[float], left: int, top: int, width: int, height: int
) -> tuple[float, float, float, float] | None:
    x1, y1, x2, y2 = (float(value) for value in box)
    mapped = (
        max(0.0, min(float(width), x1 + left)),
        max(0.0, min(float(height), y1 + top)),
        max(0.0, min(float(width), x2 + left)),
        max(0.0, min(float(height), y2 + top)),
    )
    return mapped if mapped[2] > mapped[0] and mapped[3] > mapped[1] else None


def deterministic_nms(
    candidates: Iterable[Candidate], iou_threshold: float, maximum: int
) -> list[Candidate]:
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be between zero and one")
    if maximum <= 0:
        raise ValueError("maximum must be positive")
    ranked = sorted(
        candidates,
        key=lambda item: (
            -item.score,
            item.box,
            item.tile_top,
            item.tile_left,
        ),
    )
    kept: list[Candidate] = []
    for candidate in ranked:
        if all(box_iou(candidate.box, prior.box) <= iou_threshold for prior in kept):
            kept.append(candidate)
            if len(kept) == maximum:
                break
    return kept

