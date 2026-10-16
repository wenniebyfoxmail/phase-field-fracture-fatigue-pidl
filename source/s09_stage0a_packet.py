"""Fail-closed Stage-0A payload decoding for S09-E008.

This module has no CLI and does not choose or open a scientific archive by
itself.  Callers must supply an already qualified state index and explicit
cycle membership.  Every selected payload is hashed before the first HDF5
file is opened.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from numbers import Integral
from pathlib import Path
import re

import h5py
import numpy as np


SHA256 = re.compile(r"[0-9a-f]{64}")
STATE_KEY = re.compile(r"c(?P<cycle>[0-9]{4})_s(?P<substep>[0-9]{2})")
REQUIRED_DATASETS = {
    "u_node",
    "d_node",
    "history_gp",
    "strain_en_undgr_gp",
    "strain_en_degr_gp",
}


@dataclass(frozen=True)
class DecodedStage0AState:
    logical_cycle: int
    logical_substep: int
    source_state_key: str
    u_node: np.ndarray
    d_node: np.ndarray
    history_gp: np.ndarray
    strain_en_undgr_gp: np.ndarray
    strain_en_degr_gp: np.ndarray
    imposed_displacement: float
    payload_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _integer(row: dict[str, str], name: str) -> int:
    value = int(row[name])
    _require(str(value) == row[name] or row[name] == f"{value:d}",
             f"noncanonical integer {name}")
    return value


def _state_identity(key: str) -> tuple[int, int]:
    match = STATE_KEY.fullmatch(key)
    _require(match is not None, f"invalid state key: {key}")
    return int(match.group("cycle")), int(match.group("substep"))


def index_by_key(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_key = {row["state_key"]: row for row in rows}
    _require(len(by_key) == len(rows), "duplicate state key")
    return by_key


def _payload_path(states_dir: Path, row: dict[str, str]) -> Path:
    relative = Path(row["payload_file"])
    _require(
        relative.parts == ("states", relative.name)
        and relative.name not in ("", ".", ".."),
        f"invalid payload path for {row['state_key']}",
    )
    root = states_dir.resolve(strict=True)
    path = states_dir / relative.name
    _require(not path.is_symlink(), f"payload symlink is forbidden: {relative.name}")
    resolved = path.resolve(strict=True)
    _require(resolved.parent == root, f"payload escapes states directory: {relative.name}")
    return resolved


def transition_rows(
    rows: list[dict[str, str]], cycles: tuple[int, ...] | list[int]
) -> list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]]:
    """Return `(s00, s04, previous_s05)` rows after causal identity checks."""
    _require(
        all(isinstance(cycle, Integral) and not isinstance(cycle, (bool, np.bool_))
            for cycle in cycles),
        "cycles must contain exact integer values",
    )
    selected = tuple(int(cycle) for cycle in cycles)
    _require(selected == tuple(sorted(set(selected))),
             "cycles must be unique and increasing")
    _require(all(1 <= cycle <= 73 for cycle in selected), "cycle out of range")
    by_key = index_by_key(rows)
    result = []
    for cycle in selected:
        pre_key = f"c{cycle:04d}_s00"
        peak_key = f"c{cycle:04d}_s04"
        _require(pre_key in by_key and peak_key in by_key,
                 f"missing Stage-0A rows for cycle {cycle}")
        pre, peak = by_key[pre_key], by_key[peak_key]
        _require(_integer(pre, "cycle") == cycle and _integer(pre, "substep") == 0,
                 f"invalid pre row for cycle {cycle}")
        _require(_integer(peak, "cycle") == cycle and _integer(peak, "substep") == 4,
                 f"invalid peak row for cycle {cycle}")
        _require(pre["timing"] == "pre_cycle_committed",
                 f"invalid pre timing for cycle {cycle}")
        _require(peak["timing"] == "post_history_commit",
                 f"invalid peak timing for cycle {cycle}")
        _require(peak["is_alias"] == "0" and peak["source_state_key"] == peak_key,
                 f"peak row cannot be an alias for cycle {cycle}")
        previous = None
        if cycle == 1:
            _require(pre["is_alias"] == "0" and pre["source_state_key"] == pre_key,
                     "cycle-1 pre row must be native")
        else:
            previous_key = f"c{cycle - 1:04d}_s05"
            _require(previous_key in by_key, f"missing {previous_key}")
            previous = by_key[previous_key]
            _require(
                _integer(previous, "cycle") == cycle - 1
                and _integer(previous, "substep") == 5
                and previous["timing"] == "post_history_commit"
                and previous["is_alias"] == "0"
                and previous["source_state_key"] == previous_key
                and previous["converged"] == "1"
                and SHA256.fullmatch(previous["payload_sha256"]) is not None,
                f"invalid previous s05 row for cycle {cycle}",
            )
            _require(pre["is_alias"] == "1" and
                     pre["source_state_key"] == previous_key and
                     pre["payload_file"] == previous["payload_file"] and
                     pre["payload_sha256"] == previous["payload_sha256"],
                     f"invalid s00 alias for cycle {cycle}")
        for row in (pre, peak):
            _require(SHA256.fullmatch(row["payload_sha256"]) is not None,
                     f"invalid payload hash for {row['state_key']}")
            _require(row["converged"] == "1", f"unconverged {row['state_key']}")
        result.append((pre, peak, previous))
    return result


def preflight_payloads(
    states_dir: Path,
    transitions: list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]],
) -> list[dict[str, object]]:
    """Hash every unique required payload before any scientific decode."""
    rows = [row for pre, peak, _ in transitions for row in (pre, peak)]
    return preflight_rows(states_dir, rows)


def preflight_rows(
    states_dir: Path, rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    """Hash every unique payload represented by `rows` without opening HDF5."""
    expected: dict[Path, str] = {}
    for row in rows:
        path = _payload_path(states_dir, row)
        prior = expected.setdefault(path, row["payload_sha256"])
        _require(prior == row["payload_sha256"],
                 f"conflicting hashes for {path.name}")
    inventory = []
    for path in sorted(expected):
        _require(path.is_file(), f"missing payload: {path.name}")
        observed = sha256_file(path)
        _require(observed == expected[path], f"preflight hash mismatch: {path.name}")
        inventory.append({"file": path.name, "sha256": observed, "bytes": path.stat().st_size})
    return inventory


def _exact_scalar(handle: h5py.File, name: str, expected: float) -> float:
    dataset = handle[name]
    _require(dataset.dtype == np.dtype("float64") and dataset.shape == (1, 1),
             f"invalid scalar storage: {name}")
    value = float(np.asarray(dataset)[0, 0])
    _require(np.isfinite(value) and value == expected, f"scalar mismatch: {name}")
    return value


def _require_matlab_string(handle: h5py.File, name: str) -> None:
    dataset = handle[name]
    value = dataset.attrs.get("MATLAB_class", b"")
    if isinstance(value, bytes):
        value = value.decode("ascii")
    _require(value == "string", f"{name} is not an exact MATLAB string")


def _exact_matlab_logical(handle: h5py.File, name: str, expected: bool) -> bool:
    """Decode the producer's exact MATLAB-v7.3 scalar logical storage."""
    dataset = handle[name]
    matlab_class = dataset.attrs.get("MATLAB_class", b"")
    if isinstance(matlab_class, bytes):
        matlab_class = matlab_class.decode("ascii")
    int_decode = dataset.attrs.get("MATLAB_int_decode", None)
    _require(
        dataset.dtype == np.dtype("uint8")
        and dataset.shape == (1, 1)
        and matlab_class == "logical"
        and int_decode == 1,
        f"invalid MATLAB logical storage: {name}",
    )
    value = int(np.asarray(dataset)[0, 0])
    _require(value in (0, 1) and bool(value) is expected,
             f"logical mismatch: {name}")
    return bool(value)


