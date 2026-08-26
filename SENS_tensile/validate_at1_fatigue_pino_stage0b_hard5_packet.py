#!/usr/bin/env python3
"""Fail-closed validator for the Hard5-only AT1-fatigue PINO Stage 0b packet.

This gate validates packet identity, exact state coverage, payload hashes,
native Q4 shapes, state timing, damage non-recovery and the producer's exact
four-channel committed history update. It deliberately does not claim to
recompute equilibrium or the AT1 phase residual; those remain a separate Mac
gate after a real producer packet is accepted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat


REQUIRED_INDEX_COLUMNS = {
    "case_id",
    "physical_cycle",
    "substep",
    "load_factor",
    "state_kind",
    "state_file",
    "source_kind",
    "source_checkpoint",
    "converged",
    "n_stagger",
    "n_newton_u",
    "n_newton_d",
    "equilibrium_residual_free_l2",
    "phase_residual_active_l2",
}

REQUIRED_MESH_FIELDS = {
    "node_coords",
    "connectivity_q4",
    "element_material_id",
    "active_dof_u",
    "active_dof_d",
    "dirichlet_dof_u",
    "dirichlet_dof_d",
    "Nxi",
    "dNdxi",
    "gauss_weights",
    "thickness",
    "E",
    "nu",
    "Gc",
    "ell",
    "res_stiff",
    "alpha_T",
    "fatigue_p",
    "stress_state_code",
}

REQUIRED_STATE_FIELDS = {"u_node", "d_node", "history_gp", "strain_en_undgr_gp"}
ALLOWED_SOURCE_KINDS = {"direct_export", "checkpoint_replay", "fresh_exact_replay"}


class PacketError(RuntimeError):
    """Raised when a packet violates the frozen Request 31 contract."""


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PacketError(f"JSON root must be an object: {path}")
    return value


def _load_mat(path: Path) -> dict[str, np.ndarray]:
    try:
        raw = loadmat(path, squeeze_me=False, struct_as_record=False)
    except Exception as exc:
        raise PacketError(f"cannot read MATLAB v7-or-earlier file {path}: {exc}") from exc
    return {key: np.asarray(value) for key, value in raw.items() if not key.startswith("__")}


def _require_fields(data: dict, required: set[str], label: str) -> None:
    missing = sorted(required - set(data))
    if missing:
        raise PacketError(f"{label} missing fields: {', '.join(missing)}")


def _shape(name: str, value: np.ndarray, expected: tuple[int, ...]) -> np.ndarray:
    array = np.asarray(value)
    if array.shape == expected:
        normalized = array
    elif np.squeeze(array).shape == expected:
        normalized = np.squeeze(array)
    elif array.size == int(np.prod(expected)):
        normalized = array.reshape(expected)
    else:
        raise PacketError(f"{name} shape {array.shape}, expected {expected}")
    if not np.all(np.isfinite(normalized)):
        raise PacketError(f"{name} contains NaN or Inf")
    return normalized.astype(np.float64, copy=False)


def _as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except (KeyError, ValueError) as exc:
        raise PacketError(f"invalid integer {key}={row.get(key)!r}") from exc


def _as_float(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise PacketError(f"invalid float {key}={row.get(key)!r}") from exc
    if not np.isfinite(value):
        raise PacketError(f"non-finite {key}={row.get(key)!r}")
    return value


def _scalar(name: str, value: np.ndarray) -> float:
    array = np.asarray(value).squeeze()
    if array.size != 1:
        raise PacketError(f"{name} must be a finite scalar")
    result = float(array)
    if not np.isfinite(result):
        raise PacketError(f"{name} must be a finite scalar")
    return result


def _safe_relative_path(value: str, label: str) -> str:
    path = Path(value)
    if not value or "\\" in value or path.is_absolute() or ".." in path.parts:
        raise PacketError(f"{label} must be a safe POSIX relative path: {value!r}")
    return path.as_posix()


def _read_index(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise PacketError(f"empty state index: {path}")
            missing = sorted(REQUIRED_INDEX_COLUMNS - set(reader.fieldnames))
            if missing:
                raise PacketError(f"state_index.csv missing columns: {', '.join(missing)}")
            return list(reader)
    except OSError as exc:
        raise PacketError(f"cannot read state index {path}: {exc}") from exc


def _read_sha256sums(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PacketError(f"cannot read {path}: {exc}") from exc
    result: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise PacketError(f"malformed SHA256SUMS line: {line!r}")
        relpath = parts[1].lstrip("*")
        if relpath in result:
            raise PacketError(f"duplicate SHA256SUMS entry: {relpath}")
        result[relpath] = parts[0].lower()
    return result


def _check_hashes(packet: Path, sums: dict[str, str], required_files: set[str]) -> None:
    missing = sorted(required_files - set(sums))
    if missing:
        raise PacketError(f"SHA256SUMS does not cover: {', '.join(missing)}")
    for relpath, expected in sums.items():
        path = packet / relpath
        if not path.is_file():
            raise PacketError(f"SHA256SUMS references missing file: {relpath}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise PacketError(f"SHA-256 mismatch for {relpath}")


def _load_state(path: Path, nnode: int, nelem: int, ngp: int) -> dict[str, np.ndarray]:
    data = _load_mat(path)
    _require_fields(data, REQUIRED_STATE_FIELDS, str(path))
    return {
        "u": _shape(f"{path}:u_node", data["u_node"], (nnode, 2)),
        "d": _shape(f"{path}:d_node", data["d_node"], (nnode,)),
        "history": _shape(f"{path}:history_gp", data["history_gp"], (nelem, ngp, 4)),
        "psi": _shape(
            f"{path}:strain_en_undgr_gp", data["strain_en_undgr_gp"], (nelem, ngp)
        ),
    }


def validate(packet: Path, spec_path: Path) -> dict:
    spec = _load_json(spec_path)
    if spec.get("scope") != "hard5_u012_only" or len(spec.get("cases", [])) != 1:
        raise PacketError("locked spec must contain exactly the Hard5 U0.12 case")
    case = spec["cases"][0]
    if case.get("case_id") != "hard5_u012" or case.get("cycles") != [1, 60, 82]:
        raise PacketError("locked Hard5 case identity or cycles changed")
    if case.get("load_factors") != [0.25, 0.5, 0.75, 1.0, 0.0]:
        raise PacketError("locked Hard5 five-substep schedule changed")

    manifest = _load_json(packet / "REQUEST_MANIFEST.json")
    for key in ("request_id", "schema_version", "scope", "state_timing", "history_channel_order"):
        if manifest.get(key) != spec.get(key):
            raise PacketError(f"manifest {key} does not match the locked Request 31 spec")

    mesh_rel = _safe_relative_path(manifest.get("mesh_file", "static_mesh.mat"), "mesh_file")
    index_rel = _safe_relative_path(
        manifest.get("state_index_file", "state_index.csv"), "state_index_file"
    )
    sums_rel = _safe_relative_path(
        manifest.get("sha256sums_file", "SHA256SUMS"), "sha256sums_file"
    )
    mesh = _load_mat(packet / mesh_rel)
    _require_fields(mesh, REQUIRED_MESH_FIELDS, str(packet / mesh_rel))

    expected = spec["expected_mesh"]
    nnode, nelem, ngp = expected["nnode"], expected["nelem"], expected["ngp"]
    _shape("node_coords", mesh["node_coords"], (nnode, 2))
    connectivity = _shape("connectivity_q4", mesh["connectivity_q4"], (nelem, 4))
    if np.min(connectivity) < 1 or np.max(connectivity) > nnode:
        raise PacketError("connectivity_q4 must use MATLAB 1-based node indices")
    connectivity0 = connectivity.astype(np.int64) - 1
    _shape("element_material_id", mesh["element_material_id"], (nelem,))
    nxi = _shape("Nxi", mesh["Nxi"], (4, ngp))
    _shape("dNdxi", mesh["dNdxi"], (2, 4, ngp))
    _shape("gauss_weights", mesh["gauss_weights"], (ngp,))
    if _scalar("thickness", mesh["thickness"]) <= 0:
        raise PacketError("thickness must be positive")
    for positive_field in ("E", "Gc", "ell"):
        if _scalar(positive_field, mesh[positive_field]) <= 0:
            raise PacketError(f"{positive_field} must be positive")
    nu = _scalar("nu", mesh["nu"])
    if not -1.0 < nu < 0.5:
        raise PacketError("nu must lie in (-1, 0.5)")
    for mesh_field, case_field in (
        ("res_stiff", "res_stiff"),
        ("alpha_T", "alpha_T"),
        ("fatigue_p", "fatigue_p"),
    ):
        if not np.isclose(
            _scalar(mesh_field, mesh[mesh_field]), float(case[case_field]), atol=1e-14, rtol=0
        ):
            raise PacketError(f"mesh {mesh_field} differs from the locked case value")
    _scalar("stress_state_code", mesh["stress_state_code"])

    rows = _read_index(packet / index_rel)
    keyed: dict[tuple[str, int, int], dict[str, str]] = {}
    state_files: set[str] = set()
    for row in rows:
        key = (row["case_id"], _as_int(row, "physical_cycle"), _as_int(row, "substep"))
        if key in keyed:
            raise PacketError(f"duplicate state-index row: {key}")
        if row["source_kind"] not in ALLOWED_SOURCE_KINDS:
            raise PacketError(f"invalid source_kind for {key}: {row['source_kind']!r}")
        if row["converged"].strip().lower() not in {"true", "1"}:
            raise PacketError(f"non-converged state is not admissible: {key}")
        for field in ("n_stagger", "n_newton_u", "n_newton_d"):
            if _as_int(row, field) < 0:
                raise PacketError(f"negative {field} for {key}")
        for field in ("equilibrium_residual_free_l2", "phase_residual_active_l2"):
            if _as_float(row, field) < 0:
                raise PacketError(f"negative {field} for {key}")
        state_file = _safe_relative_path(row["state_file"], f"state_file for {key}")
        if state_file in state_files:
            raise PacketError(f"duplicate state_file reference: {state_file}")
        row["state_file"] = state_file
        keyed[key] = row
        state_files.add(state_file)

    expected_keys = {
        (case["case_id"], cycle, substep)
        for cycle in case["cycles"]
        for substep in range(len(case["load_factors"]) + 1)
    }
    if set(keyed) != expected_keys:
        missing = sorted(expected_keys - set(keyed))
        extra = sorted(set(keyed) - expected_keys)
        raise PacketError(f"state coverage mismatch; missing={missing}, extra={extra}")
    if len(rows) != spec["expected_state_count"]:
        raise PacketError("state count differs from the locked Request 31 spec")

    required_files = {
        "REQUEST_MANIFEST.json",
        mesh_rel,
        index_rel,
        "README.md",
        "provenance/source_commit.txt",
        "provenance/source_file_hashes.txt",
        "provenance/export_or_replay_commands.txt",
        "provenance/runtime_versions.txt",
        *state_files,
    }
    _check_hashes(packet, _read_sha256sums(packet / sums_rel), required_files)

    tol = spec["history_validation_tolerances"]
    alpha_t = float(case["alpha_T"])
    exponent = float(case["fatigue_p"])
    res_stiff = float(case["res_stiff"])
    max_history_error = 0.0
    transition_count = 0
    for cycle in case["cycles"]:
        previous_row = keyed[(case["case_id"], cycle, 0)]
        if previous_row["state_kind"] != "precycle_committed":
            raise PacketError(f"cycle {cycle} substep 0 must be precycle_committed")
        if not np.isclose(_as_float(previous_row, "load_factor"), 0.0, atol=1e-12, rtol=0):
            raise PacketError(f"cycle {cycle} substep 0 must have load factor 0")
        previous = _load_state(packet / previous_row["state_file"], nnode, nelem, ngp)
        for substep, expected_factor in enumerate(case["load_factors"], start=1):
            row = keyed[(case["case_id"], cycle, substep)]
            if row["state_kind"] != "post_substep_committed":
                raise PacketError(f"{case['case_id']} c{cycle} s{substep} has wrong state_kind")
            if not np.isclose(_as_float(row, "load_factor"), expected_factor, atol=1e-12, rtol=0):
                raise PacketError(f"{case['case_id']} c{cycle} s{substep} has wrong load factor")
            current = _load_state(packet / row["state_file"], nnode, nelem, ngp)
            d_tol = float(tol["damage_bound_tolerance"])
            if np.min(current["d"]) < -d_tol or np.max(current["d"]) > 1 + d_tol:
                raise PacketError(f"damage outside [0,1] for {case['case_id']} c{cycle} s{substep}")
            if np.min(current["d"] - previous["d"]) < -d_tol:
                raise PacketError(
                    f"damage recovery exceeds tolerance for {case['case_id']} c{cycle} s{substep}"
                )
            d_gp = np.einsum("en,ng->eg", current["d"][connectivity0], nxi)
            q_now = ((1.0 - d_gp) ** 2 + res_stiff) * current["psi"]
            old_h = previous["history"]
            expected_h = np.maximum(old_h[:, :, 0], current["psi"])
            expected_alpha = old_h[:, :, 1] + np.maximum(q_now - old_h[:, :, 2], 0.0)
            expected_f = np.minimum(
                1.0,
                (1.0 - ((expected_alpha - alpha_t) / (expected_alpha + alpha_t))) ** exponent,
            )
            expected_history = np.stack((expected_h, expected_alpha, q_now, expected_f), axis=2)
            error = float(np.max(np.abs(current["history"] - expected_history)))
            max_history_error = max(max_history_error, error)
            if not np.allclose(
                current["history"],
                expected_history,
                atol=float(tol["atol"]),
                rtol=float(tol["rtol"]),
            ):
                raise PacketError(
                    f"history update mismatch for {case['case_id']} c{cycle} s{substep}; "
                    f"max_abs_error={error:.6e}"
                )
            previous = current
            transition_count += 1

    if transition_count != spec["expected_transition_count"]:
        raise PacketError("transition count differs from the locked Request 31 spec")
    return {
        "verdict": "PASS_REQUEST31_HARD5_STAGE0B_SCHEMA_AND_HISTORY",
        "request_id": spec["request_id"],
        "state_count": len(rows),
        "transition_count": transition_count,
        "max_history_abs_error": max_history_error,
        "claim_boundary": (
            "Schema/history pass only; independent equilibrium and AT1 phase residual "
            "recomputation remain required before any PINO training."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/experiments/at1_fatigue_mesh_pino_stage0b_hard5_export_spec_v2.json",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.packet.resolve(), args.spec.resolve())
    except PacketError as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
