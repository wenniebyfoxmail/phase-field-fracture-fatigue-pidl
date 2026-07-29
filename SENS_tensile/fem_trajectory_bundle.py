"""Contracts and validators for FEM fracture trajectory bundles.

The bundle is source-backed: large per-cycle arrays remain in immutable source
archives while the manifest records their hashes, state semantics, and field
mapping.  A consumer must validate the manifest before materialising arrays.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import numpy as np
from scipy.io import loadmat


BUNDLE_SCHEMA_VERSION = "fem_trajectory_bundle_v1"
SPLIT_SCHEMA_VERSION = "fem_loto_split_v1"
REQUIRED_SOURCE_FIELDS = {
    "damage": "d_elem",
    "alpha_bar": "alpha_bar_elem",
    "fatigue_degradation": "f_alpha_elem",
    "raw_driver": "psi_elem",
}
REQUIRED_EXPORTED_FIELDS = (
    "damage",
    "alpha_bar",
    "fatigue_degradation",
    "damage_degradation",
    "raw_driver",
    "active_driver",
)
REQUIRED_PROXY_CHANNELS = (
    "crack_geometry_image",
    "fwd_basin",
    "strain_localization",
)
ALLOWED_PHASES = {"cycle_peak", "cycle_unloaded", "state0"}
DAMAGE_NUMERICAL_TOL = 5e-5
ALLOWED_CLASSES = {
    "independent_physical_trajectory",
    "load_amplitude_sensitivity",
    "controlled_factorial_combination",
    "protocol_comparator",
}


@dataclass
class ValidationReport:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def error(self, message: str) -> None:
        self.valid = False
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def mesh_content_sha256(graph_path: Path) -> tuple[str, int]:
    """Hash geometry/topology arrays without inheriting old trajectory states."""
    data = np.load(graph_path, allow_pickle=False)
    required = ("centroids", "areas", "connectivity", "edge_index")
    missing = [key for key in required if key not in data.files]
    if missing:
        raise ValueError(f"mesh graph missing arrays: {missing}")
    digest = hashlib.sha256()
    for key in required:
        array = np.ascontiguousarray(data[key])
        digest.update(key.encode("ascii"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest(), int(np.asarray(data["areas"]).size)


def vtk_mesh_content_sha256(path: Path) -> tuple[str, int, int]:
    """Hash normalized ASCII VTK geometry/topology, excluding solution fields."""
    digest = hashlib.sha256()
    started = False
    point_count = -1
    cell_count = -1
    with path.open("r", encoding="ascii", errors="strict") as handle:
        for line in handle:
            stripped = " ".join(line.split())
            if stripped.startswith("DATASET "):
                started = True
            if not started:
                continue
            if stripped.startswith(("CELL_DATA ", "POINT_DATA ")):
                break
            if stripped.startswith("POINTS "):
                point_count = int(stripped.split()[1])
            if stripped.startswith("CELLS "):
                cell_count = int(stripped.split()[1])
            digest.update(stripped.encode("ascii"))
            digest.update(b"\n")
    if point_count <= 0 or cell_count <= 0:
        raise ValueError(f"could not parse VTK mesh counts from {path}")
    return digest.hexdigest(), point_count, cell_count


def _cycle_from_path(path: Path) -> int:
    match = re.fullmatch(r"cycle_(\d{4})\.mat", path.name)
    if not match:
        raise ValueError(f"unsupported state shard name: {path.name}")
    return int(match.group(1))


def _field_stats(array: np.ndarray) -> dict[str, Any]:
    values = np.asarray(array).reshape(-1)
    return {
        "count": int(values.size),
        "dtype": str(values.dtype),
        "finite": bool(np.isfinite(values).all()),
        "min": float(np.nanmin(values)),
        "max": float(np.nanmax(values)),
    }


def inspect_state_shard(
    path: Path, expected_cells: int
) -> tuple[dict[str, Any], list[str]]:
    """Read one Hard5 state shard and validate physical-array basics."""
    errors: list[str] = []
    data = loadmat(path)
    missing = [
        source for source in REQUIRED_SOURCE_FIELDS.values() if source not in data
    ]
    if missing:
        return {"path": str(path), "missing": missing}, [
            f"{path}: missing fields {missing}"
        ]

    arrays = {
        exported: np.asarray(data[source]).reshape(-1)
        for exported, source in REQUIRED_SOURCE_FIELDS.items()
    }
    arrays["damage_degradation"] = np.square(1.0 - arrays["damage"])
    arrays["active_driver"] = arrays["damage_degradation"] * arrays["raw_driver"]
    stats = {name: _field_stats(values) for name, values in arrays.items()}

    for name, values in arrays.items():
        if values.size != expected_cells:
            errors.append(
                f"{path}: {name} has {values.size} cells, expected {expected_cells}"
            )
        if not np.isfinite(values).all():
            errors.append(f"{path}: {name} contains non-finite values")
    if np.any(
        (arrays["damage"] < -DAMAGE_NUMERICAL_TOL)
        | (arrays["damage"] > 1.0 + DAMAGE_NUMERICAL_TOL)
    ):
        errors.append(
            f"{path}: damage exceeds [0,1] numerical tolerance {DAMAGE_NUMERICAL_TOL:g}"
        )
    if np.any(arrays["alpha_bar"] < -1e-12):
        errors.append(f"{path}: alpha_bar contains negative values")
    if np.any(
        (arrays["fatigue_degradation"] < -1e-10)
        | (arrays["fatigue_degradation"] > 1.0 + 1e-10)
    ):
        errors.append(f"{path}: fatigue_degradation outside [0,1]")
    if np.any(arrays["raw_driver"] < -1e-12) or np.any(
        arrays["active_driver"] < -1e-12
    ):
        errors.append(f"{path}: driver contains negative values")
    return {"path": str(path), "fields": stats}, errors


def default_observable_proxy_contract() -> dict[str, Any]:
    """Declare deployable channel names without claiming FEM proxies are real data."""
    return {
        "crack_geometry_image": {
            "availability": "synthetic_from_fem",
            "values_recipe": "damage",
            "mask_recipe": "finite(damage)",
            "uncertainty_recipe": "zero_only_for_deterministic_fem_audit",
            "deployment_equivalent": False,
            "note": "2D coupon damage is an oracle image proxy, not a road photograph.",
        },
        "fwd_basin": {
            "availability": "unavailable",
            "values_recipe": None,
            "mask_recipe": "all_false",
            "uncertainty_recipe": None,
            "deployment_equivalent": False,
            "note": "The coupon archive has no FWD spatial deflection basin.",
        },
        "strain_localization": {
            "availability": "synthetic_oracle_proxy",
            "values_recipe": "sqrt(max(raw_driver,0))",
            "mask_recipe": "finite(raw_driver)",
            "uncertainty_recipe": "zero_only_for_deterministic_fem_audit",
            "deployment_equivalent": False,
            "note": "Energy-derived localization is not measured strain and must remain labelled synthetic.",
        },
    }


def build_source_backed_bundle(
    *,
    trajectory_id: str,
    family_id: str,
    independence_class: str,
    source_root: Path,
    mesh_graph_path: Path,
    umax: float,
    first_hit_cycle: int,
    confirmed_cycle: int,
    n_substeps: int,
    peak_substep_ordinal: int = 4,
    eta: float = 0.0,
    source_package_id: str | None = None,
    provenance_files: Sequence[Path] = (),
    loading_family: str = "hard5_constant_amplitude_5step",
    nominal_load_factors: Sequence[float] | None = None,
    initial_defect_family: str = "shared_hard_recovery_state",
    material_family: str = "shared_normalized_at1_carrara",
    factorial_axes: Mapping[str, str] | None = None,
    claim_scope: str | None = None,
    provenance_notes: Sequence[str] = (),
    mesh_evidence_path: Path | None = None,
) -> dict[str, Any]:
    """Build an immutable manifest over existing per-cycle MAT state shards."""
    source_root = source_root.resolve()
    mesh_graph_path = mesh_graph_path.resolve()
    if independence_class not in ALLOWED_CLASSES:
        raise ValueError(f"unsupported independence_class: {independence_class}")
    if not source_root.is_dir():
        raise FileNotFoundError(source_root)
    mesh_hash, cell_count = mesh_content_sha256(mesh_graph_path)
    state_files = sorted((source_root / "psi_fields").glob("cycle_*.mat"))
    cycles = [_cycle_from_path(path) for path in state_files]
    if not cycles:
        raise ValueError(f"no state shards under {source_root / 'psi_fields'}")

    states = []
    source_hashes = []
    for path, cycle in zip(state_files, cycles):
        digest = sha256_file(path)
        source_hashes.append({"cycle": cycle, "sha256": digest})
        states.append(
            {
                "cycle": cycle,
                "phase": "cycle_peak",
                "peak_substep_ordinal": peak_substep_ordinal,
                "raw_step_1_based": 1
                + n_substeps * (cycle - 1)
                + (peak_substep_ordinal - 1),
                "source_file": str(path),
                "source_sha256": digest,
                "field_map": dict(REQUIRED_SOURCE_FIELDS),
                "derived_fields": {
                    "damage_degradation": "(1-damage)^2",
                    "active_driver": "damage_degradation*raw_driver",
                },
                "state_semantics_id": "cycle_peak_coherent_v1",
            }
        )

    package_inputs = {}
    for name in ("checkpoint.mat", "initial_state_metadata.mat", "state0_analysis.mat"):
        path = source_root / name
        if path.exists():
            package_inputs[name] = {"path": str(path), "sha256": sha256_file(path)}
    lock = source_root.parent / "pre_run_lock.mat"
    if lock.exists():
        package_inputs["pre_run_lock.mat"] = {
            "path": str(lock),
            "sha256": sha256_file(lock),
        }
    for path in provenance_files:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        package_inputs[f"provenance::{resolved.name}"] = {
            "path": str(resolved),
            "sha256": sha256_file(resolved),
        }

    if nominal_load_factors is None:
        nominal_load_factors = [0.25, 0.5, 0.75, 1.0, 0.0]
    if len(nominal_load_factors) != n_substeps:
        raise ValueError("nominal_load_factors must match n_substeps")
    default_claim_scope = {
        "load_amplitude_sensitivity": "load_amplitude_sensitivity_only",
        "controlled_factorial_combination": "shared_geometry_within_hard5_factorial_only",
        "independent_physical_trajectory": "independent_trajectory_candidate",
        "protocol_comparator": "protocol_comparison_only",
    }[independence_class]

    mesh_evidence = None
    if mesh_evidence_path is not None:
        mesh_evidence_path = mesh_evidence_path.resolve()
        vtk_hash, vtk_points, vtk_cells = vtk_mesh_content_sha256(mesh_evidence_path)
        mesh_evidence = {
            "path": str(mesh_evidence_path),
            "source_sha256": sha256_file(mesh_evidence_path),
            "content_sha256": vtk_hash,
            "point_count": vtk_points,
            "cell_count": vtk_cells,
        }
        if vtk_cells != cell_count:
            raise ValueError(
                f"VTK mesh has {vtk_cells} cells but graph has {cell_count}: {mesh_evidence_path}"
            )

    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": f"bundle::{trajectory_id}",
        "trajectory_id": trajectory_id,
        "family_id": family_id,
        "independence_class": independence_class,
        "claim_scope": claim_scope or default_claim_scope,
        "source": {
            "package_id": source_package_id or source_root.name,
            "root": str(source_root),
            "storage_mode": "external_source_shards",
            "package_inputs": package_inputs,
            "state_shard_hashes": source_hashes,
            "provenance_notes": list(provenance_notes),
        },
        "physics": {
            "eta": eta,
            "umax": umax,
            "loading_family": loading_family,
            "n_substeps": n_substeps,
            "nominal_load_factors": list(map(float, nominal_load_factors)),
            "initial_defect_family": initial_defect_family,
            "material_family": material_family,
            "factorial_axes": dict(factorial_axes or {}),
        },
        "mesh": {
            "source": str(mesh_graph_path),
            "source_sha256": sha256_file(mesh_graph_path),
            "content_sha256": mesh_hash,
            "cell_count": cell_count,
            "source_package_evidence": mesh_evidence,
        },
        "state_semantics": {
            "state_id": "cycle_peak_coherent_v1",
            "phase": "cycle_peak",
            "loading_branch": "peak",
            "all_fields_same_cycle_and_phase": True,
            "history_timing": "exported_with_cycle_peak_shard",
            "raw_driver_timing": "cycle_peak",
            "active_definition": "(1-damage)^2*raw_driver",
            "fatigue_degradation_field": "f_alpha_elem",
            "raw_step_mapping": "1+n_substeps*(cycle-1)+(peak_substep_ordinal-1)",
        },
        "event": {
            "first_hit": {
                "cycle": first_hit_cycle,
                "phase": "cycle_peak",
                "role": "energetic_event",
            },
            "confirmed": {
                "cycle": confirmed_cycle,
                "phase": "cycle_peak",
                "role": "penetration_robustness",
            },
            "criterion": "at_least_3_nodes_d_ge_0.95_at_x_ge_0.48",
            "confirmation_rule": "producer_declared_three_cycle_confirmation",
            "mixed_event_phase_forbidden": True,
        },
        "fields": {
            "required_exported": list(REQUIRED_EXPORTED_FIELDS),
            "source_map": dict(REQUIRED_SOURCE_FIELDS),
            "derived": {
                "damage_degradation": "(1-damage)^2",
                "active_driver": "damage_degradation*raw_driver",
            },
        },
        "observable_proxies": default_observable_proxy_contract(),
        "states": states,
    }
    bundle["manifest_sha256"] = canonical_json_sha256(bundle)
    return bundle


def validate_bundle(
    bundle: Mapping[str, Any], *, deep: bool = False
) -> ValidationReport:
    report = ValidationReport()
    required_top = (
        "schema_version",
        "bundle_id",
        "trajectory_id",
        "family_id",
        "independence_class",
        "source",
        "physics",
        "mesh",
        "state_semantics",
        "event",
        "fields",
        "observable_proxies",
        "states",
    )
    for key in required_top:
        if key not in bundle:
            report.error(f"missing top-level key: {key}")
    if not report.valid:
        return report
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION:
        report.error(f"unsupported schema_version: {bundle['schema_version']}")
    if bundle["independence_class"] not in ALLOWED_CLASSES:
        report.error(f"unsupported independence_class: {bundle['independence_class']}")

    searchable_identity = " ".join(
        [
            *(
                str(bundle.get(key, ""))
                for key in ("bundle_id", "trajectory_id", "family_id")
            ),
            str(bundle.get("source", {}).get("package_id", "")),
            str(bundle.get("source", {}).get("root", "")),
        ]
    ).lower()
    event = bundle["event"]
    first_hit = int(event.get("first_hit", {}).get("cycle", -1))
    confirmed = int(event.get("confirmed", {}).get("cycle", -1))
    legacy_markers = (
        "legacy_c69",
        "soft_hist0_element_fields_c1_c69",
        "reversebc_u12_diffuse_precrack",
    )
    if any(marker in searchable_identity for marker in legacy_markers):
        report.error("legacy c69 event package is forbidden")
    if first_hit <= 0 or confirmed < first_hit:
        report.error("invalid first-hit/confirmed ordering")
    if event.get("first_hit", {}).get("role") == event.get("confirmed", {}).get("role"):
        report.error("first-hit and confirmed roles must remain distinct")

    semantics = bundle["state_semantics"]
    if not semantics.get("all_fields_same_cycle_and_phase", False):
        report.error("mixed loading-step fields are forbidden")
    if semantics.get("phase") not in ALLOWED_PHASES:
        report.error(f"unsupported state phase: {semantics.get('phase')}")
    required_exported = set(bundle["fields"].get("required_exported", []))
    missing_exports = set(REQUIRED_EXPORTED_FIELDS) - required_exported
    if missing_exports:
        report.error(f"missing required exported fields: {sorted(missing_exports)}")
    missing_proxies = set(REQUIRED_PROXY_CHANNELS) - set(bundle["observable_proxies"])
    if missing_proxies:
        report.error(f"missing observable proxy channels: {sorted(missing_proxies)}")

    physics = bundle["physics"]
    n_substeps = int(physics.get("n_substeps", 0))
    if n_substeps <= 0:
        report.error("n_substeps must be positive")
    if len(physics.get("nominal_load_factors", [])) != n_substeps:
        report.error("loading schedule length does not match n_substeps")
    if bundle["independence_class"] == "controlled_factorial_combination":
        axes = physics.get("factorial_axes", {})
        if set(axes) != {"initial_tip_state", "loading_history"}:
            report.error("controlled factorial bundle must declare both 2x2 axes")
        if bundle.get("claim_scope") != "shared_geometry_within_hard5_factorial_only":
            report.error(
                "controlled factorial claim scope exceeds the permitted numerical gate"
            )
    states = list(bundle["states"])
    cycles = [int(state.get("cycle", -1)) for state in states]
    if cycles != sorted(set(cycles)):
        report.error("state cycles must be unique and sorted")
    if cycles and cycles != list(range(1, cycles[-1] + 1)):
        report.error("state cycles must be contiguous from cycle 1")
    if confirmed not in cycles:
        report.error("confirmed event cycle missing from states")
    if first_hit not in cycles:
        report.error("first-hit cycle missing from states")

    semantics_id = semantics.get("state_id")
    for state in states:
        cycle = int(state.get("cycle", -1))
        ordinal = int(state.get("peak_substep_ordinal", -1))
        expected_raw_step = 1 + n_substeps * (cycle - 1) + (ordinal - 1)
        if state.get("phase") != semantics.get("phase"):
            report.error(f"cycle {cycle}: loading phase mismatch")
        if state.get("state_semantics_id") != semantics_id:
            report.error(f"cycle {cycle}: state semantics mismatch")
        if int(state.get("raw_step_1_based", -1)) != expected_raw_step:
            report.error(f"cycle {cycle}: loading-step mapping mismatch")

    expected_manifest_hash = bundle.get("manifest_sha256")
    if expected_manifest_hash:
        unhashed = dict(bundle)
        unhashed.pop("manifest_sha256", None)
        actual = canonical_json_sha256(unhashed)
        if actual != expected_manifest_hash:
            report.error("manifest SHA-256 mismatch")

    expected_cells = int(bundle["mesh"].get("cell_count", 0))
    if deep and expected_cells > 0:
        mesh_path = Path(bundle["mesh"]["source"])
        if not mesh_path.is_file():
            report.error(f"missing mesh source: {mesh_path}")
        else:
            if sha256_file(mesh_path) != bundle["mesh"].get("source_sha256"):
                report.error("mesh source SHA-256 mismatch")
            content_hash, mesh_cells = mesh_content_sha256(mesh_path)
            if content_hash != bundle["mesh"].get("content_sha256"):
                report.error("mesh content SHA-256 mismatch")
            if mesh_cells != expected_cells:
                report.error("mesh cell count mismatch")
        vtk_evidence = bundle["mesh"].get("source_package_evidence")
        if vtk_evidence:
            vtk_path = Path(vtk_evidence["path"])
            if not vtk_path.is_file():
                report.error(f"missing source-package VTK mesh evidence: {vtk_path}")
            else:
                if sha256_file(vtk_path) != vtk_evidence.get("source_sha256"):
                    report.error("source-package VTK SHA-256 mismatch")
                vtk_hash, vtk_points, vtk_cells = vtk_mesh_content_sha256(vtk_path)
                if vtk_hash != vtk_evidence.get("content_sha256"):
                    report.error("source-package VTK mesh content SHA-256 mismatch")
                if vtk_points != int(vtk_evidence.get("point_count", -1)):
                    report.error("source-package VTK point count mismatch")
                if vtk_cells != expected_cells:
                    report.error("source-package VTK cell count mismatch")

        for name, asset in bundle["source"].get("package_inputs", {}).items():
            path = Path(asset["path"])
            if not path.is_file():
                report.error(f"missing provenance input {name}: {path}")
            elif sha256_file(path) != asset.get("sha256"):
                report.error(f"provenance SHA-256 mismatch: {name}")

        lock_asset = bundle["source"].get("package_inputs", {}).get("pre_run_lock.mat")
        if lock_asset:
            with h5py.File(lock_asset["path"], "r") as handle:
                cfg = handle["lock/cfg"] if "lock" in handle else handle["cfg"]
                lock_checks = {
                    "n_substeps": int(np.asarray(cfg["n_step"]).reshape(-1)[0]),
                    "umax": float(np.asarray(cfg["u_max"]).reshape(-1)[0]),
                    "eta": float(np.asarray(cfg["res_stiff"]).reshape(-1)[0]),
                    "load_factors": np.asarray(cfg["nominal_load_factor"], dtype=float)
                    .reshape(-1)
                    .tolist(),
                }
            report.checks["pre_run_lock"] = lock_checks
            if lock_checks["n_substeps"] != n_substeps:
                report.error("pre-run lock n_substeps mismatch")
            if not np.isclose(lock_checks["umax"], float(physics.get("umax"))):
                report.error("pre-run lock Umax mismatch")
            if not np.isclose(lock_checks["eta"], float(physics.get("eta"))):
                report.error("pre-run lock eta mismatch")
            if not np.allclose(
                lock_checks["load_factors"], physics.get("nominal_load_factors", [])
            ):
                report.error("pre-run lock loading schedule mismatch")

        checked = 0
        damage_min = float("inf")
        damage_max = float("-inf")
        for state in states:
            path = Path(state["source_file"])
            if not path.is_file():
                report.error(f"missing state shard: {path}")
                continue
            if sha256_file(path) != state.get("source_sha256"):
                report.error(f"state shard SHA-256 mismatch: {path}")
                continue
            inspected, errors = inspect_state_shard(path, expected_cells)
            report.errors.extend(errors)
            if errors:
                report.valid = False
            field_stats = inspected.get("fields", {}).get("damage", {})
            damage_min = min(damage_min, float(field_stats.get("min", damage_min)))
            damage_max = max(damage_max, float(field_stats.get("max", damage_max)))
            checked += 1
        report.checks["deep_state_shards_checked"] = checked
        report.checks["damage_extrema"] = {"min": damage_min, "max": damage_max}
        if damage_min < 0.0 or damage_max > 1.0:
            report.warning(
                "damage has solver-scale bound overshoot retained without clipping: "
                f"min={damage_min:.8g}, max={damage_max:.8g}"
            )

    report.checks.update(
        {
            "trajectory_id": bundle.get("trajectory_id"),
            "family_id": bundle.get("family_id"),
            "state_count": len(states),
            "first_hit_cycle": first_hit,
            "confirmed_cycle": confirmed,
            "cell_count": expected_cells,
        }
    )
    return report


def build_loto_split_lock(
    bundles: Sequence[Mapping[str, Any]],
    pending_slots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Pre-register whole-trajectory folds and refuse sensitivity-family inflation."""
    independent = [
        bundle
        for bundle in bundles
        if bundle.get("independence_class") == "independent_physical_trajectory"
    ]
    sensitivity = [
        bundle
        for bundle in bundles
        if bundle.get("independence_class") == "load_amplitude_sensitivity"
    ]
    folds = []
    ids = [str(bundle["trajectory_id"]) for bundle in independent]
    for held_out in ids:
        folds.append(
            {
                "fold_id": f"holdout::{held_out}",
                "train_trajectory_ids": [
                    trajectory_id for trajectory_id in ids if trajectory_id != held_out
                ],
                "test_trajectory_ids": [held_out],
                "unit_of_split": "complete_trajectory",
                "node_split_forbidden": True,
                "cycle_split_forbidden": True,
                "window_crossing_forbidden": True,
            }
        )
    ready = len(independent) >= 3 and all(
        len(fold["train_trajectory_ids"]) >= 2 for fold in folds
    )
    split = {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "status": "ready" if ready else "blocked_by_data",
        "primary_claim": "leave_one_independent_trajectory_out",
        "eligible_independence_class": "independent_physical_trajectory",
        "claim_boundary": "candidate cross-trajectory numerical generalization; not road validation",
        "minimum_independent_trajectories": 3,
        "available_independent_trajectory_ids": ids,
        "pending_independent_slots": list(pending_slots),
        "excluded_sensitivity_library": {
            "trajectory_ids": [str(bundle["trajectory_id"]) for bundle in sensitivity],
            "family_ids": sorted({str(bundle["family_id"]) for bundle in sensitivity}),
            "reason": "load-amplitude variants share geometry, material, initialization, and loading family",
            "grouping_rule": "all members stay together and remain outside primary LOTO",
        },
        "folds": folds,
        "leakage_guards": {
            "split_unit": "trajectory_id",
            "family_grouping_required": True,
            "node_level_random_split": False,
            "cycle_level_random_split": False,
            "future_state_in_features": False,
            "event_cycle_as_feature": False,
            "c69_legacy_allowed": False,
        },
        "training_launch_allowed": ready,
    }
    split["lock_sha256"] = canonical_json_sha256(split)
    return split