def _reject_external_hdf5_storage(handle: h5py.File) -> None:
    """Reject links or dataset storage that can read bytes outside the payload."""
    seen: set[int] = set()

    def walk(group: h5py.Group) -> None:
        token = hash(group.id)
        if token in seen:
            return
        seen.add(token)
        for key in group.keys():
            link = group.get(key, getlink=True)
            _require(isinstance(link, h5py.HardLink),
                     f"non-hard HDF5 link is forbidden: {group.name}/{key}")
            value = group[key]
            if isinstance(value, h5py.Group):
                walk(value)
            elif isinstance(value, h5py.Dataset):
                _require(not value.is_virtual,
                         f"virtual HDF5 dataset is forbidden: {value.name}")
                plist = value.id.get_create_plist()
                _require(plist.get_external_count() == 0,
                         f"external raw HDF5 storage is forbidden: {value.name}")
            else:
                raise ValueError(f"unsupported HDF5 object: {group.name}/{key}")

    walk(handle)


def decode_payload(
    path: Path,
    row: dict[str, str],
    *,
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> DecodedStage0AState:
    """Decode one hash-verified native payload without implicit dtype casts."""
    _require(not path.is_symlink(), f"payload symlink is forbidden: {path.name}")
    payload = path.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    _require(observed == row["payload_sha256"],
             f"immediate hash mismatch: {path.name}")
    logical_cycle = _integer(row, "cycle")
    logical_substep = _integer(row, "substep")
    source_cycle, source_substep = _state_identity(row["source_state_key"])
    # HDF5 reads the same immutable byte buffer that produced `observed`.
    with h5py.File(io.BytesIO(payload), "r") as handle:
        _reject_external_hdf5_storage(handle)
        _require(REQUIRED_DATASETS.issubset(handle.keys()),
                 f"required fields missing: {path.name}")
        expected_shapes = {
            "u_node": (2, expected_nodes),
            "d_node": (1, expected_nodes),
            "history_gp": (4, expected_gp, expected_elements),
            "strain_en_undgr_gp": (expected_gp, expected_elements),
            "strain_en_degr_gp": (expected_gp, expected_elements),
        }
        for name, shape in expected_shapes.items():
            dataset = handle[name]
            _require(dataset.dtype == np.dtype("float64"),
                     f"{name} must be stored float64")
            _require(dataset.shape == shape, f"native shape mismatch: {name}")
        _exact_scalar(handle, "state_metadata/cycle", float(source_cycle))
        _exact_scalar(handle, "state_metadata/substep", float(source_substep))
        imposed = _exact_scalar(
            handle, "state_metadata/imposed_displacement", float(row["imposed_displacement"])
        )
        _exact_matlab_logical(
            handle, "state_metadata/producer_metadata/converged", True
        )
        _require_matlab_string(handle, "state_metadata/state_key")
        _require_matlab_string(handle, "state_metadata/timing")
        _require_matlab_string(handle, "state_metadata/history_channel_labels")
        # Exact string contents are fixed by the matched source commit. MATLAB
        # v7.3 stores string objects through its opaque MCOS subsystem; row and
        # source identities therefore provide the inspectable timing/label lock.
        _require(source_substep in range(6), "source substep outside frozen path")
        u = np.asarray(handle["u_node"]).T
        d = np.asarray(handle["d_node"]).reshape(-1)
        history = np.asarray(handle["history_gp"]).transpose(2, 1, 0)
        undgr = np.asarray(handle["strain_en_undgr_gp"]).T
        degr = np.asarray(handle["strain_en_degr_gp"]).T
    for name, value in (("u_node", u), ("d_node", d), ("history_gp", history),
                        ("strain_en_undgr_gp", undgr), ("strain_en_degr_gp", degr)):
        _require(value.dtype == np.float64 and np.isfinite(value).all(),
                 f"invalid decoded values: {name}")
    _require(np.all((d >= 0) & (d <= 1)), "damage outside [0,1]")
    return DecodedStage0AState(
        logical_cycle=logical_cycle,
        logical_substep=logical_substep,
        source_state_key=row["source_state_key"],
        u_node=u,
        d_node=d,
        history_gp=history,
        strain_en_undgr_gp=undgr,
        strain_en_degr_gp=degr,
        imposed_displacement=imposed,
        payload_sha256=observed,
    )


def decode_stage0a_transitions(
    *,
    states_dir: Path,
    rows: list[dict[str, str]],
    cycles: tuple[int, ...] | list[int],
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> tuple[list[tuple[DecodedStage0AState, DecodedStage0AState]], dict[str, object]]:
    """Preflight then decode explicit s00-to-s04 transitions."""
    pairs = transition_rows(rows, cycles)
    inventory = preflight_payloads(states_dir, pairs)
    decoded = []
    alias_checks = []
    for pre_row, peak_row, previous_row in pairs:
        pre_path = _payload_path(states_dir, pre_row)
        peak_path = _payload_path(states_dir, peak_row)
        kwargs = dict(expected_nodes=expected_nodes, expected_elements=expected_elements,
                      expected_gp=expected_gp)
        pre = decode_payload(pre_path, pre_row, **kwargs)
        peak = decode_payload(peak_path, peak_row, **kwargs)
        if previous_row is not None:
            previous = decode_payload(pre_path, previous_row, **kwargs)
            equal = (np.array_equal(pre.u_node, previous.u_node) and
                     np.array_equal(pre.d_node, previous.d_node) and
                     np.array_equal(pre.history_gp, previous.history_gp) and
                     np.array_equal(pre.strain_en_undgr_gp, previous.strain_en_undgr_gp) and
                     np.array_equal(pre.strain_en_degr_gp, previous.strain_en_degr_gp))
            _require(equal, f"numerical s05-to-s00 alias mismatch at cycle {pre.logical_cycle}")
            alias_checks.append(pre.logical_cycle)
        decoded.append((pre, peak))
    receipt = {
        "preflight_completed_before_decode": True,
        "payload_inventory": inventory,
        "decoded_cycles": [pre.logical_cycle for pre, _ in decoded],
        "numerical_s05_to_s00_alias_cycles": alias_checks,
        "history_channel_order": ["H", "alpha_bar", "q_prev", "f"],
    }
    return decoded, receipt
