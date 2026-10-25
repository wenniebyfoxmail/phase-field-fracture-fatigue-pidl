"""Geometry-only reconstruction primitives for declared crack observations.

The package works on caller-provided arrays and has no dataset, image I/O, or
experiment-runner dependency.  Source acquisition and state assimilation stay
outside this boundary.
"""

from .damage_observation_reconstruction import (
    at1_from_binary_core_points,
    at1_from_binary_straight_extent,
    at1_from_binned_centerline,
    at1_from_core_points,
    at1_from_line_segment,
    at1_from_raster_skeleton,
    at1_from_straight_visible_extent,
    at1_profile,
    binary_core_damage,
    notch_connected_core,
    observed_core,
    raster_skeleton_points,
)

__all__ = [
    "at1_from_binary_core_points",
    "at1_from_binary_straight_extent",
    "at1_from_binned_centerline",
    "at1_from_core_points",
    "at1_from_line_segment",
    "at1_from_raster_skeleton",
    "at1_from_straight_visible_extent",
    "at1_profile",
    "binary_core_damage",
    "notch_connected_core",
    "observed_core",
    "raster_skeleton_points",
]