def build_factorial_loco_split_lock(
    bundles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a scoped leave-one-combination-out lock for the Hard5 2x2 study."""
    eligible = [
        bundle
        for bundle in bundles
        if bundle.get("independence_class") == "controlled_factorial_combination"
    ]
    combinations: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicate_combinations: list[list[str]] = []
    for bundle in eligible:
        axes = bundle.get("physics", {}).get("factorial_axes", {})
        combination = (
            str(axes.get("initial_tip_state")),
            str(axes.get("loading_history")),
        )
        if combination in combinations:
            duplicate_combinations.append(
                [
                    str(combinations[combination]["trajectory_id"]),
                    str(bundle["trajectory_id"]),
                ]
            )
        else:
            combinations[combination] = bundle

    expected = {
        ("hard_recovery", "retained_5step"),
        ("hard_recovery", "explicit_8step"),
        ("analytic_soft_profile", "retained_5step"),
        ("analytic_soft_profile", "explicit_8step"),
    }
    observed = set(combinations)
    ids = [str(combinations[key]["trajectory_id"]) for key in sorted(combinations)]
    folds = [
        {
            "fold_id": f"holdout_combination::{held_out}",
            "train_trajectory_ids": [
                trajectory_id for trajectory_id in ids if trajectory_id != held_out
            ],
            "test_trajectory_ids": [held_out],
            "unit_of_split": "complete_trajectory",
            "node_split_forbidden": True,
            "cycle_split_forbidden": True,
            "window_crossing_forbidden": True,
        }
        for held_out in ids
    ]
    ready = observed == expected and not duplicate_combinations and len(ids) == 4
    split = {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "status": "ready" if ready else "blocked_by_data",
        "primary_claim": "within_hard5_leave_one_factorial_combination_out",
        "eligible_independence_class": "controlled_factorial_combination",
        "claim_boundary": (
            "shared-geometry controlled numerical 2x2 gate only; not independent roads, "
            "material generalization, or geometry generalization"
        ),
        "minimum_independent_trajectories": 4,
        "available_independent_trajectory_ids": ids,
        "expected_factorial_combinations": [list(value) for value in sorted(expected)],
        "observed_factorial_combinations": [list(value) for value in sorted(observed)],
        "duplicate_factorial_combinations": duplicate_combinations,
        "shared_controls": {
            "geometry": "shared",
            "mesh": "shared",
            "material": "shared_normalized_at1_carrara",
            "umax": 0.12,
            "eta": 0.0,
        },
        "folds": folds,
        "leakage_guards": {
            "split_unit": "trajectory_id",
            "node_level_random_split": False,
            "cycle_level_random_split": False,
            "future_state_in_features": False,
            "event_cycle_as_feature": False,
            "duplicate_configuration_across_folds": False,
            "c69_legacy_allowed": False,
        },
        "training_launch_allowed": ready,
        "training_launched": False,
    }
    split["lock_sha256"] = canonical_json_sha256(split)
    return split


def validate_loto_split(
    split: Mapping[str, Any], bundles: Sequence[Mapping[str, Any]]
) -> ValidationReport:
    report = ValidationReport()
    if split.get("schema_version") != SPLIT_SCHEMA_VERSION:
        report.error("unsupported split schema")
        return report
    known = {str(bundle["trajectory_id"]): bundle for bundle in bundles}
    eligible_class = str(
        split.get("eligible_independence_class", "independent_physical_trajectory")
    )
    for fold in split.get("folds", []):
        train = set(map(str, fold.get("train_trajectory_ids", [])))
        test = set(map(str, fold.get("test_trajectory_ids", [])))
        if train & test:
            report.error(f"{fold.get('fold_id')}: train/test trajectory overlap")
        unknown = (train | test) - set(known)
        if unknown:
            report.error(
                f"{fold.get('fold_id')}: unknown trajectories {sorted(unknown)}"
            )
        for trajectory_id in train | test:
            if known[trajectory_id].get("independence_class") != eligible_class:
                report.error(
                    f"{fold.get('fold_id')}: trajectory outside eligible class {eligible_class}"
                )
        if not fold.get("node_split_forbidden") or not fold.get(
            "cycle_split_forbidden"
        ):
            report.error(f"{fold.get('fold_id')}: node/cycle leakage guards disabled")
    unhashed = dict(split)
    expected = unhashed.pop("lock_sha256", None)
    if expected != canonical_json_sha256(unhashed):
        report.error("split lock SHA-256 mismatch")
    independent_count = sum(
        bundle.get("independence_class") == eligible_class for bundle in bundles
    )
    expected_ready = independent_count >= int(
        split.get("minimum_independent_trajectories", 3)
    )
    if bool(split.get("training_launch_allowed")) != expected_ready:
        report.error("training launch flag inconsistent with eligible trajectory count")
    if eligible_class == "controlled_factorial_combination":
        expected = {
            tuple(value) for value in split.get("expected_factorial_combinations", [])
        }
        observed = {
            tuple(value) for value in split.get("observed_factorial_combinations", [])
        }
        if expected != observed or split.get("duplicate_factorial_combinations"):
            report.error("factorial combination coverage is incomplete or duplicated")
        if "not independent roads" not in str(split.get("claim_boundary", "")):
            report.error(
                "factorial split is missing the road-generalization claim boundary"
            )
    report.checks["eligible_independence_class"] = eligible_class
    report.checks["eligible_trajectory_count"] = independent_count
    report.checks["fold_count"] = len(split.get("folds", []))
    return report


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_bundles(paths: Iterable[Path]) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]
