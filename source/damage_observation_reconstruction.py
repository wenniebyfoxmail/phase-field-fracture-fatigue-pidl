"""Reconstruct diffuse phase-field damage from binary crack observations."""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize


def observed_core(damage: np.ndarray, threshold: float) -> np.ndarray:
    damage = np.asarray(damage, dtype=np.float64).reshape(-1)
    if not 0.0 < threshold < 1.0:
        raise ValueError("core threshold must lie strictly between zero and one")
    core = damage >= threshold
    if not np.any(core):
        raise ValueError("damage observation contains no crack-core nodes")
    return core


def at1_profile(distance: np.ndarray, length_scale: float) -> np.ndarray:
    """Return the compact AT1 squared-hat profile around an observed crack."""
    if length_scale <= 0.0:
        raise ValueError("length_scale must be positive")
    distance = np.asarray(distance, dtype=np.float64)
    return np.maximum(1.0 - distance / (2.0 * length_scale), 0.0) ** 2


def binary_core_damage(damage: np.ndarray, threshold: float) -> np.ndarray:
    return observed_core(damage, threshold).astype(np.float64)


def notch_connected_core(
    points: np.ndarray,
    cells: np.ndarray,
    damage: np.ndarray,
    *,
    threshold: float,
) -> np.ndarray:
    """Retain only the observed core component connected to the left notch."""
    points = np.asarray(points, dtype=np.float64)
    cells = np.asarray(cells, dtype=np.int64)
    core = observed_core(damage, threshold)
    core_nodes = np.flatnonzero(core)
    remap = np.full(len(points), -1, dtype=np.int64)
    remap[core_nodes] = np.arange(len(core_nodes))
    edge_pairs = np.concatenate(
        (
            cells[:, [0, 1]],
            cells[:, [1, 2]],
            cells[:, [2, 3]],
            cells[:, [3, 0]],
        ),
        axis=0,
    )
    retained = core[edge_pairs[:, 0]] & core[edge_pairs[:, 1]]
    edges = remap[edge_pairs[retained]]
    rows = np.concatenate((edges[:, 0], edges[:, 1]))
    cols = np.concatenate((edges[:, 1], edges[:, 0]))
    graph = sparse.csr_matrix(
        (np.ones(len(rows), dtype=np.uint8), (rows, cols)),
        shape=(len(core_nodes), len(core_nodes)),
    )
    _, labels = connected_components(graph, directed=False)
    notch_node = int(np.argmin(points[core_nodes, 0]))
    notch_label = labels[notch_node]
    connected = np.zeros(len(points), dtype=bool)
    connected[core_nodes[labels == notch_label]] = True
    return connected


def at1_from_core_points(
    points: np.ndarray,
    damage: np.ndarray,
    *,
    threshold: float,
    length_scale: float,
) -> np.ndarray:
    """Dilate a binary crack-core observation using the known AT1 profile."""
    points = np.asarray(points, dtype=np.float64)
    core = observed_core(damage, threshold)
    distance = cKDTree(points[core, :2]).query(points[:, :2], k=1)[0]
    return at1_profile(distance, length_scale)


def at1_from_binary_core_points(
    points: np.ndarray,
    core: np.ndarray,
    *,
    length_scale: float,
) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    core = np.asarray(core, dtype=bool).reshape(-1)
    if len(core) != len(points) or not np.any(core):
        raise ValueError("binary core must match points and contain observed nodes")
    distance = cKDTree(points[core, :2]).query(points[:, :2], k=1)[0]
    return at1_profile(distance, length_scale)


def at1_from_binned_centerline(
    points: np.ndarray,
    damage: np.ndarray,
    *,
    threshold: float,
    length_scale: float,
    bins: int = 128,
    samples: int = 2048,
) -> np.ndarray:
    """Reduce the binary core to a median-y centreline before AT1 dilation."""
    points = np.asarray(points, dtype=np.float64)
    core = observed_core(damage, threshold)
    core_points = points[core, :2]
    if bins < 2 or samples < 2:
        raise ValueError("bins and samples must both be at least two")
    edges = np.linspace(core_points[:, 0].min(), core_points[:, 0].max(), bins + 1)
    membership = np.clip(np.digitize(core_points[:, 0], edges) - 1, 0, bins - 1)
    centers: list[tuple[float, float]] = []
    for index in range(bins):
        selected = core_points[membership == index]
        if len(selected):
            centers.append((float(np.median(selected[:, 0])), float(np.median(selected[:, 1]))))
    if len(centers) < 2:
        raise ValueError("observed crack core does not span enough x bins")
    centerline = np.asarray(centers)
    order = np.argsort(centerline[:, 0])
    centerline = centerline[order]
    if samples % 2 == 0:
        samples += 1
    sample_x = np.linspace(core_points[:, 0].min(), core_points[:, 0].max(), samples)
    sample_y = np.interp(sample_x, centerline[:, 0], centerline[:, 1])
    distance = cKDTree(np.column_stack((sample_x, sample_y))).query(points[:, :2], k=1)[0]
    return at1_profile(distance, length_scale)


