"""Independent implementation of the S03-E018-D01 v1.1 written definition.

No original sampler, measurement code, answer arrays or score files are used.
The CLI reads only sanitised input NPZ/JSON and the named source photographs.
Stage indices in the output are zero based; transect IDs retain the JSON IDs.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import io
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zlib

import numpy as np


VARIANTS = ("baseline", "normal_minus2", "normal_plus2", "tangent_minus2", "tangent_plus2")
TANGENT_OFFSETS = np.arange(-2, 3, dtype=np.float64)


def measure(offsets, profile):
    """Measure a supplied median profile using float64 scalar arithmetic."""
    s = np.asarray(offsets, dtype=np.float64)
    y = np.asarray(profile, dtype=np.float64)
    if s.ndim != 1 or y.shape != s.shape or not np.all(np.isfinite(s)) or not np.all(np.isfinite(y)):
        raise ValueError("profile/offset shape or finite-value violation")
    if not np.all(np.diff(s) > 0):
        raise ValueError("normal offsets must increase strictly")
    left_shoulder, right_shoulder = s <= -45, s >= 45
    core = np.flatnonzero(np.abs(s) <= 15)
    if not np.any(left_shoulder) or not np.any(right_shoulder) or not core.size:
        raise ValueError("missing shoulder or peak search interval")
    sl, sr = float(np.median(s[left_shoulder])), float(np.median(s[right_shoulder]))
    yl, yr = float(np.median(y[left_shoulder])), float(np.median(y[right_shoulder]))
    background = yl + (yr - yl) * (s - sl) / (sr - sl)
    deficit = background - y
    shoulder_deficit = deficit[left_shoulder | right_shoulder]
    noise = float(1.4826 * np.median(np.abs(shoulder_deficit - np.median(shoulder_deficit))))
    peak = int(core[int(np.argmax(deficit[core]))])
    depth = float(deficit[peak])
    result = dict(width_px=math.nan, left_px=math.nan, right_px=math.nan,
                  valid=False, reason="", peak_index=peak, peak_px=float(s[peak]),
                  depth=depth, noise=noise, background=background, deficit=deficit)
    if depth < max(10.0, 3.0 * noise):
        result["reason"] = "insufficient_depth"
        return result
    half = depth / 2.0
    lo = hi = peak
    while lo > 0 and deficit[lo] >= half:
        lo -= 1
    while hi < len(s) - 1 and deficit[hi] >= half:
        hi += 1
    if lo == 0 or hi == len(s) - 1:
        result["reason"] = "censored"
        return result
    def crossing(a, b):
        return float(s[a] + (half - deficit[a]) * (s[b] - s[a]) / (deficit[b] - deficit[a]))
    left, right = crossing(lo, lo + 1), crossing(hi - 1, hi)
    width = right - left
    if width < 1.0:
        result["reason"] = "resolution_limited"
        return result
    result.update(width_px=width, left_px=left, right_px=right, valid=True, reason="ok")
    return result


def resize_scales(native_shape, working_shape):
    return np.array([working_shape[1] / native_shape[1], working_shape[0] / native_shape[0]], dtype=np.float64)


def apply_homography(points, matrix):
    p = np.asarray(points, dtype=np.float64)
    flat = p.reshape(-1, 2)
    matrix = np.asarray(matrix, dtype=np.float64)
    homogeneous = np.column_stack(tuple(matrix[i, 0] * flat[:, 0] + matrix[i, 1] * flat[:, 1] + matrix[i, 2] for i in range(3)))
    if np.any(~np.isfinite(homogeneous)) or np.any(np.abs(homogeneous[:, 2]) < 1e-14):
        raise ValueError("homography maps a sample to a nonfinite point or infinity")
    return (homogeneous[:, :2] / homogeneous[:, 2:3]).reshape(p.shape)


def native_to_source(points, H_inverse, native_shape, working_shape):
    scale = resize_scales(native_shape, working_shape)
    origin_working = (np.asarray(points, dtype=np.float64) + 0.5) * scale - 0.5
    stage_working = apply_homography(origin_working, H_inverse)
    return (stage_working + 0.5) / scale - 0.5


def source_to_origin(points, H, native_shape, working_shape):
    scale = resize_scales(native_shape, working_shape)
    stage_working = (np.asarray(points, dtype=np.float64) + 0.5) * scale - 0.5
    origin_working = apply_homography(stage_working, H)
    return (origin_working + 0.5) / scale - 0.5


def conjugated_check(points, H_inverse, native_shape, working_shape):
    """Algebraic comparison only: this output never drives image sampling."""
    sx, sy = resize_scales(native_shape, working_shape)
    resize = np.array([[sx, 0, (sx - 1) / 2], [0, sy, (sy - 1) / 2], [0, 0, 1]], dtype=np.float64)
    return apply_homography(points, np.linalg.inv(resize) @ H_inverse @ resize)


def sampling_grid(center, normal, offsets, variant="baseline", tangent_offsets=TANGENT_OFFSETS):
    n = np.asarray(normal, dtype=np.float64)
    tangent = np.array([-n[1], n[0]], dtype=np.float64)
    shifts = {"baseline": np.zeros(2), "normal_minus2": -2 * n, "normal_plus2": 2 * n,
              "tangent_minus2": -2 * tangent, "tangent_plus2": 2 * tangent}
    c = np.asarray(center, dtype=np.float64) + shifts[variant]
    return c + np.asarray(tangent_offsets)[:, None, None] * tangent + np.asarray(offsets)[None, :, None] * n


def bilinear(image, points, quantised=True):
    """Manual float32 sampling, with optional nearest-even 1/32 coordinates.

    The nearest-even rounding is applied to float32 coordinates multiplied by
    32. Integer carry is retained (e.g. a fraction rounded to 32 advances x).
    Samples outside the complete four-pixel stencil are rejected, never padded.
    """
    img = np.asarray(image, dtype=np.float32)
    p = np.asarray(points, dtype=np.float32)
    if img.ndim != 2 or not np.all(np.isfinite(p)):
        raise ValueError("invalid image or coordinates")
    if quantised:
        fixed = np.rint(p * np.float32(32.0)).astype(np.int64)
        base = np.floor_divide(fixed, 32)
        fractions = (fixed - base * 32).astype(np.float32) / np.float32(32)
    else:
        base = np.floor(p).astype(np.int64)
        fractions = p - base.astype(np.float32)
    x, y = base[..., 0], base[..., 1]
    if np.any(x < 0) or np.any(y < 0) or np.any(x + 1 >= img.shape[1]) or np.any(y + 1 >= img.shape[0]):
        raise ValueError("sample_out_of_bounds")
    fx, fy = fractions[..., 0], fractions[..., 1]
    one = np.float32(1.0)
    return ((img[y, x] * (one - fx) * (one - fy) + img[y, x + 1] * fx * (one - fy))
            + (img[y + 1, x] * (one - fx) * fy + img[y + 1, x + 1] * fx * fy)).astype(np.float32)


def median_source_profile(image, source_points, quantised=True):
    return np.median(bilinear(image, source_points, quantised=quantised), axis=0).astype(np.float32)


def measurement_fields(result):
    return {k: result[k] for k in ("width_px", "left_px", "right_px", "valid", "reason")}


class BudgetExceeded(RuntimeError):
    pass


def execute(inputs, output, budget_seconds):
    """Run once into a fresh directory; always retain a status/partial receipt."""
    if not (0 < budget_seconds <= 120):
        raise ValueError("budget-seconds must be positive and at most 120")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    def check_budget():
        if time.monotonic() - started >= budget_seconds:
            raise BudgetExceeded("wall-clock budget exhausted")
    receipt = dict(status="started", inputs=str(Path(inputs).resolve()), output=str(output.resolve()),
                   started_utc=datetime.now(timezone.utc).isoformat(), hostname=socket.gethostname(), pid=os.getpid(),
                   cli_argv=list(sys.argv),
                   budget_seconds=budget_seconds, stage_index_convention="zero_based", completed_rows=0,
                   source_decode="Pillow ImageOps.exif_transpose(image).convert('L') then np.asarray(dtype=float32)", script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   numpy_version=np.__version__, exposure="Only v1.1 protocol, AGENTS.md and sanitised inputs read before freeze; no original answers or implementation.",
                   source_identity=[], claim_boundary="Software computation and position sensitivity only; no physical-reference accuracy claim.")
    coordinate = dict(sample_points=0, max_mapping_abs_px=0.0, max_mapping_euclidean_px=0.0,
                      max_roundtrip_abs_px=0.0, max_roundtrip_euclidean_px=0.0)
    examples, example_metadata = {}, []
    handles = []
    try:
        receipt["code_commit"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                                                 capture_output=True, text=True, check=True, timeout=3).stdout.strip()
        import PIL
        from PIL import Image, ImageOps
        receipt["pillow_version"] = PIL.__version__
        geometry_path = Path(inputs) / "geometry.json"
        geometry_bytes = geometry_path.read_bytes()
        receipt["geometry_sha256"] = hashlib.sha256(geometry_bytes).hexdigest()
        geometry = json.loads(geometry_bytes)
        if set(geometry["beams"]) != {"4", "5", "6"}:
            raise ValueError("expected geometry beam identities 4/5/6 exactly")
        def open_table(name, fields):
            handle = (output / name).open("w", newline="")
            handles.append(handle)
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            handle.flush()
            return writer, handle
        ids = ["beam", "stage_index", "load_kN", "transect_id"]
        stored_writer, stored_handle = open_table("independent_measurements.csv", ids + ["width_px", "left_px", "right_px", "valid", "reason"])
        replay_fields = ids + [f"{mode}_{field}" for mode in ("quantised", "continuous") for field in ("width_px", "left_px", "right_px", "valid", "reason", "profile_max_abs_diff")]
        replay_writer, replay_handle = open_table("source_replay.csv", replay_fields)
        variant_writer, variant_handle = open_table("location_variants.csv", ids + ["variant", "width_px", "left_px", "right_px", "valid", "reason"])
        expected_total = 0
        for beam_key in sorted(geometry["beams"], key=int):
            check_budget()
            beam = geometry["beams"][beam_key]
            npz_path = Path(inputs) / f"Beam{beam_key}_inputs.npz"
            with np.load(npz_path, allow_pickle=False) as archive:
                expected_keys = {"normal_offsets_native_px", "profiles", "loads_kN", "homographies"}
                if set(archive.files) != expected_keys:
                    raise ValueError("sanitised NPZ key set mismatch")
                s, profiles, loads, homographies = (archive[k].copy() for k in ("normal_offsets_native_px", "profiles", "loads_kN", "homographies"))
            receipt.setdefault("input_npz_sha256", {})[npz_path.name] = hashlib.sha256(npz_path.read_bytes()).hexdigest()
            stages, transects = beam["stages"], beam["transects"]
            if (len(stages) != {"4": 4, "5": 6, "6": 4}[beam_key]
                    or [transect["id"] for transect in transects] != list(range(1, 13))):
                raise ValueError("stage count or ordered transect identities mismatch")
            if (not np.array_equal(s, np.arange(-60, 60.25, 0.25)) or profiles.dtype != np.float32
                    or profiles.shape != (len(stages), len(transects), 481) or homographies.shape != (len(stages), 3, 3)
                    or loads.shape != (len(stages),) or len(transects) != 12
                    or not np.all(np.isfinite(profiles)) or not np.all(np.isfinite(homographies))
                    or not np.all(np.isfinite(loads)) or not np.all(np.diff(loads) > 0)):
                raise ValueError("input array geometry, type or finite-value mismatch")
            expected_total += len(stages) * len(transects)
            for stage_index, stage in enumerate(stages):
                check_budget()
                if float(stage["nominal_load_kN"]) != float(loads[stage_index]) or int(stage["beam"]) != int(beam_key):
                    raise ValueError("stage identity/load mismatch")
                source_path = Path(stage["source_image"])
                raw = source_path.read_bytes()
                crc = f"{zlib.crc32(raw) & 0xffffffff:08x}"
                if len(raw) != int(stage["bytes"]) or crc.lower() != stage["crc32"].lower():
                    raise ValueError("source size/CRC identity mismatch")
                check_budget()
                with Image.open(io.BytesIO(raw)) as decoded:
                    image = np.asarray(ImageOps.exif_transpose(decoded).convert("L"), dtype=np.float32)
                if list(image.shape) != beam["native_shape"]:
                    raise ValueError("source decode/shape mismatch")
                receipt["source_identity"].append(dict(beam=int(beam_key), stage_index=stage_index, path=str(source_path), bytes=len(raw), crc32=crc))
                H = homographies[stage_index]
                H_inverse = np.linalg.inv(H)
                for transect_index, transect in enumerate(transects):
                    check_budget()
                    n = np.asarray(transect["normal"], dtype=np.float64)
                    c = np.asarray(transect["center"], dtype=np.float64)
                    if n.shape != (2,) or c.shape != (2,) or not np.all(np.isfinite(c)) or not np.all(np.isfinite(n)) or abs(np.linalg.norm(n) - 1) > 1e-8:
                        raise ValueError("invalid frozen transect geometry")
                    identity = dict(beam=int(beam_key), stage_index=stage_index, load_kN=float(loads[stage_index]), transect_id=int(transect["id"]))
                    stored_profile = profiles[stage_index, transect_index]
                    stored = measure(s, stored_profile)
                    stored_writer.writerow(identity | measurement_fields(stored))
                    stored_handle.flush()
                    baseline_profile = baseline_continuous = baseline_points = None
                    for variant in VARIANTS:
                        check_budget()
                        origin_points = sampling_grid(c, n, s, variant)
                        source_points = native_to_source(origin_points, H_inverse, beam["native_shape"], beam["working_shape"])
                        conjugate = conjugated_check(origin_points, H_inverse, beam["native_shape"], beam["working_shape"])
                        recovered = source_to_origin(source_points, H, beam["native_shape"], beam["working_shape"])
                        mapping_residual, roundtrip_residual = source_points - conjugate, recovered - origin_points
                        coordinate["sample_points"] += int(np.prod(origin_points.shape[:-1]))
                        for label, residual in (("mapping", mapping_residual), ("roundtrip", roundtrip_residual)):
                            coordinate[f"max_{label}_abs_px"] = max(coordinate[f"max_{label}_abs_px"], float(np.max(np.abs(residual))))
                            coordinate[f"max_{label}_euclidean_px"] = max(coordinate[f"max_{label}_euclidean_px"], float(np.max(np.linalg.norm(residual, axis=-1))))
                        profile = median_source_profile(image, source_points)
                        result = measure(s, profile)
                        variant_writer.writerow(identity | dict(variant=variant) | measurement_fields(result))
                        variant_handle.flush()
                        if variant == "baseline":
                            baseline_profile, baseline_points = profile, source_points
                            baseline_continuous = median_source_profile(image, source_points, quantised=False)
                            replay = dict(identity)
                            for mode, sampled in (("quantised", profile), ("continuous", baseline_continuous)):
                                measured = measure(s, sampled)
                                replay.update({f"{mode}_{k}": v for k, v in measurement_fields(measured).items()})
                                replay[f"{mode}_profile_max_abs_diff"] = float(np.max(np.abs(sampled.astype(np.float64) - stored_profile.astype(np.float64))))
                            replay_writer.writerow(replay)
                            replay_handle.flush()
                    if identity["transect_id"] == 6 and stage_index in (0, len(stages) - 1):
                        check_budget()
                        prefix = f"beam{beam_key}_stage{stage_index}_t6"
                        strip_s, strip_t = np.arange(-60, 61, dtype=np.float64), np.arange(-24, 25, dtype=np.float64)
                        strip_origin = sampling_grid(c, n, strip_s, tangent_offsets=strip_t)
                        strip_source = native_to_source(strip_origin, H_inverse, beam["native_shape"], beam["working_shape"])
                        examples[prefix + "_strip"] = bilinear(image, strip_source)
                        examples[prefix + "_strip_s"] = strip_s
                        examples[prefix + "_strip_t"] = strip_t
                        examples[prefix + "_strip_source_coordinates"] = strip_source
                        examples[prefix + "_normal_offsets"] = s
                        examples[prefix + "_source_coordinates"] = baseline_points
                        for label, profile in (("stored", stored_profile), ("quantised", baseline_profile), ("continuous", baseline_continuous)):
                            result = measure(s, profile)
                            examples[prefix + f"_{label}_profile"] = profile
                            examples[prefix + f"_{label}_background"] = result["background"]
                            examples[prefix + f"_{label}_deficit"] = result["deficit"]
                            examples[prefix + f"_{label}_crossings_width"] = np.array([result["left_px"], result["right_px"], result["width_px"]])
                        example_metadata.append(identity | dict(prefix=prefix, source_path=str(source_path), center=c.tolist(), normal=n.tolist(),
                                                               strip_axes="rows=tangent -24..24, columns=normal -60..60, 1 native px"))
                    receipt["completed_rows"] += 1
        if expected_total != 168 or receipt["completed_rows"] != 168:
            raise ValueError("expected 14 stages x 12 transects in total")
        check_budget()
        receipt["status"] = "complete"
    except Exception as exc:
        receipt.update(status="budget_stopped" if isinstance(exc, BudgetExceeded) else "stopped", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        for handle in handles:
            handle.close()
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["ended_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "runtime_receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        (output / "coordinate_summary.json").write_text(json.dumps(coordinate, indent=2, allow_nan=False) + "\n")
        (output / "examples.json").write_text(json.dumps(example_metadata, indent=2, allow_nan=False) + "\n")
        if examples:
            np.savez_compressed(output / "examples.npz", **examples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--budget-seconds", type=float, default=120)
    args = parser.parse_args()
    execute(args.inputs, args.output, args.budget_seconds)


if __name__ == "__main__":
    main()