def raster_skeleton_points(
    points: np.ndarray,
    core: np.ndarray,
    *,
    resolution: float,
) -> np.ndarray:
    """Rasterize a binary core at fixed resolution and return its skeleton."""
    points = np.asarray(points, dtype=np.float64)
    core = np.asarray(core, dtype=bool).reshape(-1)
    if len(core) != len(points) or not np.any(core):
        raise ValueError("binary core must match points and contain observed nodes")
    if resolution <= 0.0:
        raise ValueError("observation resolution must be positive")
    xmin, ymin = points[:, :2].min(axis=0)
    xmax, ymax = points[:, :2].max(axis=0)
    x_values = np.arange(xmin, xmax + 0.5 * resolution, resolution)
    y_values = np.arange(ymin, ymax + 0.5 * resolution, resolution)
    grid_x, grid_y = np.meshgrid(x_values, y_values)
    grid_points = np.column_stack((grid_x.reshape(-1), grid_y.reshape(-1)))
    nearest = cKDTree(points[core, :2]).query(grid_points, k=1)[0]
    raster = (nearest <= np.sqrt(2.0) * resolution).reshape(grid_x.shape)
    skeleton = skeletonize(raster)
    rows, cols = np.nonzero(skeleton)
    if not len(rows):
        raise ValueError("binary observation produced an empty skeleton")
    return np.column_stack((x_values[cols], y_values[rows]))


def at1_from_raster_skeleton(
    points: np.ndarray,
    core: np.ndarray,
    *,
    length_scale: float,
    resolution: float,
    vertical_shift: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    skeleton = raster_skeleton_points(points, core, resolution=resolution)
    skeleton = skeleton.copy()
    skeleton[:, 1] += vertical_shift
    distance = cKDTree(skeleton).query(np.asarray(points)[:, :2], k=1)[0]
    return at1_profile(distance, length_scale), skeleton


def at1_from_straight_visible_extent(
    points: np.ndarray,
    damage: np.ndarray,
    *,
    threshold: float,
    length_scale: float,
) -> np.ndarray:
    """Use only observed crack extent and median vertical position."""
    points = np.asarray(points, dtype=np.float64)
    core = observed_core(damage, threshold)
    core_points = points[core, :2]
    xmin = float(core_points[:, 0].min())
    xmax = float(core_points[:, 0].max())
    y_center = float(np.median(core_points[:, 1]))
    nearest_x = np.clip(points[:, 0], xmin, xmax)
    distance = np.sqrt((points[:, 0] - nearest_x) ** 2 + (points[:, 1] - y_center) ** 2)
    return at1_profile(distance, length_scale)


def at1_from_binary_straight_extent(
    points: np.ndarray,
    core: np.ndarray,
    *,
    length_scale: float,
) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    core = np.asarray(core, dtype=bool).reshape(-1)
    if len(core) != len(points) or not np.any(core):
        raise ValueError("binary core must match points and contain observed nodes")
    core_points = points[core, :2]
    xmin = float(core_points[:, 0].min())
    xmax = float(core_points[:, 0].max())
    y_center = float(np.median(core_points[:, 1]))
    return at1_from_line_segment(
        points,
        xmin=xmin,
        xmax=xmax,
        y_center=y_center,
        length_scale=length_scale,
    )


def at1_from_line_segment(
    points: np.ndarray,
    *,
    xmin: float,
    xmax: float,
    y_center: float,
    length_scale: float,
) -> np.ndarray:
    if xmax <= xmin:
        raise ValueError("line segment xmax must exceed xmin")
    points = np.asarray(points, dtype=np.float64)
    nearest_x = np.clip(points[:, 0], xmin, xmax)
    distance = np.sqrt((points[:, 0] - nearest_x) ** 2 + (points[:, 1] - y_center) ** 2)
    return at1_profile(distance, length_scale)
